# Memory Ledger

## Project Snapshot
- Service: StepSales telesales assistant with web interface and Stepstone integration.
- Runtime: Local dev server currently expected on port `8010`.
- Environment: Primary env file path is `environment/.env` (do not store values here).
- Current state: Core flows run, but operational/documentation hardening is still in progress.

## Active Decisions
- Standardize local HTTP port to `8010` unless explicitly overridden for a specific test.
- Use `environment/.env` as the canonical env file location for runtime configuration.
- Track architecture and process updates in this ledger + `decisions.jsonl` to keep sessions consistent.

## Open Risks
- Env loading assumptions may drift if scripts still reference root `.env`.
- No enforced memory sync routine yet; context can become stale between sessions.
- Known gaps remain in reliability docs, runbook detail, and validation coverage.

## Next Actions
- Add/verify a single env-loading path in app startup and docs (`environment/.env`).
- Run memory bootstrap at session start and memory sync at session end.
- Close highest-impact known gaps and log each decision/event in `decisions.jsonl`.

## Last Updated
- 2026-04-23T08:06:14Z
- Updated by: Kilo memory MVP bootstrap

## Safety Rules
- Never store raw secrets, API keys, tokens, passwords, or private customer data in memory files.
- Redact sensitive values using placeholders (example: `<REDACTED_API_KEY>`).
- Record only minimal operational context needed for continuity.
