"""
Stripe Billing Service
Handles customer creation, invoice drafting/finalizing/sending,
and webhook processing for payment state tracking.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

import httpx
import stripe

from config.settings import AppConfig

logger = logging.getLogger("stepsales.stripe")


class StripeBilling:
    """Stripe Invoicing service for Stepsales billing workflows."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._client = httpx.AsyncClient(
            base_url=self.config.stripe.api_base,
            auth=(self.config.stripe.api_key, ""),
            timeout=30.0,
        )

    async def create_or_get_customer(
        self,
        email: str,
        name: str = "",
        company: str = "",
        phone: str = "",
    ) -> Dict:
        """Create or find existing Stripe customer."""
        existing = await self._client.get("/customers", params={"email": email, "limit": 1})
        existing.raise_for_status()
        customers = existing.json().get("data", [])

        if customers:
            return {"success": True, "customer_id": customers[0]["id"], "existing": True}

        customer_data = {"email": email}
        if name:
            customer_data["name"] = name
        if company:
            customer_data["description"] = company
        if phone:
            customer_data["phone"] = phone

        resp = await self._client.post("/customers", data=customer_data)
        resp.raise_for_status()
        customer = resp.json()

        logger.info(f"Stripe customer created: {customer['id']} ({email})")
        return {
            "success": True,
            "customer_id": customer["id"],
            "existing": False,
        }

    async def create_invoice(
        self,
        customer_id: str,
        items: list,
        description: str = "",
        due_days: int = 14,
        auto_advance: bool = False,
    ) -> Dict:
        """Create a draft invoice with line items."""
        invoice_data = {
            "customer": customer_id,
            "auto_advance": str(auto_advance).lower(),
            "collection_method": "send_invoice",
            "days_until_due": due_days,
        }

        if description:
            invoice_data["description"] = description

        resp = await self._client.post("/invoices", data=invoice_data)
        resp.raise_for_status()
        invoice = resp.json()
        invoice_id = invoice["id"]

        for item in items:
            line_item = {
                "invoice": invoice_id,
                "amount": str(int(item["amount_cents"])),
                "currency": item.get("currency", self.config.stripe.currency),
                "description": item["description"],
            }
            line_resp = await self._client.post("/invoiceitems", data=line_item)
            line_resp.raise_for_status()

        logger.info(
            f"Draft invoice created: {invoice_id} for customer {customer_id} "
            f"({len(items)} items)"
        )

        return {
            "success": True,
            "invoice_id": invoice_id,
            "status": "draft",
            "customer_id": customer_id,
        }

    async def finalize_invoice(self, invoice_id: str) -> Dict:
        """Finalize a draft invoice (makes it ready for sending)."""
        resp = await self._client.post(f"/invoices/{invoice_id}/finalize")
        resp.raise_for_status()
        invoice = resp.json()

        logger.info(f"Invoice finalized: {invoice_id}")
        return {
            "success": True,
            "invoice_id": invoice_id,
            "status": invoice.get("status", "unknown"),
            "amount_due": invoice.get("amount_due", 0),
        }

    async def send_invoice(self, invoice_id: str) -> Dict:
        """Send finalized invoice to customer via email."""
        resp = await self._client.post(f"/invoices/{invoice_id}/send")
        resp.raise_for_status()
        invoice = resp.json()

        hosted_url = invoice.get("hosted_invoice_url", "")
        logger.info(f"Invoice sent: {invoice_id} (hosted: {hosted_url})")

        return {
            "success": True,
            "invoice_id": invoice_id,
            "hosted_invoice_url": hosted_url,
            "status": invoice.get("status", "unknown"),
            "amount_due": invoice.get("amount_due", 0),
            "due_date": invoice.get("due_date"),
        }

    async def create_and_send_invoice(
        self,
        customer_email: str,
        customer_name: str,
        customer_company: str,
        items: list,
        description: str = "",
        due_days: int = 14,
    ) -> Dict:
        """Full invoice flow: customer -> draft -> finalize -> send."""
        customer = await self.create_or_get_customer(
            email=customer_email,
            name=customer_name,
            company=customer_company,
        )
        if not customer["success"]:
            return customer

        draft = await self.create_invoice(
            customer_id=customer["customer_id"],
            items=items,
            description=description,
            due_days=due_days,
        )
        if not draft["success"]:
            return draft

        finalized = await self.finalize_invoice(draft["invoice_id"])
        if not finalized["success"]:
            return finalized

        sent = await self.send_invoice(draft["invoice_id"])
        return sent

    async def get_invoice(self, invoice_id: str) -> Dict:
        """Get invoice details."""
        resp = await self._client.get(f"/invoices/{invoice_id}")
        resp.raise_for_status()
        return resp.json()

    def verify_webhook_signature(self, payload: str, sig_header: str) -> bool:
        """Verify Stripe webhook signature using Stripe-Signature header format.

        Stripe signature format: t=timestamp,v1=signature
        Uses HMAC-SHA256 with timestamp to prevent replay attacks.
        """
        import stripe as stripe_lib

        if not self.config.stripe.webhook_secret:
            return True

        try:
            stripe_lib.Webhook.construct_event(
                payload, sig_header, self.config.stripe.webhook_secret
            )
            return True
        except (ValueError, stripe_lib.error.SignatureVerificationError):
            return False

    async def handle_webhook(self, event_data: dict) -> dict:
        """Process Stripe webhook events for payment state tracking."""
        event_type = event_data.get("type", "unknown")
        data = event_data.get("data", {}).get("object", {})

        invoice_id = data.get("id", "")
        status = data.get("status", "unknown")

        logger.info(f"Stripe webhook: {event_type} for invoice {invoice_id} (status: {status})")

        return {
            "success": True,
            "event_type": event_type,
            "invoice_id": invoice_id,
            "status": status,
        }

    async def close(self):
        await self._client.aclose()
