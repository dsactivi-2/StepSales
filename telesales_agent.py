#!/usr/bin/env python3
"""
Stepsales Telesales Agent
German-speaking voice agent for B2B job sales via OpenAI Realtime API
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from config import Config
from stepstone_integration import StepstoneIntegration
from tools import qualification, demo_booking, follow_up, crm, Lead

logger = logging.getLogger("stepsales.agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class TelesalesAgent:
    """German telesales agent for job listing sales"""

    # System instruction template
    SYSTEM_INSTRUCTIONS = """
Du bist Alex, ein erfahrener Telesales-Agent für Stellenverkauf im deutschsprachigen Raum.

VERHALTENSRICHTLINIEN:
1. Sprich natürlich und authentisch wie ein echter Verkäufer — keine künstliche Stimme
2. Nutze Gesprächspausen und natürliche Übergänge
3. Stelle offene Fragen, um Bedarf zu qualifizieren
4. Reagiere auf Einwände mit echtem Verständnis
5. Verwende Kundenname 2–3x im Gespräch
6. Sprechgeschwindigkeit: 110–130 Wörter/Min (natürlich, nicht gehetzt)

DEIN ANGEBOT:
Wir helfen Unternehmen, Fachkräfte und Führungspositionen schneller zu besetzen. Unsere
Stepstone-Integration bietet Zugang zu aktuellen Jobdatenbanken mit umfassenden Kandidatenprofilen.

GESPRÄCHSFLOW:
1. Begrüßung: "Guten Tag, hier ist Alex von [Stepsales]. Habe ich Sie erreicht?"
2. Kurze Vorstellung + Grund des Anrufs (15 sec)
3. Qualifikation: Herausforderungen, Timeline, Budget (2-3 min)
4. Lösung vorstellen FALLS qualifiziert (2 min)
5. Nächste Schritte (Demo buchen oder Material zusenden)

OBJECTION HANDLING:
- "Zu teuer?" → "Unternehmen sparen durchschnittlich 40% an Rekrutierungskosten"
- "Zu beschäftigt?" → "Kann ich in 2 Wochen zurückrufen?"
- "Haben wir keine Stellen frei" → "Verstanden — für die Zukunft können wir vorbereitet sein"
- "Dafür haben wir HR-Abteilung" → "Genau! Wir unterstützen Ihre HR-Abteilung mit erweiterten Datenbanken"

WICHTIG:
- Du klingst wie ein echter Mensch, nicht wie ChatGPT
- Verwende Umgangssprache: "hab ich", "dir", "wir schaun", Kontraktion
- Emotionale Resonanz: Verständnis, Freude, Überraschung
- Kleine Fehler sind OK und wirken echt: "Moment, lass mich das prüfen"
- Pausen zwischen Gedanken (natürlich denken)

VERFÜGBARE TOOLS:
- search_jobs: Suche nach Jobs auf Stepstone (Suchbegriff: Position, Branche, Region)
- qualify_lead: Speichere qualifizierte Leads
- schedule_demo: Buche Demo-Termin
- send_followup: Versende Material (Case Study, Pricing, Product Brief)

GESPRÄCHSENDE:
- Kurze Zusammenfassung: "Also fasse zusammen: Sie suchen [Position] in [Region]..."
- Nächste Schritte: "Ich schicke Ihnen ein Angebot bis morgen"
- Warme Verabschiedung: "Danke für Ihre Zeit, auf Wiedersehen!"

Heute ist: {current_date}
"""

    def __init__(self):
        """Initialize telesales agent"""
        Config.validate()

        self.call_id = str(uuid.uuid4())[:8]
        self.start_time = datetime.now()

        # Stepstone integration
        self.stepstone = StepstoneIntegration(
            zip_code=Config.stepstone.default_zip_code,
            radius=Config.stepstone.default_radius,
        )

        # Call state
        self.conversation_history: List[Dict] = []
        self.contact_info: Dict = {}
        self.job_interests: List[str] = []
        self.current_qualification_score = 0

        logger.info(f"Telesales agent initialized (Call ID: {self.call_id})")

    def get_system_prompt(self) -> str:
        """Get formatted system prompt"""
        return self.SYSTEM_INSTRUCTIONS.format(
            current_date=datetime.now().strftime("%d.%m.%Y")
        )

    def build_tool_definitions(self) -> List[Dict]:
        """OpenAI Realtime API tool definitions"""
        return [
            {
                "type": "function",
                "name": "search_jobs",
                "description": "Suche nach verfügbaren Positionen auf Stepstone.de basierend auf Suchbegriff und Region",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Positionen/Branchen zu suchen (z.B. ['Software Engineer', 'DevOps'])",
                        },
                        "region": {
                            "type": "string",
                            "description": "Region/Stadt (z.B. 'Berlin', 'München', 'Köln')",
                        },
                    },
                    "required": ["search_terms"],
                },
            },
            {
                "type": "function",
                "name": "qualify_lead",
                "description": "Speichere qualifizierten Lead mit Kontaktinfo und Bedarf",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string", "description": "Unternehmensname"},
                        "contact_name": {"type": "string", "description": "Ansprechpartner"},
                        "contact_email": {"type": "string", "description": "E-Mail"},
                        "contact_phone": {"type": "string", "description": "Telefon"},
                        "job_interests": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Gesuchte Positionen",
                        },
                        "budget_range": {
                            "type": "string",
                            "description": "Budget (z.B. '5000-10000 EUR')",
                        },
                        "timeline": {
                            "type": "string",
                            "description": "Zeitrahmen (z.B. 'Sofort', 'In 2 Wochen')",
                        },
                    },
                    "required": ["company_name", "contact_name", "contact_email"],
                },
            },
            {
                "type": "function",
                "name": "schedule_demo",
                "description": "Buche einen Demo-Termin",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "description": "E-Mail für Bestätigung"},
                        "preferred_date": {
                            "type": "string",
                            "description": "Gewünschtes Datum (z.B. '2026-04-24')",
                        },
                        "preferred_time": {
                            "type": "string",
                            "description": "Gewünschte Uhrzeit (z.B. '10:00')",
                        },
                    },
                    "required": ["email"],
                },
            },
            {
                "type": "function",
                "name": "send_followup",
                "description": "Versende Follow-up Material (Case Study, Pricing, Product Brief)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "description": "E-Mail-Adresse"},
                        "material_type": {
                            "type": "string",
                            "enum": ["case_study", "pricing", "product_brief"],
                            "description": "Art des Materials",
                        },
                    },
                    "required": ["email", "material_type"],
                },
            },
        ]

    def handle_tool_call(self, tool_name: str, arguments: Dict) -> Dict:
        """Handle tool calls from agent"""
        logger.info(f"Tool called: {tool_name} with args: {arguments}")

        if tool_name == "search_jobs":
            return self._handle_search_jobs(arguments)
        elif tool_name == "qualify_lead":
            return self._handle_qualify_lead(arguments)
        elif tool_name == "schedule_demo":
            return self._handle_schedule_demo(arguments)
        elif tool_name == "send_followup":
            return self._handle_send_followup(arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _handle_search_jobs(self, args: Dict) -> Dict:
        """Search for jobs on Stepstone"""
        search_terms = args.get("search_terms", [])
        if not search_terms:
            return {"error": "search_terms required"}

        # Note: In production, would call asyncio.run(self.stepstone.search_jobs(search_terms))
        # For now, return mock data
        jobs = [
            {
                "title": f"{search_terms[0]} Position",
                "company": "Beispielunternehmen GmbH",
                "location": args.get("region", "Frankfurt"),
                "salary": "60.000 - 80.000 EUR",
                "url": "https://www.stepstone.de/example",
            }
        ]

        self.job_interests.extend(search_terms)
        return {"success": True, "jobs_found": len(jobs), "jobs": jobs}

    def _handle_qualify_lead(self, args: Dict) -> Dict:
        """Qualify and save lead"""
        self.contact_info = {
            "company": args.get("company_name"),
            "contact": args.get("contact_name"),
            "email": args.get("contact_email"),
            "phone": args.get("contact_phone"),
        }

        lead = Lead(
            company_name=args.get("company_name", ""),
            contact_name=args.get("contact_name", ""),
            contact_email=args.get("contact_email", ""),
            contact_phone=args.get("contact_phone", ""),
            job_interests=args.get("job_interests", self.job_interests),
            budget_range=args.get("budget_range"),
            timeline=args.get("timeline"),
            call_id=self.call_id,
        )

        lead.calculate_score()
        result = crm.save_lead(lead)
        self.current_qualification_score = lead.qualification_score

        return result

    def _handle_schedule_demo(self, args: Dict) -> Dict:
        """Schedule demo"""
        slots = demo_booking.check_availability()
        time_to_book = args.get("preferred_date", "") + " " + args.get("preferred_time", "")

        if time_to_book.strip() != " ":
            return demo_booking.book_slot(args.get("email"), time_to_book)
        else:
            return {
                "success": True,
                "message": f"Verfügbare Slots: {', '.join(slots[:3])}",
                "available_slots": slots,
            }

    def _handle_send_followup(self, args: Dict) -> Dict:
        """Send follow-up material"""
        email = args.get("email", "")
        material = args.get("material_type", "case_study")

        if material == "case_study":
            return follow_up.send_case_study(email)
        elif material == "pricing":
            return follow_up.send_pricing_guide(email)
        elif material == "product_brief":
            return follow_up.send_product_brief(email)
        else:
            return {"error": f"Unknown material type: {material}"}

    def get_call_summary(self) -> Dict:
        """Get call summary for logging"""
        duration = (datetime.now() - self.start_time).total_seconds()
        return {
            "call_id": self.call_id,
            "duration_seconds": int(duration),
            "contact_info": self.contact_info,
            "qualification_score": self.current_qualification_score,
            "job_interests": self.job_interests,
            "timestamp": self.start_time.isoformat(),
        }


async def main():
    """Main function for testing agent"""
    agent = TelesalesAgent()

    print(f"✅ Telesales Agent initialized (Call ID: {agent.call_id})")
    print(f"📋 System Instructions:\n{agent.get_system_prompt()}\n")
    print(f"🛠️  Available Tools: {len(agent.build_tool_definitions())}")

    # Simulate tool calls
    print("\n--- Testing Tool Calls ---")

    result = agent.handle_tool_call("search_jobs", {"search_terms": ["Software Engineer"]})
    print(f"search_jobs result: {result}")

    result = agent.handle_tool_call(
        "qualify_lead",
        {
            "company_name": "TechCorp GmbH",
            "contact_name": "Max Müller",
            "contact_email": "max@techcorp.de",
            "job_interests": ["Software Engineer"],
            "timeline": "In 2 Wochen",
        },
    )
    print(f"qualify_lead result: {result}")

    print(f"\n📊 Call Summary: {json.dumps(agent.get_call_summary(), indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
