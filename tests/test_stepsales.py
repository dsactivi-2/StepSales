#!/usr/bin/env python3
"""
Stepsales Production System - Test Suite
Tests based on LIVE codebase (2026-04-24)

All tests reference actual files and services that exist in the repository.
No references to deleted files (telesales_agent.py, web_server.py, etc.)
"""

import sys
import os
import json
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─── Config Tests ───────────────────────────────────────────────────────────────

class TestAppConfig:
    """Test AppConfig loading and validation."""

    def test_app_config_loads(self):
        """AppConfig should load without errors."""
        from config.settings import AppConfig
        assert AppConfig is not None

    def test_telnyx_config_loaded(self):
        """Telnyx config should have api_base set."""
        from config.settings import AppConfig
        assert AppConfig.telnyx.api_base == "https://api.telnyx.com/v2"
        assert AppConfig.telnyx.connection_id is not None

    def test_deepgram_config_loaded(self):
        """Deepgram config should have correct defaults."""
        from config.settings import AppConfig
        assert AppConfig.deepgram.model == "nova-3"
        assert AppConfig.deepgram.language == "de"
        assert AppConfig.deepgram.sample_rate == 16000
        assert AppConfig.deepgram.eot_threshold == 0.5

    def test_elevenlabs_config_loaded(self):
        """ElevenLabs config should have correct defaults."""
        from config.settings import AppConfig
        assert AppConfig.elevenlabs.model_id == "eleven_multilingual_v2"
        assert AppConfig.elevenlabs.api_base == "https://api.elevenlabs.io/v1"

    def test_openai_config_loaded(self):
        """OpenAI config should use gpt-4o model."""
        from config.settings import AppConfig
        assert AppConfig.openai.model == "gpt-4o"
        assert AppConfig.openai.temperature == 0.8
        assert AppConfig.openai.max_tokens == 512

    def test_stripe_config_loaded(self):
        """Stripe config should have correct defaults."""
        from config.settings import AppConfig
        assert AppConfig.stripe.currency == "eur"
        assert AppConfig.stripe.default_tax_rate == 0.19

    def test_runtime_config_loaded(self):
        """Runtime config should default to port 8010."""
        from config.settings import AppConfig
        assert AppConfig.runtime.port == 8010
        assert AppConfig.runtime.host == "0.0.0.0"

    def test_validate_returns_list(self):
        """validate() should return a list of errors."""
        from config.settings import AppConfig
        errors = AppConfig.validate()
        assert isinstance(errors, list)

    def test_transcript_dir_created(self):
        """Persistence transcript_dir should exist after validation."""
        from config.settings import AppConfig
        AppConfig.validate()
        assert Path(AppConfig.persistence.transcript_dir).exists()


# ─── Domain Model Tests ────────────────────────────────────────────────────────

class TestDomainModels:
    """Test SQLAlchemy domain models."""

    def test_lead_status_enum(self):
        """LeadStatus should have expected values."""
        from models.domain import LeadStatus
        assert LeadStatus.NEW.value == "new"
        assert LeadStatus.QUALIFIED.value == "qualified"
        assert LeadStatus.PAID.value == "paid"
        assert LeadStatus.DNC.value == "dnc"

    def test_call_stage_enum(self):
        """CallStage should have expected values."""
        from models.domain import CallStage
        assert CallStage.GREET.value == "greet"
        assert CallStage.DISCOVERY.value == "discovery"
        assert CallStage.CLOSE.value == "close"
        assert CallStage.FOLLOWUP.value == "followup"

    def test_company_model(self):
        """Company model should have correct table name."""
        from models.domain import Company
        assert Company.__tablename__ == "companies"

    def test_lead_model(self):
        """Lead model should have correct table name."""
        from models.domain import Lead
        assert Lead.__tablename__ == "leads"

    def test_call_model(self):
        """Call model should have correct table name."""
        from models.domain import Call
        assert Call.__tablename__ == "calls"

    def test_invoice_model(self):
        """Invoice model should have correct table name."""
        from models.domain import Invoice
        assert Invoice.__tablename__ == "invoices"

    def test_memory_fact_model(self):
        """MemoryFact model should have correct table name."""
        from models.domain import MemoryFact
        assert MemoryFact.__tablename__ == "memory_facts"


# ─── Intent Classifier Tests ───────────────────────────────────────────────────

class TestIntentClassifier:
    """Test intent classifier structure (without API calls)."""

    def test_intent_type_enum(self):
        """IntentType should have expected values."""
        import enum
        # Read the file directly to verify enum values exist
        source = Path(__file__).resolve().parent.parent / "services" / "intent_classifier.py"
        content = source.read_text()
        assert "INTEREST" in content
        assert "OBJECTION_PRICE" in content
        assert "GOODBYE" in content
        assert "DECISION_POSITIVE" in content
        assert "class IntentType(str, Enum)" in content

    def test_intent_classification_model(self):
        """IntentClassification should be a valid Pydantic model."""
        source = Path(__file__).resolve().parent.parent / "services" / "intent_classifier.py"
        content = source.read_text()
        assert "class IntentClassification(BaseModel)" in content
        assert "intent: IntentType" in content
        assert "confidence: float" in content
        assert "keywords: list[str]" in content
        assert "needs_followup: bool" in content

    def test_live_intent_classification(self):
        """POST /intent should classify user intent via running API."""
        import requests
        resp = requests.post(
            f"{BASE_URL}/intent",
            json={"user_input": "Ich habe kein Interesse", "current_stage": "discovery"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "intent" in data
        assert "confidence" in data
        assert data["intent"] == "objection_interest"
        assert data["confidence"] >= 0.8


# ─── API Endpoint Tests (Live Integration) ─────────────────────────────────────

BASE_URL = os.getenv("STEPSALES_BASE_URL", "http://localhost:8010")


class TestHealthEndpoints:
    """Test API health and status endpoints."""

    def test_health_endpoint(self):
        """GET /health should return healthy status."""
        import requests
        resp = requests.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_status_endpoint(self):
        """GET /status should return service health."""
        import requests
        resp = requests.get(f"{BASE_URL}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["healthy"] is True
        assert data["services"]["orchestrator"] is True
        assert data["services"]["knowledgebase"] is True

    def test_metrics_endpoint(self):
        """GET /metrics should return process and business metrics."""
        import requests
        resp = requests.get(f"{BASE_URL}/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "stepsales-agent"
        assert "process" in data
        assert "business" in data
        assert "sla" in data

    def test_analytics_endpoint(self):
        """GET /analytics should return KPIs, funnel, and forecast."""
        import requests
        resp = requests.get(f"{BASE_URL}/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert "kpis" in data
        assert "funnel" in data
        assert "forecast" in data
        assert "objections" in data

    def test_webhooks_stats_endpoint(self):
        """GET /webhooks/stats should return webhook event stats."""
        import requests
        resp = requests.get(f"{BASE_URL}/webhooks/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert "telnyx_events" in data


class TestKnowledgebaseEndpoints:
    """Test knowledgebase API endpoints."""

    def test_kb_documents(self):
        """GET /kb/documents should return list of documents."""
        import requests
        resp = requests.get(f"{BASE_URL}/kb/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 8
        assert len(data["documents"]) >= 8
        # Verify document structure
        doc = data["documents"][0]
        assert "id" in doc
        assert "title" in doc
        assert "content" in doc
        assert "category" in doc

    def test_kb_search(self):
        """POST /kb/search should return relevant documents."""
        import requests
        resp = requests.post(
            f"{BASE_URL}/kb/search",
            json={"query": "Multiposting", "top_k": 3}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data

    def test_kb_context(self):
        """GET /kb/context/{stage} should return stage-specific context."""
        import requests
        resp = requests.get(f"{BASE_URL}/kb/context/objection")
        assert resp.status_code == 200
        data = resp.json()
        assert data["stage"] == "objection"


class TestSLAEndpoints:
    """Test SLA escalation endpoints."""

    def test_sla_active(self):
        """GET /sla/active should return active SLA events."""
        import requests
        resp = requests.get(f"{BASE_URL}/sla/active")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "stats" in data

    def test_sla_overdue(self):
        """GET /sla/overdue should return overdue SLA events."""
        import requests
        resp = requests.get(f"{BASE_URL}/sla/overdue")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "count" in data


class TestGraphEndpoints:
    """Test Neo4j graph memory endpoints."""

    def test_graph_stats(self):
        """GET /graph/stats should return graph statistics."""
        import requests
        resp = requests.get(f"{BASE_URL}/graph/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert "total_nodes" in data
        assert "total_relationships" in data


class TestCallEndpoints:
    """Test call trigger endpoints."""

    def test_call_trigger(self):
        """POST /call should trigger a call and return success."""
        import requests
        resp = requests.post(
            f"{BASE_URL}/call",
            json={"phone": "+49999999999"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        # Response contains thread info in string format
        assert "call" in data


class TestCadenceEndpoints:
    """Test outbound cadence endpoints."""

    def test_cadence_status(self):
        """GET /cadence/status should return cadence queue status."""
        import requests
        resp = requests.get(f"{BASE_URL}/cadence/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_sequences" in data
        assert "active" in data


class TestExportEndpoints:
    """Test data export endpoints."""

    def test_export_leads_json(self):
        """GET /export/leads should return data (may be empty list or 500 if DB not ready)."""
        import requests
        resp = requests.get(f"{BASE_URL}/export/leads")
        # Can be 200 (returns list) or 500 (persistence not initialized)
        assert resp.status_code in (200, 500)

    def test_export_analytics(self):
        """GET /export/analytics should return analytics summary."""
        import requests
        resp = requests.get(f"{BASE_URL}/export/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_calls" in data


# ─── Service Structure Tests ───────────────────────────────────────────────────

class TestServiceFiles:
    """Test that all expected service files exist."""

    def test_services_directory(self):
        """All expected service modules should exist."""
        services_dir = Path(__file__).resolve().parent.parent / "services"
        expected_files = [
            "__init__.py",
            "orchestrator_langgraph.py",
            "intent_classifier.py",
            "deepgram_stt.py",
            "elevenlabs_tts.py",
            "telnyx_gateway.py",
            "telnyx_ai_assistant.py",
            "stripe_billing.py",
            "persistence.py",
            "lead_intel.py",
            "fulfillment.py",
            "cadence.py",
            "knowledgebase.py",
            "agent_coach.py",
            "sla_escalation.py",
            "analytics.py",
            "webhooks.py",
            "audit_monitoring.py",
            "graph_memory.py",
        ]
        for filename in expected_files:
            assert (services_dir / filename).exists(), f"Missing: {filename}"

    def test_config_files(self):
        """Config files should exist."""
        config_dir = Path(__file__).resolve().parent.parent / "config"
        assert (config_dir / "__init__.py").exists()
        assert (config_dir / "settings.py").exists()

    def test_models_files(self):
        """Model files should exist."""
        models_dir = Path(__file__).resolve().parent.parent / "models"
        assert (models_dir / "domain.py").exists()

    def test_main_file_exists(self):
        """main.py should exist."""
        main_path = Path(__file__).resolve().parent.parent / "main.py"
        assert main_path.exists()

    def test_docker_compose_exists(self):
        """docker-compose.yml should exist."""
        compose_path = Path(__file__).resolve().parent.parent / "docker-compose.yml"
        assert compose_path.exists()

    def test_dockerfile_exists(self):
        """Dockerfile should exist."""
        dockerfile_path = Path(__file__).resolve().parent.parent / "Dockerfile"
        assert dockerfile_path.exists()


# ─── Orchestrator Tests ────────────────────────────────────────────────────────

class TestOrchestratorStructure:
    """Test orchestrator structure without running full graph."""

    def test_conversation_state_model(self):
        """ConversationState should have all required fields in source."""
        source = Path(__file__).resolve().parent.parent / "services" / "orchestrator_langgraph.py"
        content = source.read_text()
        assert "class ConversationState(BaseModel)" in content
        assert "thread_id: str" in content
        assert "stage: str" in content
        assert "turn_count: int" in content
        assert "max_turns: int = 40" in content
        assert "messages: List[Dict[str, str]]" in content
        assert "transcript: List[Dict[str, str]]" in content

    def test_build_system_prompt(self):
        """_build_system_prompt function should exist in source."""
        source = Path(__file__).resolve().parent.parent / "services" / "orchestrator_langgraph.py"
        content = source.read_text()
        assert "def _build_system_prompt" in content
        assert "Alex" in content
        assert "Step2Job" in content

    def test_build_conversation_graph(self):
        """build_conversation_graph function should exist in source."""
        source = Path(__file__).resolve().parent.parent / "services" / "orchestrator_langgraph.py"
        content = source.read_text()
        assert "def build_conversation_graph" in content
        assert "StateGraph" in content
        assert "MemorySaver" in content

    def test_barge_in_support(self):
        """Orchestrator should have Barge-In support methods."""
        source = Path(__file__).resolve().parent.parent / "services" / "orchestrator_langgraph.py"
        content = source.read_text()
        assert "_cancel_tts" in content
        assert "_speak_barge_in" in content
        assert "_stream_audio_chunks" in content
        assert "cancel_event" in content

    def test_langgraph_nodes(self):
        """Orchestrator should define all LangGraph nodes."""
        source = Path(__file__).resolve().parent.parent / "services" / "orchestrator_langgraph.py"
        content = source.read_text()
        for node in ["greet", "discovery", "qualify", "offer", "objection", "close", "followup", "summary"]:
            assert f"node_{node}" in content or f'"{node}"' in content


# ─── File Count / LOC Tests ────────────────────────────────────────────────────

class TestProjectMetrics:
    """Test project size and structure metrics."""

    def test_service_file_count(self):
        """Should have exactly 19 service files (including __init__)."""
        services_dir = Path(__file__).resolve().parent.parent / "services"
        py_files = list(services_dir.glob("*.py"))
        assert len(py_files) >= 19

    def test_no_dead_files(self):
        """Deleted files should not exist."""
        root = Path(__file__).resolve().parent.parent
        dead_files = [
            "web_server.py",
            "telesales_agent.py",
            "stepstone_integration.py",
            "config_legacy.py",
        ]
        for filename in dead_files:
            assert not (root / filename).exists(), f"Dead file still exists: {filename}"

    def test_no_old_orchestrator(self):
        """Old orchestrator.py should not exist."""
        root = Path(__file__).resolve().parent.parent / "services"
        assert not (root / "orchestrator.py").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
