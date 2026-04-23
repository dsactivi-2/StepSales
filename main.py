#!/usr/bin/env python3
"""
Stepsales Production System - Main Entry Point
Unified service launcher for the AI-powered outbound sales platform.
Combines Telnyx telephony, Deepgram STT, ElevenLabs TTS, OpenAI LLM,
Stripe Billing, and persistent storage into a single operational system.
"""

import asyncio
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from config.settings import AppConfig
from services.telnyx_gateway import TelnyxGateway
from services.deepgram_stt import DeepgramSTT
from services.elevenlabs_tts import ElevenLabsTTS
from services.stripe_billing import StripeBilling
from services.persistence import PersistenceService
from services.lead_intel import LeadIntelService
from services.orchestrator_langgraph import LangGraphOrchestrator
from services.fulfillment import FulfillmentService, JobAdSubmission
from services.cadence import OutboundCadence, CadenceSequence
from services.knowledgebase import KnowledgebaseService
from services.agent_coach import AgentCoachService
from services.sla_escalation import SLAEscalationService, SLAPolicy
from services.analytics import AnalyticsService

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "stepsales_main.log"),
    ],
)
logger = logging.getLogger("stepsales.main")

app = FastAPI(title="Stepsales API", version="1.0.0")
_system = None

class CallRequest(BaseModel):
    phone: str
    lead_id: str | None = None

class CampaignRequest(BaseModel):
    phones: list[str]
    lead_id: str | None = None

class JobAdRequest(BaseModel):
    title: str
    company: str
    description: str
    location: str
    employment_type: str = "full_time"
    salary_range: str = ""
    requirements: list[str] = []
    benefits: list[str] = []
    contact_email: str = ""
    contact_phone: str = ""
    duration_days: int = 30

class CadenceRequest(BaseModel):
    lead_id: str
    phone: str
    company: str
    max_call_attempts: int = 3
    email_fallback: bool = True

class IntentRequest(BaseModel):
    user_input: str
    current_stage: str = "discovery"
    agent_response: str = ""

class CoachAnalyzeRequest(BaseModel):
    call_id: str
    speaker: str
    text: str
    stage: str = "discovery"

class CoachScoreRequest(BaseModel):
    call_id: str

class KBSearchRequest(BaseModel):
    query: str
    top_k: int = 3
    category: str = ""

class SLARequest(BaseModel):
    policy: str
    entity_id: str
    deadline_hours: float = 24

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/call")
async def trigger_call(req: CallRequest):
    if not _system or not _system.orchestrator:
        raise HTTPException(503, "System not initialized")
    try:
        result = await _system.orchestrator.start_outbound_call(
            phone_number=req.phone,
            lead_id=req.lead_id,
        )
        return {"success": True, "call": str(result)}
    except Exception as e:
        logger.error(f"Call trigger failed: {e}")
        raise HTTPException(500, str(e))

@app.get("/leads")
async def get_leads():
    if not _system or not _system.lead_intel:
        raise HTTPException(503, "System not initialized")
    queue = await _system.lead_intel.generate_lead_queue()
    return {"leads": queue[:20], "total": len(queue)}

@app.post("/invoice")
async def trigger_invoice(lead_id: str, email: str, name: str, company: str):
    if not _system or not _system.orchestrator:
        raise HTTPException(503, "System not initialized")
    result = await _system.orchestrator.create_invoice_for_lead(
        lead_id=lead_id,
        customer_email=email,
        customer_name=name,
        customer_company=company,
        items=[{"description": "Multiposting StepStone + Indeed", "amount_cents": 649000, "currency": "eur"}],
    )
    return result

@app.post("/intent")
async def classify_intent(req: IntentRequest):
    if not _system or not _system.orchestrator:
        raise HTTPException(503, "System not initialized")
    from services.intent_classifier import IntentClassifier
    classifier = IntentClassifier(_system.config)
    result = await classifier.classify(
        user_input=req.user_input,
        current_stage=req.current_stage,
        agent_response=req.agent_response,
    )
    next_stage = classifier.intent_to_stage(result)
    return {
        "intent": result.intent.value,
        "confidence": result.confidence,
        "keywords": result.keywords,
        "needs_followup": result.needs_followup,
        "suggested_stage": next_stage,
    }

@app.post("/fulfill")
async def submit_job_ad(req: JobAdRequest):
    if not _system or not _system.fulfillment:
        raise HTTPException(503, "System not initialized")
    ad = JobAdSubmission({
        "title": req.title,
        "company": req.company,
        "description": req.description,
        "location": req.location,
        "employment_type": req.employment_type,
        "salary_range": req.salary_range,
        "requirements": req.requirements,
        "benefits": req.benefits,
        "contact_email": req.contact_email,
        "contact_phone": req.contact_phone,
        "duration_days": req.duration_days,
    })
    validation = await _system.fulfillment.validate_ad(ad)
    return {"validation": validation, "ad": {"title": ad.title, "company": ad.company}}

@app.post("/fulfill/multiposting")
async def submit_multiposting(req: JobAdRequest):
    if not _system or not _system.fulfillment:
        raise HTTPException(503, "System not initialized")
    ad = JobAdSubmission({
        "title": req.title, "company": req.company, "description": req.description,
        "location": req.location, "employment_type": req.employment_type,
        "salary_range": req.salary_range, "requirements": req.requirements,
        "benefits": req.benefits, "contact_email": req.contact_email,
        "contact_phone": req.contact_phone, "duration_days": req.duration_days,
    })
    return await _system.fulfillment.submit_multiposting(ad)

@app.post("/cadence")
async def create_cadence(req: CadenceRequest):
    if not _system or not _system.cadence:
        raise HTTPException(503, "System not initialized")
    seq = _system.cadence.create_sequence(
        lead_id=req.lead_id,
        phone=req.phone,
        company=req.company,
        max_call_attempts=req.max_call_attempts,
        email_fallback=req.email_fallback,
    )
    return {"lead_id": req.lead_id, "steps": len(seq.steps), "sequence": "created"}

@app.get("/cadence/status")
async def get_cadence_status():
    if not _system or not _system.cadence:
        raise HTTPException(503, "System not initialized")
    return _system.cadence.get_queue_status()

@app.post("/coach/analyze")
async def coach_analyze(req: CoachAnalyzeRequest):
    if not _system or not _system.coach:
        raise HTTPException(503, "System not initialized")
    hints = _system.coach.analyze_turn(req.call_id, req.speaker, req.text, req.stage)
    return {"hints": [h.to_dict() for h in hints], "call_id": req.call_id}

@app.post("/coach/score")
async def coach_score(req: CoachScoreRequest):
    if not _system or not _system.coach:
        raise HTTPException(503, "System not initialized")
    score = _system.coach.score_call(req.call_id)
    return score.to_dict()

@app.get("/coach/history")
async def coach_history(limit: int = 20):
    if not _system or not _system.coach:
        raise HTTPException(503, "System not initialized")
    return {"history": _system.coach.get_qa_history(limit), "average": _system.coach.get_avg_score()}

@app.get("/kb/documents")
async def kb_list_documents():
    if not _system or not _system.knowledgebase:
        raise HTTPException(503, "System not initialized")
    docs = await _system.knowledgebase.get_all_documents()
    return {"documents": docs, "count": len(docs)}

@app.post("/kb/search")
async def kb_search(req: KBSearchRequest):
    if not _system or not _system.knowledgebase:
        raise HTTPException(503, "System not initialized")
    results = await _system.knowledgebase.search(req.query, req.top_k, req.category or None)
    return {"query": req.query, "results": results, "count": len(results)}

@app.get("/kb/context/{stage}")
async def kb_context(stage: str, user_input: str = ""):
    if not _system or not _system.knowledgebase:
        raise HTTPException(503, "System not initialized")
    context = await _system.knowledgebase.get_context_for_stage(stage, user_input)
    return {"stage": stage, "context": context}

@app.post("/sla/create")
async def sla_create(req: SLARequest):
    if not _system or not _system.sla:
        raise HTTPException(503, "System not initialized")
    policy_map = {p.value: p for p in SLAPolicy}
    policy = policy_map.get(req.policy)
    if not policy:
        raise HTTPException(400, f"Unknown policy: {req.policy}. Valid: {list(policy_map.keys())}")
    event = _system.sla.create_event(policy, req.entity_id, req.deadline_hours)
    return event.to_dict()

@app.get("/sla/active")
async def sla_active(severity: str = ""):
    if not _system or not _system.sla:
        raise HTTPException(503, "System not initialized")
    events = _system.sla.get_active_events()
    return {"events": [e.to_dict() for e in events], "stats": _system.sla.get_stats()}

@app.get("/sla/overdue")
async def sla_overdue():
    if not _system or not _system.sla:
        raise HTTPException(503, "System not initialized")
    events = _system.sla.get_overdue_events()
    return {"events": [e.to_dict() for e in events], "count": len(events)}

@app.post("/sla/resolve/{event_id}")
async def sla_resolve(event_id: str, note: str = ""):
    if not _system or not _system.sla:
        raise HTTPException(503, "System not initialized")
    success = _system.sla.resolve_event(event_id, note)
    return {"success": success, "event_id": event_id}

@app.get("/analytics")
async def get_analytics():
    if not _system or not _system.analytics:
        raise HTTPException(503, "System not initialized")
    return _system.analytics.get_summary()

@app.get("/analytics/funnel")
async def get_funnel():
    if not _system or not _system.analytics:
        raise HTTPException(503, "System not initialized")
    return _system.analytics.get_funnel()

@app.get("/analytics/forecast")
async def get_forecast():
    if not _system or not _system.analytics:
        raise HTTPException(503, "System not initialized")
    return _system.analytics.get_forecast()

@app.get("/analytics/objections")
async def get_objections():
    if not _system or not _system.analytics:
        raise HTTPException(503, "System not initialized")
    return _system.analytics.get_objection_analysis()

@app.post("/analytics/record-call")
async def record_call(duration: float, stage: str, deal_value: float = 0):
    if not _system or not _system.analytics:
        raise HTTPException(503, "System not initialized")
    _system.analytics.record_call(duration, stage, deal_value)
    return {"recorded": True}

@app.get("/status")
async def full_status():
    return {
        "healthy": True,
        "services": {
            "orchestrator": _system.orchestrator is not None,
            "lead_intel": _system.lead_intel is not None,
            "billing": _system.billing is not None,
            "fulfillment": _system.fulfillment is not None,
            "cadence": _system.cadence is not None,
            "knowledgebase": _system.knowledgebase is not None,
            "coach": _system.coach is not None,
        },
        "cadence": _system.cadence.get_queue_status() if _system.cadence else {},
        "coach_avg": _system.coach.get_avg_score() if _system.coach else {},
        "kb_docs": len(_system.knowledgebase._local_cache) if _system.knowledgebase else 0,
        "timestamp": datetime.utcnow().isoformat(),
    }


class StepsalesSystem:
    """Main system coordinator for all Stepsales services."""

    def __init__(self):
        self.config = AppConfig
        self.orchestrator = None
        self.lead_intel = None
        self.billing = None
        self.telnyx = None
        self.fulfillment = None
        self.cadence = None
        self.knowledgebase = None
        self.coach = None
        self.sla = None
        self.analytics = None
        self._running = False

    async def initialize(self):
        """Validate config and initialize all services."""
        logger.info("=" * 60)
        logger.info("Stepsales Production System - Initializing")
        logger.info("=" * 60)

        errors = self.config.validate()
        if errors:
            for err in errors:
                logger.error(f"Config error: {err}")
            logger.warning("Some services may not function without proper API keys")

        self.orchestrator = LangGraphOrchestrator(self.config)
        await self.orchestrator.initialize()

        self.lead_intel = LeadIntelService(self.config)
        self.billing = StripeBilling(self.config)
        self.fulfillment = FulfillmentService(self.config)
        self.cadence = OutboundCadence(self.config, self.orchestrator)
        self.knowledgebase = KnowledgebaseService(self.config)
        await self.knowledgebase.initialize()
        self.coach = AgentCoachService(self.config)
        self.sla = SLAEscalationService(self.config)
        await self.sla.initialize()
        self.analytics = AnalyticsService(self.config)
        await self.analytics.initialize()

        logger.info("All services initialized successfully")
        self._running = True

    async def run_outbound_campaign(self, phone_numbers: list, context: dict = None):
        """Run outbound call campaign to a list of phone numbers."""
        logger.info(f"Starting outbound campaign: {len(phone_numbers)} numbers")

        for i, number in enumerate(phone_numbers):
            if not self._running:
                logger.info("Campaign stopped by user")
                break

            logger.info(f"[{i+1}/{len(phone_numbers)}] Calling {number}")
            try:
                result = await self.orchestrator.start_outbound_call(
                    phone_number=number,
                    context=context,
                )
                logger.info(f"Call result: {json.dumps(result, indent=2)}")

                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Call to {number} failed: {e}")

        logger.info("Campaign completed")

    async def process_lead_queue(self, queries: list = None):
        """Generate lead queue and process cross-posting gaps."""
        queries = queries or ["IT", "Software", "Pflege", "Vertrieb"]
        logger.info(f"Processing lead queue for: {queries}")

        queue = await self.lead_intel.generate_lead_queue(queries=queries)
        logger.info(f"Found {len(queue)} leads with cross-posting gaps")

        for lead in queue[:5]:
            logger.info(
                f"Lead: {lead['company']} | "
                f"Stepstone: {lead.get('has_stepstone')} | "
                f"Indeed: {lead.get('has_indeed')} | "
                f"Opportunity: {lead.get('opportunity')}"
            )

        return queue

    async def handle_stripe_webhook(self, event_data: dict):
        """Process Stripe webhook for invoice/payment state."""
        result = await self.billing.handle_webhook(event_data)
        event_type = event_data.get("type", "")

        if "invoice.payment_succeeded" in event_type:
            invoice_id = result.get("invoice_id", "")
            await self.persistence.update_invoice_status(
                invoice_id, "paid", datetime.utcnow()
            )
            logger.info(f"Payment confirmed for invoice {invoice_id}")

        return result

    async def shutdown(self):
        """Gracefully shutdown all services."""
        logger.info("Shutting down Stepsales system...")
        self._running = False

        if self.orchestrator:
            await self.orchestrator.close()
        if self.lead_intel:
            await self.lead_intel.close()
        if self.billing:
            await self.billing.close()
        if self.fulfillment:
            await self.fulfillment.close()
        if self.cadence:
            self.cadence.stop_scheduler()
        if self.knowledgebase:
            await self.knowledgebase.close()
        if self.sla:
            self.sla.stop_monitor()

        logger.info("All services shut down")


async def main():
    global _system
    system = StepsalesSystem()
    _system = system

    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(system.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await system.initialize()

        if len(sys.argv) > 1:
            command = sys.argv[1]

            if command == "leads":
                queue = await system.process_lead_queue()
                print(json.dumps(queue[:10], indent=2, ensure_ascii=False))

            elif command == "call" and len(sys.argv) > 2:
                phone = sys.argv[2]
                lead_id = sys.argv[3] if len(sys.argv) > 3 else None
                await system.orchestrator.start_outbound_call(
                    phone_number=phone,
                    lead_id=lead_id,
                )
                await asyncio.sleep(120)
                await system.shutdown()

            elif command == "invoice":
                result = await system.orchestrator.create_invoice_for_lead(
                    lead_id="demo-lead",
                    customer_email="demo@example.de",
                    customer_name="Max Mustermann",
                    customer_company="Test GmbH",
                    items=[
                        {
                            "description": "Multiposting StepStone + Indeed (8 Anzeigen)",
                            "amount_cents": 649000,
                            "currency": "eur",
                        }
                    ],
                )
                print(json.dumps(result, indent=2))

            else:
                print("Usage: python main.py [leads|call <phone>|invoice]")
        else:
            logger.info("Starting REST API server on port 8010")
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=8010,
                log_level="info",
            )
            server = uvicorn.Server(config)
            await server.serve()

    except KeyboardInterrupt:
        pass
    finally:
        await system.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
