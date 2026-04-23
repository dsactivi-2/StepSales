"""
Webhook Router - Telnyx and Stripe Production Webhooks
Handles incoming webhook events, verifies signatures,
and dispatches to appropriate service handlers.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from config.settings import AppConfig

logger = logging.getLogger("stepsales.webhooks")


class WebhookRouter:
    """Central webhook handler for all external service webhooks."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._handlers: Dict[str, Callable] = {}
        self._events_log: list = []

    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler for a specific webhook event type."""
        self._handlers[event_type] = handler
        logger.info(f"Webhook handler registered: {event_type}")

    async def handle_telnyx_webhook(self, payload: dict, signature: str = "", timestamp: str = "") -> dict:
        """Process incoming Telnyx webhook."""
        from services.telnyx_gateway import TelnyxGateway

        gateway = TelnyxGateway(self.config)

        if signature and timestamp:
            if not gateway.verify_webhook_signature(str(payload), signature, timestamp):
                logger.warning("Telnyx webhook signature verification failed")
                return {"success": False, "error": "Invalid signature"}

        event_type = payload.get("event_type", "unknown")
        call_id = payload.get("data", {}).get("id", "")
        call_state = payload.get("data", {}).get("state", "")

        logger.info(f"Telnyx webhook: {event_type} | call={call_id} | state={call_state}")

        self._events_log.append({
            "source": "telnyx",
            "event_type": event_type,
            "call_id": call_id,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        })

        handler = self._handlers.get(f"telnyx.{event_type}")
        if handler:
            try:
                result = await handler(payload)
                return {"success": True, "handler_result": result}
            except Exception as e:
                logger.error(f"Telnyx webhook handler error: {e}")
                return {"success": False, "error": str(e)}

        return {"success": True, "event": event_type, "call_id": call_id, "state": call_state}

    async def handle_stripe_webhook(self, payload_body: bytes, sig_header: str) -> dict:
        """Process incoming Stripe webhook with signature verification."""
        import stripe

        webhook_secret = self.config.stripe.webhook_secret
        if not webhook_secret:
            logger.warning("Stripe webhook secret not configured - skipping verification")
            event = {"data": {}}
        else:
            try:
                event = stripe.Webhook.construct_event(
                    payload_body, sig_header, webhook_secret
                )
            except ValueError as e:
                logger.error(f"Stripe webhook invalid payload: {e}")
                return {"success": False, "error": "Invalid payload"}
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"Stripe webhook signature invalid: {e}")
                return {"success": False, "error": "Invalid signature"}

        event_type = event.get("type", "unknown")
        data = event.get("data", {}).get("object", {})

        logger.info(f"Stripe webhook: {event_type}")

        self._events_log.append({
            "source": "stripe",
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        })

        handler = self._handlers.get(f"stripe.{event_type}")
        if handler:
            try:
                result = await handler(event)
                return {"success": True, "handler_result": result}
            except Exception as e:
                logger.error(f"Stripe webhook handler error: {e}")
                return {"success": False, "error": str(e)}

        if "invoice.payment_succeeded" in event_type:
            return {
                "success": True,
                "event": "payment_succeeded",
                "invoice_id": data.get("id"),
                "amount": data.get("amount_paid"),
            }

        return {"success": True, "event": event_type}

    def get_event_log(self, source: str = None, limit: int = 50) -> list:
        """Get recent webhook events."""
        events = self._events_log
        if source:
            events = [e for e in events if e.get("source") == source]
        return events[-limit:]

    def get_stats(self) -> dict:
        """Get webhook statistics."""
        telnyx_count = sum(1 for e in self._events_log if e.get("source") == "telnyx")
        stripe_count = sum(1 for e in self._events_log if e.get("source") == "stripe")
        return {
            "total_events": len(self._events_log),
            "telnyx_events": telnyx_count,
            "stripe_events": stripe_count,
            "registered_handlers": len(self._handlers),
        }
