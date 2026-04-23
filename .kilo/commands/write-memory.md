# /write-memory

Sanitize and persist a memory update using dual/triple-write across decisions log, vector store, and graph append log.

## Inputs
- `type`: `decision` or `event`
- `topic`: short kebab/snake/camel compatible label
- `summary`: concise operational update (sanitized)
- `status`: `active|open|superseded|closed`
- `sensitivity`: `public|restricted-redacted`

## Workflow
1. Validate arguments and normalize values.
2. Sanitize summary:
   - redact secret-like tokens/password patterns
   - remove raw credential material
   - trim to operationally necessary context
3. Build canonical record with:
   - `timestamp` (UTC ISO-8601)
   - `id` (auto-increment `mem-###`)
   - provided fields + optional evidence placeholder
4. Persist writes:
   - append JSON line to `.kilo/memory/decisions.jsonl`
   - append vector record to `.kilo/memory/vector_store.json`
   - append Cypher `MERGE` snippet under append log in `.kilo/memory/graph.cypher`
5. Emit deterministic result payload with ids and file update status.

## Deterministic Output Format
```json
{
  "status": "MEMORY_WRITE_OK",
  "record_id": "mem-###",
  "vector_id": "vec-###",
  "topic": "<topic>",
  "type": "decision|event",
  "files": {
    "decisions_jsonl": true,
    "vector_store_json": true,
    "graph_cypher": true
  },
  "warnings": []
}
```

## Preferred Local Runner
- `python3 .kilo/scripts/memory_write.py --type event --topic "..." --summary "..." --status active --sensitivity public`

## Safety
- Never store secrets or private customer identifiers.
- If input appears sensitive, write only redacted summary.
