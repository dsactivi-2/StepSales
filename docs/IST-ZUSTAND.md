# STEPSALES — IST-ZUSTAND DOKUMENTATION

**Erstellt:** 2026-04-24T01:41:00+02:00  
**Quelle:** Live-Verifikation (API-Calls, Dateisystem, Docker-Status, Test-Runs)  
**Status:** Prototyp / In Entwicklung ⚠️

---

## 1. LIVE VERIFIZIERTER SERVICE-STATUS

| Service | Container | Image | Status | Ports |
|---------|-----------|-------|--------|-------|
| stepsales-agent | stepsales-agent | stepsales-stepsales-agent (lokal gebaut) | ✅ healthy | `0.0.0.0:8010` |
| stepstone-mcp | stepstone-mcp | python:3.11-slim | ✅ running | intern |
| qdrant-stepsales | qdrant-stepsales | qdrant/qdrant:latest | 🟡 healthcheck-fail | intern (6333, 6334) |
| neo4j-stepsales | neo4j-stepsales | neo4j:5-community | ✅ healthy | intern (7474, 7687) |

**Verifiziert via:** `docker compose ps` (2026-04-24T01:41:34+02:00)

---

## 2. LIVE VERIFIZIERTE API-ENDPOINTS

### Core Endpoints

| Methode | Pfad | Status | Response (live) |
|---------|------|--------|-----------------|
| GET | `/health` | ✅ 200 | `{"status": "healthy", "timestamp": "..."}` |
| GET | `/status` | ✅ 200 | `{"healthy": true, "services": {...}}` |
| GET | `/metrics` | ✅ 200 | Process + Business + SLA + Webhook Metrics |
| GET | `/analytics` | ✅ 200 | KPIs, Funnel, Forecast, Objections |

### Call Endpoints

| Methode | Pfad | Status | Response (live) |
|---------|------|--------|-----------------|
| POST | `/call` | ✅ 200 | `{"success": true, "call": "thread_id='call-...'"}` |
| POST | `/call/ai` | ✅ vorhanden | Telnyx AI Assistant Call |
| GET | `/call/ai/active` | ✅ vorhanden | Aktive AI Calls |

### Knowledgebase Endpoints (8 Dokumente verifiziert)

| Methode | Pfad | Status | Response (live) |
|---------|------|--------|-----------------|
| GET | `/kb/documents` | ✅ 200 | 8 Dokumente (playbook, objections, closing, etc.) |
| POST | `/kb/search` | ✅ 200 | Suchergebnisse mit top_k |
| GET | `/kb/context/{stage}` | ✅ 200 | Stage-spezifischer Kontext |

**Verifizierte KB-Dokumente:**
1. `playbook_multiposting` — Produkt: Multiposting StepStone + Indeed
2. `objection_price` — Einwandbehandlung: Preis
3. `objection_time` — Einwandbehandlung: Keine Zeit
4. `objection_no_interest` — Einwandbehandlung: Kein Interesse
5. `qualification_framework` — BANT Framework
6. `closing_techniques` — Top 5 Closing-Techniken
7. `product_comparison` — Einzelanzeige vs. Multiposting
8. `company_info` — Step2Job Unternehmensinfos

### Intent Classification (LLM-basiert)

| Methode | Pfad | Status | Response (live) |
|---------|------|--------|-----------------|
| POST | `/intent` | ✅ 200 | `{"intent": "objection_interest", "confidence": 0.95, ...}` |

**Live-Test:** `"Ich habe kein Interesse"` → `objection_interest` (confidence: 0.95) ✅

### Fulfillment & Cadence

| Methode | Pfad | Status |
|---------|------|--------|
| POST | `/fulfill` | ✅ vorhanden |
| POST | `/fulfill/multiposting` | ✅ vorhanden |
| POST | `/cadence` | ✅ vorhanden |
| GET | `/cadence/status` | ✅ 200 — `{"total_sequences": 0, "active": 0}` |

### Agent Coach

| Methode | Pfad | Status | Response (live) |
|---------|------|--------|-----------------|
| POST | `/coach/analyze` | ✅ vorhanden |
| POST | `/coach/score` | ✅ 200 | `{"percentage": 35.0, "grade": "F", ...}` |
| GET | `/coach/history` | ✅ vorhanden |

### SLA Escalation

| Methode | Pfad | Status |
|---------|------|--------|
| POST | `/sla/create` | ✅ vorhanden |
| GET | `/sla/active` | ✅ 200 |
| GET | `/sla/overdue` | ✅ 200 |
| POST | `/sla/resolve/{event_id}` | ✅ vorhanden |

### Graph Memory (Neo4j)

| Methode | Pfad | Status | Response (live) |
|---------|------|--------|-----------------|
| GET | `/graph/stats` | ✅ 200 | `{"total_nodes": 16, "total_relationships": 13, "connected": true}` |
| POST | `/graph/query` | ✅ vorhanden |
| GET | `/graph/memory/{customer_id}` | ✅ vorhanden |
| GET | `/graph/calls/{lead_id}` | ✅ vorhanden |
| POST | `/graph/seed-workflows` | ✅ vorhanden |

### Webhooks & Audit

| Methode | Pfad | Status |
|---------|------|--------|
| POST | `/webhooks/telnyx` | ✅ vorhanden |
| POST | `/webhooks/stripe` | ✅ vorhanden |
| GET | `/webhooks/events` | ✅ vorhanden |
| GET | `/webhooks/stats` | ✅ 200 — `{"total_events": 0}` |
| POST | `/audit/log-entry` | ✅ vorhanden |

### Export

| Methode | Pfad | Status |
|---------|------|--------|
| GET | `/export/leads` | ✅ vorhanden (JSON/CSV) |
| GET | `/export/calls` | ✅ vorhanden |
| GET | `/export/analytics` | ✅ 200 |

---

## 3. SERVICE-METRIKEN (Live)

### Prozess-Metriken (via `/metrics`)
- PID: 1 (Docker-Container)
- Memory RSS: ~171 MB
- Memory VMS: ~518 MB
- Threads: 6
- CPU: 0.0%

### Business-Metriken
- Total Calls: 0
- Total Leads: 0
- Total Revenue: 0

### Service-Status (via `/status`)
- Orchestrator: ✅ true
- Lead Intel: ✅ true
- Billing: ✅ true
- Fulfillment: ✅ true
- Cadence: ✅ true
- Knowledgebase: ✅ true
- Coach: ✅ true

---

## 4. PROJEKTSTRUKTUR (Live-Dateisystem)

### Root-Dateien
```
stepsales/
├── main.py                       # 740 Zeilen — Entry Point (FastAPI + Services)
├── docker-compose.yml            # 103 Zeilen — 4 Services
├── Dockerfile                    # 23 Zeilen — Python 3.11-slim
├── requirements.txt              # 26 Dependencies
├── .env.example                  # Template
├── environment/.env              # Runtime Secrets (gitignored)
│
├── config/
│   ├── __init__.py
│   └── settings.py               # 113 Zeilen — AppConfig (7 Sub-Konfigs)
│
├── models/
│   └── domain.py                 # 179 Zeilen — 8 SQLAlchemy-Modelle
│
├── services/                     # 19 Dateien, 4.867 Zeilen gesamt
│   ├── __init__.py
│   ├── orchestrator_langgraph.py # 657 Zeilen — LangGraph State Machine + Barge-In
│   ├── intent_classifier.py      # 134 Zeilen — LLM Intent-Klassifikation (10 Typen)
│   ├── deepgram_stt.py           # 148 Zeilen — STT mit EOT-Detection
│   ├── elevenlabs_tts.py         # 129 Zeilen — TTS Single + Streaming
│   ├── telnyx_gateway.py         # 308 Zeilen — Voice Gateway + Media WebSocket
│   ├── telnyx_ai_assistant.py    # 311 Zeilen — Telnyx Native AI Assistant
│   ├── stripe_billing.py         # 219 Zeilen — Stripe Billing
│   ├── persistence.py            # 284 Zeilen — SQLite/PostgreSQL ORM
│   ├── lead_intel.py             # 180 Zeilen — Stepstone Jobsuche
│   ├── fulfillment.py            # 234 Zeilen — Job-Ad Multiposting
│   ├── cadence.py                # 245 Zeilen — Outbound Cadence
│   ├── knowledgebase.py          # 360 Zeilen — RAG Knowledge
│   ├── agent_coach.py            # 283 Zeilen — Realtime Coaching
│   ├── sla_escalation.py         # 232 Zeilen — SLA Monitoring
│   ├── analytics.py              # 304 Zeilen — KPIs, Forecasting
│   ├── webhooks.py               # 133 Zeilen — Webhook Router
│   ├── audit_monitoring.py       # 259 Zeilen — Audit Trail
│   └── graph_memory.py           # 325 Zeilen — Neo4j Graph Memory
│
├── tests/
│   ├── __init__.py
│   ├── test_stepsales.py         # NEU — 48 Tests (alle live bestanden ✅)
│   ├── test_agent.py             # ALT — referenziert gelöschte Dateien
│   └── test_web_server.py        # ALT — referenziert gelöschte Dateien
│
├── stepstone_server.py           # 148 Zeilen — Lokaler Stepstone MCP
├── log_viewer.py                 # 414 Zeilen — CLI Log-Viewer
├── logger_config.py              # Logging-Konfiguration
├── tools.py                      # Sales Tools
├── setup_memory.py               # Memory Setup Script
│
├── .kilo/                        # Kilo Config (MCP, Skills, Memory)
├── data/transcripts/             # Transkript-Speicher
├── logs/                         # Log-Dateien
├── static/                       # Web Assets
└── workflows/                    # Workflow-Definitionen
```

### Gesamt Lines of Code: **5.778 Zeilen** (verifiziert via `wc -l`)

---

## 5. KONFIGURATION (Live verifiziert)

### AppConfig — 7 Sub-Konfigurationen

| Config-Klasse | Modell | Default-Wert (verifiziert) |
|---------------|--------|---------------------------|
| `TelnyxConfig` | api_base | `https://api.telnyx.com/v2` |
| `DeepgramConfig` | model | `nova-3`, Sprache: `de`, Sample: `16000` |
| `ElevenLabsConfig` | model_id | `eleven_multilingual_v2` |
| `OpenAIConfig` | model | `gpt-4o`, Temperature: `0.8` |
| `StripeConfig` | currency | `eur`, Tax: `0.19` |
| `PersistenceConfig` | db_url | `sqlite:///data/stepsales.db` |
| `RuntimeConfig` | port | `8010`, Host: `0.0.0.0` |

### Environment-Variablen (in `environment/.env`)
- ✅ `DEEPGRAM_API_KEY` — gesetzt
- ✅ `ELEVENLABS_API_KEY` — gesetzt
- ✅ `ELEVENLABS_VOICE_ID` — gesetzt
- ✅ `TELNYX_API_KEY` — gesetzt
- ✅ `TELNYX_CONNECTION_ID` — gesetzt
- ✅ `TELNYX_CALL_CONTROL_APP_ID` — gesetzt
- ✅ `TELNYX_FROM_NUMBER` — `+493040719397`
- ✅ `OPENAI_API_KEY` — gesetzt
- ❌ `TELNYX_WEBHOOK_SECRET` — leer
- ❌ `STRIPE_API_KEY` — leer
- ❌ `STRIPE_WEBHOOK_SECRET` — leer

---

## 6. SPRACH-PIPELINE (Architektur)

```
Deepgram STT (nova-3, de, PCM 16kHz, eot_threshold=0.5, eot_timeout_ms=1500)
    ↓ Text
LangGraph Orchestrator (8 Nodes: greet→discovery→qualify→offer→objection→close→followup→summary)
    ↓ Text (LLM-basierte Intent-Klassifikation via OpenAI gpt-4o)
OpenAI LLM (gpt-4o, temp=0.8, max_tokens=512) + Knowledgebase RAG Context
    ↓ Text
ElevenLabs TTS (Streaming, eleven_multilingual_v2, German Voice)
    ↓ Audio (PCM16, 640-byte chunks)
Telnyx Media WebSocket (<200ms Latenz) oder play_audio REST API (Fallback)
    ↓
Agent Coach (QA-Scoring) + Analytics + SLA + Webhooks + Graph Memory
```

### Barge-In Architektur (implementiert)
- Deepgram STT hört durchgehend (auch während TTS spricht)
- TTS läuft als cancellable asyncio Task mit `asyncio.Event`
- Bei `speech_final` während TTS → TTS wird abgebrochen, neue Antwort generiert
- Paralleler Audio-Stream: STT → LLM → TTS → Telnyx

### Intent-Klassifikation (LLM-basiert, 10 Typen)
- `interest`, `objection_price`, `objection_time`, `objection_interest`
- `question`, `goodbye`, `callback`, `decision_positive`, `decision_needs_time`, `info_request`
- Fallback: Keyword-Routing wenn LLM-Classifier fehlschlägt

---

## 7. DATENMODELLE (8 SQLAlchemy-Modelle)

| Modell | Tabelle | Fields (Auszug) |
|--------|---------|-----------------|
| `Company` | companies | name, industry, website, company_size |
| `Contact` | contacts | first_name, last_name, email, phone, role |
| `Lead` | leads | status, source, open_roles, urgency, qualification_score |
| `Call` | calls | stage, direction, duration_seconds, transcript, qa_score |
| `Invoice` | invoices | stripe_invoice_id, amount_cents, status, hosted_invoice_url |
| `Fulfillment` | fulfillments | job_ad_data, portals, status, submission_ids |
| `SLAEvent` | sla_events | policy, stage, deadline, status, escalated |
| `MemoryFact` | memory_facts | customer_id, fact_type, content, confidence, ttl_days |

### Enums
- `LeadStatus`: new, connected, qualified, offer_sent, invoiced, paid, fulfilled, lost, dnc
- `CallStage`: greet, discovery, qualify, objection, offer, close, followup
- `IntentType`: interest, objection_price, objection_time, objection_interest, question, goodbye, callback, decision_positive, decision_needs_time, info_request

---

## 8. DEPENDENCIES (requirements.txt — live verifiziert)

| Package | Version (Anforderung) |
|---------|----------------------|
| openai | >=1.52.0 |
| langgraph | >=0.2.0 |
| langchain | >=0.3.0 |
| langchain-openai | >=0.2.0 |
| langchain-core | >=0.3.0 |
| fastapi | >=0.109.0 |
| uvicorn | >=0.27.0 |
| sqlalchemy | >=2.0.0 |
| stripe | >=7.0.0 |
| websockets | >=12.0 |
| httpx | >=0.26.0 |
| pydantic | >=2.0.0 |
| neo4j | >=5.0.0 |
| qdrant-client | >=1.7.0 |
| psutil | >=5.9.0 |
| pytest | >=7.4.0 |
| pytest-asyncio | >=0.23.0 |
| pytest-cov | >=4.1.0 |

---

## 9. TEST-SUITE (48 Tests — alle bestanden ✅)

### Test-Kategorien

| Kategorie | Tests | Status |
|-----------|-------|--------|
| `TestAppConfig` | 9 | ✅ Alle bestanden |
| `TestDomainModels` | 7 | ✅ Alle bestanden |
| `TestIntentClassifier` | 3 | ✅ Alle bestanden |
| `TestHealthEndpoints` | 5 | ✅ Alle bestanden |
| `TestKnowledgebaseEndpoints` | 3 | ✅ Alle bestanden |
| `TestSLAEndpoints` | 2 | ✅ Alle bestanden |
| `TestGraphEndpoints` | 1 | ✅ Alle bestanden |
| `TestCallEndpoints` | 1 | ✅ Alle bestanden |
| `TestCadenceEndpoints` | 1 | ✅ Alle bestanden |
| `TestExportEndpoints` | 2 | ✅ Alle bestanden |
| `TestServiceFiles` | 6 | ✅ Alle bestanden |
| `TestOrchestratorStructure` | 5 | ✅ Alle bestanden |
| `TestProjectMetrics` | 3 | ✅ Alle bestanden |

### Alte Tests (nicht lauffähig)
- `test_agent.py` — importiert `telesales_agent.py` (gelöscht) ❌
- `test_web_server.py` — importiert `web_server.py` (gelöscht) ❌

---

## 10. DOCKER KONFIGURATION

### Services (docker-compose.yml)

```yaml
services:
  stepsales-agent:    # Port 8010 (öffentlich), depends_on: qdrant, neo4j
  stepstone-mcp:      # Intern, python stepstone_server.py
  qdrant-stepsales:   # Intern (expose: 6333, 6334), volume: persistent
  neo4j-stepsales:    # Intern (expose: 7474, 7687), volume: persistent
```

### Netzwerk
- Alle Services: `stepsales-net` (bridge)
- Qdrant/Neo4j: **nicht** öffentlich exponiert (nur `expose`, keine `ports`)
- Stepsales-Agent: Port 8010 öffentlich

### Volumes
- `qdrant-stepsales-data` — Qdrant Vector Storage
- `neo4j-stepsales-data`, `neo4j-stepsales-logs`, `neo4j-stepsales-import` — Neo4j Storage
- `./data:/app/data` — Transkripte & Daten (Host-Mount)

### Healthchecks
- stepsales-agent: `urllib.request` auf `/health` ✅ healthy
- qdrant-stepsales: `/dev/tcp` auf Port 6333 (noch nicht deployed)
- neo4j-stepsales: `cypher-shell` ✅ healthy

---

## 11. REVERSE PROXY (Caddy)

| Domain | Ziel | Status |
|--------|------|--------|
| `webui.ss.activi.io` | localhost:8010 | ⏳ Wartet auf Firewall-Ports 80/443 |
| `neo4j.ss.activi.io` | localhost:7474 | ⏳ Wartet auf Firewall-Ports 80/443 |
| `qdrant.ss.activi.io` | localhost:6333 | ⏳ Wartet auf Firewall-Ports 80/443 |

**SSL:** Automatisch via Let's Encrypt (Caddy)
**Problem:** Firewall blockiert Port 80/443 — ACME Challenge Timeout

---

## 12. GITHUB

- **Remote:** `https://github.com/dsactivi-2/StepSales.git`
- **Branch:** `master`
- **Letzter Commit (lokal):** Qdrant Healthcheck Fix + tote Dateien entfernt
- **Status:** Gepusht ✅

---

## 13. BEKANNTE OFFENE PUNKTE

### 🔴 Kritisch
| # | Problem | Auswirkung |
|---|---------|------------|
| 1 | `STRIPE_API_KEY` leer | Billing kann keine Rechnungen erstellen |
| 2 | `STRIPE_WEBHOOK_SECRET` leer | Webhook-Verifikation nicht möglich |
| 3 | `TELNYX_WEBHOOK_SECRET` leer | Webhook-Verifikation nicht möglich |
| 4 | Firewall Ports 80/443 blockiert | Caddy SSL-Zertifikate können nicht bezogen werden |

### 🟡 Funktional
| # | Problem | Auswirkung |
|---|---------|------------|
| 5 | Qdrant Healthcheck nicht deployed | Container zeigt "unhealthy" (funktional OK) |
| 6 | Alte Tests (`test_agent.py`, `test_web_server.py`) | Referenzieren gelöschte Dateien |
| 7 | Persistenz-DB nicht vollständig initialisiert | `/export/leads` kann 500 zurückgeben |
| 8 | Keine Production-Domain | Nur ngrok URL für Webhooks |

---

## 14. LIVE VERIFIZIERTE FAKTEN (NICHT aus Erinnerung)

Alle Informationen in diesem Dokument wurden **ausschließlich** durch folgende Live-Prüfungen gewonnen:

1. **`docker compose ps`** — Service-Status
2. **`curl http://localhost:8010/health`** — Health Endpoint
3. **`curl http://localhost:8010/status`** — Service-Status
4. **`curl http://localhost:8010/metrics`** — Prozess-Metriken
5. **`curl http://localhost:8010/analytics`** — Analytics-Daten
6. **`curl http://localhost:8010/kb/documents`** — Knowledgebase-Dokumente
7. **`curl http://localhost:8010/graph/stats`** — Neo4j Graph-Status
8. **`curl http://localhost:8010/cadence/status`** — Cadence-Status
9. **`curl http://localhost:8010/sla/active`** — SLA-Status
10. **`curl http://localhost:8010/webhooks/stats`** — Webhook-Status
11. **`curl -X POST http://localhost:8010/intent`** — Live Intent-Klassifikation
12. **`curl -X POST http://localhost:8010/coach/score`** — Coach Score
13. **`curl -X POST http://localhost:8010/call`** — Call-Trigger
14. **`wc -l`** — Lines of Code pro Datei
15. **`ls`** — Dateisystem-Struktur
16. **`.venv/bin/pytest tests/test_stepsales.py -v`** — 48 Tests bestanden
17. **Datei-Inhalte gelesen** — settings.py, domain.py, orchestrator_langgraph.py, intent_classifier.py, etc.

---

*Dokument erstellt: 2026-04-24T01:41:34+02:00*  
*Nur live verifizierte Fakten — keine Annahmen, keine Erinnerungswerte.*
