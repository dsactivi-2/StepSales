"""
Knowledgebase Service - RAG Pipeline mit Qdrant
Stores and retrieves sales playbooks, product info, and objection handling guides
using semantic search over Qdrant vector database.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from openai import AsyncOpenAI

from config.settings import AppConfig

logger = logging.getLogger("stepsales.knowledgebase")

COLLECTION = "step2job_memory"

DEFAULT_PLAYBOOKS = [
    {
        "id": "playbook_multiposting",
        "title": "Multiposting StepStone + Indeed",
        "category": "product",
        "content": """Multiposting kombiniert StepStone und Indeed in einem Paket.
Vorteile: 3x mehr Sichtbarkeit als Einzelanzeige, planbarer Bewerbereingang, ein Ansprechpartner.
Pakete: Basic (2 Anzeigen, 4 Wochen) ab 499 EUR, Premium (4 Anzeigen, 8 Wochen) ab 799 EUR, Enterprise (8 Anzeigen, 12 Wochen) ab 1.299 EUR.
Zielgruppe: KMU in Deutschland mit 10-500 Mitarbeitenden.""",
        "tags": ["multiposting", "stepstone", "indeed", "preise", "pakete"],
    },
    {
        "id": "objection_price",
        "title": "Einwandbehandlung: Preis",
        "category": "objection_handling",
        "content": """Wenn Kunde sagt "zu teuer":
1. Empathie: "Ich verstehe, Budget ist wichtig."
2. Kontext: "Was kostet eine vakante Stelle pro Monat? Ca. 5.000-8.000 EUR durch Leerlauf."
3. ROI: "Unsere Pakete amortisieren sich ab der ersten Einstellung."
4. Vergleich: "Einzelanzeige StepStone: 699 EUR. Bei uns: StepStone + Indeed ab 499 EUR."
5. Closing: "Welches Paket passt zu Ihrem aktuellen Bedarf?"
Wichtig: Nie sofort Rabatt anbieten. Erst Wert vermitteln.""",
        "tags": ["einwand", "preis", "rabatt", "roi", "closing"],
    },
    {
        "id": "objection_time",
        "title": "Einwandbehandlung: Keine Zeit",
        "category": "objection_handling",
        "content": """Wenn Kunde sagt "keine Zeit" oder "rufen Sie später an":
1. Respekt: "Ich will Sie nicht aufhalten."
2. Hook: "Nur eine kurze Frage: Wie viele offene Stellen haben Sie aktuell?"
3. Termin: "Wann passt es besser? 10 Minuten nächste Woche?"
4. Email-Alternative: "Soll ich Ihnen die Infos per Email schicken?"
Beste Zeiten: Dienstag-Donnerstag 9-11 Uhr oder 14-16 Uhr.""",
        "tags": ["einwand", "zeit", "termin", "callback"],
    },
    {
        "id": "objection_no_interest",
        "title": "Einwandbehandlung: Kein Interesse",
        "category": "objection_handling",
        "content": """Wenn Kunde sagt "kein Interesse" oder "kein Bedarf":
1. Akzeptieren: "Verstehe, danke fur Ihre Ehrlichkeit."
2. Door-Opener: "Darf ich fragen, wie Sie aktuell Stellen ausschreiben?"
3. Value: "Viele unserer Kunden hatten anfangs keinen Bedarf, dann kam die Schlusselfigur."
4. Permission: "Darf ich Sie in 3 Monaten nochmal kontaktieren?"
5. Never push: Wenn klar "Nein", dann professionell verabschieden.""",
        "tags": ["einwand", "kein interesse", "bedarf", "verabschiedung"],
    },
    {
        "id": "qualification_framework",
        "title": "Lead Qualifizierungs-Framework",
        "category": "sales_process",
        "content": """BANT Framework fur Stepsales:
Budget: "Haben Sie ein Budget fur Recruiting-Maenahmen eingeplant?" (Ja/Nein/Weis nicht)
Authority: "Sind Sie der Entscheider oder muss noch jemand einbezogen werden?"
Need: "Wie viele Stellen sind aktuell offen? Seit wann?" (1-3=mittel, 4+=hoch)
Timeline: "Wann sollen die Stellen besetzt sein?" (sofort=hoch, 3 Monate=mittel, 6+=niedrig)

Qualification Score: Budget(25) + Authority(25) + Need(25) + Timeline(25) = 0-100
Score > 75: Hot Lead -> Direct Close
Score 50-75: Warm Lead -> Follow-up in 48h
Score < 50: Cold Lead -> Email Nurture""",
        "tags": ["qualifizierung", "bant", "score", "lead"],
    },
    {
        "id": "closing_techniques",
        "title": "Closing-Techniken",
        "category": "sales_process",
        "content": """Top 5 Closing-Techniken fur Stepsales:
1. Alternative Close: "Premium oder Enterprise - was passt besser?"
2. Urgency Close: "StepStone hat nachste Woche PreisAnpassung. Jetzt noch altes Pricing sichern."
3. Trial Close: "Wenn wir das Budget-Frage klaren, konnten wir diese Woche starten?"
4. Summary Close: "Zusammengefasst: Sie haben 4 offene Stellen, brauchen Bewerber in 2 Wochen, Budget ist da. Soll ich das Premium-Paket vorbereiten?"
5. Assumptive Close: "Ich schicke Ihnen die Auftragsbestatigung per Email. Welche Adresse?"

Wichtig: Immer konkrete nachste Schritte definieren. Nie "melde mich" sagen.""",
        "tags": ["closing", "techniken", "abschluss", "verkauf"],
    },
    {
        "id": "product_comparison",
        "title": "Produktvergleich: Einzelanzeige vs. Multiposting",
        "category": "product",
        "content": """Einzelanzeige StepStone: 699 EUR/Anzeige, 4 Wochen, nur StepStone, kein Indeed.
Einzelanzeige Indeed: Kosten pro Klick (ca. 2-5 EUR), unkontrollierbar, Budget schnell aufgebraucht.
Stepsales Multiposting Basic: 499 EUR, 2 Anzeigen, StepStone + Indeed, feste Kosten, 4 Wochen.
Stepsales Multiposting Premium: 799 EUR, 4 Anzeigen, StepStone + Indeed, Priority-Placement, 8 Wochen.
Stepsales Multiposting Enterprise: 1.299 EUR, 8 Anzeigen, StepStone + Indeed, Dedicated Account Manager, 12 Wochen.

Ersparnis Premium vs. Einzelanzeigen: 2x StepStone = 1.398 EUR -> Premium = 799 EUR (43% sparen)""",
        "tags": ["vergleich", "preise", "einzelanzeige", "multiposting", "ersparnis"],
    },
    {
        "id": "company_info",
        "title": "Step2Job Unternehmensinfos",
        "category": "company",
        "content": """Step2Job GmbH - Berlin
Gegrundet: 2023
Sitz: Berlin, Deutschland
Geschaftsfuhrer: [Name]
Mitarbeitende: 25+
Partner: StepStone, Indeed (zertifiziert)
Branche: Recruiting-Technologie, Jobvermittlung
USP: Operativer Vertriebspartner fur StepStone und Indeed - keine Agentur, sondern direkter Partner.
Kunden: 500+ KMU in Deutschland
Erfolgsquote: 89% der Kunden buchen innerhalb von 6 Monaten erneut.""",
        "tags": ["unternehmen", "step2job", "infos", "partner"],
    },
]


class KnowledgeDocument:
    """Represents a single knowledge base document."""

    def __init__(self, doc_id: str, title: str, content: str, category: str = "general", tags: list = None):
        self.id = doc_id
        self.title = title
        self.content = content
        self.category = category
        self.tags = tags or []
        self.created_at = datetime.utcnow().isoformat()
        self._embedding: Optional[List[float]] = None

    def to_payload(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "tags": self.tags,
            "created_at": self.created_at,
        }


class KnowledgebaseService:
    """RAG knowledgebase with Qdrant vector storage and OpenAI embeddings."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._client = httpx.AsyncClient(timeout=30.0)
        self._openai = AsyncOpenAI(api_key=self.config.openai.api_key)
        self._qdrant_url = "http://qdrant-stepsales:6333"
        self._collection = COLLECTION
        self._initialized = False
        self._local_cache: Dict[str, KnowledgeDocument] = {}

    async def initialize(self):
        """Verify Qdrant connection and seed default playbooks."""
        try:
            resp = await self._client.get(f"{self._qdrant_url}/collections/{self._collection}")
            if resp.status_code == 200:
                self._initialized = True
                logger.info(f"Knowledgebase connected to Qdrant collection: {self._collection}")

                existing = await self._get_all_ids()
                for playbook in DEFAULT_PLAYBOOKS:
                    if playbook["id"] not in existing:
                        doc = KnowledgeDocument(
                            doc_id=playbook["id"],
                            title=playbook["title"],
                            content=playbook["content"],
                            category=playbook["category"],
                            tags=playbook["tags"],
                        )
                        await self.add_document(doc)
                        logger.info(f"  Seeded playbook: {playbook['title']}")

                logger.info(f"Knowledgebase initialized with {len(self._local_cache)} documents")
        except Exception as e:
            logger.warning(f"Knowledgebase init warning (Qdrant): {e}")
            for playbook in DEFAULT_PLAYBOOKS:
                doc = KnowledgeDocument(
                    doc_id=playbook["id"],
                    title=playbook["title"],
                    content=playbook["content"],
                    category=playbook["category"],
                    tags=playbook["tags"],
                )
                self._local_cache[doc.id] = doc
            self._initialized = True
            logger.info(f"Knowledgebase using local cache with {len(self._local_cache)} documents")

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding for text."""
        response = await self._openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text[:8191],
        )
        return response.data[0].embedding

    async def _get_all_ids(self) -> set:
        """Get all existing document IDs from Qdrant."""
        resp = await self._client.get(f"{self._qdrant_url}/collections/{self._collection}/points/scroll", params={
            "limit": 1000,
            "with_payload": False,
            "with_vector": False,
        })
        if resp.status_code == 200:
            data = resp.json()
            return {str(p["id"]) for p in data.get("result", {}).get("points", [])}
        return set()

    async def add_document(self, doc: KnowledgeDocument) -> bool:
        """Add a document to the knowledgebase with embedding."""
        try:
            embedding = await self._get_embedding(doc.content)
            doc._embedding = embedding

            point = {
                "id": hashlib.md5(doc.id.encode()).hexdigest(),
                "vector": embedding,
                "payload": doc.to_payload(),
            }

            resp = await self._client.put(
                f"{self._qdrant_url}/collections/{self._collection}/points?wait=true",
                json={"points": [point]},
            )

            if resp.status_code == 200:
                self._local_cache[doc.id] = doc
                logger.info(f"Document added: {doc.id} ({doc.title})")
                return True
            return False

        except Exception as e:
            logger.warning(f"Failed to add document to Qdrant, using cache: {e}")
            self._local_cache[doc.id] = doc
            return True

    async def search(self, query: str, top_k: int = 3, category: str = None) -> List[Dict[str, Any]]:
        """Semantic search over knowledgebase."""
        try:
            embedding = await self._get_embedding(query)

            search_payload = {
                "vector": embedding,
                "limit": top_k,
                "with_payload": True,
                "with_vector": False,
            }

            if category:
                search_payload["filter"] = {
                    "must": [{"key": "category", "match": {"value": category}}]
                }

            resp = await self._client.post(
                f"{self._qdrant_url}/collections/{self._collection}/points/search",
                json=search_payload,
            )

            if resp.status_code == 200:
                results = resp.json().get("result", [])
                return [
                    {
                        "id": r["payload"].get("id", ""),
                        "title": r["payload"].get("title", ""),
                        "content": r["payload"].get("content", ""),
                        "category": r["payload"].get("category", ""),
                        "score": r.get("score", 0.0),
                        "tags": r["payload"].get("tags", []),
                    }
                    for r in results
                ]

        except Exception as e:
            logger.warning(f"Qdrant search failed, falling back to local: {e}")

        return self._local_search(query, top_k, category)

    def _local_search(self, query: str, top_k: int = 3, category: str = None) -> List[Dict[str, Any]]:
        """Fallback: keyword search over local cache."""
        query_lower = query.lower()
        results = []

        for doc_id, doc in self._local_cache.items():
            if category and doc.category != category:
                continue

            score = 0
            content_lower = doc.content.lower()
            title_lower = doc.title.lower()

            if query_lower in title_lower:
                score += 10
            if query_lower in content_lower:
                score += 5
            for tag in doc.tags:
                if tag.lower() in query_lower or query_lower in tag.lower():
                    score += 3

            if score > 0:
                results.append({
                    "id": doc.id,
                    "title": doc.title,
                    "content": doc.content,
                    "category": doc.category,
                    "score": score,
                    "tags": doc.tags,
                })

        return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]

    async def get_context_for_stage(self, stage: str, user_input: str = "") -> str:
        """Get relevant knowledge context for a conversation stage."""
        stage_map = {
            "greet": ["company_info"],
            "discovery": ["qualification_framework"],
            "qualify": ["qualification_framework", "product_comparison"],
            "offer": ["product_comparison", "multiposting"],
            "objection": ["objection_price", "objection_time", "objection_no_interest"],
            "close": ["closing_techniques", "product_comparison"],
            "followup": ["objection_time"],
            "summary": ["closing_techniques"],
        }

        relevant_ids = stage_map.get(stage, [])
        context_parts = []

        if user_input:
            search_results = await self.search(user_input, top_k=2)
            for r in search_results:
                if r["id"] not in relevant_ids:
                    context_parts.append(f"[{r['title']}]: {r['content'][:300]}")

        for doc_id in relevant_ids:
            if doc_id in self._local_cache:
                doc = self._local_cache[doc_id]
                context_parts.append(f"[{doc.title}]: {doc.content[:400]}")

        return "\n\n".join(context_parts) if context_parts else ""

    async def get_all_documents(self) -> List[Dict[str, Any]]:
        """List all documents in the knowledgebase."""
        return [doc.to_payload() for doc in self._local_cache.values()]

    async def close(self):
        await self._client.aclose()
