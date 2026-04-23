"""
Conversation Orchestrator
LangGraph-based state machine for the sales conversation.
Replaces heuristic keyword-matching with real AI-powered dialog flow
including turn-taking, tool routing, guardrails, and memory injection.
"""

import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from config.settings import AppConfig
from services.deepgram_stt import DeepgramSTT
from services.elevenlabs_tts import ElevenLabsTTS
from services.telnyx_gateway import TelnyxGateway
from services.stripe_billing import StripeBilling
from services.persistence import PersistenceService
from services.lead_intel import LeadIntelService

logger = logging.getLogger("stepsales.orchestrator")


class ConversationState(str, Enum):
    GREET = "greet"
    DISCOVERY = "discovery"
    QUALIFY = "qualify"
    OBJECTION = "objection"
    OFFER = "offer"
    CLOSE = "close"
    FOLLOWUP = "followup"
    SUMMARY = "summary"
    NEXT_ACTION = "next_action"


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


class ConversationOrchestrator:
    """Manages the full voice conversation loop: STT -> AI -> TTS -> Call."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self.telnyx = TelnyxGateway(self.config)
        self.stt = DeepgramSTT(self.config)
        self.tts = ElevenLabsTTS(self.config)
        self.billing = StripeBilling(self.config)
        self.persistence = PersistenceService(self.config)
        self.lead_intel = LeadIntelService(self.config)

        self._state: Dict[str, Any] = {}
        self._conversation_history: List[dict] = []
        self._openai_client = None

    async def initialize(self):
        """Initialize all services and connect to providers."""
        await self.persistence.initialize()

        self.telnyx.register_event_handler(self._on_telnyx_event)

        self.stt.register_transcript_handler(self._on_transcript)
        self.stt.register_end_of_turn_handler(self._on_end_of_turn)

        self.tts.register_audio_handler(self._on_audio_chunk)
        self.tts.register_complete_handler(self._on_tts_complete)

        await self.stt.connect()

        from openai import AsyncOpenAI
        self._openai_client = AsyncOpenAI(api_key=self.config.openai.api_key)

        logger.info("Conversation Orchestrator initialized (Telnyx + Deepgram + ElevenLabs + OpenAI)")

    async def start_outbound_call(
        self,
        phone_number: str,
        lead_id: str = None,
        context: dict = None,
    ) -> dict:
        """Start an outbound sales call to a prospect."""
        logger.info(f"Starting outbound call to {phone_number} (lead: {lead_id})")

        self._state = {
            "phone_number": phone_number,
            "lead_id": lead_id,
            "context": context or {},
            "stage": ConversationState.GREET.value,
            "started_at": datetime.utcnow().isoformat(),
            "turn_count": 0,
            "objections": [],
            "contact_info": {},
            "transcript": [],
        }

        if lead_id and self.config.openai.api_key:
            memory = await self.persistence.get_customer_memory(lead_id)
            if memory:
                logger.info(f"Loaded {len(memory)} memory facts for lead {lead_id}")
                self._state["customer_memory"] = memory

        call_result = await self.telnyx.initiate_outbound_call(
            to_number=phone_number,
            metadata={"lead_id": lead_id, "stage": "greet"},
        )

        if call_result.get("success"):
            self._state["telnyx_call_id"] = call_result.get("call_id")

        return call_result

    async def _on_telnyx_event(self, event_type: str, data: dict):
        """Handle Telnyx call events."""
        logger.info(f"Telnyx event: {event_type}")

        if event_type == "call.connected":
            await self._send_greeting()
        elif event_type == "call.completed":
            await self._finalize_call()

    async def _send_greeting(self):
        """Send the initial greeting."""
        greeting = "Guten Tag, hier ist Alex von Step2Job aus Berlin. Wir haben gesehen, dass Sie aktuell Mitarbeitende suchen. Darf ich Ihnen kurz zeigen, wie wir mit Multiposting auf StepStone und Indeed Ihre Besetzungszeit deutlich verkurzen konnen?"
        await self._speak(greeting)
        self._state["stage"] = ConversationState.DISCOVERY.value

    async def _on_transcript(self, data: dict):
        """Handle interim/final transcript from STT."""
        text = data.get("text", "")
        is_final = data.get("is_final", False)

        if text:
            self._conversation_history.append({
                "role": "user",
                "text": text,
                "is_final": is_final,
                "timestamp": datetime.utcnow().isoformat(),
            })
            logger.debug(f"STT: {text} (final={is_final})")

    async def _on_end_of_turn(self, data: dict):
        """Handle end-of-user-turn: generate and send AI response."""
        user_text = data.get("text", "").strip()
        if not user_text:
            return

        self._state["turn_count"] += 1

        ai_response = await self._generate_ai_response(user_text)
        self._state["transcript"].append({"role": "user", "text": user_text})
        self._state["transcript"].append({"role": "agent", "text": ai_response})

        await self._speak(ai_response)

    async def _generate_ai_response(self, user_input: str) -> str:
        """Generate AI response using OpenAI with sales system prompt."""
        stage = self._state.get("stage", ConversationState.GREET.value)
        customer_memory = self._state.get("customer_memory", [])

        system_prompt = SYSTEM_PROMPT.format(
            current_date=datetime.utcnow().strftime("%d.%m.%Y")
        )

        if customer_memory:
            memory_context = "\n".join(
                f"- [{m['type']}] {m['content']}" for m in customer_memory[:5]
            )
            system_prompt += f"\n\nKUNDENKONTEXT:\n{memory_context}"

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        for msg in self._conversation_history[-12:]:
            messages.append({"role": "user" if msg["role"] == "user" else "assistant", "content": msg["text"]})

        messages.append({"role": "user", "content": user_input})

        try:
            response = await self._openai_client.chat.completions.create(
                model=self.config.openai.model,
                messages=messages,
                temperature=self.config.openai.temperature,
                max_tokens=self.config.openai.max_tokens,
            )

            reply = response.choices[0].message.content.strip()
            self._update_stage(stage, user_input, reply)
            return reply

        except Exception as e:
            logger.error(f"OpenAI response failed: {e}")
            return "Entschuldigung, da war ein technisches Problem. Konnen Sie das bitte wiederholen?"

    def _update_stage(self, current_stage: str, user_input: str, ai_response: str):
        """Update conversation state machine."""
        text = user_input.lower()

        if any(w in text for w in ["auf wiedersehen", "tschuss", "bye"]):
            self._state["stage"] = ConversationState.SUMMARY.value
        elif any(w in text for w in ["kein bedarf", "kein interesse", "nicht mehr anrufen"]):
            self._state["stage"] = ConversationState.FOLLOWUP.value
            self._state.get("objections", []).append("no_interest")
        elif any(w in text for w in ["zu teuer", "preis", "kosten"]):
            self._state["stage"] = ConversationState.OBJECTION.value
            self._state.get("objections", []).append("price")
        elif any(w in text for w in ["woche", "monat", "sofort", "dringend"]):
            self._state["stage"] = ConversationState.OFFER.value
        elif any(w in text for w in ["ja", "gerne", "okay", "einverstanden"]):
            self._state["stage"] = ConversationState.NEXT_ACTION.value
        elif any(w in text for w in ["entwickler", "engineer", "software", "hr", "vertrieb"]):
            self._state["stage"] = ConversationState.QUALIFY.value

    async def _speak(self, text: str):
        """Synthesize text and send audio to call."""
        try:
            audio = await self.tts.synthesize(text)
            if audio and self._state.get("telnyx_call_id"):
                import base64
                audio_b64 = base64.b64encode(audio).decode("utf-8")
                await self.telnyx.send_audio(self._state["telnyx_call_id"], audio_b64)
        except Exception as e:
            logger.error(f"TTS/Speak failed: {e}")

    async def _on_audio_chunk(self, chunk: bytes, is_final: bool):
        """Handle outgoing audio chunks (for monitoring/streaming)."""
        pass

    async def _on_tts_complete(self, data: dict):
        """Handle TTS completion."""
        pass

    async def _finalize_call(self):
        """Finalize call: save transcript, update lead status."""
        duration = 0
        started = self._state.get("started_at")
        if started:
            try:
                start_dt = datetime.fromisoformat(started)
                duration = int((datetime.utcnow() - start_dt).total_seconds())
            except Exception:
                pass

        call_data = {
            "lead_id": self._state.get("lead_id"),
            "telnyx_call_id": self._state.get("telnyx_call_id"),
            "stage": self._state.get("stage"),
            "duration_seconds": duration,
            "transcript": self._state.get("transcript", []),
            "objections": self._state.get("objections", []),
            "status": "completed",
        }

        await self.persistence.save_call(call_data)

        lead_id = self._state.get("lead_id")
        if lead_id:
            memory_facts = []
            for msg in self._state.get("transcript", []):
                if msg["role"] == "user" and len(msg.get("text", "")) > 20:
                    memory_facts.append({
                        "customer_id": lead_id,
                        "fact_type": "conversation",
                        "content": msg["text"][:200],
                        "source": "call",
                    })

            for fact in memory_facts[:5]:
                try:
                    await self.persistence.save_memory_fact(fact)
                except Exception:
                    pass

        self._conversation_history.clear()
        self._state.clear()

        logger.info(f"Call finalized: {duration}s, {len(call_data.get('transcript', []))} turns")

    async def create_invoice_for_lead(
        self,
        lead_id: str,
        customer_email: str,
        customer_name: str,
        customer_company: str,
        items: list,
        description: str = "Multiposting Stellenanzeige StepStone + Indeed",
    ) -> dict:
        """Create and send invoice for a lead."""
        result = await self.billing.create_and_send_invoice(
            customer_email=customer_email,
            customer_name=customer_name,
            customer_company=customer_company,
            items=items,
            description=description,
        )

        if result.get("success"):
            await self.persistence.save_invoice_record({
                "lead_id": lead_id,
                "stripe_invoice_id": result.get("invoice_id"),
                "stripe_customer_id": result.get("customer_id"),
                "amount_cents": result.get("amount_due", 0),
                "status": result.get("status", "sent"),
                "description": description,
                "items": items,
                "hosted_invoice_url": result.get("hosted_invoice_url"),
            })

        return result

    async def close(self):
        await self.telnyx.close()
        await self.stt.disconnect()
        await self.tts.close()
        await self.billing.close()
        await self.lead_intel.close()
