# /bootstrap-memory

Hydrate session context from memory artifacts and emit a compact context pack.

## Inputs
- query text (optional; default `current project state`)
- `.kilo/memory/memory-ledger.md`
- `.kilo/memory/decisions.jsonl`
- `.kilo/memory/vector_store.json`
- `.kilo/memory/graph.cypher`
- `.kilo/memory/retrieval_profile.yaml`
- `.kilo/commands/query-memory.md`
- `.kilo/scripts/memory_query.py`

## Workflow
1. Validate files exist; if missing, create minimal safe defaults.
2. Read `memory-ledger.md` and extract:
   - `Project Snapshot`
   - `Active Decisions`
   - `Open Risks`
   - `Next Actions`
   - `Last Updated`
3. Read `decisions.jsonl` and parse newline-delimited JSON entries.
4. Keep latest high-signal items only (suggestion: last 10 entries, prioritize `status=active|open`).
5. Build and output a compact context pack:

```text
CONTEXT_PACK
project_snapshot: <1-3 bullets>
active_decisions: <bullets>
open_risks: <bullets>
next_actions: <bullets>
recent_events: <timestamped bullets>
safety: no raw secrets; redact sensitive values
```

6. If parsing fails for any line, skip invalid line and report it in output as `parse_warning`.
7. Prefer delegating retrieval to `/query-memory` or `python3 .kilo/scripts/memory_query.py "<query>"` for consistent hybrid scoring behavior.

## Safety Rules
- Never store or output raw secrets/API keys/tokens/passwords.
- Redact sensitive values before emitting context (example: `<REDACTED>`).
- Preserve only operationally necessary context.

## Success Criteria
- Context pack is produced in under ~1 page.
- Pack reflects current port (`8010`), env path (`environment/.env`), and latest open gaps.
