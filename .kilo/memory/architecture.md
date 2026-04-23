# Memory Architecture

## Memory Planes
- **Ledger (`memory-ledger.md`)**: human-readable operational snapshot and continuity notes.
- **Vector Index (`vector_store.json`)**: lightweight semantic-ish memory records for quick similarity retrieval.
- **Graph Store (`graph.cypher`)**: append-only Cypher facts for entities, dependencies, risks, and next actions.
- **Decision Log (`decisions.jsonl`)**: canonical event/decision timeline with structured metadata.

## Retrieval Policy
Hybrid retrieval returns a deterministic context pack:
1. **Lexical pass** over ledger + decisions + vector text/tag fields.
2. **Semantic pass** over vector records (mock semantic score via term normalization and tag affinity).
3. **Graph expansion** from matched nodes (`graph_hops` bounded) to pull related decisions, risks, tasks, providers, and gaps.
4. **Rerank** by weighted score = lexical + semantic + freshness, filtered by sensitivity policy.

## Write Policy
Write pipeline for every memory append/update:
1. **Sanitize**: redact suspected secrets/tokens, minimize PII, normalize text.
2. **Classify**: identify memory type (`decision` or `event`), topic, status, sensitivity, TTL class.
3. **Persist (dual/triple-write)**:
   - append JSONL record to `decisions.jsonl`
   - append vector record to `vector_store.json`
   - append Cypher MERGE snippet to `graph.cypher` append log
   - optionally refresh summary fields in ledger when significant

## Safety Model
- Never store raw secrets (API keys, bearer tokens, passwords, private keys).
- PII minimization: keep operational summaries only; no direct customer identifiers.
- Sensitivity classes:
  - `public`: broadly shareable operational context.
  - `restricted-redacted`: sensitive context after redaction only.
- TTL classes (enforced by record `ttl_days`):
  - short-lived signals (7-14)
  - working memory (30-90)
  - durable decisions (180-365)
- Retrieval must apply `sensitivity_filter` before output emission.
