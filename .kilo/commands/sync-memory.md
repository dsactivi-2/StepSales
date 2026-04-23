# /sync-memory

Summarize session deltas, append one decision/event line, and refresh the ledger.

## Inputs
- Current session notes and changes
- `.kilo/memory/memory-ledger.md`
- `.kilo/memory/decisions.jsonl`
- `.kilo/memory/vector_store.json`
- `.kilo/memory/graph.cypher`
- `.kilo/commands/write-memory.md`
- `.kilo/scripts/memory_write.py`

## Workflow
1. Collect what changed this session (features, fixes, infra/docs/process updates).
2. Condense to a short delta summary:
   - what changed
   - why it changed
   - remaining risk or follow-up
3. Classify one primary record type:
   - `decision` for policy/standard changes
   - `event` for notable state/progress updates
4. Append exactly one JSON object line to `decisions.jsonl` with fields:
   - `timestamp` (ISO-8601 UTC)
   - `type` (`decision`|`event`)
   - `id` (unique, e.g., `mem-004`)
   - `topic`
   - `summary`
   - `status` (`active`|`open`|`superseded`|`closed`)
   - `evidence`
   - `sensitivity` (`public`|`restricted-redacted`)
5. Update `memory-ledger.md` sections:
   - Refresh `Active Decisions`, `Open Risks`, `Next Actions`, and `Last Updated`.
   - Keep entries concise and remove stale/superseded items.
6. Execute write path via `/write-memory` or `python3 .kilo/scripts/memory_write.py ...` so JSONL/vector/graph updates stay synchronized.
7. Output a short sync report:

```text
MEMORY_SYNC_OK
appended_record: <id>
ledger_updated: true
highlights: <2-4 bullets>
```

## Safety Rules
- Never write raw secrets/API keys/tokens/passwords/private customer data.
- Redact sensitive values (example: `<REDACTED_DB_URL>`).
- If a change includes sensitive material, store only a sanitized summary.

## Validation
- `decisions.jsonl` remains valid JSONL (one JSON object per line).
- Ledger sections stay present in required structure.
- `Last Updated` uses current UTC timestamp.
