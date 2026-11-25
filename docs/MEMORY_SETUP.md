# 📚 Memory System Setup & Instructions
**Wie man alle 3 Memory Systems konkret einsetzt**

---

## 🎯 SYSTEM OVERVIEW

| System | Ort | Setup | Zugriff |
|--------|-----|-------|---------|
| **MEMORY.md** | Lokal (Repo) | Manual Index | `cat MEMORY.md` |
| **memory.db** | Lokal (`~/.claude/memory.db`) | CLI Commands | `~/mem-search.sh "query"` |
| **Supermemory** | Remote (Cloud API) | Auto-Sync Hook | Browser UI oder API |

---

## ✅ SETUP CHECKLIST

### **1️⃣ MEMORY.md (Index File)**

**Datei:** `~/.claude/projects/-Users-dsselmanovic/MEMORY.md`

**Inhalt (template):**
```markdown
# Memory Index
Last updated: 2026-04-24

## Documentation
- [Collaboration Guidelines](./COLLABORATION_GUIDELINES.md) — Official rules for Claude Code sessions
- [StepSales Analysis](./STEPSALES_ANALYSIS.md) — Voice agent configuration + business case
- [Memory Setup](./MEMORY_SETUP.md) — How to use all 3 memory systems

## Active Projects
- StepSales: German B2B Telesales Voice Agent
- Voice System: Production (157.90.126.58)
- CCT Server: Infrastructure (178.104.51.123)
- OpenClaw: Local multi-agent

## Key Decisions
- Memory: Use all 3 systems (MEMORY.md + memory.db + Supermemory)
- Voice Agent: Keep system prompt <200 tokens (latency constraint)
- Phase-by-Phase: Do Phase 1 only, wait for "next"
```

**Verwaltung:**
```bash
# Hinzufügen
echo "- [New Doc](path) — Description" >> MEMORY.md

# Suchen
grep "keyword" MEMORY.md

# Git tracking
git add MEMORY.md
git commit -m "Update memory index"
```

---

### **2️⃣ memory.db (Semantic Database)**

**Installation Check:**
```bash
# Prüfe ob memory.db existiert
ls -lh ~/.claude/memory.db

# Falls nicht: Erstellen (auto beim ersten mem-add)
~/mem-add.sh "test" preferences procedural
```

**Daten speichern (konkrete Befehle):**

```bash
# 1. TECHSTACK
~/mem-add.sh "StepSales: German B2B Telesales Voice Agent (OpenAI Realtime gpt-realtime-1.5 + ElevenLabs shimmer voice)" techstack episodic

~/mem-add.sh "CCT Server Infrastructure: IP 178.104.51.123, Orchestrator:8000, HippoRAG:8001, Mem0:8002, Qdrant:16333, Neo4j:7474/7687" techstack episodic

~/mem-add.sh "Voice System Production: Server 157.90.126.58, Hetzner 89.167.104.5, Portkey Router 47a8bae3-1fbb-4478-bf53-77962f6c7a05" techstack episodic

# 2. PATTERNS (Best Practices)
~/mem-add.sh "Memory Rule: Store ONLY completed insights + learnings. NEVER store ephemeral task state ('50% done'), in-progress work, derivable patterns, or git history" patterns procedural

~/mem-add.sh "Voice Agent Pattern: System prompt MUST be <200 tokens for OpenAI Realtime API (latency constraint). Longer prompts kill conversation naturalness" patterns procedural

~/mem-add.sh "Claude Code Workflow: Phase-by-phase approach. Do ONLY Phase 1, STOP, wait for 'next'. Never skip ahead or assume continuation" patterns procedural

~/mem-add.sh "Verification-First Culture: Never green-check without testing. Before claiming 'done': verify (build, test, lint), then read all files again" patterns procedural

# 3. DECISIONS (Architecture)
~/mem-add.sh "Memory System Strategy: Use all 3 systems. MEMORY.md for index, memory.db for semantic search, Supermemory for cloud backup/sync" decisions procedural

~/mem-add.sh "StepSales Business Model: Selling job posting services (NOT job listings). Target: SMEs (10-1000 employees). Revenue: SaaS per package (€299-1299/month)" decisions episodic

# 4. ERRORS (What NOT to do)
~/mem-add.sh "Anti-Pattern: Long system prompts for voice agents (>200 tokens). Causes: 20-50ms latency increase, agent sounds slow, kills conversation flow" errors procedural

~/mem-add.sh "Anti-Pattern: Store task state in memory ('50% done'). Changes constantly, becomes stale, clogs semantic index. Store only ROOT CAUSE + learnings" errors procedural

# 5. PREFERENCES (User Settings)
~/mem-add.sh "Claude Code User Preferences: Languages (Deutsch primary, English code), Verification-first, Phase-by-phase execution, No green-checks without proof" preferences procedural
```

**Daten abrufen:**
```bash
# Suchen
~/mem-search.sh "StepSales configuration"
~/mem-search.sh "voice agent latency"
~/mem-search.sh "memory best practices"

# Alle Layer anschauen
python3 ~/.claude/bin/mem-query.py "StepSales" --all-layers

# Namespace filtern
~/mem-search.sh "voice" # searches all namespaces
```

---

### **3️⃣ Supermemory (Cloud Sync)**

**Setup (einmalig):**

```bash
# 1. API Key konfigurieren
echo 'export SUPERMEMORY_CC_API_KEY="sm_your_api_key_here"' >> ~/.zshrc
source ~/.zshrc

# 2. Verify Connection
curl -H "Authorization: Bearer $SUPERMEMORY_CC_API_KEY" \
  https://api.supermemory.ai/v3/documents

# Expected: 200 OK (keine Auth-Fehler)
```

**Auto-Sync Hook (bereits aktiv):**
```bash
# SessionEnd Hook in ~/.claude/hooks/supermemory-sync.sh
# Automatisch bei Session-Ende:
# 1. Liest memory.db
# 2. Synct zu Supermemory Cloud API
# 3. Speichert in containerTag "claude-code-memory"
```

**Manuell in Cloud speichern:**
```bash
# Falls Hook nicht lauft, manuell:
~/supermemory-import.sh all

# Oder einzelne Kategorien:
~/supermemory-import.sh techstack
~/supermemory-import.sh patterns
~/supermemory-import.sh decisions
```

**Abrufen aus Cloud (Supermemory UI):**
- URL: https://app.supermemory.ai (login mit API Key)
- Container: claude-code-memory
- Filter: Nach tags/namespaces

---

## 🔄 WORKFLOW EXAMPLES

### **Beispiel 1: Bug fixen + in Memory speichern**

```bash
# 1. Bug fixen (work)
# ... fix the bug in code ...

# 2. Root Cause analysieren
# Bug war: Race condition in async handler

# 3. In memory.db speichern (NICHT den Task State!)
~/mem-add.sh "Bug #456: Race condition in async handler (line 123). Fix: Added mutex lock before shared state access" errors episodic

# 4. Auto-synct zu Supermemory (SessionEnd Hook)

# 5. Später suchen:
~/mem-search.sh "race condition async"
```

### **Beispiel 2: Architecture Decision dokumentieren**

```bash
# 1. Decision treffen
# Entscheidung: Memory System nutzt alle 3 (MEMORY.md + memory.db + Supermemory)

# 2. In memory.db speichern
~/mem-add.sh "Memory Strategy Decision: Use all 3 systems. Reasoning: MEMORY.md for quick index, memory.db for semantic search, Supermemory for cloud backup/cross-device sync" decisions procedural

# 3. Auch in MEMORY.md indexieren
echo "- Memory System: All 3 active (MEMORY.md + memory.db + Supermemory)" >> MEMORY.md

# 4. SESSION-STATE.md updaten
# (Normal workflow tracking)
```

### **Beispiel 3: Neues Projekt hinzufügen**

```bash
# 1. Projekt info sammeln
# Name: StepSales
# Type: Voice Agent
# Tech: OpenAI Realtime + ElevenLabs
# Status: Active

# 2. In memory.db
~/mem-add.sh "Project: StepSales — German B2B Telesales Voice Agent for job posting services. Tech: OpenAI Realtime gpt-realtime-1.5 + ElevenLabs shimmer. Status: Active (Jan-Apr 2026)" projects episodic

# 3. In MEMORY.md
echo "- StepSales (Active): Voice Agent for job posting services" >> MEMORY.md

# 4. Search später
~/mem-search.sh "StepSales"
```

---

## 📋 TROUBLESHOOTING

### **Problem: memory.db nicht gefunden**
```bash
# Check
ls ~/.claude/memory.db

# If missing: erstelle es
~/mem-add.sh "bootstrap" preferences procedural

# Verify
ls -lh ~/.claude/memory.db
```

### **Problem: mem-search.sh nicht gefunden**
```bash
# Prüfe PATH
echo $PATH | grep -i claude

# Falls fehlend: Manual path
~/mem-search.sh "query"
/Users/dsselmanovic/mem-search.sh "query"
# oder
python3 ~/.claude/bin/mem-query.py "query"
```

### **Problem: Supermemory API Key ungültig**
```bash
# Check
echo $SUPERMEMORY_CC_API_KEY

# Update
export SUPERMEMORY_CC_API_KEY="sm_new_key_here"

# Test
curl -H "Authorization: Bearer $SUPERMEMORY_CC_API_KEY" \
  https://api.supermemory.ai/v3/documents
```

---

## ✅ VERIFICATION CHECKLIST

- [ ] MEMORY.md exists at `~/.claude/projects/-Users-dsselmanovic/MEMORY.md`
- [ ] memory.db exists at `~/.claude/memory.db`
- [ ] `~/mem-add.sh` works (`~/mem-add.sh "test" preferences procedural`)
- [ ] `~/mem-search.sh` works (`~/mem-search.sh "StepSales"`)
- [ ] Supermemory API Key configured (`echo $SUPERMEMORY_CC_API_KEY`)
- [ ] SessionEnd Hook active (`cat ~/.claude/hooks/supermemory-sync.sh`)

---

## 📖 REFERENCE

| Command | Purpose | Example |
|---------|---------|---------|
| `~/mem-add.sh "text" namespace type` | Speichern in memory.db | `~/mem-add.sh "Bug XYZ root cause" errors episodic` |
| `~/mem-search.sh "query"` | Suchen in memory.db | `~/mem-search.sh "voice agent"` |
| `python3 ~/.claude/bin/mem-query.py "query" --all-layers` | Deep search (alle Layer) | `python3 ~/.claude/bin/mem-query.py "latency"` |
| `grep "keyword" MEMORY.md` | Suchen in lokalem Index | `grep "StepSales" MEMORY.md` |
| `git add MEMORY.md && git commit -m "msg"` | MEMORY.md versionieren | `git add MEMORY.md && git commit -m "Update memory index"` |

---

**Version:** 2026-04-24  
**Status:** 🟢 Complete & Ready  
**Last Updated:** {current_date}
