"""
Telnyx Voice Gateway Service
Handles outbound calls, webhooks, and media streaming for AI voice agents.
Supports both REST API (play_audio) and Media WebSocket (real-time PCM16 streaming).

Media WebSocket Architecture:
- Outbound: Call initiates with media_streaming_start payload
- Inbound: Webhook triggers WebSocket connection (separate agent)
- Audio: PCM16, 16kHz, mono, bidirectional streaming
- Latency: <200ms vs ~2-5s with play_audio
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Callable, Dict, Optional

import httpx
import websockets

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
    MEDIA_AUDIO_RECEIVED = "media.audio_received"


class TelnyxGateway:
    """Telnyx Voice API adapter for AI calls with Media WebSocket support."""

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
        self._on_audio: Optional[Callable] = None
        self._media_ws: Dict[str, websockets.WebSocketClientProtocol] = {}
        self._media_tasks: Dict[str, asyncio.Task] = {}

    def register_event_handler(self, handler: Callable):
        self._on_event = handler

    def register_audio_handler(self, handler: Callable):
        """Register handler for incoming media stream audio."""
        self._on_audio = handler

    async def initiate_outbound_call(
        self,
        to_number: str,
        from_number: str = None,
        webhook_url: str = None,
        connection_id: str = None,
        metadata: dict = None,
        media_websocket_url: str = None,
    ) -> dict:
        """Initiate an outbound call via Telnyx Call Control API."""
        from_number = from_number or self.config.telnyx.from_number
        # Use Call Control App ID, not SIP connection ID
        connection_id = connection_id or self.config.telnyx.call_control_app_id

        payload = {
            "connection_id": connection_id,
            "to": to_number,
            "from": from_number,
            "webhook_event_type": ["call.initiated", "call.ringing", "call.connected", "call.completed", "call.failed"],
            "timeout": 60,
        }

        if webhook_url:
            payload["webhook_url"] = webhook_url
        elif self.config.telnyx.webhook_url:
            payload["webhook_url"] = self.config.telnyx.webhook_url

        if self.config.telnyx.webhook_failback_url:
            payload["webhook_event_failover_url"] = self.config.telnyx.webhook_failback_url

        logger.info(f"Initiating outbound call to {to_number} from {from_number}")
        if media_websocket_url:
            logger.info(f"Media WebSocket: {media_websocket_url}")
        start = time.time()

        try:
            resp = await self._client.post("/calls", json=payload)
            resp.raise_for_status()
            call_data = resp.json()["data"]
            # Call Control API returns call_control_id, not id
            call_id = call_data.get("call_control_id") or call_data.get("id", "")

            self._call_registry[call_id] = {
                "to": to_number,
                "from": from_number,
                "status": "initiated",
                "telnyx_call_id": call_id,
                "media_ws_url": media_websocket_url,
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
                "media_streaming": media_websocket_url is not None,
            }

        except httpx.HTTPError as e:
            logger.error(f"Failed to initiate call to {to_number}: {e}")
            return {
                "success": False,
                "error": str(e),
                "to": to_number,
            }

    async def connect_to_media_stream(self, call_id: str, ws_url: str) -> bool:
        """Connect to Telnyx Media WebSocket for real-time audio streaming.

        This replaces the slow play_audio REST API with low-latency WebSocket streaming.
        Audio is sent as PCM16 (16kHz, mono) in chunks of 20ms (640 bytes).
        """
        if call_id in self._media_ws:
            logger.warning(f"Media WebSocket already connected for {call_id}")
            return True

        try:
            ws = await websockets.connect(ws_url)
            self._media_ws[call_id] = ws

            task = asyncio.create_task(self._media_listen_loop(call_id, ws))
            self._media_tasks[call_id] = task

            if call_id in self._call_registry:
                self._call_registry[call_id]["media_connected"] = True

            logger.info(f"Media WebSocket connected for call {call_id}")
            await self._emit_event(TelnyxEvent.MEDIA_STREAMING, {"call_id": call_id, "url": ws_url})
            return True

        except Exception as e:
            logger.error(f"Failed to connect media WebSocket for {call_id}: {e}")
            return False

    async def _media_listen_loop(self, call_id: str, ws: websockets.WebSocketClientProtocol):
        """Listen for incoming audio from Telnyx media stream."""
        try:
            async for message in ws:
                if isinstance(message, bytes):
                    if self._on_audio:
                        await self._on_audio(call_id, message)
                elif isinstance(message, str):
                    data = json.loads(message)
                    logger.debug(f"Media control message: {data.get('type', 'unknown')}")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Media WebSocket closed for call {call_id}")
        except Exception as e:
            logger.error(f"Media stream error for {call_id}: {e}")
        finally:
            self._media_ws.pop(call_id, None)
            self._media_tasks.pop(call_id, None)

    async def send_audio_stream(self, call_id: str, audio_chunk: bytes) -> bool:
        """Send PCM16 audio chunk via Media WebSocket (low-latency).

        Replaces send_audio() which uses slow play_audio REST API.
        Audio must be PCM16, 16kHz, mono.
        Chunks should be ~640 bytes (20ms of audio).
        """
        ws = self._media_ws.get(call_id)
        if not ws:
            logger.warning(f"No media WebSocket for call {call_id}, falling back to play_audio")
            audio_b64 = base64.b64encode(audio_chunk).decode("utf-8")
            return await self.send_audio(call_id, audio_b64)

        try:
            await ws.send(audio_chunk)
            return True
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Media WebSocket closed for {call_id}")
            self._media_ws.pop(call_id, None)
            return False

    async def hangup_call(self, call_id: str) -> dict:
        """End an active call and close media stream."""
        await self._close_media_stream(call_id)

        try:
            resp = await self._client.post(f"/calls/{call_id}/actions/hangup")
            resp.raise_for_status()
            logger.info(f"Call {call_id} hung up")
            return {"success": True, "call_id": call_id}
        except httpx.HTTPError as e:
            logger.error(f"Failed to hangup call {call_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _close_media_stream(self, call_id: str):
        """Close media WebSocket for a call."""
        ws = self._media_ws.pop(call_id, None)
        if ws:
            try:
                await ws.close()
            except Exception:
                pass

        task = self._media_tasks.pop(call_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def send_audio(self, call_id: str, audio_base64: str):
        """Send audio to an active call (fallback via play_audio REST API).

        For low-latency streaming, use send_audio_stream() instead.
        """
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
        for call_id in list(self._media_ws.keys()):
            await self._close_media_stream(call_id)
        await self._client.aclose()
