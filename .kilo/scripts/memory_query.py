#!/usr/bin/env python3
"""Lightweight memory query utility (stdlib only)."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def has_memory_files(kilo_home: Path) -> bool:
    mem_dir = kilo_home / "memory"
    return (mem_dir / "decisions.jsonl").exists() or (mem_dir / "vector_store.json").exists()


def resolve_kilo_home() -> Path:
    env_home = os.getenv("KILO_MEMORY_HOME", "").strip()
    if env_home:
        candidate = Path(env_home).expanduser().resolve()
        if candidate.exists() and has_memory_files(candidate):
            return candidate

    cwd = Path.cwd().resolve()
    for base in [cwd, *cwd.parents]:
        candidate = base / ".kilo"
        if candidate.exists() and has_memory_files(candidate):
            return candidate

    root_home = Path("/.kilo")
    if root_home.exists() and has_memory_files(root_home):
        return root_home

    return Path("/root/.config/kilo/.kilo")


KILO_HOME = resolve_kilo_home()
MEM_DIR = KILO_HOME / "memory"
LEDGER_PATH = MEM_DIR / "memory-ledger.md"
DECISIONS_PATH = MEM_DIR / "decisions.jsonl"
VECTOR_PATH = MEM_DIR / "vector_store.json"

TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+")
SECRET_PATTERNS = [
    re.compile(r"\b(?:sk|pk|api|tok|key)[-_]?[A-Za-z0-9]{12,}\b", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9+/]{24,}={0,2}\b"),
    re.compile(r"\b(?:bearer|password|secret)\s+[A-Za-z0-9._-]{6,}\b", re.IGNORECASE),
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def redact_text(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("<REDACTED>", redacted)
    return redacted


def read_ledger_lines() -> List[str]:
    if not LEDGER_PATH.exists():
        return []
    try:
        return [line.strip() for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return []


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not path.exists():
        return out
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    out.append(item)
            except json.JSONDecodeError:
                continue
    except OSError:
        return out
    return out


def read_vector() -> List[Dict[str, Any]]:
    if not VECTOR_PATH.exists():
        return []
    try:
        data = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    except (OSError, json.JSONDecodeError):
        return []
    return []


def recency_boost(created_at: str | None) -> float:
    if not created_at:
        return 0.0
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_days = max((now - dt).total_seconds() / 86400.0, 0.0)
        return 1.0 / (1.0 + age_days)
    except ValueError:
        return 0.0


def overlap_score(query_tokens: List[str], text: str, extra_tokens: List[str] | None = None) -> float:
    if not query_tokens:
        return 0.0
    tokens = set(tokenize(text))
    if extra_tokens:
        tokens.update(t.lower() for t in extra_tokens)
    hits = sum(1 for t in query_tokens if t in tokens)
    return hits / float(len(set(query_tokens)))


def build_items(query: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    items: List[Dict[str, Any]] = []
    q_tokens = tokenize(query)

    for idx, line in enumerate(read_ledger_lines(), start=1):
        score = overlap_score(q_tokens, line)
        if score <= 0:
            continue
        items.append(
            {
                "source": "ledger",
                "id": f"ledger-{idx}",
                "text": line,
                "created_at": None,
                "sensitivity": "public",
                "score": score,
            }
        )

    for entry in read_jsonl(DECISIONS_PATH):
        text = str(entry.get("summary", ""))
        created_at = entry.get("timestamp")
        score = overlap_score(q_tokens, text)
        if score <= 0:
            continue
        items.append(
            {
                "source": "decision",
                "id": str(entry.get("id", "decision-unknown")),
                "text": text,
                "created_at": created_at,
                "sensitivity": str(entry.get("sensitivity", "public")),
                "score": score + 0.2 * recency_boost(created_at),
            }
        )

    vectors = read_vector()
    if not vectors and VECTOR_PATH.exists():
        warnings.append("vector_store_unreadable_or_empty")
    for entry in vectors:
        text = str(entry.get("text", ""))
        tags = entry.get("tags") if isinstance(entry.get("tags"), list) else []
        created_at = entry.get("created_at")
        lexical = overlap_score(q_tokens, text, [str(t) for t in tags])
        if lexical <= 0:
            continue
        items.append(
            {
                "source": "vector",
                "id": str(entry.get("id", "vector-unknown")),
                "text": text,
                "created_at": created_at,
                "sensitivity": str(entry.get("sensitivity", "public")),
                "score": lexical + 0.3 * recency_boost(created_at),
            }
        )

    return items, warnings


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "query argument required"}, indent=2))
        return 1

    query = " ".join(sys.argv[1:]).strip()
    items, warnings = build_items(query)
    items.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    top = items[:8]

    results = []
    for rank, item in enumerate(top, start=1):
        results.append(
            {
                "rank": rank,
                "source": item["source"],
                "id": item["id"],
                "score": round(float(item["score"]), 4),
                "created_at": item.get("created_at"),
                "sensitivity": item.get("sensitivity", "public"),
                "text": redact_text(str(item.get("text", ""))),
            }
        )

    payload = {
        "query": query,
        "kilo_home": str(KILO_HOME),
        "generated_at": utc_now_iso(),
        "result_count": len(results),
        "results": results,
        "warnings": warnings,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
