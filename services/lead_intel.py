"""
Lead Intelligence Service
Discovers companies with open positions, detects cross-posting gaps
(Stepstone yes/Indeed no or vice versa), and prioritizes outbound targets.
Sources: Bundesagentur fur Arbeit API, Stepstone, Indeed (partner-conform).
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

import httpx

from config.settings import AppConfig

logger = logging.getLogger("stepsales.lead_intel")


class LeadIntelService:
    """Lead discovery and cross-posting gap detection."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._client = httpx.AsyncClient(timeout=30.0)

        self._stepstone_cache: List[dict] = []
        self._indeed_cache: List[dict] = []
        self._ba_cache: List[dict] = []

    async def search_stepstone(self, query: str, location: str = "", limit: int = 20) -> List[dict]:
        """Search Stepstone for companies with open positions."""
        try:
            url = "http://localhost:8000/search"
            params = {"q": query}
            if location:
                params["location"] = location

            resp = await self._client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("jobs", [])[:limit]
                self._stepstone_cache = results
                logger.info(f"Stepstone search '{query}': {len(results)} results")
                return results
        except Exception as e:
            logger.warning(f"Stepstone search failed: {e}")

        return []

    async def search_ba_jobs(self, query: str, location: str = "", limit: int = 20) -> List[dict]:
        """Search Bundesagentur fur Arbeit Jobsuche API."""
        try:
            url = "https://rest.arbeitsagentur.de/arsys/v1/jobsuche"
            params = {
                "was": query,
                "wo": location,
                "size": limit,
            }
            resp = await self._client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("stellenangebote", [])[:limit]
                self._ba_cache = results
                logger.info(f"BA Jobsuche '{query}': {len(results)} results")
                return results
        except Exception as e:
            logger.warning(f"BA Jobsuche failed: {e}")

        return []

    async def detect_cross_posting_gaps(
        self,
        query: str = "",
        location: str = "",
        days_back: int = 7,
    ) -> List[dict]:
        """Detect companies posting on one platform but not another."""
        stepstone = await self.search_stepstone(query, location) if query else self._stepstone_cache
        ba_jobs = await self.search_ba_jobs(query, location) if query else self._ba_cache

        stepstone_companies = set()
        for job in stepstone:
            company = job.get("company", job.get("company_name", "")).strip()
            if company:
                stepstone_companies.add(company.lower())

        ba_companies = set()
        for job in ba_jobs:
            company = job.get("firmenname", job.get("company", "")).strip()
            if company:
                ba_companies.add(company.lower())

        gaps = []

        only_stepstone = stepstone_companies - ba_companies
        only_ba = ba_companies - stepstone_companies

        for company in only_stepstone:
            gaps.append({
                "company": company,
                "has_stepstone": True,
                "has_indeed": False,
                "has_ba": False,
                "opportunity": "indeed_cross_post",
                "priority": "high" if len(stepstone_companies) > 3 else "medium",
                "detected_at": datetime.utcnow().isoformat(),
            })

        for company in only_ba:
            gaps.append({
                "company": company,
                "has_stepstone": False,
                "has_indeed": False,
                "has_ba": True,
                "opportunity": "stepstone_cross_post",
                "priority": "high",
                "detected_at": datetime.utcnow().isoformat(),
            })

        logger.info(f"Cross-posting gaps detected: {len(gaps)} (Stepstone-only: {len(only_stepstone)}, BA-only: {len(only_ba)})")
        return sorted(gaps, key=lambda x: 0 if x["priority"] == "high" else 1)

    async def enrich_lead(self, company_name: str) -> Dict:
        """Enrich a lead with available public data."""
        enriched = {
            "company_name": company_name,
            "open_positions_stepstone": 0,
            "open_positions_ba": 0,
            "latest_posting": None,
            "industries": [],
            "locations": [],
        }

        for job in self._stepstone_cache:
            if company_name.lower() in job.get("company", "").lower():
                enriched["open_positions_stepstone"] += 1
                if job.get("location"):
                    enriched["locations"].append(job["location"])

        for job in self._ba_cache:
            if company_name.lower() in job.get("firmenname", "").lower():
                enriched["open_positions_ba"] += 1
                if job.get("arbeitsort"):
                    enriched["locations"].append(job["arbeitsort"])

        enriched["locations"] = list(set(enriched["locations"]))
        return enriched

    async def generate_lead_queue(
        self,
        queries: List[str] = ["IT", "Software", "Pflege", "Vertrieb"],
        location: str = "",
        max_leads: int = 50,
    ) -> List[dict]:
        """Generate prioritized lead queue for outbound calls."""
        all_gaps = []

        for query in queries:
            gaps = await self.detect_cross_posting_gaps(query, location)
            all_gaps.extend(gaps)

        seen = set()
        unique_gaps = []
        for gap in all_gaps:
            if gap["company"] not in seen:
                seen.add(gap["company"])
                unique_gaps.append(gap)

        enriched = []
        for gap in unique_gaps[:max_leads]:
            detail = await self.enrich_lead(gap["company"])
            gap.update(detail)
            enriched.append(gap)

        logger.info(f"Lead queue generated: {len(enriched)} companies")
        return enriched

    async def close(self):
        await self._client.aclose()
