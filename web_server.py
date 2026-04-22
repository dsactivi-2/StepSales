#!/usr/bin/env python3
"""
Web Server for Live Voice Calls with Telesales Agent
FastAPI + WebSocket + OpenAI Realtime API
"""

import asyncio
import json
import logging
import base64
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import Config
from telesales_agent import TelesalesAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stepsales.web")

# Initialize FastAPI
app = FastAPI(title="Stepsales Web Call", version="1.0.0")

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global state for active calls
class CallSession:
    """Manages a single web call session"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.agent = TelesalesAgent()
        self.call_start = datetime.now()
        self.transcript = []
        self.connected = False

    def add_transcript(self, speaker: str, text: str):
        """Add message to transcript"""
        self.transcript.append(
            {
                "timestamp": datetime.now().isoformat(),
                "speaker": speaker,
                "text": text,
            }
        )

    def get_call_summary(self) -> dict:
        """Get call summary"""
        duration = (datetime.now() - self.call_start).total_seconds()
        return {
            "call_id": self.agent.call_id,
            "session_id": self.session_id,
            "duration_seconds": int(duration),
            "transcript_lines": len(self.transcript),
            "timestamp": self.call_start.isoformat(),
        }


# Active sessions
active_sessions: dict[str, CallSession] = {}


@app.get("/")
async def get_index():
    """Serve main HTML page"""
    return FileResponse("static/index.html", media_type="text/html")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "stepsales-web-call",
        "active_calls": len(active_sessions),
    }


@app.websocket("/ws/call/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for voice calls"""
    await websocket.accept()
    logger.info(f"WebSocket connected: {session_id}")

    # Create or get session
    if session_id not in active_sessions:
        active_sessions[session_id] = CallSession(session_id)

    session = active_sessions[session_id]
    session.connected = True

    try:
        # Send initial greeting from agent
        initial_message = "Guten Tag, hier ist Alex von Stepsales. Wie kann ich Ihnen heute helfen?"
        session.add_transcript("Agent", initial_message)

        await websocket.send_json(
            {
                "type": "agent_message",
                "text": initial_message,
                "call_id": session.agent.call_id,
            }
        )

        # Listen for incoming messages
        while True:
            data = await websocket.receive_json()

            if data["type"] == "user_audio":
                # Incoming audio from user
                audio_base64 = data.get("audio", "")
                if audio_base64:
                    # Decode audio
                    audio_bytes = base64.b64decode(audio_base64)

                    # In production, send to OpenAI Realtime API
                    # For now, echo back with simulated response
                    user_text = data.get("transcript", "")
                    if user_text:
                        session.add_transcript("User", user_text)

                        # Simulate agent response
                        agent_response = await generate_agent_response(
                            session, user_text
                        )

                        session.add_transcript("Agent", agent_response)

                        await websocket.send_json(
                            {
                                "type": "agent_message",
                                "text": agent_response,
                            }
                        )

            elif data["type"] == "end_call":
                logger.info(f"Call ended by user: {session_id}")
                summary = session.get_call_summary()
                await websocket.send_json({"type": "call_ended", "summary": summary})
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
        session.connected = False
        if session_id in active_sessions:
            del active_sessions[session_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass


async def generate_agent_response(session: CallSession, user_input: str) -> str:
    """Generate agent response (simulated for now)"""
    # In production, this would call OpenAI Realtime API
    # For MVP, use simple heuristics

    user_lower = user_input.lower()

    # Simple responses
    if any(
        word in user_lower for word in ["hallo", "guten tag", "hallo alex"]
    ):
        return "Guten Tag! Schön, Sie zu sprechen. Kann ich Ihnen bei der Personalsuche helfen?"

    elif any(word in user_lower for word in ["ja", "ja gerne", "ja bitte"]):
        return "Großartig! Erzählen Sie mir, welche Positionen Sie derzeit besetzen möchten."

    elif any(word in user_lower for word in ["entwickler", "engineer", "software"]):
        return "Software Engineers sind sehr gefragt. Wie viele Stellen möchten Sie besetzen und in welcher Region?"

    elif any(word in user_lower for word in ["berlin", "münchen", "köln", "hamburg"]):
        return "Perfekt! Wir haben gerade interessante Profile aus der Region. Möchten Sie eine Vorschau bekommen?"

    elif any(word in user_lower for word in ["danke", "danke dir", "dankeschön"]):
        return "Gerne geschehen! Falls Sie weitere Fragen haben, stehe ich gerne zur Verfügung."

    elif any(word in user_lower for word in ["auf wiedersehen", "tschüss", "bye"]):
        return "Auf Wiedersehen! Danke für das Gespräch. Haben Sie einen schönen Tag!"

    else:
        return f"Interessant, dass Sie erwähnen: {user_input[:30]}... Können Sie mir mehr Details geben?"


@app.post("/api/calls/{session_id}/end")
async def end_call(session_id: str):
    """Manually end a call"""
    if session_id in active_sessions:
        session = active_sessions[session_id]
        summary = session.get_call_summary()
        del active_sessions[session_id]
        return {"status": "ended", "summary": summary}
    return {"status": "not_found", "error": f"Session {session_id} not found"}


@app.get("/api/calls/{session_id}/transcript")
async def get_transcript(session_id: str):
    """Get call transcript"""
    if session_id in active_sessions:
        session = active_sessions[session_id]
        return {
            "session_id": session_id,
            "transcript": session.transcript,
            "summary": session.get_call_summary(),
        }
    return {"error": "Session not found"}


async def lifespan(app: FastAPI):
    """Startup/shutdown events"""
    logger.info("🚀 Stepsales Web Call Server starting...")
    yield
    logger.info("🛑 Stepsales Web Call Server shutting down...")


app.router.lifespan_context = lifespan


def main():
    """Run web server"""
    Config.validate()

    logger.info("=" * 60)
    logger.info("📞 Stepsales Web Call Server")
    logger.info("=" * 60)
    logger.info("🌐 Local: http://localhost:8000")
    logger.info("📊 Health: http://localhost:8000/health")
    logger.info("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    main()
