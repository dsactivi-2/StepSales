"""
Telnyx Voice Gateway Service
Handles outbound calls, webhooks, and media streaming for AI voice agents.
Adapter pattern: unified VoiceProvider interface with Telnyx implementation.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Callable, Dict, Optional

import httpx

from config.settings import AppConfig

logger = logging.getLogger("stepsales.telnyx")


class TelnyxEvent:
    CALL_INITIATED = "call.initiated"
    CALL_RINGING = "call.ringing"
    CALL_CONNECTED = "call.connected"
    CALL_COMPLETED = "call.completed"
    CALL_FAILED = "call.failed"
    WEBHOOK_RECEIVED = "webhook.received"
    MEDIA_STREAMING = "media.streaming"


class TelnyxGateway:
    """Telnyx Voice API adapter for outbound AI calls."""

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
        self._media_ws_url: Optional[str] = None

    def register_event_handler(self, handler: Callable):
        self._on_event = handler

    async def initiate_outbound_call(
        self,
        to_number: str,
        from_number: str = None,
        webhook_url: str = None,
        connection_id: str = None,
        metadata: dict = None,
    ) -> dict:
        """Initiate an outbound call via Telnyx Voice API."""
        from_number = from_number or self.config.telnyx.from_number
        connection_id = connection_id or self.config.telnyx.connection_id

        payload = {
            "to": to_number,
            "from": from_number,
            "connection_id": connection_id,
            "webhook_event_type": ["call.initiated", "call.ringing", "call.connected", "call.completed", "call.failed"],
            "webhook_url": webhook_url,
            "webhook_failover_url": webhook_url,
            "timeout": 60,
        }

        if metadata:
            payload["messaging_profile_id"] = metadata.get("messaging_profile_id")

        logger.info(f"Initiating outbound call to {to_number} from {from_number}")
        start = time.time()

        try:
            resp = await self._client.post("/calls", json=payload)
            resp.raise_for_status()
            call_data = resp.json()["data"]
            call_id = call_data.get("id", "")

            self._call_registry[call_id] = {
                "to": to_number,
                "from": from_number,
                "status": "initiated",
                "telnyx_call_id": call_id,
                "created_at": time.time(),
                "metadata": metadata or {},
            }

            duration = (time.time() - start) * 1000
            logger.info(
                f"Call initiated: {call_id} to {to_number} ({duration:.0f}ms)"
            )

            await self._emit_event(TelnyxEvent.CALL_INITIATED, self._call_registry[call_id])

            return {
                "success": True,
                "call_id": call_id,
                "call_state": call_data.get("state", "unknown"),
                "telnyx_call_id": call_id,
            }

        except httpx.HTTPError as e:
            logger.error(f"Failed to initiate call to {to_number}: {e}")
            return {
                "success": False,
                "error": str(e),
                "to": to_number,
            }

    async def hangup_call(self, call_id: str) -> dict:
        """End an active call."""
        try:
            resp = await self._client.post(f"/calls/{call_id}/actions/hangup")
            resp.raise_for_status()
            logger.info(f"Call {call_id} hung up")
            return {"success": True, "call_id": call_id}
        except httpx.HTTPError as e:
            logger.error(f"Failed to hangup call {call_id}: {e}")
            return {"success": False, "error": str(e)}

    async def send_audio(self, call_id: str, audio_base64: str):
        """Send audio to an active call's media stream."""
        payload = {
            "call_control_id": call_id,
            "audio": audio_base64,
            "format": "base64",
        }
        try:
            resp = await self._client.post(f"/calls/{call_id}/actions/play_audio", json=payload)
            resp.raise_for_status()
            return {"success": True}
        except httpx.HTTPError as e:
            logger.error(f"Failed to send audio to {call_id}: {e}")
            return {"success": False, "error": str(e)}

    def verify_webhook_signature(self, payload: str, signature: str, timestamp: str) -> bool:
        """Verify Telnyx webhook signature for security."""
        secret = self.config.telnyx.webhook_secret
        if not secret:
            return True

        payload_to_sign = timestamp + payload
        expected = hmac.new(
            secret.encode("utf-8"),
            payload_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    async def handle_webhook(self, event_data: dict) -> dict:
        """Process incoming Telnyx webhook events."""
        event_type = event_data.get("event_type", "unknown")
        call_id = event_data.get("data", {}).get("id", "")

        logger.info(f"Telnyx webhook: {event_type} for call {call_id}")

        if call_id and call_id in self._call_registry:
            self._call_registry[call_id]["status"] = event_type.split(".")[-1]

        event_map = {
            "call.initiated": TelnyxEvent.CALL_INITIATED,
            "call.ringing": TelnyxEvent.CALL_RINGING,
            "call.connected": TelnyxEvent.CALL_CONNECTED,
            "call.completed": TelnyxEvent.CALL_COMPLETED,
            "call.failed": TelnyxEvent.CALL_FAILED,
        }

        mapped_event = event_map.get(event_type, TelnyxEvent.WEBHOOK_RECEIVED)
        await self._emit_event(mapped_event, event_data)

        return {"success": True, "event": event_type, "call_id": call_id}

    async def _emit_event(self, event_type: str, data: dict):
        if self._on_event:
            try:
                if asyncio.iscoroutinefunction(self._on_event):
                    await self._on_event(event_type, data)
                else:
                    self._on_event(event_type, data)
            except Exception as e:
                logger.error(f"Error in webhook event handler: {e}")

    async def close(self):
        await self._client.aclose()
