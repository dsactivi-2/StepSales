#!/usr/bin/env python3
"""
Telesales tools for qualification, booking, and follow-up
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("stepsales.tools")


@dataclass
class Lead:
    """Lead information from call"""
    company_name: str
    contact_name: str
    contact_email: str
    contact_phone: str
    job_interests: List[str]
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    pain_points: List[str] = None
    qualification_score: int = 0
    created_at: str = ""
    call_id: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.pain_points is None:
            self.pain_points = []

    def to_dict(self) -> Dict:
        return asdict(self)

    def calculate_score(self) -> int:
        """Calculate lead quality score 0-100"""
        score = 0

        # Company information
        if self.company_name:
            score += 10
        if self.contact_name:
            score += 10
        if self.contact_email:
            score += 10

        # Engagement signals
        if self.job_interests:
            score += 20
        if self.budget_range:
            score += 20
        if self.timeline and any(keyword in self.timeline for keyword in ["Woche", "Monat"]):
            score += 30  # Near-term timeline is higher value

        self.qualification_score = min(score, 100)
        return self.qualification_score


class QualificationTool:
    """Qualify leads during calls"""

    QUESTIONS = {
        "company": "Welche Branche und Größe hat Ihr Unternehmen?",
        "hiring_need": "Welche Position/Positionen möchten Sie besetzen?",
        "timeline": "Wie dringend ist der Besetzungsbedarf?",
        "budget": "Welches Budget steht für die Rekrutierung zur Verfügung?",
        "pain_point": "Welche Herausforderungen haben Sie derzeit bei der Personalbeschaffung?",
    }

    def __init__(self):
        self.collected_info: Dict[str, str] = {}

    def next_question(self, conversation_context: List[str]) -> Optional[str]:
        """Get next qualification question based on context"""
        asked = set(self.collected_info.keys())
        unanswered = [q for q in self.QUESTIONS.keys() if q not in asked]

        if not unanswered:
            return None

        return self.QUESTIONS[unanswered[0]]

    def extract_info(self, response: str, question_type: str) -> bool:
        """Extract and store qualification info"""
        if response and len(response.strip()) > 3:
            self.collected_info[question_type] = response
            logger.info(f"Collected {question_type}: {response[:50]}...")
            return True
        return False

    def is_complete(self) -> bool:
        """Check if qualification is complete"""
        required = ["company", "hiring_need", "timeline"]
        return all(q in self.collected_info for q in required)

    def get_lead(
        self,
        contact_name: str,
        contact_email: str,
        contact_phone: str,
        job_interests: List[str],
        call_id: str,
    ) -> Lead:
        """Create Lead object from collected data"""
        return Lead(
            company_name=self.collected_info.get("company", ""),
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            job_interests=job_interests,
            budget_range=self.collected_info.get("budget"),
            timeline=self.collected_info.get("timeline"),
            pain_points=[self.collected_info.get("pain_point", "")],
            call_id=call_id,
        )


class DemoBookingTool:
    """Schedule demo/meeting tool"""

    AVAILABLE_SLOTS = [
        "2026-04-24 10:00",
        "2026-04-24 14:00",
        "2026-04-25 09:00",
        "2026-04-25 15:00",
        "2026-04-27 11:00",
    ]

    def check_availability(self) -> List[str]:
        """Get available demo time slots"""
        return self.AVAILABLE_SLOTS

    def book_slot(self, email: str, time_slot: str) -> Dict:
        """Book a demo slot"""
        if time_slot not in self.AVAILABLE_SLOTS:
            return {"success": False, "message": f"Slot {time_slot} nicht verfügbar"}

        # Remove booked slot
        self.AVAILABLE_SLOTS.remove(time_slot)

        return {
            "success": True,
            "message": f"Demo gebucht für {time_slot}",
            "confirmation_email": email,
            "time": time_slot,
            "duration_minutes": 30,
            "meeting_link": f"https://meet.example.com/demo/{email.split('@')[0]}",
        }


class FollowUpTool:
    """Manage follow-up communications"""

    def __init__(self):
        self.follow_ups: List[Dict] = []

    def schedule_followup(
        self, lead_email: str, material_type: str, days: int = 2
    ) -> Dict:
        """Schedule follow-up email"""
        follow_up = {
            "email": lead_email,
            "type": material_type,
            "scheduled_days": days,
            "scheduled_at": datetime.now().isoformat(),
            "status": "pending",
        }
        self.follow_ups.append(follow_up)

        return {
            "success": True,
            "message": f"Follow-up ({material_type}) in {days} Tagen geplant",
            "email": lead_email,
        }

    def send_case_study(self, email: str) -> Dict:
        """Send case study PDF"""
        return {
            "success": True,
            "sent_to": email,
            "file": "case-study-fortune500-recruitment.pdf",
            "message": "Case Study wurde versendet",
        }

    def send_pricing_guide(self, email: str) -> Dict:
        """Send pricing/packages guide"""
        return {
            "success": True,
            "sent_to": email,
            "file": "pricing-guide-2026.pdf",
            "message": "Preisübersicht wurde versendet",
        }

    def send_product_brief(self, email: str) -> Dict:
        """Send product brief"""
        return {
            "success": True,
            "sent_to": email,
            "file": "product-brief-stepstone-sales.pdf",
            "message": "Produktbeschreibung wurde versendet",
        }


class CRMTool:
    """Save leads to CRM/database"""

    def __init__(self):
        self.leads_db: List[Dict] = []

    def save_lead(self, lead: Lead) -> Dict:
        """Save lead to database"""
        lead_dict = lead.to_dict()
        self.leads_db.append(lead_dict)

        logger.info(f"Lead saved: {lead.company_name} ({lead.contact_email})")

        return {
            "success": True,
            "lead_id": f"LEAD-{len(self.leads_db):05d}",
            "company": lead.company_name,
            "score": lead.qualification_score,
            "message": f"Lead {lead.company_name} gespeichert",
        }

    def get_leads(self, filter_score_min: int = 0) -> List[Dict]:
        """Get all leads above score threshold"""
        return [
            l for l in self.leads_db if l.get("qualification_score", 0) >= filter_score_min
        ]

    def update_lead(self, lead_id: str, updates: Dict) -> bool:
        """Update existing lead"""
        for lead in self.leads_db:
            if lead.get("call_id") == lead_id:
                lead.update(updates)
                return True
        return False


# Global tool instances
qualification = QualificationTool()
demo_booking = DemoBookingTool()
follow_up = FollowUpTool()
crm = CRMTool()
