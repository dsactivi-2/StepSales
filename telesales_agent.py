#!/usr/bin/env python3
"""
Stepsales Telesales Agent
German-speaking voice agent for B2B job sales via OpenAI Realtime API
"""

import asyncio
import json
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional

from config import Config
from stepstone_integration import StepstoneIntegration
from tools import qualification, demo_booking, follow_up, crm, Lead
from logger_config import (
    logger_agent, get_logger,
    log_step, log_command, log_performance, log_error_detailed
)

logger = logger_agent


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
        start = time.time()
        try:
            log_step(logger, "Initialize TelesalesAgent", {"version": "1.0.0"})

            # Validate configuration
            Config.validate()
            log_command(logger, "config_validate", {"status": "success"})

            self.call_id = str(uuid.uuid4())[:8]
            self.start_time = datetime.now()

            # Stepstone integration
            try:
                self.stepstone = StepstoneIntegration(
                    zip_code=Config.stepstone.default_zip_code,
                    radius=Config.stepstone.default_radius,
                )
                log_command(
                    logger,
                    "stepstone_init",
                    {
                        "zip_code": Config.stepstone.default_zip_code,
                        "radius": Config.stepstone.default_radius,
                    },
                )
            except Exception as e:
                log_error_detailed(logger, e, {"operation": "stepstone_init"})
                raise

            # Call state
            self.conversation_history: List[Dict] = []
            self.contact_info: Dict = {}
            self.job_interests: List[str] = []
            self.current_qualification_score = 0

            duration = (time.time() - start) * 1000
            log_step(
                logger,
                "TelesalesAgent Initialized",
                {
                    "call_id": self.call_id,
                    "duration_ms": round(duration, 2),
                },
            )

        except Exception as e:
            log_error_detailed(logger, e, {"operation": "__init__"})
            raise

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
        start = time.time()
        try:
            log_command(
                logger,
                f"tool_call:{tool_name}",
                {
                    "call_id": self.call_id,
                    "args": str(arguments)[:100],  # Limit preview
                },
            )

            if tool_name == "search_jobs":
                return self._handle_search_jobs(arguments)
            elif tool_name == "qualify_lead":
                return self._handle_qualify_lead(arguments)
            elif tool_name == "schedule_demo":
                return self._handle_schedule_demo(arguments)
            elif tool_name == "send_followup":
                return self._handle_send_followup(arguments)
            else:
                error_msg = f"Unknown tool: {tool_name}"
                log_error_detailed(
                    logger,
                    ValueError(error_msg),
                    {"call_id": self.call_id, "tool_name": tool_name},
                )
                return {"error": error_msg}

        except Exception as e:
            duration = (time.time() - start) * 1000
            log_error_detailed(
                logger,
                e,
                {
                    "tool_name": tool_name,
                    "call_id": self.call_id,
                    "duration_ms": round(duration, 2),
                },
            )
            raise
        finally:
            duration = (time.time() - start) * 1000
            log_performance(logger, f"tool_call:{tool_name}", duration)

    def _handle_search_jobs(self, args: Dict) -> Dict:
        """Search for jobs on Stepstone"""
        start = time.time()
        try:
            search_terms = args.get("search_terms", [])
            region = args.get("region", "Frankfurt")

            if not search_terms:
                error_msg = "search_terms required"
                log_error_detailed(
                    logger,
                    ValueError(error_msg),
                    {"call_id": self.call_id},
                )
                return {"error": error_msg}

            log_step(
                logger,
                "Search Jobs Initiated",
                {
                    "call_id": self.call_id,
                    "search_terms": search_terms,
                    "region": region,
                },
            )

            # Note: In production, would call asyncio.run(self.stepstone.search_jobs(search_terms))
            # For now, return mock data
            jobs = [
                {
                    "title": f"{search_terms[0]} Position",
                    "company": "Beispielunternehmen GmbH",
                    "location": region,
                    "salary": "60.000 - 80.000 EUR",
                    "url": "https://www.stepstone.de/example",
                }
            ]

            self.job_interests.extend(search_terms)

            log_step(
                logger,
                "Jobs Search Completed",
                {
                    "call_id": self.call_id,
                    "jobs_found": len(jobs),
                    "terms": search_terms,
                },
            )

            return {"success": True, "jobs_found": len(jobs), "jobs": jobs}

        except Exception as e:
            log_error_detailed(
                logger, e, {"call_id": self.call_id, "operation": "_handle_search_jobs"}
            )
            raise

    def _handle_qualify_lead(self, args: Dict) -> Dict:
        """Qualify and save lead"""
        start = time.time()
        try:
            log_step(
                logger,
                "Qualify Lead Started",
                {
                    "call_id": self.call_id,
                    "company": args.get("company_name", "N/A")[:30],
                    "contact": args.get("contact_name", "N/A")[:30],
                },
            )

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

            # Calculate qualification score
            lead.calculate_score()
            self.current_qualification_score = lead.qualification_score

            log_step(
                logger,
                "Lead Score Calculated",
                {
                    "call_id": self.call_id,
                    "score": lead.qualification_score,
                    "budget": lead.budget_range,
                    "timeline": lead.timeline,
                },
            )

            # Save to CRM
            result = crm.save_lead(lead)

            duration = (time.time() - start) * 1000
            log_step(
                logger,
                "Lead Qualification Completed",
                {
                    "call_id": self.call_id,
                    "score": self.current_qualification_score,
                    "duration_ms": round(duration, 2),
                    "crm_result": str(result)[:100],
                },
            )

            return result

        except Exception as e:
            log_error_detailed(
                logger,
                e,
                {
                    "call_id": self.call_id,
                    "operation": "_handle_qualify_lead",
                    "company": args.get("company_name", "N/A"),
                },
            )
            raise

    def _handle_schedule_demo(self, args: Dict) -> Dict:
        """Schedule demo"""
        start = time.time()
        try:
            email = args.get("email", "")
            preferred_date = args.get("preferred_date", "")
            preferred_time = args.get("preferred_time", "")

            log_step(
                logger,
                "Schedule Demo Initiated",
                {
                    "call_id": self.call_id,
                    "email": email[:20] if email else "N/A",
                    "date": preferred_date,
                    "time": preferred_time,
                },
            )

            slots = demo_booking.check_availability()
            time_to_book = preferred_date + " " + preferred_time

            if time_to_book.strip() != " ":
                result = demo_booking.book_slot(email, time_to_book)
                log_step(
                    logger,
                    "Demo Slot Booked",
                    {
                        "call_id": self.call_id,
                        "email": email[:20],
                        "slot": time_to_book,
                    },
                )
                return result
            else:
                result = {
                    "success": True,
                    "message": f"Verfügbare Slots: {', '.join(slots[:3])}",
                    "available_slots": slots,
                }
                log_command(
                    logger,
                    "demo_slots_available",
                    {
                        "call_id": self.call_id,
                        "slot_count": len(slots),
                    },
                )
                return result

        except Exception as e:
            log_error_detailed(
                logger,
                e,
                {
                    "call_id": self.call_id,
                    "operation": "_handle_schedule_demo",
                },
            )
            raise

    def _handle_send_followup(self, args: Dict) -> Dict:
        """Send follow-up material"""
        start = time.time()
        try:
            email = args.get("email", "")
            material = args.get("material_type", "case_study")

            log_step(
                logger,
                "Send Followup Material",
                {
                    "call_id": self.call_id,
                    "email": email[:20] if email else "N/A",
                    "material_type": material,
                },
            )

            result = None
            if material == "case_study":
                result = follow_up.send_case_study(email)
            elif material == "pricing":
                result = follow_up.send_pricing_guide(email)
            elif material == "product_brief":
                result = follow_up.send_product_brief(email)
            else:
                error_msg = f"Unknown material type: {material}"
                log_error_detailed(
                    logger,
                    ValueError(error_msg),
                    {"call_id": self.call_id, "material": material},
                )
                return {"error": error_msg}

            duration = (time.time() - start) * 1000
            log_step(
                logger,
                "Followup Material Sent",
                {
                    "call_id": self.call_id,
                    "material": material,
                    "duration_ms": round(duration, 2),
                },
            )

            return result

        except Exception as e:
            log_error_detailed(
                logger,
                e,
                {
                    "call_id": self.call_id,
                    "operation": "_handle_send_followup",
                },
            )
            raise

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
    print("=" * 60)
    print("🤖 Telesales Agent Test Suite (with Logging)")
    print("=" * 60)

    try:
        agent = TelesalesAgent()

        print(f"✅ Telesales Agent initialized (Call ID: {agent.call_id})")
        print(f"🛠️  Available Tools: {len(agent.build_tool_definitions())}")

        # Simulate tool calls
        print("\n--- Testing Tool Calls ---")

        # Test 1: Search jobs
        print("\n[1] Testing search_jobs...")
        result = agent.handle_tool_call("search_jobs", {"search_terms": ["Software Engineer"]})
        print(f"    Result: {json.dumps(result, indent=2)[:100]}...")

        # Test 2: Qualify lead
        print("\n[2] Testing qualify_lead...")
        result = agent.handle_tool_call(
            "qualify_lead",
            {
                "company_name": "TechCorp GmbH",
                "contact_name": "Max Müller",
                "contact_email": "max@techcorp.de",
                "job_interests": ["Software Engineer"],
                "timeline": "In 2 Wochen",
                "budget_range": "50000-80000 EUR",
            },
        )
        print(f"    Qualification Score: {agent.current_qualification_score}")
        print(f"    Result: {json.dumps(result, indent=2)[:100]}...")

        # Test 3: Schedule demo
        print("\n[3] Testing schedule_demo...")
        result = agent.handle_tool_call(
            "schedule_demo",
            {
                "email": "max@techcorp.de",
                "preferred_date": "2026-04-25",
                "preferred_time": "14:00",
            },
        )
        print(f"    Result: {json.dumps(result, indent=2)[:100]}...")

        # Test 4: Send followup
        print("\n[4] Testing send_followup...")
        result = agent.handle_tool_call(
            "send_followup",
            {
                "email": "max@techcorp.de",
                "material_type": "case_study",
            },
        )
        print(f"    Result: {json.dumps(result, indent=2)[:100]}...")

        print(f"\n📊 Call Summary:")
        print(json.dumps(agent.get_call_summary(), indent=2))

        print("\n✅ All tests completed successfully!")
        print("📂 Check logs/ directory for detailed logging")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
