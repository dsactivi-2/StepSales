"""
Deepgram Speech-to-Text Service
Realtime transcription with German language support, end-of-turn detection,
and interim results for low-latency voice agents.
"""

import asyncio
import json
import logging
from typing import Callable, Optional

import websockets

from config.settings import AppConfig

logger = logging.getLogger("stepsales.deepgram")


class DeepgramSTT:
    """Deepgram Nova-3 STT service for German voice calls."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._ws = None
        self._connected = False
        self._on_transcript: Optional[Callable] = None
        self._on_eot: Optional[Callable] = None
        self._listen_task = None

    def register_transcript_handler(self, handler: Callable):
        self._on_transcript = handler

    def register_end_of_turn_handler(self, handler: Callable):
        self._on_eot = handler

    async def connect(self):
        """Connect to Deepgram realtime websocket."""
        params = {
            "model": self.config.deepgram.model,
            "language": self.config.deepgram.language,
            "smart_format": str(self.config.deepgram.smart_format).lower(),
            "interim_results": str(self.config.deepgram.interim_results).lower(),
            "utterance_end_ms": str(self.config.deepgram.utterance_end_ms),
            "endpointing": str(self.config.deepgram.endpointing_ms),
            "sample_rate": str(self.config.deepgram.sample_rate),
            "channels": str(self.config.deepgram.channels),
            "encoding": self.config.deepgram.encoding,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{self.config.deepgram.api_base}?{query}"

        headers = {
            "Authorization": f"Token {self.config.deepgram.api_key}",
        }

        logger.info(f"Connecting to Deepgram STT: {self.config.deepgram.model} (de)")
        self._ws = await websockets.connect(
            url,
            additional_headers=headers,
            ping_interval=10,
            ping_timeout=5,
        )
        self._connected = True
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.info("Deepgram STT connected")

    async def send_audio(self, audio_bytes: bytes):
        """Send PCM16 audio chunk for transcription."""
        if not self._connected or not self._ws:
            logger.warning("Deepgram STT not connected, dropping audio")
            return

        try:
            await self._ws.send(audio_bytes)
        except websockets.exceptions.ConnectionClosed:
            self._connected = False
            logger.error("Deepgram STT connection lost")

    async def _listen_loop(self):
        """Listen for transcription results from Deepgram."""
        try:
            async for message in self._ws:
                data = json.loads(message)

                channel = data.get("channel", {})
                if not channel:
                    continue

                alternatives = channel.get("alternatives", [])
                if not alternatives:
                    continue

                result = alternatives[0]
                transcript = result.get("transcript", "").strip()
                is_final = result.get("is_final", False)
                confidence = result.get("confidence", 0.0)

                speech_started = result.get("speech_final", False)
                start = result.get("start", 0.0)
                duration = result.get("duration", 0.0)

                if transcript:
                    if self._on_transcript:
                        await self._on_transcript({
                            "text": transcript,
                            "is_final": is_final,
                            "confidence": confidence,
                            "speech_final": speech_final,
                            "start": start,
                            "duration": duration,
                        })

                if speech_final and self._on_eot:
                    await self._on_eot({
                        "text": transcript,
                        "confidence": confidence,
                        "duration": duration,
                    })

        except websockets.exceptions.ConnectionClosed:
            self._connected = False
            logger.warning("Deepgram STT connection closed")
        except Exception as e:
            logger.error(f"Deepgram STT listen error: {e}")
            self._connected = False

    async def flush(self):
        """Flush current utterance (force end-of-turn)."""
        if self._ws and self._connected:
            await self._ws.send(json.dumps({"type": "Flush"}))

    async def disconnect(self):
        """Disconnect from Deepgram."""
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            await self._ws.close()
            self._connected = False
            logger.info("Deepgram STT disconnected")
