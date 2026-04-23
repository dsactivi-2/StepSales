# RUNBOOK

## Prerequisites

- Python 3.11+
- Docker Engine with Compose plugin (`docker compose`)
- Project virtual environment at `.venv`
- Required API credentials available before runtime (OpenAI, optional Telnyx)

## Secure Environment Setup

1. Keep secrets in `environment/.env` only.
2. Ensure `environment/.env` is not committed (already ignored by git).
3. Minimal required keys:

```bash
OPENAI_API_KEY=<set-your-key>
HOST=0.0.0.0
PORT=8010
LOG_LEVEL=INFO
```

4. Load env for local test/runtime commands without printing values:

```bash
set -a && source environment/.env && set +a
```

## Start / Stop

### Local Python runtime

```bash
set -a && source environment/.env && set +a && .venv/bin/python web_server.py
```

### Docker Compose runtime

```bash
docker compose up -d --build
```

### Stop containers

```bash
docker compose down
```

## Health / Test Verification

### Test suite

```bash
set -a && source environment/.env && set +a && .venv/bin/pytest -q
```

### Health endpoint

```bash
curl -fsS http://localhost:8010/health
```

Expected HTTP response contains `"status":"healthy"`.

## Incident Checks

### 1) Container startup or runtime failure

```bash
docker compose ps
docker compose logs --tail=200 stepsales-agent
```

### 2) Missing API key

Symptom: startup error indicating missing `OPENAI_API_KEY`.

Check:

```bash
ls environment/.env
```

Action: ensure `OPENAI_API_KEY` is set in `environment/.env`, restart service.

### 3) Port conflict on 8010

```bash
lsof -i :8010
```

Action: stop conflicting process/container, then restart Stepsales.

## Key Rotation (OpenAI / Telnyx)

1. Rotate key at provider portal.
2. Update `environment/.env` with new key value.
3. Restart runtime (`docker compose down && docker compose up -d --build` or local process restart).
4. Re-run health check and smoke tests.
5. Invalidate/revoke old key at provider side.

## Open Limitations and Next Actions

- Web voice flow currently uses heuristic response path; not a full OpenAI Realtime end-to-end loop.
- `search_jobs` currently returns mocked data; Stepstone parser integration remains incomplete.
- CRM/session/transcript state is in-memory and non-persistent across restarts.

Recommended next actions:
1. Implement full realtime call loop and validate with integration tests.
2. Replace mocked job search with production parser/API integration.
3. Add persistent storage for leads, sessions, and transcript history.
