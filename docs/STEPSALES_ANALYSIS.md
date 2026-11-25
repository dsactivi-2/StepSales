# 📞 StepSales — Telesales Agent Analyse

**Repository:** `https://github.com/dsactivi-2/StepSales`  
**Status:** Production Ready ✅  
**Last Updated:** 2026-04-23  
**Version:** 1.0.0

---

## 🎯 BUSINESS CASE

**Ziel:** Deutschsprachiger B2B Telesales-Agent für den Verkauf von Stellenanzeigen-Services  

**Problem/Lösung:**
- **Problem:** Firmen mit offenen Positionen wissen nicht, wie sie ihre Stellenanzeigen effektiv auf Stepstone.de & anderen Portalen posten
- **Lösung:** Autonomer Agent ruft Firmen an, bietet ihnen Stellenanzeigen-Services an (Posting auf Stepstone, Karriereseiten, etc.), qualifiziert ihre Rekrutierungsbedarfe, bucht Demos
- **Zielgruppe:** Mittelständische Unternehmen (10–1.000 Mitarbeiter) mit offenen Stellen
- **Revenue Model:** SaaS-Gebühr pro Stellenanzeigen-Paket, Pro-Ansicht-Modell, oder Premium-Posting-Services

**Geschäftsfluss:**
```
Firmen anrufen → Rekrutierungsbedarf qualifizieren → Stellenanzeigen-Pakete vorstellen → Demo buchen → Lead speichern → Follow-up → Abschluss
```

---

## 🤖 AGENT KONFIGURATION

### Agent Identität
| Feld | Wert |
|------|------|
| **Name** | Alex |
| **Persönlichkeit** | Erfahrener Telesales-Profi (natürlich, nicht künstlich) |
| **Sprache** | Deutsch (Standard) |
| **Ton** | Warm, authentisch, verkaufsorientiert |

### Voice/Audio Einstellungen
| Setting | Wert | Begründung |
|---------|------|------------|
| **API** | OpenAI Realtime API | Echtzeit-Audio, natürliche Pausen/Emotion |
| **Modell** | gpt-realtime-1.5 | Spezialisiert auf Voice-Interaktion |
| **Voice** | shimmer | Warmer, sympathischer Klang |
| **Sprechgeschwindigkeit** | 1.0 (110–130 Wörter/min) | Natürlich, nicht gehetzt |
| **Temperature** | 0.7 | Kreativ genug für Konversation, aber konsistent |
| **Max Output Tokens** | 512 | Begrenzt Responses auf ~1–2 Min Sprechzeit |

### Gesprächsparameter
| Parameter | Wert | Zweck |
|-----------|------|-------|
| **Max Call Duration** | 900s (15 min) | Realistische Anrufzeit |
| **VAD Threshold** | 0.5 | Voice Activity Detection |
| **Silence Duration** | 1200ms | Pause bis Gerede-Ende erkannt wird |

---

## 💬 SYSTEM PROMPT

**Template (aus `telesales_agent.py`):**

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
Wir helfen Unternehmen, ihre Stellenanzeigen auf Stepstone.de und anderen Top-Portalen zu posten.
Das beschleunigt die Personalgewinnung und erhöht die Kandidaten-Sichtbarkeit. Unsere Services
umfassen: Stellenanzeigen-Posting, Optimierung für Suchmaschinen, Kandidaten-Management.

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
```

**Wichtigste Optimierungen:**
- ✅ Natürliches Deutsch (Umgangssprache, Kontraktionen)
- ✅ Keine ChatGPT-artige Responses
- ✅ Objection Handling vortrainiert
- ✅ Strukturierter Gesprächsfluss

---

## 🛠️ VERFÜGBARE TOOLS

### 1. `search_jobs` (oder besser: `get_available_positions`)
**Zweck:** Verfügbare Positionen der Firma abrufen (um Posting-Bedarf zu qualifizieren)  
**Input:**
```json
{
  "company_name": "TechCorp GmbH",
  "search_region": "Berlin" // Optional
}
```
**Output:**
```json
{
  "success": true,
  "open_positions": 3,
  "positions": [
    {
      "title": "Senior Software Engineer",
      "department": "Engineering",
      "location": "Berlin",
      "priority": "high",
      "posting_ready": false
    }
  ]
}
```
**Logik:** Integriert mit HR-System der Firma (über Stepstone oder direkt)

---

### 2. `qualify_lead`
**Zweck:** Lead speichern + Qualification Score berechnen  
**Input:**
```json
{
  "company_name": "TechCorp",
  "contact_name": "Max Müller",
  "contact_email": "max@techcorp.de",
  "contact_phone": "+49123456789",
  "job_interests": ["Engineer"],
  "budget_range": "50000-75000 EUR",
  "timeline": "In 2 Wochen"
}
```
**Scoring Logik:**
- Company Info: +10
- Contact: +10
- Email: +10
- Job Interests: +20
- Budget: +20
- Timeline (Near-term): +30 (max 100)

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

### 3. `schedule_demo`
**Zweck:** Demo-Termin buchen  
**Input:**
```json
{
  "email": "max@techcorp.de",
  "preferred_date": "2026-04-24",
  "preferred_time": "10:00"
}
```
**Verfügbare Slots:**
- 2026-04-24: 10:00, 14:00
- 2026-04-25: 09:00, 15:00
- 2026-04-27: 11:00

**Output:**
```json
{
  "success": true,
  "confirmation_email": "max@techcorp.de",
  "time": "2026-04-24 10:00",
  "meeting_link": "https://meet.example.com/demo/max"
}
```

---

### 4. `send_followup`
**Zweck:** Marketing Material versenden  
**Input:**
```json
{
  "email": "max@techcorp.de",
  "material_type": "case_study" // or "pricing", "product_brief"
}
```
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

## ⚙️ KONFIGURATIONSABWEICHUNGEN

### Aktuell (.env)
```bash
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_MODEL=gpt-realtime-1.5
VOICE=shimmer
MAX_OUTPUT_TOKENS=512
TEMPERATURE=0.7

STEPSTONE_SERVER_PATH=/path/to/mcp-stepstone
DEFAULT_ZIP_CODE=40210           # Düsseldorf
DEFAULT_RADIUS=15                # km
REQUEST_TIMEOUT=10               # sec

MAX_CALL_DURATION=900            # 15 min
VOICE_SPEED=1.0
LOG_LEVEL=INFO

CRM_ENABLED=false
```

### Optimierungsvorschläge
| Parameter | Aktuell | Empfohlen | Grund |
|-----------|---------|-----------|-------|
| TEMPERATURE | 0.7 | 0.6 | Konsistentere Responses |
| MAX_OUTPUT_TOKENS | 512 | 400 | Kürzere Responses = schneller |
| DEFAULT_ZIP_CODE | 40210 | Geografisch flexibel | CLI-Parameter erlauben |
| CRM_ENABLED | false | true | Lead Persistence |

---

## 📊 CALL FLOW (Beispiel)

```
┌─ Incoming Call ─────────────┐
│ HR Manager anrufen          │
└──────────┬──────────────────┘
           ▼
┌─ Qualifikation ─────────────┐
│ • Unternehmen?              │
│ • Pos./Branche?             │
│ • Budget?                   │
│ • Timeline?                 │
└──────────┬──────────────────┘
           ▼
    Qualification Score
    ↓         ↓
   <50      ≥50
    ↓         ↓
   Skip   Search Jobs
         (Stepstone)
           │
           ▼
    ┌─────────────────┐
    │ Demo Buchen?    │
    └────┬────────┬───┘
         │ Ja     │ Nein
         ▼        ▼
      Book   Send Material
      Demo   (Case Study/
             Pricing)
         │
         ▼
    ┌─────────────────┐
    │ Save Lead (CRM) │
    │ Score: 75/100   │
    └─────────────────┘
```

---

## 🔐 SECURITY CONSIDERATIONS

**API Keys:**
- ✅ OpenAI API Key — in `.env` (git-ignored)
- ⚠️ CRM API Key — optional, aber sensibel

**Datenhandling:**
- ✅ Lead-Daten lokal (./data/)
- ⚠️ Keine PII in Logs (gekürzt)
- ✅ Call Transcripts optional

**Compliance:**
- ⚠️ GDPR: Consent für Call Recording + Lead Storage
- ⚠️ TCPA (USA): Telemarketing Compliance
- ✅ Germany: Televerkaufs-Gesetze beachten

---

## 📋 TECHNISCHER STACK

| Component | Tech | Version |
|-----------|------|---------|
| **Backend** | Python | 3.11+ |
| **Voice API** | OpenAI Realtime | gpt-realtime-1.5 |
| **Job Data** | Stepstone MCP | `mcp-stepstone` |
| **Logging** | Custom Logger | info/debug/error |
| **Testing** | Pytest | Coverage >95% |
| **Container** | Docker Compose | Production |

---

## 🚀 DEPLOYMENT

**Local:**
```bash
python telesales_agent.py
```

**Docker:**
```bash
docker-compose up -d
```

**Health Check:**
```bash
curl http://localhost:8000/health
```

---

## 📝 NEXT STEPS

1. ✅ OpenAI API Key setzen
2. ✅ Stepstone MCP Server starten
3. ✅ CRM Integration aktivieren (optional)
4. ✅ Call Logging überprüfen
5. ✅ A/B Testing für Objection Handling

---

**Created:** 2026-04-24 | **Analyst:** Claude Code
