"""
SLA Escalation Service
Timer-based escalation for missing data, overdue follow-ups,
and policy violations in the Stepsales pipeline.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from config.settings import AppConfig

logger = logging.getLogger("stepsales.sla")


class SLAPolicy(str, Enum):
    FOLLOWUP_48H = "followup_48h"
    INVOICE_7D = "invoice_7d"
    LEAD_RESPONSE_24H = "lead_response_24h"
    FULFILLMENT_48H = "fulfillment_48h"
    MEMORY_EXPIRY = "memory_expiry"


class SLASeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BREACHED = "breached"


class SLAEvent:
    """Represents an SLA event that needs attention."""

    def __init__(self, event_id: str, policy: SLAPolicy, entity_id: str, deadline: datetime, severity: SLASeverity = SLASeverity.WARNING):
        self.id = event_id
        self.policy = policy
        self.entity_id = entity_id
        self.deadline = deadline
        self.severity = severity
        self.created_at = datetime.utcnow()
        self.escalation_count = 0
        self.resolved = False
        self.resolved_at: Optional[datetime] = None
        self.notes: List[str] = []

    @property
    def is_overdue(self) -> bool:
        return datetime.utcnow() > self.deadline and not self.resolved

    @property
    def time_remaining(self) -> timedelta:
        return self.deadline - datetime.utcnow()

    @property
    def hours_remaining(self) -> float:
        return self.time_remaining.total_seconds() / 3600

    def escalate(self) -> SLASeverity:
        """Escalate the event to the next severity level."""
        self.escalation_count += 1
        severity_order = [SLASeverity.INFO, SLASeverity.WARNING, SLASeverity.CRITICAL, SLASeverity.BREACHED]
        current_idx = severity_order.index(self.severity)
        if current_idx < len(severity_order) - 1:
            self.severity = severity_order[current_idx + 1]
        return self.severity

    def resolve(self, note: str = ""):
        """Mark the SLA event as resolved."""
        self.resolved = True
        self.resolved_at = datetime.utcnow()
        if note:
            self.notes.append(note)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "policy": self.policy.value,
            "entity_id": self.entity_id,
            "deadline": self.deadline.isoformat(),
            "severity": self.severity.value,
            "escalation_count": self.escalation_count,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "hours_remaining": round(self.hours_remaining, 1),
            "is_overdue": self.is_overdue,
            "notes": self.notes,
        }


class SLAEscalationService:
    """Manages SLA events, deadlines, and automated escalations."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._events: Dict[str, SLAEvent] = {}
        self._running = False
        self._check_interval = 300
        self._on_escalation: Optional[Callable] = None

    def register_escalation_handler(self, handler: Callable):
        self._on_escalation = handler

    async def initialize(self):
        self._running = True
        logger.info("SLA Escalation Service initialized")

    def create_event(self, policy: SLAPolicy, entity_id: str, deadline_hours: float, severity: SLASeverity = SLASeverity.WARNING) -> SLAEvent:
        """Create a new SLA event with a deadline."""
        event_id = f"sla-{policy.value}-{entity_id}-{int(datetime.utcnow().timestamp())}"
        deadline = datetime.utcnow() + timedelta(hours=deadline_hours)

        event = SLAEvent(
            event_id=event_id,
            policy=policy,
            entity_id=entity_id,
            deadline=deadline,
            severity=severity,
        )

        self._events[event_id] = event
        logger.info(f"SLA event created: {event_id} (policy={policy.value}, deadline={deadline_hours}h)")
        return event

    def create_followup_sla(self, lead_id: str) -> SLAEvent:
        """Create a 48h follow-up SLA for a lead."""
        return self.create_event(
            policy=SLAPolicy.FOLLOWUP_48H,
            entity_id=lead_id,
            deadline_hours=48,
            severity=SLASeverity.WARNING,
        )

    def create_invoice_sla(self, invoice_id: str) -> SLAEvent:
        """Create a 7-day invoice payment SLA."""
        return self.create_event(
            policy=SLAPolicy.INVOICE_7D,
            entity_id=invoice_id,
            deadline_hours=168,
            severity=SLASeverity.INFO,
        )

    def create_lead_response_sla(self, lead_id: str) -> SLAEvent:
        """Create a 24h lead response SLA."""
        return self.create_event(
            policy=SLAPolicy.LEAD_RESPONSE_24H,
            entity_id=lead_id,
            deadline_hours=24,
            severity=SLASeverity.WARNING,
        )

    def resolve_event(self, event_id: str, note: str = "") -> bool:
        """Resolve an SLA event."""
        event = self._events.get(event_id)
        if event:
            event.resolve(note)
            logger.info(f"SLA event resolved: {event_id}")
            return True
        return False

    def get_active_events(self, severity: SLASeverity = None) -> List[SLAEvent]:
        """Get all active (unresolved) SLA events."""
        events = [e for e in self._events.values() if not e.resolved]
        if severity:
            events = [e for e in events if e.severity == severity]
        return sorted(events, key=lambda e: e.deadline)

    def get_overdue_events(self) -> List[SLAEvent]:
        """Get all overdue events."""
        return [e for e in self._events.values() if e.is_overdue]

    async def check_and_escalate(self) -> List[SLAEvent]:
        """Check all active events and escalate overdue ones."""
        escalated = []

        for event in self.get_active_events():
            if event.is_overdue:
                old_severity = event.severity
                new_severity = event.escalate()

                if new_severity != old_severity:
                    logger.warning(f"SLA escalated: {event.id} {old_severity.value} → {new_severity.value}")
                    escalated.append(event)

                    if self._on_escalation:
                        await self._on_escalation(event)

        return escalated

    async def start_monitor(self, check_interval: int = 300):
        """Start the SLA monitoring loop."""
        self._check_interval = check_interval
        logger.info(f"SLA monitor started (interval: {check_interval}s)")

        while self._running:
            try:
                escalated = await self.check_and_escalate()
                if escalated:
                    logger.info(f"Escalated {len(escalated)} SLA events")
            except Exception as e:
                logger.error(f"SLA monitor error: {e}")

            await asyncio.sleep(self._check_interval)

    def stop_monitor(self):
        self._running = False
        logger.info("SLA monitor stopped")

    def get_stats(self) -> dict:
        """Get SLA statistics."""
        total = len(self._events)
        active = len(self.get_active_events())
        overdue = len(self.get_overdue_events())
        resolved = total - active

        severity_counts = {}
        for event in self.get_active_events():
            severity_counts[event.severity.value] = severity_counts.get(event.severity.value, 0) + 1

        policy_counts = {}
        for event in self._events.values():
            policy_counts[event.policy.value] = policy_counts.get(event.policy.value, 0) + 1

        return {
            "total": total,
            "active": active,
            "overdue": overdue,
            "resolved": resolved,
            "severity_breakdown": severity_counts,
            "policy_breakdown": policy_counts,
        }
