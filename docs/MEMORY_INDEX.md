# Memory Index
**Last updated:** 2026-04-24  
**Status:** 🟢 Complete & Production-Ready

---

## 📚 Documentation (StepSales Complete Framework)

### Core Documents (Read in Order)
1. [Collaboration Guidelines](./COLLABORATION_GUIDELINES.md) — Official work rules + managed rules (PFLICHT lesen)
2. [StepSales Analysis](./STEPSALES_ANALYSIS.md) — Agent config + system prompt + business case
3. [StepSales Project Briefing](./STEPSALES_PROJECT_BRIEFING.md) — Complete briefing (4500+ lines)
4. [Memory Setup Guide](./MEMORY_SETUP.md) — How to use all 3 memory systems (MEMORY.md + memory.db + Supermemory)
5. [StepSales Recommendations](./STEPSALES_RECOMMENDATIONS.md) — Architecture + Skills + Memory strategy

### Supporting Files
- [Lena System Prompt (ElevenLabs)](../Downloads/Lena_SystemPrompt_ElevenLabs.txt) — Current optimized prompt
- [Session State](../.omc/SESSION-STATE.md) — Current task tracking

---

## 🚀 Active Projects

### **StepSales** (Current Focus 2026-04-24 → ongoing)
- **Type:** German B2B Telesales Voice Agent
- **Business Model:** Selling job posting services (Stellenanzeigen) to companies with open positions
- **Tech Stack:** OpenAI Realtime (gpt-realtime-1.5) + ElevenLabs shimmer voice
- **Agent:** Lena (female, authentic, 110-130 words/min)
- **System Prompt:** <200 tokens (latency-critical), version-controlled
- **Repository:** https://github.com/dsactivi-2/StepSales
- **Phases:** Phase 1 (voice baseline) → Phase 2 (backend) → Phase 3 (production)

### **Voice System** (Production)
- **Server:** 157.90.126.58 (Hetzner 89.167.104.5)
- **URL:** https://voice.activi.io ✅
- **Deployment:** `docker compose up -d --build orchestrator`
- **Portkey Router:** 47a8bae3-1fbb-4478-bf53-77962f6c7a05

### **CCT Server** (Infrastructure)
- **IP:** 178.104.51.123
- **Services:** Orchestrator:8000, HippoRAG:8001, Mem0:8002, Qdrant:16333, Neo4j:7474/7687
- **Verify:** `~/cct-verify.sh` or `~/cct-verify.sh --quick`
- **Tunnel:** `cct-tunnels` alias (port forwarding: 16333→26333, 7474→27474, 7687→27687)

### **OpenClaw** (Multi-Agent Orchestration)
- **Gateway:** Port 18789 (local)
- **Supervisor:** "Activi" 🧠 (clawdboss-enterprise-local/local-mac/agents/supervisor)
- **Main Agent:** "Ava" ⚡ (anthropic/claude-sonnet-4-6)
- **Deploy Server:** 37.27.71.134 (7 agents ready to deploy)
- **Telegram:** @Activi_bot (Denis-ID: 8212488253)

---

## 🎯 Key Decisions

### **Memory System Strategy** (✅ 2026-04-24)
- **Decision:** Use all 3 systems (MEMORY.md + memory.db + Supermemory)
- **Why:** Quick index for humans (MEMORY.md) + semantic search for AI (memory.db) + persistent cloud backup (Supermemory)
- **Setup:** Completed in MEMORY_SETUP.md with concrete bash commands

### **Voice Agent Optimization** (✅ 2026-04-24)
- **Decision:** Lena (female, authentic) for B2B telesales to German HR/Recruiting
- **Why:** Better rapport than male agent (market research)
- **Constraint:** System prompt <200 tokens (latency critical for OpenAI Realtime)

### **Architecture & Collaboration** (✅ 2026-04-24)
- **Decision:** Phase-by-phase execution (do Phase 1 only, wait "next")
- **Why:** Prevents context overflow, ensures alignment, enables course correction
- **Verification-First:** Never green-check without: build ✓, test ✓, lint ✓, verify ✓

### **Skills Setup** (✅ 2026-04-24)
- **Priority 1:** voice-agents (analyze, debug, quality)
- **Priority 2:** prompt-engineering-patterns (optimize)
- **Priority 3:** agent-orchestration-improve-agent (baseline metrics)
- **Priority 4:** api-security-hardening (backend)
- **Priority 5:** api-design (tool definitions)

---

## 📋 Framework Checklist

### Phase 1: Memory System Setup (→ Session 1)
- [ ] Read: COLLABORATION_GUIDELINES.md + MEMORY_SETUP.md
- [ ] Initialize: `~/mem-add.sh "bootstrap" preferences procedural`
- [ ] Verify: `~/mem-search.sh "StepSales"`
- [ ] Test Supermemory: SessionEnd hook auto-sync

### Phase 2: Voice Agent Baseline (→ Session 2-3)
- [ ] Activate voice-agents + prompt-engineering-patterns skills
- [ ] Analyze current agent: call recordings, token length, latency
- [ ] Optimize system prompt: <200 tokens, measure A/B results
- [ ] Deliverable: Optimized prompt + baseline metrics

### Phase 3: Backend Integration (→ Session 4-5)
- [ ] Activate api-security-hardening + api-design skills
- [ ] Review tool APIs: security, error handling, validation
- [ ] Implement improvements
- [ ] Deliverable: Secure, tested backend APIs

### Phase 4: Production Hardening (→ Session 6-7)
- [ ] A/B test improved prompt: conversion, duration, naturalness
- [ ] Deploy staged: 5% → 20% → 50% → 100%
- [ ] Monitor for 7 days
- [ ] Deliverable: Production-ready voice agent

---

## 🔐 Critical Constraints

| Constraint | Value | Why | How to Apply |
|-----------|-------|-----|--------------|
| System Prompt Length | <200 tokens | OpenAI Realtime latency (each 50 tokens = 10-20ms) | Split long instructions into examples |
| Response Latency | <500ms | Natural conversation (silence >1s triggers speaker switch) | Monitor token consumption + API response time |
| Session Duration | Phase 1 only | Prevent context overflow | Stop after Phase 1, wait explicit "next" |
| Memory Storage | 3 systems | Optimal redundancy + search | Use MEMORY.md (index) + memory.db (semantic) + Supermemory (backup) |
| Verification | 100% required | Prevents false positives | Always: build + test + lint + manual check before "done" |

---

## 📞 Voice Agent Quick Reference

**Agent:** Lena (female, authentic German)  
**Voice:** ElevenLabs shimmer, 110-130 words/min, 0.7 temperature  
**System Prompt:** <200 tokens (CURRENT: 135 tokens in Lena_SystemPrompt_ElevenLabs.txt)  
**Tools:** search_jobs, qualify_lead, schedule_demo, send_followup  
**Qualification Score:** 0-100 (threshold: ≥60 for demo)  
**Call Duration:** Optimal 5-10 minutes  

**Real Call Insights (2026-04-24 Analysis):**
- ❌ Agent speaking 60%+ without pauses (kill active listening)
- ❌ "Hhmmmm...yeah" repetition 5x (unnatural)
- ❌ Pitch too hard instead of qualifying
- ✅ Multiposting strategy resonates with qualified leads
- ✅ Time-savings argument (weeks → days) drives interest

---

## 🛠️ Skills & Tools (Always Available)

**Claude Code Skills (5 Primary):**
1. `voice-agents` — Voice quality, audio analysis, VAD, turn-taking
2. `prompt-engineering-patterns` — Prompt optimization, few-shot, CoT
3. `agent-orchestration-improve-agent` — Performance baseline, A/B testing
4. `api-security-hardening` — Auth, CORS, rate limiting, encryption
5. `api-design` — REST design, tool definitions, error handling

**MCP Servers:**
- `memory.db` (local semantic search)
- `mem0` (REST API http://localhost:8002)
- `supermemory` (cloud backup + sync)

**Custom Scripts:**
- `~/mem-add.sh "text" namespace type` — Add to memory.db
- `~/mem-search.sh "query"` — Semantic search
- `~/cct-verify.sh` — Verify CCT Server health

---

## 📊 Status Summary

| Area | Status | Evidence |
|------|--------|----------|
| **Documentation** | ✅ Complete | 5 comprehensive docs + briefing |
| **Memory System** | ✅ Ready | Setup guide with concrete commands |
| **Architecture** | ✅ Designed | Recommendation doc with all layers |
| **Skills Setup** | ✅ Planned | Priority ordering + activation workflow |
| **Collaboration Rules** | ✅ Defined | COLLABORATION_GUIDELINES.md (official) |
| **Voice Agent** | ⏳ Optimizing | Baseline captured, Phase 1 starting |
| **Backend** | ⏳ Planned | Phase 2 (4-5 sessions ahead) |
| **Production** | ⏳ Staged | Phase 3+ deployment plan ready |

---

## 🚀 Next Session (Immediate)

**Do:**
1. Read STEPSALES_RECOMMENDATIONS.md (Architecture + Skills + Memory)
2. Confirm Phase 1 approach
3. Start memory system setup (if not done)
4. Activate voice-agents skill
5. Begin voice agent optimization

**Don't:**
- Skip to Phase 2 or Phase 3 (Phase 1 first!)
- Assume previous context (read COLLABORATION_GUIDELINES.md)
- Make changes without verification
- Store ephemeral task state in memory

---

**Created by:** Claude Code (2026-04-24)  
**Framework:** Phase-by-phase, verification-first, all 3 memory systems  
**Governance:** COLLABORATION_GUIDELINES.md (binding)  
**Last Review:** 2026-04-24  
**Next Review:** After Phase 1 completion (~1 week)
