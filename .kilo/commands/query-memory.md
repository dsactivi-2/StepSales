# /query-memory

Retrieve a deterministic context pack using hybrid memory retrieval over ledger + decision log + vector store + graph references.

## Inputs
- query string (required)
- optional overrides: `top_k`, `sensitivity`, `graph_hops`
- `.kilo/memory/memory-ledger.md`
- `.kilo/memory/decisions.jsonl`
- `.kilo/memory/vector_store.json`
- `.kilo/memory/graph.cypher`
- `.kilo/memory/retrieval_profile.yaml`

## Workflow
1. Load retrieval profile defaults.
2. Read memory files (create safe in-memory empty defaults if missing).
3. Lexical score: token overlap against ledger snippets, decisions, and vector text/tags.
4. Semantic proxy score: normalized token/tag affinity from vector records.
5. Graph expansion: include connected entities up to configured `graph_hops` using relation text from `graph.cypher`.
6. Rerank with weighted sum + freshness boost.
7. Apply sensitivity filter before output.
8. Redact suspicious token-like values before emitting.

## Deterministic Output Format
```json
{
  "query": "<string>",
  "retrieval_profile": {
    "top_k": <int>,
    "lexical_weight": <float>,
    "semantic_weight": <float>,
    "graph_hops": <int>,
    "freshness_boost": <float>
  },
  "results": [
    {
      "rank": 1,
      "source": "ledger|decision|vector|graph",
      "id": "<id-or-derived>",
      "score": <float>,
      "created_at": "<iso8601-or-null>",
      "sensitivity": "public|restricted-redacted",
      "text": "<sanitized summary>"
    }
  ],
  "context_pack": {
    "project_snapshot": ["..."],
    "active_decisions": ["..."],
    "open_risks": ["..."],
    "next_actions": ["..."],
    "recent_events": ["..."]
  },
  "warnings": ["..."]
}
```

## Preferred Local Runner
- `python3 .kilo/scripts/memory_query.py "<query>"`

## Safety
- Never output raw secrets or private keys.
- Minimize PII and operationally unnecessary detail.
