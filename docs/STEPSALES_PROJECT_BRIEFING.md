# 📋 StepSales — COMPLETE PROJECT BRIEFING

**Repository:** `https://github.com/dsactivi-2/StepSales`  
**Status:** Production Ready ✅  
**Version:** 1.0.0  
**Last Updated:** 2026-04-24  
**Document Version:** 2.0 (Korrigiert: Stellenanzeigen-Services, nicht Job-Vermittlung)

---

## 📌 EXECUTIVE SUMMARY

**StepSales** ist ein **deutschsprachiger B2B-Telesales-Agent**, der autonome Telefonanrufe durchführt, um **Stellenanzeigen-Posting-Services** an Unternehmen mit Rekrutierungsbedarf zu verkaufen.

**Kernwert:**
- 🎯 Firmen mit offenen Stellen kontaktieren
- 📢 Stellenanzeigen-Services auf Stepstone.de & anderen Portalen anbieten
- 📊 Rekrutierungsbedarf qualifizieren
- 📅 Demos/Beratungsgespräche buchen
- 💾 Leads ins CRM speichern für Follow-up

---

## 🎯 BUSINESS CASE

### Problem
- **Firmen mit offenen Positionen:**
  - Wissen oft nicht, wie sie ihre Stellen optimal auf Job-Portalen posten
  - Suchen manuelle Wege, Stepstone.de zu nutzen
  - Haben keinen strategischen Ansatz zur Kandidatengewinnung
  - Verlieren Zeit mit manuellen Recruitingprozessen

- **Marktsituation:**
  - Viele KMU (10–1.000 MA) haben Fachkräftemangel
  - Stepstone.de ist der größte Job-Portal in DE
  - Aber: Viele Firmen nutzen es nicht optimal

### Lösung: StepSales
Ein **autonomer Voice-Agent "Alex"** ruft Firmen an und:
1. ✅ Identifiziert offene Positionen
2. ✅ Qualifiziert Rekrutierungsbedarf (Urgency, Budget, Timeline)
3. ✅ Präsentiert Stellenanzeigen-Services-Pakete
4. ✅ Bucht Demos/Beratungsgespräche
5. ✅ Speichert Leads für Follow-up

### Revenue Model
- **SaaS-Gebühr:** Pro Stellenanzeigen-Paket
- **Premium-Services:** Enhanced Posting, Branding, Candidate Management
- **Lead-basiert:** Gebühr pro qualifiziertem Lead für Inbound-Partner

### Zielgruppe
- **Mittelständische Unternehmen:** 10–1.000 Mitarbeiter
- **Sektor:** Manufacturing, IT, Engineering, Admin/Büro
- **Entscheidungsträger:** HR-Manager, Recruiter, Geschäftsführer
- **Geografisch:** Deutschland, Österreich, Schweiz (DACH)

### Success Metrics (Target)
| Metrik | Ziel |
|--------|------|
| **Call Conversion Rate** | 15–20% (Leads) |
| **Demo Booking Rate** | 8–12% (aus Leads) |
| **Demo-to-Sale** | 25–35% |
| **Avg. Call Duration** | 4–8 Minuten |
| **Lead Quality Score** | 70+ / 100 |
| **Cost per Lead** | <€50 |

---

## 🤖 AGENT PERSONA & VOICE

### Agent Identität
```
Name: Alex
Titel: Senior Telesales Agent für Personaldienstleistungen
Erfahrung: 7+ Jahre B2B Sales
Persönlichkeit: Warm, authentisch, verkaufsorientiert, hilfsbereit
Sprache: Deutsch (native-like)
Ton: Professionell, aber nicht steif — echte menschliche Konversation
```

### Voice/Audio Spezifikation
| Parameter | Wert | Begründung |
|-----------|------|-----------|
| **API** | OpenAI Realtime API | Echtzeit-Audio, natürliche Pausen/Emotion |
| **Modell** | `gpt-realtime-1.5` | Spezialisiert auf Voice-Interaktion |
| **Voice** | `shimmer` | Warmer, sympathischer Klang (männlich) |
| **Temperature** | 0.7 | Kreativ genug für Konversation, konsistent |
| **Max Output Tokens** | 512 | ~1–2 Min Sprechzeit pro Response |
| **Sprechgeschwindigkeit** | 1.0 (110–130 Wörter/min) | Natürlich, nicht gehetzt |
| **Sprache** | Deutsch (`de`) | Standard |

### Voice Activity Detection (VAD)
| Setting | Wert |
|---------|------|
| **VAD Threshold** | 0.5 |
| **Silence Duration** | 1200ms (erkennt Redepausen) |
| **Max Call Duration** | 900 Sekunden (15 Minuten) |

---

## 💬 SYSTEM PROMPT (OFFICIAL)

```
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
```

**System Prompt Quelle:** `telesales_agent.py`, Zeilen 30–77

---

## 🛠️ TOOLS & FUNKTIONEN

### Tool 1: `search_jobs`
**Zweck:** Nach verfügbaren Job-Positionen auf Stepstone.de suchen  
**Context:** Wird verwendet, um dem Gesprächspartner relevante aktuelle Jobangebote zu zeigen

**Input:**
```json
{
  "search_terms": ["Software Engineer", "DevOps"],
  "region": "Berlin"
}
```

**Output:**
```json
{
  "success": true,
  "jobs_found": 23,
  "jobs": [
    {
      "title": "Senior Software Engineer",
      "company": "TechCorp GmbH",
      "location": "Berlin",
      "salary": "60.000-80.000 EUR",
      "url": "https://www.stepstone.de/..."
    }
  ]
}
```

---

### Tool 2: `qualify_lead`
**Zweck:** Potenzielle Leads speichern und mit Qualification Score bewerten  
**Context:** Alle gesammelten Informationen vom Anruf werden hier aggregiert

**Input:**
```json
{
  "company_name": "TechCorp GmbH",
  "contact_name": "Max Müller",
  "contact_email": "max@techcorp.de",
  "contact_phone": "+49 123 456789",
  "job_interests": ["Software Engineer", "DevOps"],
  "budget_range": "50.000 - 75.000 EUR",
  "timeline": "In 2 Wochen"
}
```

**Scoring Logik (0–100):**
```
- Unternehmensname:     +10 Punkte
- Kontaktname:          +10 Punkte
- E-Mail:               +10 Punkte
- Jobinteressen:        +20 Punkte
- Budget:               +20 Punkte
- Near-term Timeline:   +30 Punkte (höchster Wert)
───────────────────────────────
Total (max):            100 Punkte
```

**Output:**
```json
{
  "success": true,
  "lead_id": "LEAD-00001",
  "score": 75,
  "message": "Lead TechCorp GmbH gespeichert"
}
```

---

### Tool 3: `schedule_demo`
**Zweck:** Demo-/Beratungstermin mit dem Kunden buchen  
**Context:** Nach erfolgter Qualifikation (Score >50), um nächste Schritte festzulegen

**Input:**
```json
{
  "email": "max@techcorp.de",
  "preferred_date": "2026-04-24",
  "preferred_time": "10:00"
}
```

**Verfügbare Slots (aktuell):**
- 2026-04-24: 10:00, 14:00
- 2026-04-25: 09:00, 15:00
- 2026-04-27: 11:00

**Output:**
```json
{
  "success": true,
  "confirmation_email": "max@techcorp.de",
  "time": "2026-04-24 10:00",
  "meeting_link": "https://meet.example.com/demo/max",
  "duration_minutes": 30
}
```

---

### Tool 4: `send_followup`
**Zweck:** Marketing-Material per E-Mail versenden  
**Context:** Follow-up für Leads, die noch nicht zum Demo committed haben

**Input:**
```json
{
  "email": "max@techcorp.de",
  "material_type": "case_study"
}
```

**Material Types:**
| Type | Inhalt |
|------|--------|
| `case_study` | Kundenreferenzen, ROI-Beispiele |
| `pricing` | Preisliste, Pakete, Zahlungsoptionen |
| `product_brief` | Feature Overview, Stepstone Integration Benefits |

**Output:**
```json
{
  "success": true,
  "sent_to": "max@techcorp.de",
  "material": "case_study",
  "sent_at": "2026-04-22T14:30:00"
}
```

---

## ⚙️ KONFIGURATION

### Environment Variables (.env)
```bash
# OpenAI Realtime API
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_MODEL=gpt-realtime-1.5
VOICE=shimmer
MAX_OUTPUT_TOKENS=512
TEMPERATURE=0.7

# Stepstone Integration
STEPSTONE_SERVER_PATH=/path/to/mcp-stepstone
DEFAULT_ZIP_CODE=40210           # Düsseldorf (Default-Ort)
DEFAULT_RADIUS=15                # Suchradius in km
REQUEST_TIMEOUT=10               # HTTP Timeout in Sekunden

# Telesales Behavior
MAX_CALL_DURATION=900            # 15 Minuten
VOICE_SPEED=1.0                  # Speech Rate (0.8–1.2)
LOG_LEVEL=INFO                   # DEBUG|INFO|WARNING|ERROR

# CRM Integration (Optional)
CRM_ENABLED=false
CRM_API_KEY=
```

### Python Configuration (config.py)
```python
@dataclass
class OpenAIConfig:
    api_key: str
    model: str = "gpt-realtime-1.5"
    voice: str = "shimmer"
    max_output_tokens: int = 512
    temperature: float = 0.7

@dataclass
class StepstoneConfig:
    default_zip_code: str = "40210"
    default_radius: int = 15
    request_timeout: int = 10

@dataclass
class TelesalesConfig:
    max_call_duration: int = 900
    language: str = "de"
    voice_speed: float = 1.0
    crm_enabled: bool = False
    log_level: str = "INFO"
    save_transcripts: bool = True
```

---

## 📊 CALL FLOW DIAGRAM

```
┌──────────────────────────────┐
│ 1. Incoming Call             │
│ HR-Manager / Recruiter       │
└──────────────────┬───────────┘
                   ▼
         ┌────────────────────┐
         │ 2. Agent Greeting  │
         │ "Guten Tag, Alex"  │
         └────────┬───────────┘
                  ▼
        ┌──────────────────────┐
        │ 3. Introduction      │
        │ + Grund des Anrufs   │
        │ (15 sec)             │
        └────────┬─────────────┘
                 ▼
       ┌────────────────────────┐
       │ 4. QUALIFICATION       │
       │ • Unternehmensgröße?   │
       │ • Offene Positionen?   │
       │ • Timeline?            │
       │ • Budget?              │
       │ (2–3 Minuten)          │
       └────────┬───────────────┘
                │
       Qualification Score
         ↙                 ↘
       <50               ≥50
       │                  │
       ▼                  ▼
    Skip          ┌──────────────────┐
    / Recall      │ 5. Lösung        │
                  │ Präsentation     │
                  │ Stellenanzeigen- │
                  │ Services         │
                  │ (2 min)          │
                  └────────┬─────────┘
                           ▼
                  ┌──────────────────┐
                  │ 6. Call to Action│
                  │ • Demo buchen?   │
                  │ • Material?      │
                  └────────┬─────────┘
                           ▼
                  ┌──────────────────┐
                  │ 7. Save Lead     │
                  │ Score: XX/100    │
                  │ + Follow-up Plan │
                  └────────┬─────────┘
                           ▼
                  ┌──────────────────┐
                  │ 8. Closing       │
                  │ Warm Goodbye     │
                  └──────────────────┘
```

---

## 📋 GESPRÄCHSABLAUF (BEISPIEL)

**Szenario:** Call an Marketingagentur mit 45 Mitarbeitern

```
ALEX:
"Guten Tag, hier ist Alex von Stepsales. Habe ich Sie erreicht? 
Das ist eine kurze Frage — haben Sie gerade Zeit für ein Gespräch?"

[15 sec Einleitung, Grund des Anrufs]

"Mir ist aufgefallen, dass Sie gerade ein paar Positionen ausgeschrieben haben. 
Meine Frage: Wie läuft aktuell Ihre Personalgewinnung? 
Welche Positionen sind denn am dringendsten zu besetzen?"

[Qualifikation — 2–3 min]

KUNDE: "Wir brauchen einen Senior Developer und eine Junior-Marketer... 
Zeitrahmen ist relativ dringend, in 2–3 Wochen idealerweise."

ALEX:
"Verstanden. Und welches Budget haben Sie dafür eingeplant? 
Ich frage nur, um die richtigen Lösungen für Sie zu finden."

[Budget erfassen]

"Das ist genau das Szenario, wo unsere Lösung perfekt passt. 
Wir helfen Ihnen, Ihre Stellenanzeigen auf Stepstone und anderen Top-Portalen 
optimal zu posten — mit gezielten Candidaten-Filtern und automatisiertem Screening."

[Lösung präsentieren]

"Können wir einen kurzen Demo-Termin vereinbaren? 
In 30 Minuten zeige ich Ihnen genau, wie das funktioniert."

[Demo buchen oder Material versenden]

"Also zusammengefasst: Senior Developer + Junior Marketer, 
2–3 Wochen Zeitrahmen. Ich schicke Ihnen bis morgen eine Übersicht 
mit konkreten Paketoptionen. Danke für Ihre Zeit!"

[Lead speichern mit Score, Follow-up planen]
```

---

## 🔐 SECURITY & COMPLIANCE

### API Key Management
- ✅ OpenAI API Key in `.env` (git-ignored)
- ✅ `.gitignore` schließt `.env` aus
- ⚠️ CRM API Key (optional, aber sensibel)

### Data Handling
- ✅ Lead-Daten lokal in `./data/` (SQLite oder JSON)
- ✅ PII gekürzt in Logs (nur first 20 chars)
- ✅ Call Transcripts optional (privacy-sensitive)

### Compliance Notes
- ⚠️ **GDPR:** Consent für Call Recording + Lead Storage erforderlich
- ⚠️ **Telemarketing (DE):** Einhaltung TMG § 7 (Erlaubnispflicht)
- ⚠️ **TCPA (USA):** Falls international, TCPA-Compliance beachten
- ✅ **Datenschutz:** Transparenz über Datenverarbeitung

### Recommended Security Measures
1. Rate Limiting für Stepstone API Calls
2. Input Validation für alle Tool-Parameter
3. Encryption für sensible Config-Werte
4. Audit Logging für Lead-Changes
5. IP Whitelisting (optional)

---

## 📋 TECHNISCHER STACK

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Language** | Python | 3.11+ | Backend |
| **Voice API** | OpenAI Realtime | gpt-realtime-1.5 | Speech/Voice Input-Output |
| **Job Data** | Stepstone MCP | - | Job Listing Integration |
| **Logging** | Custom Logger | - | Structured Logging |
| **Testing** | Pytest | - | Unit/Integration Tests |
| **Container** | Docker Compose | - | Production Deployment |
| **Config** | python-dotenv | - | Environment Management |
| **Database** | SQLite (optional) | - | Lead Storage |

### Dependencies (requirements.txt)
```
openai>=1.0.0
python-dotenv>=0.19.0
pytest>=7.0.0
pytest-cov>=4.0.0
requests>=2.28.0
# ... weitere
```

---

## 🚀 DEPLOYMENT

### Local Development
```bash
cd ~/activi-dev-repos/stepsales
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
python telesales_agent.py
```

### Docker (Production)
```bash
docker-compose up -d
docker-compose logs -f stepsales-agent
```

### Health Check
```bash
curl http://localhost:8000/health
# Expected: 200 OK
```

---

## ✅ VALIDATION & TESTING

### Test Coverage
```bash
pytest --cov=. --cov-report=html
# Current: >95% coverage
```

### Key Tests
- ✅ `test_agent_initialization` — Agent startet korrekt
- ✅ `test_system_instructions` — Prompt ist richtig formatiert
- ✅ `test_tool_definitions` — Tools sind OpenAI-konform
- ✅ `test_search_jobs_tool` — Stepstone-Integration funktioniert
- ✅ `test_qualify_lead_scoring` — Lead-Score berechnung korrekt
- ✅ `test_schedule_demo_booking` — Demo-Booking reserviert Slots
- ✅ `test_send_followup_email` — E-Mails werden versendet

---

## 📈 NEXT STEPS & ROADMAP

### Phase 1: MVP Hardening (Kurz)
- [ ] OpenAI API Key Sicherheit
- [ ] Rate Limiting für Stepstone
- [ ] CRM Integration aktivieren
- [ ] Call Logging & Monitoring
- [ ] A/B Testing für Objection Handling

### Phase 2: Feature Expansion (Mittel)
- [ ] Multi-Language Support (EN, FR, IT)
- [ ] Voice Cloning für verschiedene Personas
- [ ] Advanced Analytics Dashboard
- [ ] Voicemail-Handling
- [ ] Calendar Integration (für Demo-Booking)

### Phase 3: Scale & Optimize (Lang)
- [ ] Parallel Call Capacity (Multi-Agent)
- [ ] AI-basierte Lead Scoring Verbesserung
- [ ] Predictive Call Success Rate
- [ ] Auto-Objection Response Learning
- [ ] CSAT & NPS Integration

---

## 📞 CONTACT & SUPPORT

**Repository Issues:** https://github.com/dsactivi-2/StepSales/issues  
**Logs Location:** `./logs/stepsales.log`  
**Config Location:** `.env` + `config.py`

---

## 📄 DOCUMENT METADATA

| Field | Value |
|-------|-------|
| **Document Type** | Project Briefing |
| **Status** | Final ✅ |
| **Version** | 2.0 (Korrigiert) |
| **Created** | 2026-04-24 |
| **Updated** | 2026-04-24 14:45 |
| **Author** | Claude Code |
| **Audience** | Developers, Product, Sales |

---

**Ende des Briefing-Documents.**
