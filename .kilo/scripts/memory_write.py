#!/usr/bin/env python3
"""Lightweight memory write utility (stdlib only)."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


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
DECISIONS_PATH = MEM_DIR / "decisions.jsonl"
VECTOR_PATH = MEM_DIR / "vector_store.json"
GRAPH_PATH = MEM_DIR / "graph.cypher"

SECRET_PATTERNS = [
    re.compile(r"\b(?:sk|pk|api|tok|key)[-_]?[A-Za-z0-9]{12,}\b", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9+/]{24,}={0,2}\b"),
    re.compile(r"\b(?:bearer|password|secret)\s+[A-Za-z0-9._-]{6,}\b", re.IGNORECASE),
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sanitize_text(text: str) -> str:
    out = " ".join(text.split())
    for pattern in SECRET_PATTERNS:
        out = pattern.sub("<REDACTED>", out)
    return out.strip()


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "general"


def ensure_files() -> None:
    MEM_DIR.mkdir(parents=True, exist_ok=True)
    if not DECISIONS_PATH.exists():
        DECISIONS_PATH.write_text("", encoding="utf-8")
    if not VECTOR_PATH.exists():
        VECTOR_PATH.write_text("[]\n", encoding="utf-8")
    if not GRAPH_PATH.exists():
        GRAPH_PATH.write_text("// Append Log\n", encoding="utf-8")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
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


def next_id(prefix: str, existing: List[str]) -> str:
    max_n = 0
    for item in existing:
        m = re.match(rf"^{re.escape(prefix)}-(\d+)$", item)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"{prefix}-{max_n + 1:03d}"


def load_vectors() -> List[Dict[str, Any]]:
    try:
        data = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    except (OSError, json.JSONDecodeError):
        return []
    return []


def write_vectors(vectors: List[Dict[str, Any]]) -> None:
    VECTOR_PATH.write_text(json.dumps(vectors, indent=2) + "\n", encoding="utf-8")


def append_graph(record_id: str, topic: str, record_type: str, status: str) -> None:
    node_label = "Decision" if record_type == "decision" else "Task"
    topic_slug = slugify(topic)
    snippet = (
        f"\n// {utc_now_iso()} memory_write append\n"
        f"MERGE (m:{node_label} {{id:'{record_id}', topic:'{topic_slug}', status:'{status}'}})\n"
        "MERGE (p:Project {id:'stepsales'})\n"
        "MERGE (p)-[:NEXT_ACTION]->(m)\n"
    )

    text = GRAPH_PATH.read_text(encoding="utf-8") if GRAPH_PATH.exists() else ""
    if "// Append Log" not in text:
        text = text.rstrip() + "\n\n// Append Log\n"
    text += snippet
    GRAPH_PATH.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write memory record")
    parser.add_argument("--type", required=True, choices=["decision", "event"])
    parser.add_argument("--topic", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--status", required=True, choices=["active", "open", "superseded", "closed"])
    parser.add_argument("--sensitivity", required=True, choices=["public", "restricted-redacted"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_files()

    now = utc_now_iso()
    sanitized_summary = sanitize_text(args.summary)

    existing_records = read_jsonl(DECISIONS_PATH)
    record_ids = [str(x.get("id", "")) for x in existing_records]
    mem_id = next_id("mem", record_ids)

    record = {
        "timestamp": now,
        "type": args.type,
        "id": mem_id,
        "topic": slugify(args.topic),
        "summary": sanitized_summary,
        "status": args.status,
        "evidence": "memory_write.py append",
        "sensitivity": args.sensitivity,
    }

    with DECISIONS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")

    vectors = load_vectors()
    vec_ids = [str(x.get("id", "")) for x in vectors]
    vec_id = next_id("vec", vec_ids)
    ttl_days = 365 if args.type == "decision" else 90
    vectors.append(
        {
            "id": vec_id,
            "text": sanitized_summary,
            "tags": [slugify(args.topic), args.type, args.status],
            "source": f"decision:{mem_id}",
            "created_at": now,
            "ttl_days": ttl_days,
            "sensitivity": args.sensitivity,
        }
    )
    write_vectors(vectors)

    append_graph(mem_id, args.topic, args.type, args.status)

    payload = {
        "status": "MEMORY_WRITE_OK",
        "record_id": mem_id,
        "vector_id": vec_id,
        "topic": slugify(args.topic),
        "type": args.type,
        "files": {
            "decisions_jsonl": True,
            "vector_store_json": True,
            "graph_cypher": True,
        },
        "warnings": [],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
