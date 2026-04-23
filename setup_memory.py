#!/usr/bin/env python3
"""
Memory Infrastructure Setup
Creates Qdrant collections and Neo4j graph schema for Stepsales memory system.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import httpx
from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import AppConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("stepsales.setup_memory")

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant-stepsales:6333")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j-stepsales:7687")
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "stepsales_memory_2026"


async def setup_qdrant():
    """Create Qdrant collections for vector memory."""
    logger.info(f"Setting up Qdrant at {QDRANT_URL}")

    client = httpx.AsyncClient(base_url=QDRANT_URL, timeout=30.0)

    collections = [
        {
            "name": "step2job_memory",
            "vectors": {
                "size": 1536,
                "distance": "Cosine",
            },
            "optimizers_config": {
                "memmap_threshold": 20000,
            },
        },
        {
            "name": "step2job_transcripts",
            "vectors": {
                "size": 1536,
                "distance": "Cosine",
            },
            "on_disk_payload": True,
        },
        {
            "name": "step2job_leads",
            "vectors": {
                "size": 1536,
                "distance": "Cosine",
            },
        },
    ]

    for col in collections:
        name = col["name"]
        logger.info(f"Creating collection: {name}")

        resp = await client.put(f"/collections/{name}", json=col)

        if resp.status_code in [200, 409]:
            if resp.status_code == 409:
                logger.info(f"  Collection {name} already exists")
            else:
                logger.info(f"  Collection {name} created")
        else:
            logger.error(f"  Failed to create {name}: {resp.status_code} {resp.text}")

    await client.aclose()
    logger.info("Qdrant setup complete")


def setup_neo4j():
    """Create Neo4j graph schema and constraints."""
    logger.info(f"Setting up Neo4j at {NEO4J_URI}")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        constraints = [
            "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT lead_id IF NOT EXISTS FOR (l:Lead) REQUIRE l.id IS UNIQUE",
            "CREATE CONSTRAINT call_id IF NOT EXISTS FOR (c:Call) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT contact_id IF NOT EXISTS FOR (c:Contact) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT memory_fact_id IF NOT EXISTS FOR (m:MemoryFact) REQUIRE m.id IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                session.run(constraint)
                logger.info(f"  Constraint created: {constraint.split('FOR')[0].replace('CREATE CONSTRAINT ', '')}")
            except Exception as e:
                logger.warning(f"  Constraint skipped: {e}")

        indexes = [
            "CREATE INDEX lead_status IF NOT EXISTS FOR (l:Lead) ON (l.status)",
            "CREATE INDEX call_date IF NOT EXISTS FOR (c:Call) ON (c.created_at)",
            "CREATE INDEX memory_type IF NOT EXISTS FOR (m:MemoryFact) ON (m.fact_type)",
            "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",
        ]

        for index in indexes:
            try:
                session.run(index)
                logger.info(f"  Index created: {index.split('FOR')[0].replace('CREATE INDEX ', '')}")
            except Exception as e:
                logger.warning(f"  Index skipped: {e}")

        logger.info("Neo4j schema setup complete")
        driver.close()


async def main():
    logger.info("=" * 60)
    logger.info("Stepsales Memory Infrastructure Setup")
    logger.info("=" * 60)

    await setup_qdrant()
    setup_neo4j()

    logger.info("=" * 60)
    logger.info("Memory infrastructure ready")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
