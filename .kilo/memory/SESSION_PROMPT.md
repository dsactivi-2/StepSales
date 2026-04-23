# Stepsales AI Telesales Agent – Neue Session Fortführung

## Kontext
Du übernimmst die Arbeit an einem deutschen AI-Telesales-Agenten (Stepsales) für Multiposting auf StepStone + Indeed. Das Projekt ist in `/root/activi-dev-repos/stepsales/`.

## Zuerst lesen
1. Lese `/root/activi-dev-repos/stepsales/.kilo/memory/handover-2026-04-23.md` – das ist der vollständige Session-Handover
2. Lese `/root/activi-dev-repos/stepsales/.kilo/memory/decisions.jsonl` – alle bisherigen Entscheidungen
3. Lese `/root/activi-dev-repos/stepsales/.kilo/memory/memory-ledger.md` – Projekt-Status

## Architektur (aktiv)
```
Deepgram STT (nova-3, de, PCM 16kHz, VAD: utterance_end_ms=1000)
    ↓ Text
LangGraph Orchestrator (8-Node State Machine: greet→discovery→qualify→offer→objection→close→followup→summary)
    ↓ Text
OpenAI LLM (chat.completions, gpt-4.1-2025-04-14)
    ↓ Text
ElevenLabs TTS (Streaming, eleven_multilingual_v2)
    ↓ Audio
Telnyx play_audio (REST API)
```

## Laufende Docker Services
- `stepsales-agent` → Port 8010 (Entry Point: `main.py`)
- `qdrant-stepsales` → Port 6333/6334 (Vector DB)
- `neo4j-stepsales` → Port 7474/7687 (Graph DB)
- `stepstone-mcp` → intern (Job-Suche)

Befehl: `cd /root/activi-dev-repos/stepsales && docker compose ps`

## Kritische Blocker (müssen zuerst gelöst werden)
1. `STRIPE_API_KEY` ist LEER in `.env` → Billing funktioniert nicht
2. `TELNYX_FROM_NUMBER` fehlt in `.env` → Outbound Calls scheitern
3. Agent Healthcheck zeigt "unhealthy" (falsches CMD im Healthcheck)
4. Qdrant Healthcheck zeigt "unhealthy" (bash/curl fehlt im Image)

## Funktionale Lücken (Prio 1-3)
1. **Kein Call-Trigger** – `main.py` läuft im Idle-Loop, es gibt keinen REST-Endpoint oder Scheduler der `start_outbound_call()` aufruft
2. **Stepstone-DNS falsch** – `lead_intel.py` nutzt `http://localhost:8000` statt `http://stepstone-mcp:8000` im Docker-Netz
3. **Barge-In fehlt** – Kunde kann nicht unterbrechen während der Agent spricht
4. **Latency ~1.5-3s** – 3 Hop-Punkte ohne Optimierung

## Was NICHT mehr genutzt wird (toter Code)
- `web_server.py` – alter Web-UI Server, nicht gestartet
- `telesales_agent.py` – alter Heuristik-Agent, nicht gestartet
- `services/orchestrator.py` – alte Orchestrator-Implementierung (Keyword-Matching)
- `config_legacy.py` – alte Config-Datei

## Context7 MCP
- CLI: `ctx7` global installiert
- MCP: Konfiguriert in `.kilo/kilo.json` mit API-Key
- Skill: `.kilo/skills/context7/SKILL.md` mit 12 Library-IDs
- Verwendung: `ctx7 docs /langchain-ai/langgraph "conditional edges"`

## Auto-Run Modus
- Aktiviert in `.kilo/kilo.json`: `bash: allow`, `edit: allow`, `read: allow`
- Keine Rückfragen für Bash-Befehle, Datei-Operationen

## GitHub
- Remote: `https://github.com/dsactivi-2/StepSales.git`
- Letzter Commit: `4146434` – "docs: add session handover and update memory decisions"
- SSH Key: `/root/.ssh/id_ed25519` (oder PAT nutzen)

## Nächste sinnvolle Schritte (Priorität)
1. REST-Endpoint erstellen für Outbound-Calls (`POST /call`)
2. Stepstone-DNS fixen (`localhost` → `stepstone-mcp`)
3. Healthcheck fixen (CMD auf `main.py` Laufzeit prüfen)
4. API Keys nachtragen (STRIPE_API_KEY, TELNYX_FROM_NUMBER)
5. Barge-In implementieren (paralleles Hören während TTS)
6. PostgreSQL-Checkpointer statt MemorySaver

## Wichtige Pfade
- Projekt-Root: `/root/activi-dev-repos/stepsales/`
- Entry Point: `main.py` (LangGraphOrchestrator)
- Services: `services/orchestrator_langgraph.py` (aktiv)
- Config: `config/settings.py` (Unified), `.env` (API Keys)
- Kilo Config: `.kilo/kilo.json` (Projekt), `~/.config/kilo/kilo.jsonc` (Global)

## Arbeitsweise
- Arbeite iterativ, Schritt für Schritt
- Nach jeder größeren Änderung: `docker compose up -d --build` und Status prüfen
- Bei Code-Änderungen: `git add -A && git commit -m "..." && git push`
- Veränderte Dateien immer zuerst lesen vor dem Editieren
- Keine Secrets committen (werden von GitHub blockiert)
- Context7 für Library-Dokumentation nutzen wenn unsicher
