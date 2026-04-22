#!/usr/bin/env python3
"""
Web Server for Live Voice Calls with Telesales Agent
FastAPI + WebSocket + OpenAI Realtime API
"""

import asyncio
import json
import logging
import base64
import os
import time
import uuid
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import Config
from telesales_agent import TelesalesAgent
from logger_config import (
    logger_web, logger_websocket, get_logger,
    log_step, log_command, log_performance, log_error_detailed
)

# Use advanced logger
logger = logger_web


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown events"""
    logger.info("🚀 Stepsales Web Call Server starting...")
    yield
    logger.info("🛑 Stepsales Web Call Server shutting down...")


# Initialize FastAPI
app = FastAPI(
    title="Stepsales Web Call",
    version="1.0.0",
    lifespan=lifespan
)

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
    start = time.time()
    try:
        log_step(logger, "GET /", {"type": "index_page"})
        result = FileResponse("static/index.html", media_type="text/html")
        duration = (time.time() - start) * 1000
        log_performance(logger, "GET /", duration)
        return result
    except Exception as e:
        log_error_detailed(logger, e, {"endpoint": "GET /"})
        return {"error": str(e)}, 500


@app.get("/health")
async def health():
    """Health check endpoint"""
    start = time.time()
    try:
        result = {
            "status": "healthy",
            "service": "stepsales-web-call",
            "active_calls": len(active_sessions),
            "timestamp": datetime.now().isoformat(),
        }
        log_command(logger, "health_check", result)
        duration = (time.time() - start) * 1000
        log_performance(logger, "GET /health", duration)
        return result
    except Exception as e:
        log_error_detailed(logger, e, {"endpoint": "GET /health"})
        return {"status": "unhealthy", "error": str(e)}, 500


@app.websocket("/ws/call/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for voice calls"""
    request_id = str(uuid.uuid4())[:8]
    ws_start = time.time()
    message_count = 0

    try:
        await websocket.accept()
        log_step(
            logger_websocket,
            "WebSocket Connected",
            {
                "session_id": session_id,
                "request_id": request_id,
                "client": str(websocket.client),
            },
        )

        # Create or get session
        if session_id not in active_sessions:
            active_sessions[session_id] = CallSession(session_id)
            log_command(
                logger_websocket,
                "create_session",
                {"session_id": session_id, "request_id": request_id},
            )
        else:
            log_command(logger_websocket, "reuse_session", {"session_id": session_id})

        session = active_sessions[session_id]
        session.connected = True

        # Send initial greeting from agent
        initial_message = (
            "Guten Tag, hier ist Alex von Stepsales. "
            "Wie kann ich Ihnen heute helfen?"
        )
        session.add_transcript("Agent", initial_message)

        log_step(
            logger_websocket,
            "Agent Greeting Sent",
            {
                "session_id": session_id,
                "call_id": session.agent.call_id,
                "message_length": len(initial_message),
            },
        )

        await websocket.send_json(
            {
                "type": "agent_message",
                "text": initial_message,
                "call_id": session.agent.call_id,
            }
        )

        # Listen for incoming messages
        while True:
            msg_start = time.time()
            data = await websocket.receive_json()
            message_count += 1

            try:
                if data["type"] == "user_audio":
                    # Incoming audio from user
                    audio_base64 = data.get("audio", "")
                    user_text = data.get("transcript", "")

                    if audio_base64:
                        audio_bytes = base64.b64decode(audio_base64)
                        audio_size_kb = len(audio_bytes) / 1024

                        log_step(
                            logger_websocket,
                            "Audio Received",
                            {
                                "session_id": session_id,
                                "size_kb": round(audio_size_kb, 2),
                                "text_preview": user_text[:40] if user_text else "N/A",
                                "message_num": message_count,
                            },
                        )

                        if user_text:
                            session.add_transcript("User", user_text)

                            log_command(
                                logger_websocket,
                                "user_message",
                                {
                                    "session_id": session_id,
                                    "text_length": len(user_text),
                                    "message_num": message_count,
                                },
                            )

                            # Get agent response
                            agent_start = time.time()
                            agent_response = await generate_agent_response(
                                session, user_text
                            )
                            agent_duration = (time.time() - agent_start) * 1000

                            session.add_transcript("Agent", agent_response)

                            log_step(
                                logger_websocket,
                                "Agent Response Generated",
                                {
                                    "session_id": session_id,
                                    "duration_ms": round(agent_duration, 2),
                                    "response_length": len(agent_response),
                                },
                            )

                            await websocket.send_json(
                                {
                                    "type": "agent_message",
                                    "text": agent_response,
                                }
                            )

                            msg_duration = (time.time() - msg_start) * 1000
                            log_performance(
                                logger_websocket,
                                f"user_message_complete",
                                msg_duration,
                            )

                elif data["type"] == "end_call":
                    call_duration = (time.time() - ws_start) * 1000
                    summary = session.get_call_summary()

                    log_step(
                        logger_websocket,
                        "Call Ended by User",
                        {
                            "session_id": session_id,
                            "duration_ms": round(call_duration, 2),
                            "message_count": message_count,
                            "transcript_lines": len(session.transcript),
                        },
                    )

                    await websocket.send_json(
                        {"type": "call_ended", "summary": summary}
                    )
                    break
            except json.JSONDecodeError as je:
                log_error_detailed(
                    logger_websocket,
                    je,
                    {
                        "session_id": session_id,
                        "message_num": message_count,
                        "data": str(data)[:100],
                    },
                )
                await websocket.send_json(
                    {"type": "error", "message": "Invalid JSON in message"}
                )
            except Exception as e:
                log_error_detailed(
                    logger_websocket,
                    e,
                    {
                        "session_id": session_id,
                        "message_num": message_count,
                    },
                )
                await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        call_duration = (time.time() - ws_start) * 1000
        log_step(
            logger_websocket,
            "WebSocket Disconnected",
            {
                "session_id": session_id,
                "duration_ms": round(call_duration, 2),
                "message_count": message_count,
            },
        )
        session.connected = False
        if session_id in active_sessions:
            del active_sessions[session_id]

    except Exception as e:
        call_duration = (time.time() - ws_start) * 1000
        log_error_detailed(
            logger_websocket,
            e,
            {
                "session_id": session_id,
                "duration_ms": round(call_duration, 2),
                "message_count": message_count,
            },
        )
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
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
    start = time.time()
    try:
        log_command(logger, "end_call", {"session_id": session_id})

        if session_id in active_sessions:
            session = active_sessions[session_id]
            summary = session.get_call_summary()

            log_step(
                logger,
                "Call Ended",
                {
                    "session_id": session_id,
                    "duration_sec": summary.get("duration_seconds"),
                    "message_count": summary.get("transcript_lines"),
                },
            )

            del active_sessions[session_id]

            duration = (time.time() - start) * 1000
            log_performance(logger, "POST /api/calls/{id}/end", duration)

            return {"status": "ended", "summary": summary}

        log_error_detailed(
            logger, ValueError(f"Session not found: {session_id}"), {"session_id": session_id}
        )
        return {"status": "not_found", "error": f"Session {session_id} not found"}

    except Exception as e:
        log_error_detailed(logger, e, {"session_id": session_id, "endpoint": "end_call"})
        return {"status": "error", "error": str(e)}, 500


@app.get("/api/calls/{session_id}/transcript")
async def get_transcript(session_id: str):
    """Get call transcript"""
    start = time.time()
    try:
        log_command(logger, "get_transcript", {"session_id": session_id})

        if session_id in active_sessions:
            session = active_sessions[session_id]
            summary = session.get_call_summary()

            result = {
                "session_id": session_id,
                "transcript": session.transcript,
                "summary": summary,
            }

            log_step(
                logger,
                "Transcript Retrieved",
                {
                    "session_id": session_id,
                    "lines": len(session.transcript),
                    "duration_sec": summary.get("duration_seconds"),
                },
            )

            duration = (time.time() - start) * 1000
            log_performance(logger, "GET /api/calls/{id}/transcript", duration)

            return result

        log_error_detailed(
            logger, ValueError(f"Session not found: {session_id}"), {"session_id": session_id}
        )
        return {"error": "Session not found"}

    except Exception as e:
        log_error_detailed(logger, e, {"session_id": session_id, "endpoint": "get_transcript"})
        return {"status": "error", "error": str(e)}, 500


def main():
    """Run web server"""
    start = time.time()

    try:
        log_step(logger, "Initialize Web Server", {"version": "1.0.0"})

        # Validate configuration
        try:
            Config.validate()
            log_command(logger, "config_validate", {"status": "success"})
        except Exception as e:
            log_error_detailed(logger, e, {"operation": "config_validate"})
            raise

        # Get port from environment or use default
        port = int(os.getenv("PORT", "8001"))
        host = os.getenv("HOST", "0.0.0.0")

        log_step(
            logger,
            "Server Configuration Loaded",
            {
                "host": host,
                "port": port,
                "log_dir": str(logger_web.handlers[1].baseFilename),
            },
        )

        logger.info("=" * 60)
        logger.info("📞 Stepsales Web Call Server")
        logger.info("=" * 60)
        logger.info(f"🌐 Local: http://localhost:{port}")
        logger.info(f"📊 Health: http://localhost:{port}/health")
        logger.info(f"📂 Logs: logs/")
        logger.info("=" * 60)

        log_step(logger, "Starting Uvicorn Server", {"port": port, "host": host})

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
        )

    except KeyboardInterrupt:
        duration = (time.time() - start) * 1000
        log_step(
            logger, "Server Shutdown (User)", {"duration_ms": round(duration, 2)}
        )
    except Exception as e:
        log_error_detailed(logger, e, {"operation": "main"})
        raise


if __name__ == "__main__":
    main()
