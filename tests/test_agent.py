#!/usr/bin/env python3
"""
Unit tests for Telesales Agent
"""

import pytest
from telesales_agent import TelesalesAgent
from tools import Lead, qualification, demo_booking, follow_up, crm


class TestTelesalesAgent:
    """Test agent initialization and core functionality"""

    def test_agent_initialization(self):
        """Test agent can be initialized"""
        agent = TelesalesAgent()
        assert agent.call_id
        assert agent.start_time
        assert agent.stepstone is not None

    def test_system_instructions(self):
        """Test system instructions are formatted"""
        agent = TelesalesAgent()
        instructions = agent.get_system_prompt()
        assert "Alex" in instructions
        assert "Telesales" in instructions or "Telesales" in instructions
        assert "deutsch" in instructions.lower() or "german" in instructions.lower()

    def test_tool_definitions(self):
        """Test tool definitions are valid"""
        agent = TelesalesAgent()
        tools = agent.build_tool_definitions()

        assert len(tools) == 4
        tool_names = [t["name"] for t in tools]
        assert "search_jobs" in tool_names
        assert "qualify_lead" in tool_names
        assert "schedule_demo" in tool_names
        assert "send_followup" in tool_names

    def test_search_jobs_tool(self):
        """Test search_jobs tool call"""
        agent = TelesalesAgent()
        result = agent.handle_tool_call("search_jobs", {"search_terms": ["Developer"]})

        assert result["success"] is True
        assert "jobs_found" in result
        assert "Developer" in agent.job_interests

    def test_qualify_lead_tool(self):
        """Test qualify_lead tool call"""
        agent = TelesalesAgent()
        result = agent.handle_tool_call(
            "qualify_lead",
            {
                "company_name": "TestCorp",
                "contact_name": "John Doe",
                "contact_email": "john@test.de",
                "contact_phone": "+49123456789",
                "job_interests": ["Engineer"],
            },
        )

        assert result["success"] is True
        assert "LEAD-" in result["lead_id"]
        assert agent.current_qualification_score > 0

    def test_schedule_demo_tool(self):
        """Test schedule_demo tool"""
        agent = TelesalesAgent()
        result = agent.handle_tool_call(
            "schedule_demo",
            {"email": "test@example.de", "preferred_date": "2026-04-24", "preferred_time": "10:00"},
        )

        assert result["success"] is True
        assert "test@example.de" in str(result)


class TestQualificationTool:
    """Test lead qualification"""

    def test_next_question(self):
        """Test qualification questions"""
        q = qualification
        question = q.next_question([])
        assert question is not None

    def test_extract_info(self):
        """Test info extraction"""
        q = qualification
        result = q.extract_info("Großunternehmen, 500+ Mitarbeiter", "company")
        assert result is True
        assert "company" in q.collected_info

    def test_is_complete(self):
        """Test completion check"""
        q = qualification
        assert q.is_complete() is False


class TestLead:
    """Test Lead data model"""

    def test_lead_creation(self):
        """Test creating a lead"""
        lead = Lead(
            company_name="TestCorp",
            contact_name="Jane Doe",
            contact_email="jane@test.de",
            contact_phone="+49987654321",
            job_interests=["Engineer", "Developer"],
            call_id="test-123",
        )

        assert lead.company_name == "TestCorp"
        assert len(lead.job_interests) == 2

    def test_lead_score_calculation(self):
        """Test lead quality scoring"""
        lead = Lead(
            company_name="TechCorp",
            contact_name="Max",
            contact_email="max@test.de",
            contact_phone="+49123456789",
            job_interests=["Developer"],
            budget_range="50000-75000",
            timeline="In 2 Wochen",
            call_id="test-456",
        )

        score = lead.calculate_score()
        assert 0 <= score <= 100
        assert score > 50  # Should be high-quality lead

    def test_lead_to_dict(self):
        """Test lead serialization"""
        lead = Lead(
            company_name="Corp",
            contact_name="John",
            contact_email="john@corp.de",
            contact_phone="+49111111111",
            job_interests=["Role1"],
            call_id="test-789",
        )

        lead_dict = lead.to_dict()
        assert lead_dict["company_name"] == "Corp"
        assert "created_at" in lead_dict


class TestCRMTool:
    """Test CRM operations"""

    def test_save_lead(self):
        """Test saving lead to CRM"""
        crm.leads_db.clear()  # Reset
        lead = Lead(
            company_name="SaveCorp",
            contact_name="Handler",
            contact_email="handler@savecorp.de",
            contact_phone="+49555555555",
            job_interests=["Manager"],
            call_id="crm-test",
        )

        result = crm.save_lead(lead)
        assert result["success"] is True
        assert "LEAD-" in result["lead_id"]
        assert len(crm.leads_db) > 0

    def test_get_leads(self):
        """Test retrieving leads"""
        leads = crm.get_leads(filter_score_min=0)
        assert isinstance(leads, list)


class TestDemoBookingTool:
    """Test demo booking"""

    def test_check_availability(self):
        """Test getting available slots"""
        slots = demo_booking.check_availability()
        assert len(slots) > 0
        assert all(isinstance(s, str) for s in slots)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
