"""
Outbound Cadence Scheduler
Automated lead queue processing with retry logic,
email fallback, and intelligent scheduling.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from config.settings import AppConfig
from services.persistence import PersistenceService

logger = logging.getLogger("stepsales.cadence")


class CadenceStep:
    """A single step in an outbound cadence."""

    def __init__(self, step_type: str, delay_hours: float, config: dict = None):
        self.step_type = step_type
        self.delay_hours = delay_hours
        self.config = config or {}
        self.attempted = False
        self.succeeded = False
        self.attempted_at: Optional[datetime] = None


class CadenceSequence:
    """Multi-step outbound cadence for a single lead."""

    def __init__(self, lead_id: str, phone: str, company: str):
        self.lead_id = lead_id
        self.phone = phone
        self.company = company
        self.steps: List[CadenceStep] = []
        self.current_step = 0
        self.created_at = datetime.utcnow()
        self.completed = False
        self.failed = False

    def add_call(self, delay_hours: float, max_retries: int = 2):
        """Add a call step to the cadence."""
        for i in range(max_retries + 1):
            self.steps.append(CadenceStep(
                step_type="call",
                delay_hours=delay_hours + (i * 24),
                config={"retry": i, "max_retries": max_retries},
            ))

    def add_email(self, delay_hours: float):
        """Add an email fallback step."""
        self.steps.append(CadenceStep(
            step_type="email",
            delay_hours=delay_hours,
            config={"template": "followup_multiposting"},
        ))

    @property
    def next_step(self) -> Optional[CadenceStep]:
        """Get the next pending step."""
        for step in self.steps[self.current_step:]:
            if not step.attempted:
                due_time = self.created_at + timedelta(hours=step.delay_hours)
                if datetime.utcnow() >= due_time:
                    return step
        return None

    @property
    def is_complete(self) -> bool:
        """Check if all steps have been attempted."""
        return all(s.attempted for s in self.steps)


class OutboundCadence:
    """Manages outbound call cadences with retry and email fallback."""

    def __init__(self, config=None, orchestrator=None):
        self.config = config or AppConfig
        self.orchestrator = orchestrator
        self.persistence: Optional[PersistenceService] = None
        self._sequences: Dict[str, CadenceSequence] = {}
        self._running = False
        self._check_interval = 60
        self._on_call_complete: Optional[Callable] = None
        self._on_sequence_complete: Optional[Callable] = None

    def register_call_complete_handler(self, handler: Callable):
        self._on_call_complete = handler

    def register_sequence_complete_handler(self, handler: Callable):
        self._on_sequence_complete = handler

    async def initialize(self, persistence: PersistenceService):
        self.persistence = persistence
        await self.persistence.initialize()
        logger.info("Outbound Cadence initialized")

    def create_sequence(
        self,
        lead_id: str,
        phone: str,
        company: str,
        max_call_attempts: int = 3,
        email_fallback: bool = True,
    ) -> CadenceSequence:
        """Create a new cadence sequence for a lead."""
        seq = CadenceSequence(lead_id, phone, company)

        seq.add_call(delay_hours=0, max_retries=max_call_attempts - 1)

        if email_fallback:
            seq.add_email(delay_hours=(max_call_attempts * 24) + 4)

        self._sequences[lead_id] = seq
        logger.info(f"Cadence created for {lead_id}: {company} ({phone}) - {len(seq.steps)} steps")

        return seq

    def add_phone_to_queue(self, phone: str, lead_id: str = None, context: dict = None):
        """Add a phone number to the immediate call queue."""
        self._immediate_queue.append({
            "phone": phone,
            "lead_id": lead_id,
            "context": context or {},
            "added_at": datetime.utcnow(),
        })

    async def process_pending_sequences(self):
        """Process all sequences that have due steps."""
        processed = 0

        for lead_id, seq in self._sequences.items():
            if seq.completed or seq.failed:
                continue

            step = seq.next_step
            if not step:
                continue

            step.attempted = True
            step.attempted_at = datetime.utcnow()
            seq.current_step += 1

            if step.step_type == "call":
                success = await self._execute_call(seq, step)
                step.succeeded = success

                if success:
                    logger.info(f"Cadence step {seq.current_step}/{len(seq.steps)} succeeded for {lead_id}")
                    break
                else:
                    retry = step.config.get("retry", 0)
                    max_retries = step.config.get("max_retries", 2)
                    if retry >= max_retries:
                        logger.warning(f"All call retries exhausted for {lead_id}")

            elif step.step_type == "email":
                success = await self._execute_email(seq, step)
                step.succeeded = success

            processed += 1

        for lead_id, seq in self._sequences.items():
            if seq.is_complete and not seq.completed:
                seq.completed = True
                logger.info(f"Cadence completed for {lead_id}: {seq.company}")
                if self._on_sequence_complete:
                    await self._on_sequence_complete(seq)

        return processed

    async def _execute_call(self, seq: CadenceSequence, step: CadenceStep) -> bool:
        """Execute a call step."""
        if not self.orchestrator:
            logger.error("No orchestrator available for call execution")
            return False

        try:
            result = await self.orchestrator.start_outbound_call(
                phone_number=seq.phone,
                lead_id=seq.lead_id,
            )

            if self._on_call_complete:
                await self._on_call_complete(seq.lead_id, result)

            return result.get("success", False)

        except Exception as e:
            logger.error(f"Call execution failed for {seq.lead_id}: {e}")
            return False

    async def _execute_email(self, seq: CadenceSequence, step: CadenceStep) -> bool:
        """Execute an email fallback step."""
        logger.info(f"Email fallback for {seq.lead_id}: {seq.company}")
        return True

    async def start_scheduler(self, check_interval: int = 60):
        """Start the cadence scheduler loop."""
        self._running = True
        self._check_interval = check_interval

        logger.info(f"Cadence scheduler started (interval: {check_interval}s)")

        while self._running:
            try:
                processed = await self.process_pending_sequences()
                if processed > 0:
                    logger.info(f"Processed {processed} cadence steps")
            except Exception as e:
                logger.error(f"Cadence scheduler error: {e}")

            await asyncio.sleep(self._check_interval)

    def stop_scheduler(self):
        """Stop the cadence scheduler."""
        self._running = False
        logger.info("Cadence scheduler stopped")

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current cadence queue status."""
        active = sum(1 for s in self._sequences.values() if not s.completed and not s.failed)
        completed = sum(1 for s in self._sequences.values() if s.completed)
        failed = sum(1 for s in self._sequences.values() if s.failed)

        return {
            "total_sequences": len(self._sequences),
            "active": active,
            "completed": completed,
            "failed": failed,
            "sequences": {
                lead_id: {
                    "company": seq.company,
                    "phone": seq.phone,
                    "steps": len(seq.steps),
                    "current_step": seq.current_step,
                    "completed": seq.completed,
                    "failed": seq.failed,
                }
                for lead_id, seq in self._sequences.items()
            },
        }
