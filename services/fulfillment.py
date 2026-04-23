"""
Fulfillment Service
Handles job ad creation, validation, and portal submission
for StepStone and Indeed after a successful sale.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from config.settings import AppConfig

logger = logging.getLogger("stepsales.fulfillment")


class JobAdSubmission:
    """Represents a job ad to be submitted to a portal."""

    def __init__(self, ad_data: dict):
        self.title = ad_data.get("title", "")
        self.company = ad_data.get("company", "")
        self.description = ad_data.get("description", "")
        self.location = ad_data.get("location", "")
        self.employment_type = ad_data.get("employment_type", "full_time")
        self.salary_range = ad_data.get("salary_range", "")
        self.requirements = ad_data.get("requirements", [])
        self.benefits = ad_data.get("benefits", [])
        self.contact_email = ad_data.get("contact_email", "")
        self.contact_phone = ad_data.get("contact_phone", "")
        self.start_date = ad_data.get("start_date")
        self.portal = ad_data.get("portal", "stepstone")
        self.duration_days = ad_data.get("duration_days", 30)


class FulfillmentService:
    """Job ad fulfillment: validate, create, submit to portals."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._client = httpx.AsyncClient(timeout=60.0)

    async def validate_ad(self, ad: JobAdSubmission) -> Dict[str, Any]:
        """Validate job ad against portal requirements."""
        errors = []
        warnings = []

        if not ad.title or len(ad.title) < 5:
            errors.append("Titel muss mindestens 5 Zeichen haben")
        if len(ad.title) > 100:
            errors.append("Titel darf maximal 100 Zeichen haben")
        if not ad.description or len(ad.description) < 50:
            errors.append("Beschreibung muss mindestens 50 Zeichen haben")
        if not ad.location:
            errors.append("Standort ist erforderlich")
        if not ad.contact_email:
            errors.append("Kontakt-E-Mail ist erforderlich")
        if not ad.requirements:
            warnings.append("Keine Anforderungen angegeben – reduziert Bewerbungen")

        if ad.portal == "stepstone":
            if len(ad.description) > 5000:
                errors.append("StepStone: Beschreibung maximal 5000 Zeichen")
        elif ad.portal == "indeed":
            if len(ad.description) > 6000:
                errors.append("Indeed: Beschreibung maximal 6000 Zeichen")

        is_valid = len(errors) == 0

        logger.info(f"Ad validation: {'PASSED' if is_valid else 'FAILED'} ({len(errors)} errors, {len(warnings)} warnings)")

        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
        }

    async def submit_to_stepstone(self, ad: JobAdSubmission) -> Dict[str, Any]:
        """Submit job ad to StepStone API."""
        payload = {
            "title": ad.title,
            "company": ad.company,
            "description": ad.description,
            "location": ad.location,
            "employmentType": ad.employment_type,
            "salaryRange": ad.salary_range,
            "requirements": ad.requirements,
            "benefits": ad.benefits,
            "contactEmail": ad.contact_email,
            "contactPhone": ad.contact_phone,
            "startDate": ad.start_date,
            "durationDays": ad.duration_days,
        }

        logger.info(f"Submitting ad to StepStone: '{ad.title}' at {ad.company}")

        try:
            resp = await self._client.post(
                "https://api.stepstone.com/v1/job-ads",
                json=payload,
                headers={"Authorization": f"Bearer {self.config.telnyx.api_key}"},
            )

            if resp.status_code in [200, 201]:
                result = resp.json()
                logger.info(f"StepStone ad created: {result.get('id', 'unknown')}")
                return {
                    "success": True,
                    "portal": "stepstone",
                    "ad_id": result.get("id"),
                    "status": result.get("status", "pending"),
                    "url": result.get("url"),
                }
            else:
                logger.error(f"StepStone submission failed: {resp.status_code} {resp.text}")
                return {
                    "success": False,
                    "portal": "stepstone",
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                }

        except Exception as e:
            logger.error(f"StepStone submission error: {e}")
            return {
                "success": False,
                "portal": "stepstone",
                "error": str(e),
            }

    async def submit_to_indeed(self, ad: JobAdSubmission) -> Dict[str, Any]:
        """Submit job ad to Indeed API (via Partner API)."""
        payload = {
            "title": ad.title,
            "company": ad.company,
            "description": ad.description,
            "location": ad.location,
            "employmentType": ad.employment_type,
            "salary": ad.salary_range,
            "qualifications": ad.requirements,
            "benefits": ad.benefits,
            "applyUrl": f"mailto:{ad.contact_email}",
            "postedDate": datetime.utcnow().isoformat(),
            "validThrough": datetime.utcnow().isoformat(),
        }

        logger.info(f"Submitting ad to Indeed: '{ad.title}' at {ad.company}")

        try:
            resp = await self._client.post(
                "https://apis.indeed.com/v1/jobs",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.config.telnyx.api_key,
                },
            )

            if resp.status_code in [200, 201]:
                result = resp.json()
                logger.info(f"Indeed ad created: {result.get('id', 'unknown')}")
                return {
                    "success": True,
                    "portal": "indeed",
                    "ad_id": result.get("id"),
                    "status": result.get("status", "pending"),
                    "url": result.get("url"),
                }
            else:
                logger.error(f"Indeed submission failed: {resp.status_code} {resp.text}")
                return {
                    "success": False,
                    "portal": "indeed",
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                }

        except Exception as e:
            logger.error(f"Indeed submission error: {e}")
            return {
                "success": False,
                "portal": "indeed",
                "error": str(e),
            }

    async def submit_multiposting(self, ad: JobAdSubmission) -> Dict[str, Any]:
        """Submit to both StepStone and Indeed (multiposting)."""
        validation = await self.validate_ad(ad)
        if not validation["valid"]:
            return {
                "success": False,
                "validation": validation,
                "results": [],
            }

        results = await asyncio.gather(
            self.submit_to_stepstone(ad),
            self.submit_to_indeed(ad),
        )

        success_count = sum(1 for r in results if r.get("success"))
        total = len(results)

        logger.info(f"Multiposting result: {success_count}/{total} portals successful")

        return {
            "success": success_count == total,
            "partial_success": success_count > 0,
            "validation": validation,
            "results": results,
            "success_count": success_count,
            "total_portals": total,
            "submitted_at": datetime.utcnow().isoformat(),
        }

    async def get_ad_status(self, portal: str, ad_id: str) -> Dict[str, Any]:
        """Check status of a submitted job ad."""
        if portal == "stepstone":
            url = f"https://api.stepstone.com/v1/job-ads/{ad_id}"
        elif portal == "indeed":
            url = f"https://apis.indeed.com/v1/jobs/{ad_id}"
        else:
            return {"success": False, "error": f"Unknown portal: {portal}"}

        try:
            resp = await self._client.get(url)
            if resp.status_code == 200:
                return {"success": True, "status": resp.json().get("status"), "data": resp.json()}
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def close(self):
        await self._client.aclose()
