"""
Persistence Service
SQLite/PostgreSQL-backed storage for leads, calls, invoices, and memory facts.
SQLAlchemy ORM with async session support.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from config.settings import AppConfig
from models.domain import (
    Base, Company, Contact, Lead, Call, Invoice, Fulfillment, SLAEvent, MemoryFact,
    LeadStatus, CallStage,
)

logger = logging.getLogger("stepsales.persistence")


class PersistenceService:
    """Database service for Stepsales persistent storage."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._engine = None
        self._async_engine = None
        self._session_factory = None

    async def initialize(self):
        """Initialize database engine and create tables."""
        db_url = self.config.persistence.db_url
        logger.info(f"Initializing persistence: {db_url}")

        if db_url.startswith("sqlite"):
            async_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
        elif db_url.startswith("postgresql"):
            async_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        else:
            async_url = db_url

        self._async_engine = create_async_engine(async_url, echo=False)
        self._session_factory = async_sessionmaker(
            self._async_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with self._async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created/verified")

    @asynccontextmanager
    async def session(self):
        """Provide a transactional scope around database operations."""
        if not self._session_factory:
            raise RuntimeError("Persistence not initialized. Call initialize() first.")

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def save_lead(self, lead_data: dict) -> str:
        """Create or update a lead with company/contact info."""
        async with self.session() as s:
            company_name = lead_data.get("company_name", "")
            contact_name = lead_data.get("contact_name", "")
            email = lead_data.get("contact_email", "")
            phone = lead_data.get("contact_phone", "")

            company = (
                await s.execute(select(Company).where(Company.name == company_name))
            ).scalar_one_or_none()

            if not company:
                company = Company(name=company_name, industry=lead_data.get("industry"))
                s.add(company)
                await s.flush()

            contact = None
            if email:
                contact = (
                    await s.execute(select(Contact).where(Contact.email == email))
                ).scalar_one_or_none()

            if not contact:
                parts = contact_name.split(" ", 1) if contact_name else ["", ""]
                contact = Contact(
                    company_id=company.id,
                    first_name=parts[0],
                    last_name=parts[1] if len(parts) > 1 else "",
                    email=email,
                    phone=phone,
                    role=lead_data.get("role"),
                )
                s.add(contact)
                await s.flush()

            lead = Lead(
                company_id=company.id,
                contact_id=contact.id,
                status=lead_data.get("status", LeadStatus.NEW.value),
                source=lead_data.get("source", "outbound_call"),
                open_roles=lead_data.get("open_roles", 0),
                urgency=lead_data.get("urgency", "medium"),
                budget_range=lead_data.get("budget_range"),
                timeline=lead_data.get("timeline"),
                pain_points=lead_data.get("pain_points"),
                job_interests=lead_data.get("job_interests", []),
                qualification_score=lead_data.get("qualification_score", 0),
            )
            s.add(lead)
            await s.flush()

            logger.info(f"Lead saved: {lead.id} ({company_name})")
            return lead.id

    async def save_call(self, call_data: dict) -> str:
        """Save call record with transcript and summary."""
        async with self.session() as s:
            call = Call(
                lead_id=call_data.get("lead_id"),
                session_id=call_data.get("session_id"),
                telnyx_call_id=call_data.get("telnyx_call_id"),
                stage=call_data.get("stage", CallStage.GREET.value),
                direction=call_data.get("direction", "outbound"),
                status=call_data.get("status", "completed"),
                duration_seconds=call_data.get("duration_seconds", 0),
                transcript=call_data.get("transcript", []),
                summary=call_data.get("summary"),
                objections=call_data.get("objections", []),
                contact_info=call_data.get("contact_info", {}),
                qa_score=call_data.get("qa_score"),
                ended_at=call_data.get("ended_at", datetime.utcnow()),
            )
            s.add(call)
            await s.flush()

            if call_data.get("lead_id"):
                stmt = select(Lead).where(Lead.id == call_data["lead_id"])
                lead = (await s.execute(stmt)).scalar_one_or_none()
                if lead:
                    lead.updated_at = datetime.utcnow()
                    if call_data.get("status") == "completed":
                        if lead.status == LeadStatus.NEW.value:
                            lead.status = LeadStatus.CONNECTED.value

            logger.info(f"Call saved: {call.id} ({call_data.get('duration_seconds', 0)}s)")
            return call.id

    async def save_invoice_record(self, invoice_data: dict) -> str:
        """Save invoice tracking record."""
        async with self.session() as s:
            invoice = Invoice(
                lead_id=invoice_data.get("lead_id"),
                stripe_invoice_id=invoice_data.get("stripe_invoice_id"),
                stripe_customer_id=invoice_data.get("stripe_customer_id"),
                amount_cents=invoice_data.get("amount_cents", 0),
                currency=invoice_data.get("currency", "eur"),
                status=invoice_data.get("status", "draft"),
                description=invoice_data.get("description", ""),
                items=invoice_data.get("items", []),
                hosted_invoice_url=invoice_data.get("hosted_invoice_url"),
                due_date=invoice_data.get("due_date"),
            )
            s.add(invoice)
            await s.flush()

            logger.info(f"Invoice record saved: {invoice.id} (stripe: {invoice_data.get('stripe_invoice_id')})")
            return invoice.id

    async def update_invoice_status(self, stripe_invoice_id: str, status: str, paid_at=None):
        """Update invoice status from webhook event."""
        async with self.session() as s:
            stmt = select(Invoice).where(Invoice.stripe_invoice_id == stripe_invoice_id)
            invoice = (await s.execute(stmt)).scalar_one_or_none()
            if invoice:
                invoice.status = status
                if paid_at:
                    invoice.paid_at = paid_at
                if invoice.lead_id:
                    lead_stmt = select(Lead).where(Lead.id == invoice.lead_id)
                    lead = (await s.execute(lead_stmt)).scalar_one_or_none()
                    if lead:
                        lead.status = LeadStatus.PAID.value if status == "paid" else lead.status

    async def save_memory_fact(self, fact_data: dict) -> str:
        """Save a memory fact for long-term customer memory."""
        from datetime import timedelta

        async with self.session() as s:
            ttl_days = fact_data.get("ttl_days", 180)
            fact = MemoryFact(
                customer_id=fact_data["customer_id"],
                thread_id=fact_data.get("thread_id"),
                fact_type=fact_data.get("fact_type", "note"),
                content=fact_data["content"],
                source=fact_data.get("source", "call"),
                confidence=fact_data.get("confidence", 1.0),
                ttl_days=ttl_days,
                expires_at=datetime.utcnow() + timedelta(days=ttl_days),
            )
            s.add(fact)
            await s.flush()
            return fact.id

    async def get_customer_memory(self, customer_id: str) -> List[dict]:
        """Retrieve memory facts for a customer."""
        async with self.session() as s:
            stmt = (
                select(MemoryFact)
                .where(
                    MemoryFact.customer_id == customer_id,
                    MemoryFact.expires_at > datetime.utcnow(),
                )
                .order_by(MemoryFact.created_at.desc())
            )
            facts = (await s.execute(stmt)).scalars().all()

            return [
                {
                    "id": f.id,
                    "type": f.fact_type,
                    "content": f.content,
                    "source": f.source,
                    "confidence": f.confidence,
                    "created_at": f.created_at.isoformat(),
                }
                for f in facts
            ]

    async def get_leads(self, status: str = None, limit: int = 50) -> List[dict]:
        """Query leads with optional status filter."""
        async with self.session() as s:
            stmt = select(Lead).limit(limit)
            if status:
                stmt = stmt.where(Lead.status == status)
            stmt = stmt.order_by(Lead.created_at.desc())
            leads = (await s.execute(stmt)).scalars().all()

            return [
                {
                    "id": l.id,
                    "company_id": l.company_id,
                    "status": l.status,
                    "source": l.source,
                    "open_roles": l.open_roles,
                    "urgency": l.urgency,
                    "qualification_score": l.qualification_score,
                    "created_at": l.created_at.isoformat(),
                }
                for l in leads
            ]

    async def get_sla_pending(self) -> List[dict]:
        """Get SLA events that are pending and past deadline."""
        async with self.session() as s:
            stmt = (
                select(SLAEvent)
                .where(
                    SLAEvent.status == "pending",
                    SLAEvent.deadline < datetime.utcnow(),
                )
            )
            events = (await s.execute(stmt)).scalars().all()

            return [
                {
                    "id": e.id,
                    "entity_type": e.entity_type,
                    "entity_id": e.entity_id,
                    "policy": e.policy,
                    "deadline": e.deadline.isoformat(),
                    "reminder_count": e.reminder_count,
                }
                for e in events
            ]
