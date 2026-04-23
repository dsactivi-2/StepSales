"""
LangGraph Conversation Orchestrator with Barge-In Support
Replaces heuristic keyword-matching with a real LangGraph state machine
for the German AI sales conversation.

Barge-In Architecture:
- Deepgram STT hört durchgehend zu (auch während TTS spricht)
- TTS läuft als cancellable asyncio Task
- Bei speech_final während TTS → TTS wird abgebrochen, neue Antwort generiert
- Paralleler Audio-Stream: STT → LLM → TTS → Telnyx

Graph Structure:
  greet → discovery → qualify → offer → objection → close → followup → summary
            ↑              ↓              ↓              ↓
            └── retry ─────┘              └── escalate ──┘
"""

import asyncio
import base64
import logging
import time
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config.settings import AppConfig
from services.deepgram_stt import DeepgramSTT
from services.elevenlabs_tts import ElevenLabsTTS
from services.telnyx_gateway import TelnyxGateway
from services.stripe_billing import StripeBilling
from services.persistence import PersistenceService
from services.lead_intel import LeadIntelService

logger = logging.getLogger("stepsales.orchestrator_langgraph")

# ─── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
Du bist Alex, ein erfahrener Telesales-Closer von Step2Job aus Berlin.
Du rufst aktiv Firmen in Deutschland an und verkaufst Multiposting-Stellenanzeigen auf StepStone und Indeed.

VERHALTENSRICHTLINIEN:
1. Sprich naturlich, freundlich, pragmatisch, mit kurzen Satzen.
2. Klangbild: warm, klar, ruhig, professionell, ohne Callcenter-Kunstlichkeit.
3. Kein roboterhafter Stil, keine monotone Wiederholung.
4. Nutze aktive Zuhortechniken: bestatigen, spiegeln, gezielt ruckfragen.
5. Fokussiere auf den Nutzen: Time-to-Hire, relevante Bewerbungen, weniger Leerlauf.
6. Spreche Preise selbstbewusst und transparent an.
7. Sprechtempo ca. 140-160 Worter/min, kurze Pausen an Satzgrenzen.
8. Einwandbehandlung: empathisch starten, faktenbasiert losen, konkret abschlieen.

ZIEL:
- Primar: direkter Abschluss im Erstgesprach fur Multiposting auf StepStone/Indeed.
- Sekundar: verbindlicher Termin mit Entscheider in 48 Stunden.

SALES-VERHALTEN:
- Kontext: Du weisst, dass die Firma aktiv Mitarbeitende sucht (Arbeitsmarktseiten).
- Erwahne zu Beginn den Outbound-Kontext: offene Suche nach Mitarbeitenden gesehen.
- Fuehre das Gesprach: Einstieg -> Bedarf -> Qualifizierung -> Angebot -> Einwandbehandlung -> Abschluss.
- Closer-Modus: Jede Antwort auf Abschlusschance prufen und aktiv zum Commit fuhren.
- Micro-Closings: Zustimmung zu Bedarf, Budgetrahmen, Startzeitpunkt, nachster Schritt.
- Wenn Kunde zogert: maximal 1 Kernargument + 1 konkrete Handlungsoption.
- Nie mehr als 2 Preiszahlen in einem Satz.

PITCH-RAHMEN:
- Step2Job aus Berlin als operativer Recruiting-Vertriebspartner fur StepStone und Indeed.
- Value Proof: bessere Sichtbarkeit, schnellere Rucklaufe, planbarer Bewerbereingang.
- Angebot: Multiposting-Paket statt Einzelanzeige.
- Call-to-Action: immer konkreter nachster Schritt (Auftrag jetzt oder fester Termin).

Heute: {current_date}
"""

# ─── Graph State ─────────────────────────────────────────────────────────────────

class ConversationState(BaseModel):
    """LangGraph state for the sales conversation."""

    thread_id: str = Field(default_factory=lambda: f"thread-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    lead_id: Optional[str] = None
    phone_number: Optional[str] = None
    telnyx_call_id: Optional[str] = None

    messages: List[Dict[str, str]] = Field(default_factory=list)
    user_input: str = ""
    agent_response: str = ""

    stage: str = "greet"
    turn_count: int = 0
    max_turns: int = 40

    objections: List[str] = Field(default_factory=list)
    contact_info: Dict[str, str] = Field(default_factory=dict)
    qualification_score: int = 0

    customer_memory: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: str = ""
    transcript: List[Dict[str, str]] = Field(default_factory=list)

    error: Optional[str] = None
    should_end: bool = False

# ─── Node Functions ──────────────────────────────────────────────────────────────

def _build_system_prompt(state: ConversationState, config: AppConfig) -> str:
    prompt = SYSTEM_PROMPT.format(current_date=datetime.utcnow().strftime("%d.%m.%Y"))

    stage_context = {
        "greet": "Du bist am Anfang des Gesprachs. Begruisse den Ansprechpartner professionell und erwahne, dass du gesehen hast, dass sie Mitarbeitende suchen.",
        "discovery": "Frage nach dem aktuellen Hiring-Bedarf: welche Rollen, wie viele Personen, wie lange schon offen.",
        "qualify": "Qualifiziere den Lead: Budget vorhanden? Entscheidungstrager erreichbar? Timeline dringend?",
        "offer": "Praesentiere das Multiposting-Angebot: StepStone + Indeed Kombi, konkrete Pakete und Preise.",
        "objection": "Der Kunde hat einen Einwand (Preis, Zeit, Zweifel). Gehe empathisch darauf ein, biete eine konkrete Losung.",
        "close": "Versuche den Abschluss: direkter Auftrag oder fester Termin in 48 Stunden.",
        "followup": "Der Kunde ist nicht bereit. Vereinbare ein Follow-up und hinterlasse professionellen Eindruck.",
        "summary": "Zusammenfassung des Gesprachs, Verabschiedung, nachster Schritt bestatigen.",
    }

    context = stage_context.get(state.stage, "")
    if context:
        prompt += f"\n\nAKTUELLE PHASE: {context}"

    if state.customer_memory:
        memory_lines = [f"- [{m.get('type', 'note')}] {m.get('content', '')}" for m in state.customer_memory[:5]]
        prompt += f"\n\nKUNDENKONTEXT (fruehere Gespraeche):\n" + "\n".join(memory_lines)

    if state.contact_info:
        contact_str = ", ".join(f"{k}: {v}" for k, v in state.contact_info.items())
        prompt += f"\n\nKONTAKTDATEN: {contact_str}"

    prompt += f"\nTALK COUNT: {state.turn_count}/{state.max_turns}"

    return prompt


def node_greet(state: ConversationState, config: AppConfig) -> dict:
    """Initial greeting node."""
    system_prompt = _build_system_prompt(state, config)
    llm = ChatOpenAI(
        model=config.openai.model,
        temperature=config.openai.temperature,
        max_tokens=config.openai.max_tokens,
        api_key=config.openai.api_key,
    )

    messages = [SystemMessage(content=system_prompt)]
    messages.append(HumanMessage(content="Beginne das Gesprach mit einer professionellen Begruung."))

    response = llm.invoke(messages)
    greeting = response.content.strip()

    logger.info(f"[GREET] {greeting}")

    return {
        "agent_response": greeting,
        "messages": [{"role": "assistant", "content": greeting}],
        "stage": "discovery",
        "turn_count": state.turn_count + 1,
        "transcript": [{"role": "agent", "text": greeting, "stage": "greet"}],
    }


def node_discovery(state: ConversationState, config: AppConfig) -> dict:
    """Discovery: ask about hiring needs."""
    return _run_llm_turn(state, config, "discovery")


def node_qualify(state: ConversationState, config: AppConfig) -> dict:
    """Qualify: budget, timeline, decision maker."""
    return _run_llm_turn(state, config, "qualify")


def node_offer(state: ConversationState, config: AppConfig) -> dict:
    """Present the multiposting offer."""
    return _run_llm_turn(state, config, "offer")


def node_objection(state: ConversationState, config: AppConfig) -> dict:
    """Handle objections empathetically."""
    result = _run_llm_turn(state, config, "objection")
    if state.user_input:
        lower = state.user_input.lower()
        if any(w in lower for w in ["zu teuer", "preis", "kosten", "budget"]):
            result["objections"] = state.objections + ["price"]
        elif any(w in lower for w in ["kein bedarf", "kein interesse"]):
            result["objections"] = state.objections + ["no_interest"]
        elif any(w in lower for w in ["nachdenken", "spater", "melden"]):
            result["objections"] = state.objections + ["delay"]
    return result


def node_close(state: ConversationState, config: AppConfig) -> dict:
    """Attempt to close the deal."""
    return _run_llm_turn(state, config, "close")


def node_followup(state: ConversationState, config: AppConfig) -> dict:
    """Schedule follow-up when not ready to close."""
    return _run_llm_turn(state, config, "followup")


def node_summary(state: ConversationState, config: AppConfig) -> dict:
    """Summarize and end the call."""
    return _run_llm_turn(state, config, "summary")


def _run_llm_turn(state: ConversationState, config: AppConfig, stage: str) -> dict:
    """Generic LLM turn execution."""
    system_prompt = _build_system_prompt(state, config)
    llm = ChatOpenAI(
        model=config.openai.model,
        temperature=config.openai.temperature,
        max_tokens=config.openai.max_tokens,
        api_key=config.openai.api_key,
    )

    messages = [SystemMessage(content=system_prompt)]
    for msg in state.messages[-12:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    if state.user_input:
        messages.append(HumanMessage(content=state.user_input))

    try:
        response = llm.invoke(messages)
        reply = response.content.strip()
    except Exception as e:
        logger.error(f"LLM failed: {e}")
        reply = "Entschuldigung, da war ein technisches Problem. Konnen Sie das bitte wiederholen?"

    logger.info(f"[{stage.upper()}] User: {state.user_input[:50]}... | Agent: {reply[:80]}...")

    new_messages = state.messages + [
        {"role": "user", "content": state.user_input},
        {"role": "assistant", "content": reply},
    ]

    new_transcript = state.transcript + [
        {"role": "user", "text": state.user_input, "stage": stage},
        {"role": "agent", "text": reply, "stage": stage},
    ]

    return {
        "agent_response": reply,
        "messages": new_messages,
        "turn_count": state.turn_count + 1,
        "transcript": new_transcript,
        "stage": stage,
    }


def route_next_state(state: ConversationState) -> Literal["discovery", "qualify", "offer", "objection", "close", "followup", "summary", "end"]:
    """LangGraph conditional edge router."""

    if state.turn_count >= state.max_turns:
        return "summary"

    if state.should_end:
        return "end"

    if state.error:
        return "summary"

    text = state.user_input.lower()

    if any(w in text for w in ["auf wiedersehen", "tschuss", "bye", "ende"]):
        return "summary"

    if any(w in text for w in ["kein bedarf", "kein interesse", "nicht mehr anrufen", "stop"]):
        return "followup"

    if any(w in text for w in ["zu teuer", "preis", "kosten", "budget", "leisten"]):
        return "objection"

    if any(w in text for w in ["ja", "gerne", "okay", "einverstanden", "machen wir", "deal", "passt"]):
        if state.stage in ["offer", "qualify", "objection"]:
            return "close"
        return "qualify"

    if any(w in text for w in ["woche", "monat", "sofort", "dringend", "brauchen"]):
        return "offer"

    if state.stage == "greet":
        return "discovery"

    if state.stage == "discovery":
        if any(w in text for w in ["budget", "zahlen", "kosten", "preis"]):
            return "offer"
        return "qualify"

    if state.stage == "qualify":
        if state.qualification_score >= 60:
            return "offer"
        return "qualify"

    if state.stage == "offer":
        if any(w in text for w in ["einwand", "aber", "problem", "schwierig"]):
            return "objection"
        return "close"

    if state.stage == "objection":
        if any(w in text for w in ["okay", "einverstanden", "gut", "passt"]):
            return "close"
        return "objection"

    if state.stage == "close":
        return "summary"

    if state.stage == "followup":
        return "summary"

    return state.stage


# ─── Graph Builder ───────────────────────────────────────────────────────────────

def build_conversation_graph(config: AppConfig):
    """Build and compile the LangGraph conversation state machine."""

    workflow = StateGraph(ConversationState)

    workflow.add_node("greet", lambda s: node_greet(s, config))
    workflow.add_node("discovery", lambda s: node_discovery(s, config))
    workflow.add_node("qualify", lambda s: node_qualify(s, config))
    workflow.add_node("offer", lambda s: node_offer(s, config))
    workflow.add_node("objection", lambda s: node_objection(s, config))
    workflow.add_node("close", lambda s: node_close(s, config))
    workflow.add_node("followup", lambda s: node_followup(s, config))
    workflow.add_node("summary", lambda s: node_summary(s, config))

    workflow.set_entry_point("greet")

    workflow.add_conditional_edges(
        "greet", route_next_state,
        {
            "discovery": "discovery",
            "qualify": "qualify",
            "offer": "offer",
            "objection": "objection",
            "close": "close",
            "followup": "followup",
            "summary": "summary",
            "end": END,
        }
    )

    for node in ["discovery", "qualify", "offer", "objection", "close", "followup"]:
        workflow.add_conditional_edges(
            node, route_next_state,
            {
                "discovery": "discovery",
                "qualify": "qualify",
                "offer": "offer",
                "objection": "objection",
                "close": "close",
                "followup": "followup",
                "summary": "summary",
                "end": END,
            }
        )

    workflow.add_edge("summary", END)

    checkpointer = MemorySaver()
    graph = workflow.compile(checkpointer=checkpointer)

    logger.info("LangGraph conversation graph compiled successfully")
    return graph


# ─── Orchestrator Class ──────────────────────────────────────────────────────────

class LangGraphOrchestrator:
    """LangGraph-based conversation orchestrator with Barge-In support.

    Barge-In Architecture:
    - Deepgram STT hört durchgehend zu (auch während TTS spricht)
    - TTS läuft als cancellable asyncio Task mit asyncio.Event
    - Bei speech_final während TTS → TTS wird abgebrochen
    - Neue Antwort wird sofort generiert und gesprochen
    """

    def __init__(self, config=None):
        self.config = config or AppConfig
        self.graph = build_conversation_graph(self.config)
        self.telnyx = TelnyxGateway(self.config)
        self.stt = DeepgramSTT(self.config)
        self.tts = ElevenLabsTTS(self.config)
        self.billing = StripeBilling(self.config)
        self.persistence = PersistenceService(self.config)
        self.lead_intel = LeadIntelService(self.config)
        self._active_calls: Dict[str, dict] = {}
        self._tts_cancel_events: Dict[str, asyncio.Event] = {}
        self._current_tts_task: Optional[asyncio.Task] = None
        self._latest_user_input: Dict[str, str] = {}

    async def initialize(self):
        await self.persistence.initialize()
        self.telnyx.register_event_handler(self._on_telnyx_event)
        self.stt.register_transcript_handler(self._on_transcript)
        self.stt.register_end_of_turn_handler(self._on_end_of_turn)
        self.tts.register_audio_handler(self._on_audio_chunk)
        self.tts.register_complete_handler(self._on_tts_complete)
        await self.stt.connect()
        logger.info("LangGraph Orchestrator initialized with Barge-In support")

    async def start_outbound_call(self, phone_number: str, lead_id: str = None, context: dict = None):
        thread_id = f"call-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        memory = []
        if lead_id:
            try:
                memory = await self.persistence.get_customer_memory(lead_id)
            except Exception:
                pass

        state = ConversationState(
            thread_id=thread_id,
            lead_id=lead_id,
            phone_number=phone_number,
            customer_memory=memory,
            started_at=datetime.utcnow().isoformat(),
        )

        self._active_calls[thread_id] = {"state": state, "context": context or {}}
        self._tts_cancel_events[thread_id] = asyncio.Event()

        call_result = await self.telnyx.initiate_outbound_call(
            to_number=phone_number,
            metadata={"lead_id": lead_id, "thread_id": thread_id},
        )

        if call_result.get("success"):
            state.telnyx_call_id = call_result.get("call_id")

        config = {"configurable": {"thread_id": thread_id}}

        async for event in self.graph.astream(state, config, stream_mode="values"):
            stage = event.get("stage", "unknown")
            response = event.get("agent_response", "")
            if response:
                await self._speak_barge_in(response, state, thread_id)

            if event.get("should_end") or stage == "summary":
                break

        await self._cancel_tts(thread_id)
        await self._finalize_call(state)
        return state

    async def _cancel_tts(self, thread_id: str):
        """Cancel any running TTS task for this call."""
        cancel_event = self._tts_cancel_events.get(thread_id)
        if cancel_event:
            cancel_event.set()

        if self._current_tts_task and not self._current_tts_task.done():
            self._current_tts_task.cancel()
            try:
                await self._current_tts_task
            except asyncio.CancelledError:
                pass
            logger.info(f"TTS cancelled for {thread_id}")

    async def _speak_barge_in(self, text: str, state: ConversationState, thread_id: str):
        """Speak text with Barge-In support.

        Starts TTS as a cancellable task. If user speaks during TTS,
        the task is cancelled and the new user input is processed.
        """
        cancel_event = self._tts_cancel_events.get(thread_id)
        if not cancel_event:
            return

        cancel_event.clear()

        try:
            audio = await self.tts.synthesize(text)
            if not audio or not state.telnyx_call_id:
                return

            audio_b64 = base64.b64encode(audio).decode("utf-8")
            send_task = asyncio.create_task(
                self.telnyx.send_audio(state.telnyx_call_id, audio_b64)
            )
            self._current_tts_task = send_task

            done, pending = await asyncio.wait(
                [send_task, asyncio.create_task(cancel_event.wait())],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if cancel_event.is_set():
                for task in pending:
                    task.cancel()
                logger.info(f"Barge-In: TTS interrupted for {thread_id}")
                return

            logger.info(f"TTS audio sent for {thread_id} ({len(audio)} bytes)")

        except asyncio.CancelledError:
            logger.info(f"TTS cancelled for {thread_id}")
        except Exception as e:
            logger.error(f"TTS failed: {e}")

    async def _on_telnyx_event(self, event_type: str, data: dict):
        if event_type == "call.connected":
            pass
        elif event_type == "call.completed":
            pass

    async def _on_transcript(self, data: dict):
        """Store interim transcript but don't trigger barge-in yet."""
        thread_id = self._get_active_thread()
        if thread_id:
            self._latest_user_input[thread_id] = data.get("text", "")

    async def _on_end_of_turn(self, data: dict):
        """Barge-In trigger: User finished speaking during TTS.

        Cancel running TTS and update state with user input.
        """
        thread_id = self._get_active_thread()
        if not thread_id:
            return

        text = data.get("text", "").strip()
        if not text:
            return

        logger.info(f"Barge-In: User said '{text[:50]}...' during TTS")

        self._latest_user_input[thread_id] = text

        await self._cancel_tts(thread_id)

        state_data = self._active_calls.get(thread_id, {}).get("state")
        if state_data:
            state_data.user_input = text
            if text.lower() in ["auf wiedersehen", "tschuss", "bye"]:
                state_data.should_end = True

    async def _on_audio_chunk(self, chunk: bytes, is_final: bool):
        pass

    async def _on_tts_complete(self, data: dict):
        pass

    def _get_active_thread(self) -> Optional[str]:
        """Get the currently active thread ID."""
        if self._active_calls:
            return list(self._active_calls.keys())[-1]
        return None

    async def _finalize_call(self, state: ConversationState):
        duration = 0
        try:
            start = datetime.fromisoformat(state.started_at)
            duration = int((datetime.utcnow() - start).total_seconds())
        except Exception:
            pass

        call_data = {
            "lead_id": state.lead_id,
            "session_id": state.thread_id,
            "telnyx_call_id": state.telnyx_call_id,
            "stage": state.stage,
            "duration_seconds": duration,
            "transcript": state.transcript,
            "objections": state.objections,
            "status": "completed",
        }

        try:
            await self.persistence.save_call(call_data)
        except Exception as e:
            logger.error(f"Failed to save call: {e}")

        self._active_calls.pop(state.thread_id, None)
        self._tts_cancel_events.pop(state.thread_id, None)
        logger.info(f"Call finalized: {state.thread_id} ({duration}s, stage={state.stage})")

    async def create_invoice_for_lead(self, lead_id, customer_email, customer_name, customer_company, items, description=""):
        result = await self.billing.create_and_send_invoice(
            customer_email=customer_email,
            customer_name=customer_name,
            customer_company=customer_company,
            items=items,
            description=description,
        )
        if result.get("success"):
            try:
                await self.persistence.save_invoice_record({
                    "lead_id": lead_id,
                    "stripe_invoice_id": result.get("invoice_id"),
                    "amount_cents": result.get("amount_due", 0),
                    "status": result.get("status", "sent"),
                    "description": description,
                    "items": items,
                    "hosted_invoice_url": result.get("hosted_invoice_url"),
                })
            except Exception:
                pass
        return result

    async def close(self):
        for thread_id in list(self._tts_cancel_events.keys()):
            await self._cancel_tts(thread_id)
        await self.telnyx.close()
        await self.stt.disconnect()
        await self.tts.close()
        await self.billing.close()
        await self.lead_intel.close()
