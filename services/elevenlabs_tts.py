"""
ElevenLabs Text-to-Speech Service
Streaming TTS with German multilingual voice for natural-sounding sales agent output.
WebSocket-based chunk streaming for low-latency response delivery.
"""

import asyncio
import json
import logging
from typing import AsyncIterator, Callable, Optional

import httpx
import websockets

from config.settings import AppConfig

logger = logging.getLogger("stepsales.elevenlabs")


class ElevenLabsTTS:
    """ElevenLabs TTS service with streaming and WebSocket support."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._client = httpx.AsyncClient(
            base_url=self.config.elevenlabs.api_base,
            headers={
                "xi-api-key": self.config.elevenlabs.api_key,
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
        self._on_audio_chunk: Optional[Callable] = None
        self._on_complete: Optional[Callable] = None

    def register_audio_handler(self, handler: Callable):
        self._on_audio_chunk = handler

    def register_complete_handler(self, handler: Callable):
        self._on_complete = handler

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio (single-shot, non-streaming)."""
        if not self.config.elevenlabs.voice_id:
            raise ValueError("ELEVENLABS_VOICE_ID not configured")

        url = f"/text-to-speech/{self.config.elevenlabs.voice_id}"
        payload = {
            "text": text,
            "model_id": self.config.elevenlabs.model_id,
            "voice_settings": {
                "stability": self.config.elevenlabs.stability,
                "similarity_boost": self.config.elevenlabs.similarity_boost,
                "style": self.config.elevenlabs.style,
                "use_speaker_boost": self.config.elevenlabs.use_speaker_boost,
            },
        }

        logger.info(f"Synthesizing text ({len(text)} chars) with {self.config.elevenlabs.model_id}")

        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()

        audio_bytes = resp.content
        logger.info(f"TTS complete: {len(audio_bytes)} bytes")

        if self._on_audio_chunk:
            await self._on_audio_chunk(audio_bytes, is_final=True)

        if self._on_complete:
            await self._on_complete({"bytes": len(audio_bytes), "text_length": len(text)})

        return audio_bytes

    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """Synthesize text with streaming chunks (WebSocket)."""
        if not self.config.elevenlabs.voice_id:
            raise ValueError("ELEVENLABS_VOICE_ID not configured")

        ws_url = (
            f"wss://api.elevenlabs.io/v1/"
            f"text-to-speech/{self.config.elevenlabs.voice_id}/stream"
            f"?model_id={self.config.elevenlabs.model_id}"
            f"&output_format=pcm_16000"
        )

        headers = {"xi-api-key": self.config.elevenlabs.api_key}

        async with websockets.connect(ws_url, additional_headers=headers) as ws:
            init_message = {
                "text": " ",
                "voice_settings": {
                    "stability": self.config.elevenlabs.stability,
                    "similarity_boost": self.config.elevenlabs.similarity_boost,
                    "style": self.config.elevenlabs.style,
                },
            }
            await ws.send(json.dumps(init_message))

            await ws.send(json.dumps({"text": text}))
            await ws.send(json.dumps({"text": ""}))

            total_bytes = 0
            async for message in ws:
                try:
                    data = json.loads(message)
                    audio = data.get("audio", "")
                    is_final = data.get("isFinal", False)

                    if audio:
                        import base64
                        chunk = base64.b64decode(audio)
                        total_bytes += len(chunk)

                        if self._on_audio_chunk:
                            await self._on_audio_chunk(chunk, is_final=is_final)

                        yield chunk

                    if is_final:
                        break
                except json.JSONDecodeError:
                    continue

            if self._on_complete:
                await self._on_complete({"bytes": total_bytes, "text_length": len(text)})

    async def close(self):
        await self._client.aclose()
