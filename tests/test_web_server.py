#!/usr/bin/env python3
"""
Tests for Web Server
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_server import app, CallSession, generate_agent_response


class TestWebServer:
    """Test web server endpoints"""

    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)

    def test_health_check(self):
        """Test health endpoint"""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "stepsales-web-call"
        assert "active_calls" in data

    def test_get_index(self):
        """Test index HTML page"""
        response = self.client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_call_session_creation(self):
        """Test CallSession creation"""
        session = CallSession("test-123")
        assert session.session_id == "test-123"
        assert session.connected is False
        assert len(session.transcript) == 0

    def test_call_session_transcript(self):
        """Test adding to transcript"""
        session = CallSession("test-456")
        session.add_transcript("User", "Hallo Alex")
        session.add_transcript("Agent", "Hallo! Wie geht es dir?")

        assert len(session.transcript) == 2
        assert session.transcript[0]["speaker"] == "User"
        assert session.transcript[0]["text"] == "Hallo Alex"
        assert session.transcript[1]["speaker"] == "Agent"

    def test_call_session_summary(self):
        """Test call summary"""
        session = CallSession("summary-test")
        summary = session.get_call_summary()

        assert "call_id" in summary
        assert summary["session_id"] == "summary-test"
        assert "duration_seconds" in summary
        assert summary["transcript_lines"] == 0

    def test_end_call_endpoint(self):
        """Test end call endpoint"""
        # Create a session first
        session = CallSession("end-test")
        from web_server import active_sessions
        active_sessions["end-test"] = session

        # End the call
        response = self.client.post("/api/calls/end-test/end")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ended"
        assert "summary" in data

        # Session should be removed
        assert "end-test" not in active_sessions

    def test_get_transcript_endpoint(self):
        """Test get transcript endpoint"""
        from web_server import active_sessions

        # Create and populate session
        session = CallSession("transcript-test")
        session.add_transcript("User", "Hallo")
        session.add_transcript("Agent", "Hallo zurück!")
        active_sessions["transcript-test"] = session

        # Get transcript
        response = self.client.get("/api/calls/transcript-test/transcript")
        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == "transcript-test"
        assert len(data["transcript"]) == 2
        assert "summary" in data

    def test_get_transcript_not_found(self):
        """Test get transcript with invalid session"""
        response = self.client.get("/api/calls/invalid-123/transcript")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data


class TestAgentResponses:
    """Test agent response generation"""

    @pytest.mark.asyncio
    async def test_greeting_response(self):
        """Test greeting response"""
        session = CallSession("test-greet")
        response = await generate_agent_response(session, "Hallo Alex")
        assert "Guten Tag" in response or "Personalsuche" in response

    @pytest.mark.asyncio
    async def test_developer_response(self):
        """Test response to developer request"""
        session = CallSession("test-dev")
        response = await generate_agent_response(session, "Wir suchen Entwickler")
        assert "Engineer" in response or "gefragt" in response or "Stellen" in response

    @pytest.mark.asyncio
    async def test_farewell_response(self):
        """Test farewell response"""
        session = CallSession("test-bye")
        response = await generate_agent_response(session, "Auf Wiedersehen")
        assert "Wiedersehen" in response or "Gespräch" in response

    @pytest.mark.asyncio
    async def test_generic_response(self):
        """Test generic response"""
        session = CallSession("test-generic")
        response = await generate_agent_response(session, "xyz123")
        assert len(response) > 0
        assert isinstance(response, str)


class TestWebSocketIntegration:
    """Test WebSocket functionality"""

    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)

    def test_websocket_connection(self):
        """Test WebSocket connection"""
        with self.client.websocket_connect("/ws/call/ws-test") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "agent_message"
            assert "Guten Tag" in data["text"]


class TestErrorHandling:
    """Test error handling"""

    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)

    def test_end_call_nonexistent_session(self):
        """Test ending non-existent session"""
        response = self.client.post("/api/calls/fake-123/end")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_invalid_websocket_path(self):
        """Test invalid WebSocket path"""
        try:
            with self.client.websocket_connect("/ws/invalid/path") as ws:
                pass
        except Exception:
            # Expected to fail
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
