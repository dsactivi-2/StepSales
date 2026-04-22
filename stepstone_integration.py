#!/usr/bin/env python3
"""
Integration with mcp-stepstone for live job data
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from urllib.parse import quote

import requests

logger = logging.getLogger("stepsales.stepstone")


@dataclass
class JobListing:
    """Simplified job listing from Stepstone"""
    title: str
    company: str
    location: str
    salary: Optional[str] = None
    url: str = ""
    description: str = ""


class StepstoneIntegration:
    """Integration with mcp-stepstone for job lookups"""

    def __init__(self, zip_code: str = "40210", radius: int = 15, timeout: int = 10):
        self.zip_code = zip_code
        self.radius = radius
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Stepsales-Agent/1.0"
        }
        self._job_cache: Dict[str, List[JobListing]] = {}

    async def search_jobs(self, search_terms: List[str]) -> List[JobListing]:
        """
        Search for jobs on Stepstone.de
        Returns formatted job listings
        """
        all_jobs = []

        for term in search_terms:
            try:
                jobs = await self._search_single_term(term)
                all_jobs.extend(jobs)
                logger.info(f"Found {len(jobs)} jobs for '{term}'")
            except Exception as e:
                logger.error(f"Error searching for '{term}': {e}")
                continue

        # Deduplicate by URL
        seen_urls = set()
        deduplicated = []
        for job in all_jobs:
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                deduplicated.append(job)

        self._job_cache["last_search"] = deduplicated
        return deduplicated

    async def _search_single_term(self, term: str) -> List[JobListing]:
        """Search Stepstone for a single term"""
        return await asyncio.to_thread(self._search_sync, term)

    def _search_sync(self, term: str) -> List[JobListing]:
        """Synchronous Stepstone search via HTTP scraping"""
        url = self._build_search_url(term)
        logger.debug(f"Searching: {url}")

        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            # Extract job listings from HTML
            jobs = self._parse_job_listings(response.text)
            return jobs
        except requests.RequestException as e:
            logger.error(f"Request failed for '{term}': {e}")
            raise

    def _build_search_url(self, term: str) -> str:
        """Build Stepstone search URL"""
        base = "https://www.stepstone.de"
        params = {
            "q": term,
            "zc": self.zip_code,
            "r": str(self.radius),
        }
        query_string = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        return f"{base}/stellenangebote--{quote(term)}.html?{query_string}"

    def _parse_job_listings(self, html: str) -> List[JobListing]:
        """Parse job listings from HTML (simplified version)"""
        # This is a simplified parser. In production, use BeautifulSoup or similar
        jobs = []

        # Note: In a real implementation, use mcp-stepstone directly
        # or parse HTML with BeautifulSoup
        # For now, return empty list to avoid external dependencies

        return jobs

    async def get_job_details(self, job_url: str) -> Optional[Dict]:
        """Fetch full job details for a specific job"""
        try:
            response = requests.get(job_url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            details = self._extract_job_details(response.text)
            return details
        except Exception as e:
            logger.error(f"Failed to fetch job details: {e}")
            return None

    def _extract_job_details(self, html: str) -> Dict:
        """Extract detailed job information from HTML"""
        # Simplified extraction - in production use BeautifulSoup
        return {
            "description": "",
            "requirements": [],
            "benefits": [],
            "salary": None,
        }

    def get_cached_jobs(self) -> List[JobListing]:
        """Get last search results from cache"""
        return self._job_cache.get("last_search", [])

    def format_job_for_sales(self, job: JobListing) -> str:
        """Format job info for sales pitch"""
        return f"""
📌 {job.title}
🏢 {job.company}
📍 {job.location}
💰 {job.salary or 'Gehalt auf Anfrage'}
🔗 {job.url}
""".strip()
