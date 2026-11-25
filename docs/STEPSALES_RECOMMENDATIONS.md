# 🚀 StepSales — Empfehlungen
**Umfassendes Framework für Claude Code Collaboration**

**Status:** ✅ Fertig  
**Datum:** 2026-04-24  
**Gültig für:** Alle StepSales Claude Code Sessions  

---

## 📐 TEIL 1: ARCHITECTURE-EMPFEHLUNGEN

### 1.1 Systemstruktur (High-Level)

```
StepSales-Ecosystem
├── Voice Agent (ElevenLabs Realtime)
│   ├── System Prompt (<200 tokens, latency-critical)
│   ├── Tool Calls (search_jobs, qualify_lead, schedule_demo, send_followup)
│   └── Audio Pipeline (VAD, turn-taking, voice quality)
│
├── Backend Services (Node.js/Python)
│   ├── Lead Database (PostgreSQL)
│   ├── Job Portal API (Stepstone, Indeed, LinkedIn)
│   ├── CRM Integration
│   └── Analytics & Reporting
│
├── Knowledge Systems
│   ├── MEMORY.md (Quick Index)
│   ├── memory.db (Semantic Search - local)
│   └── Supermemory (Cloud Backup + Sync)
│
└── Claude Code Sessions
    ├── Phase 1: Voice Agent Optimization
    ├── Phase 2: Backend Integration
    ├── Phase 3: Analytics & Scaling
    └── Documentation & Knowledge Transfer
```

### 1.2 Dateiorganisation

**Repo-Struktur (StepSales GitHub):**
```
stepsales/
├── README.md                          # Project overview
├── docs/
│   ├── AGENT_CONFIG.md               # Agent settings + tools
│   ├── SYSTEM_PROMPT.md              # Current voice agent prompt
│   ├── DEPLOYMENT.md                 # Docker + production setup
│   └── TROUBLESHOOTING.md            # Known issues + fixes
│
├── src/
│   ├── voice-agent/
│   │   ├── system-prompt.ts          # <200 tokens, version controlled
│   │   ├── tools.ts                  # Tool definitions + validations
│   │   └── audio-pipeline.ts         # VAD, turn-taking, quality
│   │
│   ├── backend/
│   │   ├── leads/
│   │   ├── jobs/
│   │   ├── portals/
│   │   └── auth/
│   │
│   └── integration/
│       ├── stepstone/
│       ├── indeed/
│       ├── linkedin/
│       └── crm/
│
├── docker/
│   ├── docker-compose.yml
│   └── Dockerfile
│
├── tests/
│   ├── voice-agent.test.ts
│   ├── tools.test.ts
│   └── integration.test.ts
│
└── .github/
    ├── workflows/
    │   ├── test.yml
    │   ├── deploy.yml
    │   └── prompt-audit.yml
    └── ISSUE_TEMPLATE/
        └── voice-optimization.md

Claude Code Knowledge Base (~/.omc/):
├── COLLABORATION_GUIDELINES.md        # Work rules (official)
├── MEMORY_SETUP.md                   # How to use all 3 memory systems
├── STEPSALES_ANALYSIS.md             # Agent config + business case
├── STEPSALES_PROJECT_BRIEFING.md     # Complete briefing (4500+ lines)
├── Lena_SystemPrompt_ElevenLabs.txt  # Current optimized prompt
└── SESSION-STATE.md                  # Session tracking
```

### 1.3 Skill-Integration-Patterns

**Pattern 1: Voice Agent Optimization (Iterativ)**
```
🔄 Cycle:
1. Capture Real Call Recording
   ↓
2. voice-agents Skill → Analyze Audio Quality
   ↓
3. prompt-engineering-patterns → Optimize System Prompt
   ↓
4. Test with A/B Comparison
   ↓
5. Measure: Conversion Rate, Duration, Naturalness
   ↓
6. Repeat (weekly)
```

**Pattern 2: Backend Development (Structured)**
```
📋 Flow:
1. Define API endpoint (api-design skill)
   ↓
2. Implement with security (api-security-hardening skill)
   ↓
3. Test (tester agent for comprehensive validation)
   ↓
4. Deploy and monitor
```

**Pattern 3: Agent Performance Improvement (Systematic)**
```
📊 Workflow:
1. Gather Baseline Metrics (via agent-orchestration-improve-agent)
   ↓
2. Identify Failure Modes
   ↓
3. Apply Targeted Improvements (prompt-engineering-patterns)
   ↓
4. A/B Test (voice-agents + prompt-engineering combined)
   ↓
5. Deploy staged (5% → 20% → 100%)
   ↓
6. Monitor for 7 days
```

### 1.4 Deployment-Architektur

**Environments:**
```
Dev:       Lokal Docker (Port 3000)
Staging:   CCT Server (178.104.51.123:8000) + ElevenLabs Sandbox
Prod:      Voice System (157.90.126.58) + Portkey Router + ElevenLabs Live
```

**Rollout Strategy:**
```
Prompt Changes:
  1. Test lokal with agent-orchestration-improve-agent
  2. Deploy Staging (CCT Server) — 5 test calls
  3. Deploy Prod (Voice System) — canary 5% traffic
  4. Monitor 24h (conversion, duration, errors)
  5. Gradual rollout 5% → 20% → 50% → 100%

Backend Changes:
  1. Test locally
  2. Deploy Staging — run full test suite
  3. Deploy Prod — docker compose up -d --build orchestrator
  4. Monitor CCT Server health
```

### 1.5 Error-Handling & Recovery

**Critical Voice Issues:**
| Issue | Detection | Recovery | Time |
|-------|-----------|----------|------|
| Agent speaks too long | VAD analysis in voice-agents skill | Reduce max response tokens | <1h |
| Latency >500ms | Monitor in agents skill | Check system prompt length | <30min |
| Call drops | Audio pipeline errors | Review SIP config + Portkey | <2h |
| Low conversion | Weekly analytics report | Optimize objection handling | <1w |

**Backend Issues:**
| Issue | Detection | Recovery | Owner |
|-------|-----------|----------|-------|
| API timeout | Error logs | Increase rate limiting or add caching | Backend team |
| Database lock | PostgreSQL logs | Optimize query or retry | Database team |
| Portal API failure | Integration tests | Switch fallback API or notify user | Integration team |

---

## 🛠️ TEIL 2: SKILLS-SETUP-EMPFEHLUNGEN

### 2.1 Skills pro Task-Kategorie

#### **Voice Agent Development**

| Aufgabe | Primary Skill | Secondary | Trigger Keywords |
|---------|---------------|-----------|-----------------|
| Agent analysieren | `voice-agents` | `agent-orchestration-improve-agent` | voice, audio, tts, quality |
| System Prompt optimieren | `prompt-engineering-patterns` | `voice-agents` | prompt, optimize, cot, few-shot |
| Conversation Flow verbessern | `agent-orchestration-improve-agent` | `prompt-engineering-patterns` | performance, failure, objection |
| Real-time Issues debuggen | `voice-agents` | (none) | latency, vad, turn-taking |
| Call Recording analysieren | `agent-orchestration-improve-agent` | `voice-agents` | call analysis, failure patterns |

**Activation Flow:**
```
1. Detect keyword in user request
2. Suggest: "Soll ich Skill X aktivieren?"
3. Wait for explicit "ja"
4. Execute: `/skill-name`
5. Integrate results into response
```

#### **Backend & API Development**

| Aufgabe | Primary Skill | Secondary | Trigger |
|---------|---------------|-----------|---------|
| API Design | `api-design` | `api-security-hardening` | rest, graphql, endpoint, versioning |
| Security hardening | `api-security-hardening` | `api-design` | auth, cors, rate-limit, encryption |
| Tool Definition | `api-design` | (none) | tool, parameter, validation, schema |
| Error Handling | `api-security-hardening` | `code-analyzer` | error, handling, fallback, retry |

#### **Quality Assurance**

| Aufgabe | Primary Skill | Secondary | Trigger |
|---------|---------------|-----------|---------|
| Comprehensive Testing | `tester` agent | (none) | test, coverage, validate, qa |
| Code Review | `code-analyzer` | `tester` | review, quality, security, pattern |
| Performance Analysis | `performance-optimizer` | (none) | optimize, latency, throughput, benchmark |

### 2.2 Skill-Reihenfolge (Priority)

**For StepSales Voice Agent Work:**
```
1️⃣ voice-agents            (analyze, debug, quality)
2️⃣ prompt-engineering-patterns (optimize prompts)
3️⃣ agent-orchestration-improve-agent (performance baseline)
4️⃣ api-security-hardening  (backend integration)
5️⃣ api-design              (tool definition)
```

**For Backend Work:**
```
1️⃣ api-security-hardening  (CRITICAL)
2️⃣ api-design              (structuring)
3️⃣ code-analyzer           (quality)
4️⃣ tester                  (validation)
```

### 2.3 Phase-by-Phase Skill Activation

**Phase 1: Voice Agent Baseline (2-3 Sessions)**
- `voice-agents` — Analyze current agent performance
- `prompt-engineering-patterns` — Optimize system prompt
- **Deliverable:** Optimized prompt <200 tokens + baseline metrics

**Phase 2: Backend Integration (2-3 Sessions)**
- `api-security-hardening` — Secure tool APIs
- `api-design` — Refine tool definitions
- **Deliverable:** Secure, tested backend APIs

**Phase 3: Production Hardening (1-2 Sessions)**
- `agent-orchestration-improve-agent` — A/B test improvements
- `performance-optimizer` — Optimize latency
- **Deliverable:** Production-ready voice agent

**Post-Launch (Ongoing)**
- `voice-agents` — Monthly call analysis
- `prompt-engineering-patterns` — Quarterly prompt refreshes
- `tester` — Quarterly regression testing

---

## 💾 TEIL 3: MEMORY-STRATEGIE-EMPFEHLUNGEN

### 3.1 Drei-Schichten-System (Optimal)

```
LAYER 1: MEMORY.md (Quick Index)
└─ Location: ~/.omc/MEMORY.md
└─ Purpose: Fast human-readable index
└─ Update Frequency: Session-end (manual)
└─ Content: Links to topic files + active projects
└─ Max Lines: 200 (keep concise!)

LAYER 2: memory.db (Semantic Search)
└─ Location: ~/.claude/memory.db
└─ Purpose: Full-text + semantic search
└─ Update Frequency: Continuous (bash commands)
└─ Content: Structured facts with namespace + type
└─ Storage: ~500K tokens capacity

LAYER 3: Supermemory (Cloud Backup + Sync)
└─ Location: Cloud API (https://api.supermemory.ai)
└─ Purpose: Persistent backup + cross-device sync
└─ Update Frequency: Auto SessionEnd hook
└─ Content: Mirror of memory.db + attachments
└─ Storage: Unlimited (cloud)
```

### 3.2 Information-Flow (Optimal)

**Während einer Session:**
```
1. START: Read MEMORY.md (quick context check)
   ↓
2. SEARCH: Use ~/mem-search.sh "query" (semantic)
   ↓
3. WORK: Solve task, learn insights
   ↓
4. SAVE: ~/mem-add.sh "fact" namespace type (to memory.db)
   ↓
5. END: SessionEnd Hook auto-syncs to Supermemory
```

**Zwischen Sessions:**
```
Session N → memory.db → Hook → Supermemory ↔ Auto-Sync
              ↓
Session N+1 → Restore from Supermemory to memory.db
              ↓
             Read MEMORY.md (updated by hook)
```

### 3.3 Was in welche Layer speichern?

#### **MEMORY.md (Index only!)**
✅ Speichern:
- Links zu topic files (z.B. `[Voice System](voice-system.md)`)
- Active projects mit Status
- Entscheidungen (kurz)
- Skill-Setup Status

❌ NICHT speichern:
- Langtext (gehört in topic files)
- Ephemeral Task-State
- Code-Snippets
- Details (nur Links!)

**Template Entry (max 100 chars):**
```markdown
- [Lena Voice Agent](voice-agent.md) — Telesales, Realtime API, <200 token prompt ✅
```

#### **memory.db (Semantic + Structured)**
✅ Speichern (via `~/mem-add.sh "text" namespace type`):

**namespace: techstack**
```bash
~/mem-add.sh "Voice Agent: OpenAI Realtime gpt-realtime-1.5 + ElevenLabs shimmer (voice gender: female)" techstack episodic
~/mem-add.sh "Backend: Node.js + Express, PostgreSQL, Portkey Router, CCT orchestrator" techstack episodic
~/mem-add.sh "Ports: Voice 157.90.126.58, CCT 178.104.51.123 (Orchestrator:8000, Mem0:8002, Qdrant:16333)" techstack episodic
```

**namespace: patterns** (Best Practices)
```bash
~/mem-add.sh "Voice Agent Pattern: System prompt MUST be <200 tokens (OpenAI Realtime latency constraint). Longer = 20-50ms additional latency = unnatural conversation" patterns procedural
~/mem-add.sh "Prompt Optimization: Iterative cycle — record call → analyze audio → update prompt → A/B test → measure conversion/duration/naturalness" patterns procedural
~/mem-add.sh "Qualification Logic: Score 0-100 (company size + budget + urgency + fit). Threshold for demo: ≥60 points" patterns procedural
```

**namespace: decisions** (Architecture)
```bash
~/mem-add.sh "Decision: Lena (female) agent for B2B telesales (not Alex). Reason: Better rapport with HR/Recruiting managers in German market" decisions episodic
~/mem-add.sh "Decision: Use all 3 memory systems (MEMORY.md + memory.db + Supermemory). Reason: Index for humans, search for AI, backup for sync" decisions procedural
```

**namespace: errors** (Anti-Patterns)
```bash
~/mem-add.sh "Anti-Pattern: Long system prompts (>200 tokens). Issue: OpenAI Realtime latency increases 20-50ms. Solution: Keep <200, use examples instead of instructions" errors procedural
~/mem-add.sh "Bug: Agent speaks 60%+ without pause. Root cause: No active listening, VAD not detecting silence properly. Fix: Add 2-3 second pauses after questions" errors episodic
```

**namespace: preferences** (User/Project Settings)
```bash
~/mem-add.sh "Preference: Phase-by-phase execution (do Phase 1 only, wait 'next'). Reason: Prevents context overflow and ensures alignment" preferences procedural
~/mem-add.sh "Preference: Verification-first culture. Never green-check without: build ✓, test ✓, lint ✓, manual verification ✓" preferences procedural
```

❌ NICHT speichern:
- Ephemeral task state ("50% done")
- In-progress work (gehört in Git)
- Code patterns (ableitbar aus Linter)
- Git history (git log ist authoritative)

#### **Supermemory (Cloud Backup)**
✅ Auto-synced via SessionEnd Hook:
- Alles aus memory.db
- Alle Dateien aus ~/.omc/
- MEMORY.md updates
- Session-Transkripte (optional)

✅ Manuell hinzufügen:
```bash
~/supermemory-import.sh all          # Import alles
~/supermemory-import.sh techstack    # Nur 1 namespace
```

### 3.4 Search-Strategie

**Vor komplexen Tasks:**
```bash
# Semantische Suche
~/mem-search.sh "voice agent optimization"
~/mem-search.sh "prompt engineering best practices"
~/mem-search.sh "latency constraints voice"

# Deep search (all layers)
python3 ~/.claude/bin/mem-query.py "StepSales" --all-layers
```

**Workflow:**
```
User request → Identify key topic
   ↓
Search memory.db: ~/mem-search.sh "topic keywords"
   ↓
Read MEMORY.md for context/links
   ↓
If incomplete → Search Supermemory (cloud UI)
   ↓
Gather facts + start work
```

### 3.5 Session-Ende Checklist

**Immer am SessionEnd:**
```
□ Wichtige Erkenntnisse gelernt? → ~/mem-add.sh "..." 
□ Bug gelöst? → ~/mem-add.sh "root cause" errors episodic
□ Decision getroffen? → ~/mem-add.sh "entscheidung" decisions
□ New pattern erkannt? → ~/mem-add.sh "pattern" patterns
□ MEMORY.md aktualisieren (Links zu neuen files)
□ SESSION-STATE.md updaten (Current Task, Pending, Last Response)

Auto (Hook):
→ SessionEnd Hook → Auto-sync memory.db → Supermemory
→ All layers backup to cloud
```

### 3.6 Beispiel-Workflow: "Telesales Prompt optimieren"

**Step 1: Start Session**
```bash
# Read quick index
cat ~/.omc/MEMORY.md

# Search for existing insights
~/mem-search.sh "voice agent prompt optimization"
~/mem-search.sh "latency system prompt tokens"
```

**Step 2: Gather Context**
- Find: "Voice Agent Pattern: <200 tokens"
- Find: "Call recording analysis" patterns
- Find: Existing Lena_SystemPrompt_ElevenLabs.txt

**Step 3: Activate Skill**
- Detect keyword "prompt optimize" → Suggest prompt-engineering-patterns
- Wait for "ja" → Execute `/prompt-engineering-patterns`

**Step 4: Work**
- Analyze current prompt tokens
- Run A/B test with 2 variants
- Measure: conversion, duration, naturalness

**Step 5: Save Learnings**
```bash
# Root cause analysis
~/mem-add.sh "Prompt Issue: 'Bereitstellung' sentence too complex. Fix: Split into 2 sentences. Result: 15% better conversion" patterns procedural

# Decision
~/mem-add.sh "Decision: Limit intro to 15 seconds max. Reason: User attention drops after 20s in cold calls" decisions procedural

# Error
~/mem-add.sh "Anti-Pattern: Listing all 10 portals in one sentence. Fix: Mention top 3 only, rest in demo" errors episodic

# Update MEMORY.md
echo "- [Voice Prompt v2](voice-system.md) — Optimized for 15s intro, <200 tokens" >> ~/.omc/MEMORY.md
```

**Step 6: Session End**
```
- Update SESSION-STATE.md
- Hook auto-syncs to Supermemory
- Cloud backup ready
```

---

## ✅ IMPLEMENTIERUNGS-CHECKLIST

### Phase 1: Setup (1-2h)
- [ ] MEMORY.md erstellen (Initial Index)
- [ ] memory.db initialisieren: `~/mem-add.sh "bootstrap" preferences`
- [ ] Supermemory API Key in ~/.zshrc
- [ ] SessionEnd Hook aktivieren
- [ ] Test: `~/mem-search.sh "StepSales"`

### Phase 2: Knowledge Transfer (2-3h)
- [ ] Alle 5 Dateien in MEMORY.md indexieren
- [ ] Techstack in memory.db: `~/mem-add.sh "...", techstack, episodic`
- [ ] Patterns in memory.db (4-5 wichtigste)
- [ ] Decisions in memory.db
- [ ] Test Supermemory sync

### Phase 3: Skill Setup (1-2h)
- [ ] Voice-agents Skill aktivieren + testen
- [ ] Prompt-engineering-patterns Skill aktivieren
- [ ] Agent-orchestration Skill (ready, on demand)
- [ ] API-security-hardening Skill (ready, on demand)

### Phase 4: Process Refinement (Ongoing)
- [ ] Nach jeder Session: ~/mem-add.sh für Learnings
- [ ] Wöchentlich: Memory Index aktualisieren
- [ ] Monatlich: Memory review + consolidation

---

## 📊 SUCCESS METRICS

| Metrik | Baseline | Target | Timeline |
|--------|----------|--------|----------|
| Prompt Token-Länge | 280 | <200 | 1 Session |
| Agent Response Latency | 2.5s avg | <1.5s avg | 2-3 Sessions |
| Call Conversion Rate | TBD | +25% | 4 Weeks |
| Memory Search Efficiency | Manual searches | <30s semantic search | 1 Week |
| Documentation Completeness | 40% | 100% (all 3 layers) | 2 Weeks |

---

## 🎯 NEXT STEPS

1. **Immediately:**
   - [ ] Confirm all 3 recommendation types accepted
   - [ ] Schedule Phase 1 Setup (Memory system)
   - [ ] Prepare StepSales repo for voice agent optimization

2. **Week 1 (Phase 1):**
   - [ ] Voice agent baseline analysis (voice-agents skill)
   - [ ] System prompt optimization (prompt-engineering-patterns)
   - [ ] Record + analyze real calls

3. **Week 2-3 (Phase 2):**
   - [ ] Backend API security review (api-security-hardening)
   - [ ] Tool definition refinement (api-design)
   - [ ] A/B test improved prompt

4. **Week 4+ (Phase 3):**
   - [ ] Production deployment + monitoring
   - [ ] Quarterly optimization cycles
   - [ ] Cross-project learning integration

---

**Erstellt:** 2026-04-24  
**Status:** ✅ Umfassend + implementierbar  
**Nächster Review:** Nach Phase 1 (1 Woche)
