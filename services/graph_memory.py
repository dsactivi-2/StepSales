"""
Neo4j Graph Memory Service
Stores and retrieves customer memory as a knowledge graph.
Entities (Company, Lead, Call, Contact) as nodes, relationships as edges.
Supports graph traversal for customer context and relationship discovery.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver

from config.settings import AppConfig

logger = logging.getLogger("stepsales.graph_memory")

NEO4J_URI = "bolt://neo4j-stepsales:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "stepsales_memory_2026"
NEO4J_DB = "neo4j"


class GraphMemoryService:
    """Neo4j-backed graph memory for customer relationships and context."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._driver: Optional[AsyncDriver] = None
        self._connected = False

    async def initialize(self):
        """Connect to Neo4j and verify schema."""
        try:
            self._driver = AsyncGraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD),
                database=NEO4J_DB,
            )
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 AS connected")
                record = await result.single()
                if record and record["connected"] == 1:
                    self._connected = True
                    logger.info(f"Graph Memory connected to Neo4j at {NEO4J_URI}")

                    node_count = await session.run("MATCH (n) RETURN count(n) AS cnt")
                    nc = await node_count.single()
                    logger.info(f"Existing nodes: {nc['cnt']}")
        except Exception as e:
            logger.error(f"Graph Memory connection failed: {e}")
            raise

    async def close(self):
        if self._driver:
            await self._driver.close()
            self._connected = False
            logger.info("Graph Memory disconnected")

    # ─── Entity Creation ─────────────────────────────────────────────────────

    async def create_company(self, company_id: str, name: str, industry: str = "") -> dict:
        """Create or merge a Company node."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MERGE (c:Company) WHERE c.id = $id
                ON CREATE SET c.name = $name, c.industry = $industry, c.created_at = datetime()
                ON MATCH SET c.name = $name, c.industry = $industry, c.updated_at = datetime()
                RETURN c.id AS id, c.name AS name
                """,
                id=company_id, name=name, industry=industry,
            )
            record = await result.single()
            logger.info(f"Company created/merged: {name}")
            return {"id": record["id"], "name": record["name"]} if record else {}

    async def create_lead(self, lead_id: str, company_id: str, status: str = "new",
                          source: str = "outbound", contact_name: str = "",
                          phone: str = "", email: str = "") -> dict:
        """Create a Lead node linked to Company."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Company) WHERE c.id = $company_id
                MERGE (l:Lead) WHERE l.id = $lead_id
                SET l.status = $status, l.source = $source,
                    l.contact_name = $contact_name, l.phone = $phone,
                    l.email = $email, l.created_at = datetime()
                MERGE (c)-[:HAS_LEAD]->(l)
                RETURN l.id AS id, l.status AS status
                """,
                lead_id=lead_id, company_id=company_id,
                status=status, source=source,
                contact_name=contact_name, phone=phone, email=email,
            )
            record = await result.single()
            logger.info(f"Lead created: {lead_id} -> {company_id}")
            return {"id": record["id"], "status": record["status"]} if record else {}

    async def record_call(self, call_id: str, lead_id: str, stage: str,
                          duration: int = 0, outcome: str = "",
                          transcript: list = None, objections: list = None) -> dict:
        """Record a Call node linked to Lead."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (l:Lead) WHERE l.id = $lead_id
                CREATE (call:Call {
                    id: $call_id,
                    stage: $stage,
                    duration: $duration,
                    outcome: $outcome,
                    transcript: $transcript,
                    objections: $objections,
                    created_at: datetime()
                })
                MERGE (l)-[:HAS_CALL]->(call)
                RETURN call.id AS id, call.stage AS stage
                """,
                call_id=call_id, lead_id=lead_id, stage=stage,
                duration=duration, outcome=outcome,
                transcript=transcript or [], objections=objections or [],
            )
            record = await result.single()
            logger.info(f"Call recorded: {call_id} -> {lead_id} (stage={stage})")
            return {"id": record["id"], "stage": record["stage"]} if record else {}

    async def add_memory_fact(self, customer_id: str, fact: str,
                              fact_type: str = "note", confidence: float = 1.0) -> dict:
        """Add a MemoryFact node linked to a Lead/Company."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (entity) WHERE entity.id = $customer_id
                CREATE (m:MemoryFact {
                    id: randomUUID(),
                    content: $fact,
                    type: $fact_type,
                    confidence: $confidence,
                    created_at: datetime()
                })
                MERGE (entity)-[:HAS_MEMORY]->(m)
                RETURN m.id AS id, m.content AS content
                """,
                customer_id=customer_id, fact=fact,
                fact_type=fact_type, confidence=confidence,
            )
            record = await result.single()
            return {"id": record["id"], "content": record["content"]} if record else {}

    # ─── Graph Queries ───────────────────────────────────────────────────────

    async def get_customer_graph(self, customer_id: str, max_hops: int = 2) -> dict:
        """Get the full relationship graph for a customer."""
        async with self._driver.session() as session:
            # Neo4j doesn't allow parameters for variable-length relationships
            # so we use a safe string interpolation with validation
            if not isinstance(max_hops, int) or max_hops < 1 or max_hops > 5:
                max_hops = 2
            query = f"""
                MATCH (entity) WHERE entity.id = $customer_id
                MATCH path = (entity)-[*1..{max_hops}]-(related)
                RETURN path
                LIMIT 200
            """
            result = await session.run(query, customer_id=customer_id)
            nodes = {}
            relationships = []
            async for record in result:
                path = record["path"]
                for node in path.nodes:
                    nid = str(node.id)
                    if nid not in nodes:
                        nodes[nid] = {
                            "id": node.get("id", ""),
                            "labels": list(node.labels),
                            "properties": {k: v for k, v in dict(node).items()
                                          if k != "id" and isinstance(v, (str, int, float, bool))},
                        }
                for rel in path.relationships:
                    relationships.append({
                        "source": str(rel.start_node.id),
                        "target": str(rel.end_node.id),
                        "type": rel.type,
                    })

            return {
                "customer_id": customer_id,
                "nodes": list(nodes.values()),
                "relationships": relationships,
                "node_count": len(nodes),
                "relationship_count": len(relationships),
            }

    async def get_customer_memory(self, customer_id: str) -> List[dict]:
        """Get all memory facts for a customer."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (entity)-[:HAS_MEMORY]->(m:MemoryFact)
                WHERE entity.id = $customer_id
                RETURN m.id AS id, m.content AS content, m.type AS type,
                       m.confidence AS confidence, m.created_at AS created_at
                ORDER BY m.created_at DESC
                LIMIT 20
                """,
                customer_id=customer_id,
            )
            facts = []
            async for record in result:
                facts.append({
                    "id": record["id"],
                    "content": record["content"],
                    "type": record["type"],
                    "confidence": record["confidence"],
                    "created_at": str(record["created_at"]),
                })
            return facts

    async def get_related_entities(self, entity_id: str, relationship_type: str = "") -> List[dict]:
        """Find entities related to a given entity."""
        rel_filter = f":{relationship_type}" if relationship_type else ""
        async with self._driver.session() as session:
            result = await session.run(
                f"""
                MATCH (e)-[r{rel_filter}]->(related)
                WHERE e.id = $entity_id
                RETURN related, type(r) AS rel_type
                """,
                entity_id=entity_id,
            )
            entities = []
            async for record in result:
                node = record["related"]
                entities.append({
                    "id": node.get("id", ""),
                    "labels": list(node.labels),
                    "relationship": record["rel_type"],
                    "properties": {k: v for k, v in dict(node).items()
                                   if isinstance(v, (str, int, float, bool))},
                })
            return entities

    async def get_call_history(self, lead_id: str) -> List[dict]:
        """Get all calls for a lead."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (l:Lead)-[:HAS_CALL]->(c:Call)
                WHERE l.id = $lead_id
                RETURN c.id AS id, c.stage AS stage, c.duration AS duration,
                       c.outcome AS outcome, c.created_at AS created_at
                ORDER BY c.created_at DESC
                """,
                lead_id=lead_id,
            )
            calls = []
            async for record in result:
                calls.append({
                    "id": record["id"],
                    "stage": record["stage"],
                    "duration": record["duration"],
                    "outcome": record["outcome"],
                    "created_at": str(record["created_at"]),
                })
            return calls

    async def get_stats(self) -> dict:
        """Get graph database statistics."""
        async with self._driver.session() as session:
            node_result = await session.run("MATCH (n) RETURN count(n) AS cnt")
            nc = await node_result.single()
            rel_result = await session.run("MATCH ()-[r]->() RETURN count(r) AS cnt")
            rc = await rel_result.single()

            label_result = await session.run(
                "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC"
            )
            labels = {}
            async for record in label_result:
                labels[record["label"]] = record["cnt"]

            return {
                "total_nodes": nc["cnt"],
                "total_relationships": rc["cnt"],
                "node_types": labels,
                "connected": self._connected,
            }

    async def seed_graph_workflows(self):
        """Seed the graph with workflow definitions from graph.cypher."""
        async with self._driver.session() as session:
            existing = await session.run("MATCH (w:Workflow) RETURN count(w) AS cnt")
            cnt = await existing.single()
            if cnt and cnt["cnt"] > 0:
                logger.info(f"Workflows already seeded ({cnt['cnt']} workflows)")
                return

            await session.run("""
                CREATE (w:Workflow {id: 'outbound_call', name: 'Outbound Call', created_at: datetime()})
                CREATE (w)-[:HAS_STEP]->(s1:Step {id: 'oc_1', name: 'Lead Qualification', order: 1})
                CREATE (w)-[:HAS_STEP]->(s2:Step {id: 'oc_2', name: 'Call Preparation', order: 2})
                CREATE (w)-[:HAS_STEP]->(s3:Step {id: 'oc_3', name: 'Outbound Call', order: 3})
                CREATE (w)-[:HAS_STEP]->(s4:Step {id: 'oc_4', name: 'Follow-up', order: 4})
            """)

            await session.run("""
                CREATE (w:Workflow {id: 'invoice', name: 'Invoice Processing', created_at: datetime()})
                CREATE (w)-[:HAS_STEP]->(s1:Step {id: 'inv_1', name: 'Draft Invoice', order: 1})
                CREATE (w)-[:HAS_STEP]->(s2:Step {id: 'inv_2', name: 'Finalize Invoice', order: 2})
                CREATE (w)-[:HAS_STEP]->(s3:Step {id: 'inv_3', name: 'Send Invoice', order: 3})
                CREATE (w)-[:HAS_STEP]->(s4:Step {id: 'inv_4', name: 'Track Payment', order: 4})
            """)

            await session.run("""
                CREATE (w:Workflow {id: 'fulfillment', name: 'Job Ad Fulfillment', created_at: datetime()})
                CREATE (w)-[:HAS_STEP]->(s1:Step {id: 'ful_1', name: 'Job Ad Intake', order: 1})
                CREATE (w)-[:HAS_STEP]->(s2:Step {id: 'ful_2', name: 'Validate Ad', order: 2})
                CREATE (w)-[:HAS_STEP]->(s3:Step {id: 'ful_3', name: 'Submit to StepStone', order: 3})
                CREATE (w)-[:HAS_STEP]->(s4:Step {id: 'ful_4', name: 'Submit to Indeed', order: 4})
                CREATE (w)-[:HAS_STEP]->(s5:Step {id: 'ful_5', name: 'Confirm Publication', order: 5})
            """)

        logger.info("All graph workflows seeded (3 workflows, 13 steps)")
