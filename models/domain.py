"""
Data Models for Stepsales Production System
SQLAlchemy ORM models for persistent storage
"""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class LeadStatus(str, Enum):
    NEW = "new"
    CONNECTED = "connected"
    QUALIFIED = "qualified"
    OFFER_SENT = "offer_sent"
    INVOICED = "invoiced"
    PAID = "paid"
    FULFILLED = "fulfilled"
    LOST = "lost"
    DNC = "dnc"


class CallStage(str, Enum):
    GREET = "greet"
    DISCOVERY = "discovery"
    QUALIFY = "qualify"
    OBJECTION = "objection"
    OFFER = "offer"
    CLOSE = "close"
    FOLLOWUP = "followup"


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    industry = Column(String)
    website = Column(String)
    company_size = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contacts = relationship("Contact", back_populates="company")
    leads = relationship("Lead", back_populates="company")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"))
    first_name = Column(String, nullable=False)
    last_name = Column(String)
    email = Column(String)
    phone = Column(String)
    role = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="contacts")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"))
    contact_id = Column(String, ForeignKey("contacts.id"))
    status = Column(String, default=LeadStatus.NEW.value)
    source = Column(String)
    open_roles = Column(Integer, default=0)
    urgency = Column(String, default="medium")
    budget_range = Column(String)
    timeline = Column(String)
    pain_points = Column(Text)
    qualification_score = Column(Integer, default=0)
    job_interests = Column(JSON, default=list)
    lead_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="leads")
    calls = relationship("Call", back_populates="lead")
    invoices = relationship("Invoice", back_populates="lead")


class Call(Base):
    __tablename__ = "calls"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String, ForeignKey("leads.id"))
    session_id = Column(String)
    telnyx_call_id = Column(String)
    stage = Column(String, default=CallStage.GREET.value)
    direction = Column(String, default="outbound")
    status = Column(String, default="initiated")
    duration_seconds = Column(Integer, default=0)
    transcript = Column(JSON, default=list)
    summary = Column(Text)
    objections = Column(JSON, default=list)
    contact_info = Column(JSON, default=dict)
    qa_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)

    lead = relationship("Lead", back_populates="calls")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String, ForeignKey("leads.id"))
    stripe_invoice_id = Column(String)
    stripe_customer_id = Column(String)
    amount_cents = Column(Integer)
    currency = Column(String, default="eur")
    status = Column(String, default="draft")
    description = Column(Text)
    items = Column(JSON, default=list)
    hosted_invoice_url = Column(String)
    paid_at = Column(DateTime)
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="invoices")


class Fulfillment(Base):
    __tablename__ = "fulfillments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String)
    invoice_id = Column(String)
    job_ad_data = Column(JSON, default=dict)
    portals = Column(JSON, default=list)
    status = Column(String, default="pending")
    submission_ids = Column(JSON, default=dict)
    errors = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


class SLAEvent(Base):
    __tablename__ = "sla_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type = Column(String)
    entity_id = Column(String)
    policy = Column(String)
    stage = Column(String)
    deadline = Column(DateTime)
    status = Column(String, default="pending")
    reminder_count = Column(Integer, default=0)
    escalated = Column(Boolean, default=False)
    audit_trail = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)


class MemoryFact(Base):
    __tablename__ = "memory_facts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, nullable=False)
    thread_id = Column(String)
    fact_type = Column(String)
    content = Column(Text)
    source = Column(String)
    confidence = Column(Float, default=1.0)
    ttl_days = Column(Integer, default=180)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
