"""
Telnyx AI Assistant Service
Uses Telnyx's native AI Assistant feature for voice conversations.
Instead of building a custom STT→LLM→TTS pipeline, Telnyx handles
the entire voice conversation natively with built-in VAD, STT, LLM, and TTS.

Flow:
1. Initiate outbound call via Call Control API
2. Call connects → Webhook received
3. Start AI Assistant with custom prompt (German sales closer)
4. Telnyx handles: VAD → STT → OpenAI LLM → TTS → Audio back to caller
5. Monitor conversation via webhooks (ai_assistant.* events)
6. Stop AI Assistant and hangup when done

Benefits:
- Zero latency (Telnyx handles audio directly)
- Built-in VAD, barge-in, noise cancellation
- No Deepgram/ElevenLabs needed for outbound calls
- Natural conversation flow
"""

import asyncio
import json
import logging
import time
from typing import Callable, Dict, Optional

import httpx

from config.settings import AppConfig

logger = logging.getLogger("stepsales.telnyx_ai_assistant")

# German sales closer system prompt
SALES_ASSISTANT_PROMPT = """Du bist Alex, ein erfahrener Telesales-Closer von Step2Job aus Berlin.
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

PITCH-RAHMEN:
- Step2Job aus Berlin als operativer Recruiting-Vertriebspartner fur StepStone und Indeed.
- Value Proof: bessere Sichtbarkeit, schnellere Rucklaufe, planbarer Bewerbereingang.
- Pakete: Basic 499 EUR (2 Anzeigen), Premium 799 EUR (4 Anzeigen), Enterprise 1.299 EUR (8 Anzeigen).
- Call-to-Action: immer konkreter nachster Schritt (Auftrag jetzt oder fester Termin)."""


class TelnyxAIAssistant:
    """Telnyx native AI Assistant for voice conversations."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._client = httpx.AsyncClient(
            base_url=self.config.telnyx.api_base,
            headers={
                "Authorization": f"Bearer {self.config.telnyx.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self._call_registry: Dict[str, dict] = {}
        self._on_event: Optional[Callable] = None
        self._active_ai_calls: Dict[str, dict] = {}

    def register_event_handler(self, handler: Callable):
        self._on_event = handler

    async def initiate_ai_call(
        self,
        to_number: str,
        from_number: str = None,
        lead_id: str = None,
        metadata: dict = None,
    ) -> dict:
        """Initiate an outbound call with AI Assistant auto-start.

        Flow:
        1. Create call via Telnyx Call Control API
        2. Wait briefly for call to connect
        3. Start AI Assistant automatically
        """
        from_number = from_number or self.config.telnyx.from_number
        connection_id = self.config.telnyx.call_control_app_id

        payload = {
            "connection_id": connection_id,
            "to": to_number,
            "from": from_number,
            "webhook_url": self.config.telnyx.webhook_url,
            "webhook_event_failover_url": self.config.telnyx.webhook_failback_url,
            "webhook_event_type": [
                "call.initiated", "call.ringing", "call.connected",
                "call.completed", "call.failed",
                "ai_assistant.started", "ai_assistant.stopped",
                "ai_assistant.gather_result",
            ],
            "timeout": 60,
        }

        logger.info(f"Initiating AI call to {to_number} from {from_number}")
        start = time.time()

        try:
            resp = await self._client.post("/calls", json=payload)
            resp.raise_for_status()
            call_data = resp.json()["data"]
            call_control_id = call_data.get("call_control_id") or call_data.get("id", "")

            self._call_registry[call_control_id] = {
                "to": to_number,
                "from": from_number,
                "lead_id": lead_id,
                "status": "initiated",
                "created_at": time.time(),
                "metadata": metadata or {},
            }

            duration = (time.time() - start) * 1000
            logger.info(f"AI call initiated: {call_control_id} to {to_number} ({duration:.0f}ms)")

            await self._emit_event("call.initiated", self._call_registry[call_control_id])

            # Auto-start AI Assistant after brief delay (call needs time to connect)
            asyncio.create_task(self._auto_start_ai_assistant(call_control_id, lead_id))

            return {
                "success": True,
                "call_control_id": call_control_id,
                "call_state": call_data.get("call_leg_id", "unknown"),
                "to": to_number,
            }

        except httpx.HTTPError as e:
            logger.error(f"Failed to initiate AI call to {to_number}: {e}")
            return {"success": False, "error": str(e), "to": to_number}

    async def _auto_start_ai_assistant(self, call_control_id: str, lead_id: str = None):
        """Wait for call to connect, then start AI Assistant."""
        # Wait 10 seconds for the call to ring and connect
        await asyncio.sleep(10)

        # Check if call is still active
        if call_control_id in self._call_registry:
            logger.info(f"Auto-starting AI Assistant for {call_control_id}")
            result = await self.start_ai_assistant(call_control_id)
            if result.get("success"):
                logger.info(f"AI Assistant started for {call_control_id}")
            else:
                logger.warning(f"Failed to auto-start AI Assistant: {result.get('error')}")
                # Retry once after 5 more seconds
                await asyncio.sleep(5)
                result = await self.start_ai_assistant(call_control_id)
                if result.get("success"):
                    logger.info(f"AI Assistant started on retry for {call_control_id}")

    async def start_ai_assistant(self, call_control_id: str, prompt: str = None) -> dict:
        """Start Telnyx native AI Assistant on an active call.

        This replaces the entire STT→LLM→TTS pipeline with Telnyx's
        built-in AI voice assistant.
        """
        if prompt is None:
            prompt = SALES_ASSISTANT_PROMPT

        payload = {
            "ai_assistant_request": {
                "model": "openai/gpt-4o",
                "prompt": prompt,
            },
        }

        logger.info(f"Starting AI Assistant for call {call_control_id}")

        try:
            resp = await self._client.post(
                f"/calls/{call_control_id}/actions/ai_assistant_start",
                json=payload,
            )
            resp.raise_for_status()
            result = resp.json()["data"]

            self._active_ai_calls[call_control_id] = {
                "started_at": time.time(),
                "prompt_length": len(prompt),
                "model": "openai/gpt-4o",
            }

            logger.info(f"AI Assistant started for call {call_control_id}")
            return {
                "success": True,
                "call_control_id": call_control_id,
                "status": result.get("status", "ai_assistant_started"),
            }

        except httpx.HTTPError as e:
            logger.error(f"Failed to start AI Assistant for {call_control_id}: {e}")
            return {"success": False, "error": str(e)}

    async def stop_ai_assistant(self, call_control_id: str) -> dict:
        """Stop the AI Assistant on a call."""
        try:
            resp = await self._client.post(
                f"/calls/{call_control_id}/actions/ai_assistant_stop",
                json={"params": {}},
            )
            resp.raise_for_status()
            self._active_ai_calls.pop(call_control_id, None)
            logger.info(f"AI Assistant stopped for call {call_control_id}")
            return {"success": True, "call_control_id": call_control_id}
        except httpx.HTTPError as e:
            logger.error(f"Failed to stop AI Assistant for {call_control_id}: {e}")
            return {"success": False, "error": str(e)}

    async def hangup_call(self, call_control_id: str) -> dict:
        """End an active call."""
        await self.stop_ai_assistant(call_control_id)

        try:
            resp = await self._client.post(f"/calls/{call_control_id}/actions/hangup")
            resp.raise_for_status()
            logger.info(f"Call {call_control_id} hung up")
            return {"success": True, "call_control_id": call_control_id}
        except httpx.HTTPError as e:
            logger.error(f"Failed to hangup call {call_control_id}: {e}")
            return {"success": False, "error": str(e)}

    async def handle_ai_webhook(self, event_data: dict) -> dict:
        """Process AI Assistant webhook events."""
        event_type = event_data.get("event_type", "unknown")
        call_control_id = event_data.get("data", {}).get("call_control_id", "")

        logger.info(f"AI webhook: {event_type} for call {call_control_id}")

        if event_type == "call.connected":
            # Auto-start AI Assistant when call connects
            if call_control_id and call_control_id not in self._active_ai_calls:
                await self.start_ai_assistant(call_control_id)

        if event_type in ["ai_assistant.started", "ai_assistant.stopped"]:
            if call_control_id in self._call_registry:
                self._call_registry[call_control_id]["ai_status"] = event_type.split(".")[-1]

        if event_type == "ai_assistant.gather_result":
            result = event_data.get("data", {}).get("result", {})
            logger.info(f"AI gather result: {result}")

        await self._emit_event(event_type, event_data)
        return {"success": True, "event": event_type, "call_control_id": call_control_id}

    async def _emit_event(self, event_type: str, data: dict):
        if self._on_event:
            try:
                if asyncio.iscoroutinefunction(self._on_event):
                    await self._on_event(event_type, data)
                else:
                    self._on_event(event_type, data)
            except Exception as e:
                logger.error(f"Error in AI event handler: {e}")

    def get_active_calls(self) -> dict:
        """Get all active AI calls."""
        return {
            cid: {**info, "duration": time.time() - info["started_at"]}
            for cid, info in self._active_ai_calls.items()
        }

    async def close(self):
        # Stop all active AI calls
        for call_id in list(self._active_ai_calls.keys()):
            await self.stop_ai_assistant(call_id)
        await self._client.aclose()
