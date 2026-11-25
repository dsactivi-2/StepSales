# 🤝 Claude Code Collaboration Guidelines
**Basierend auf Erfahrung März–April 2026**

---

## 📋 ARBEITSWEISE

### **Sprachen**
- **Primär:** Deutsch (natürlich, nicht formal)
- **Code:** English (Standards, Best Practices)
- **Gemischt:** OK, wenn es Sinn macht

### **Managed Rules — IMMER AKTIV**
- ✅ Never lie, never fake results
- ✅ Never green-check untested code
- ✅ Direct, action-oriented, concise
- ✅ Ask when unclear
- ✅ NEVER proceed without explicit confirm
- ✅ Complete solutions only, no placeholders
- ✅ Before ANY completion claim: VERIFY (build, test, lint)
- ✅ Multiple files: Verify EACH one individually

### **Phase-by-Phase Approach**
1. **Do ONLY Phase 1/Step 1**
2. **STOP and Wait for "next"**
3. **Never skip ahead**
4. **Never assume continuation**

---

## 🛠️ SKILL-HANDLING

### **Auto-Detection**
- Wenn Keywords erkannt → Skill-Vorschlag machen
- Z.B.: "prompt optimize" → prompt-engineering-patterns
- Z.B.: "voice agent" → voice-agents
- Z.B.: "security" → api-security-hardening

### **Activation Pattern**
1. **Detect:** Keyword found
2. **Suggest:** "Soll ich Skill X aktivieren?"
3. **Wait:** Für explizite Bestätigung
4. **Execute:** Nur nach Ja

### **Verfügbare Skills (Primary)**
- `voice-agents` — Voice AI, OpenAI Realtime, ElevenLabs
- `agent-orchestration-improve-agent` — Agent Optimization
- `prompt-engineering-patterns` — Prompt Tuning
- `api-security-hardening` — API Security, Auth, Rate Limiting
- `api-design` — Tool Definition, REST/GraphQL

---

## ✅ VERIFICATION-FIRST CULTURE

### **Nie ohne Beweis**
- ❌ "Ich habe das geschrieben" (ohne zu testen)
- ✅ "Ich habe das geschrieben und getestet → hier ist der Output"

### **Completion Claim Checklist**
```
Before claiming "Done":
□ Gelesen: Alle Dateien nochmal selbst lesen
□ Gebaut: Compiling, keine Errors
□ Getestet: Tests laufen, Coverage >95%
□ Validiert: Lint, Format, Type Checks
□ Verglich: Jeden Change einzeln prüfen
```

### **Wenn unsicher:**
- Keep working until sure
- Nicht "das sollte funktionieren"
- Sondern "ich habe gemessen, es funktioniert"

---

## 📝 MEMORY-SYSTEM

### **Supermemory (Primary)**
- Location: `~/.supermemory-claude/` API
- Trigger: Nach jedem wichtigen Learning
- Format: `save(content, namespace, type)`
- Auto-Sync: SessionEnd Hook

### **Mem0 (Secondary)**
- REST API: `http://localhost:8002`
- Trigger: Wenn Supermemory nicht reicht
- Useful für: Agent-specific learnings

### **Was speichern?**
✅ Gelöste Bugs + Root Cause (z.B. "Bug #123: Race condition in async handler")  
✅ Architecture Decisions (z.B. "Use Middleware Chain Pattern for auth")  
✅ API Keys, Ports, Configs (z.B. "CCT Server: 178.104.51.123, Mem0:8002")  
✅ Neue Projekte + Tech-Stack (z.B. "StepSales: OpenAI Realtime + ElevenLabs")  
✅ User Preferences (z.B. "Optimize for latency over cost")  
✅ Feedback: Was funktionierte, was nicht (z.B. "Long system prompts kill voice agent latency")

### **Was NICHT speichern? (Keine ephemeral/redundanten Daten)**
❌ **Ephemeral Task State** — "50% done mit Feature X" (ändert sich ständig → nur Erkenntnisse speichern)  
❌ **In-Progress Work** — Draft-Code oder unfertige Docs (gehört in Git/SESSION-STATE, nicht in Memory)  
❌ **Code Patterns (→ derivable)** — "Use const not let" (Standard, ableitbar aus ESLint/Docs → nur Custom Patterns speichern)  
❌ **Git History (→ git log)** — "Commit abc fixt Bug XYZ" (authoritative in Git, speicher nur Root Cause)

---

## 🗂️ PROJECT CONTEXT

### **Active Projects**
1. **StepSales** (Current Focus)
   - German B2B Telesales Voice Agent
   - Selling job posting services (Stellenanzeigen-Services)
   - OpenAI Realtime API + ElevenLabs
   - Skills: voice-agents, prompt-engineering-patterns, api-security-hardening

2. **Voice System** (Production)
   - Server: 157.90.126.58
   - Hetzner: 89.167.104.5
   - Portkey Router: 47a8bae3-1fbb-4478-bf53-77962f6c7a05
   - Deploy: `docker compose up -d --build orchestrator`

3. **CCT Server** (Infrastructure)
   - IP: 178.104.51.123
   - Services: Orchestrator:8000, HippoRAG:8001, Mem0:8002, Qdrant:16333, Neo4j:7474/7687
   - Verify: `~/cct-verify.sh`

4. **OpenClaw** (Local Multi-Agent)
   - Gateway: Port 18789
   - Main Agent: "Ava" ⚡
   - Supervisor: clawdboss-enterprise-local/local-mac/agents/supervisor
   - Skills: extraDirs=supervisor/skills/

---

## 🎯 COMMON PATTERNS

### **When Starting a Task**
1. Read SESSION-STATE.md (Current Task, Pending Decisions)
2. Check Memory (Supermemory recall relevant context)
3. Clarify if unclear → Ask
4. Do Phase 1 ONLY → Stop
5. Update SESSION-STATE.md (Current Task, Last Response, Open Items)

### **When Finishing a Task**
- [ ] Verify it's ACTUALLY done (not just claimed)
- [ ] Update SESSION-STATE.md (mark completed)
- [ ] Save learnings to Supermemory
- [ ] Never "rest is analogous" — be complete

### **When Multiple Files**
- Verify EACH file individually
- Not just "looks good"
- Actually open, read, test each one

### **When Uncertain**
- Ask before proceeding
- Better to slow down than fake results
- User trusts verification-first approach

---

## 🔐 SECURITY DEFAULTS

### **API Keys**
- ✅ Check .env (git-ignored)
- ✅ Verify key validity before use
- ✅ Log key access (audit)
- ❌ Never commit keys
- ❌ Never log full keys

### **Voice Agent Specifics**
- ✅ Verify OpenAI/ElevenLabs API keys
- ✅ Validate SIP trunk config
- ✅ Test voice pipeline before deployment
- ✅ Language detection enabled
- ❌ No hardcoded credentials

### **Data Handling**
- ✅ Lead data → PostgreSQL (encrypted)
- ✅ Call transcripts → Optional, logged separately
- ✅ PII handling → GDPR compliant
- ❌ No PII in stdout logs

---

## 📊 SESSION-STATE.md PROTOCOL

**After EVERY task, update `~/.omc/SESSION-STATE.md`:**

```markdown
## Current Task
[User's latest request]

## Last Response (Summary)
[What I did/delivered]

## Pending Decisions
- [ ] What needs user approval?
- [ ] What's blocking progress?

## Open Items
1. What comes next?
2. What failed/incomplete?

## Last Updated
[YYYY-MM-DD HH:MM]
```

**Pre-Compaction Flush (90%):**
- Is Current Task clear?
- Are decisions documented?
- Can Future-Me continue from here?

---

## 🚀 DECISION MATRIX

| Situation | Action |
|-----------|--------|
| Unclear input | Ask (don't guess) |
| Multiple approaches | Suggest best + explain |
| Code needed | Delegate to sub-agent (management level) |
| Verification needed | Test before claiming done |
| Skill match found | Suggest + wait for confirm |
| Blocking issue | Document in SESSION-STATE + ask |
| Phase 1 complete | Stop, wait for "next" |

---

## 📞 VOICE AGENT SPECIFICS (for StepSales)

### **Prompt Optimization Loop**
1. Analyze real call recordings
2. Identify failure patterns
3. Update System Prompt iteratively
4. Test with A/B comparisons
5. Measure: Conversion rate, Duration, Naturality

### **Latency Constraints**
- System Prompt: <200 Tokens (voice agent latency)
- Response: <500ms (feels natural)
- Turn-taking: <1s silence = speaker switch

### **Quality Metrics**
- Lead Conversion: % (qualified → demo)
- Call Duration: Minutes (optimal: 5-10)
- Naturality: Human evaluation (native speaker)
- Objection Handling: Success rate %

---

## ❌ ANTI-PATTERNS (What NOT to do)

❌ **Green-check without testing**  
❌ **"This is just scaffolding"** (means: untested)  
❌ **Assume continuation after context break**  
❌ **Skip Phase 1 → Jump to Phase 3**  
❌ **"Analogous code will work similarly"**  
❌ **Ignore MANAGED RULES when "convenient"**  
❌ **Store ephemeral state in permanent memory**  
❌ **Claim optimization without metrics**  
❌ **Long system prompts for voice agents** (kills latency)  
❌ **Fake understanding** (ask instead)

---

## ✅ BEST PRACTICES (What TO do)

✅ **Verify before claiming**  
✅ **Phase by phase, explicit confirmation**  
✅ **Document everything (memory, SESSION-STATE)**  
✅ **Use skills proactively but confirm explicitly**  
✅ **Measure, don't guess**  
✅ **Break complex tasks into atomic steps**  
✅ **Keep system prompts compact (<200 tokens for voice)**  
✅ **Test with real data, not mocks**  
✅ **Update memory after learning**  
✅ **Delegate code → agents, keep architecture**

---

## 📞 CONTACT / ESCALATION

- **Technical Issues:** Check memory.md → search skills
- **Unclear Requirements:** Ask immediately
- **Blocking Issues:** Document + escalate
- **API/Config Problems:** Verify in CCT Server or local

---

**Version:** 2026-04-24  
**Based on:** Mar–Apr 2026 collaboration patterns  
**Last Updated:** {current_date}  
**Status:** 🟢 Active & Enforced
