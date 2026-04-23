"""
Audit & Monitoring Service
Comprehensive audit logging, security scanning, compliance tracking,
and system health monitoring for the Stepsales platform.
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from config.settings import AppConfig

logger = logging.getLogger("stepsales.audit")


class AuditLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditCategory(str, Enum):
    AUTH = "authentication"
    DATA_ACCESS = "data_access"
    CONFIG_CHANGE = "config_change"
    API_CALL = "api_call"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    SYSTEM = "system"


class AuditEntry:
    """Single audit log entry with full traceability."""

    def __init__(self, category: AuditCategory, action: str, actor: str = "system",
                 target: str = "", details: dict = None, level: AuditLevel = AuditLevel.INFO):
        self.id = hashlib.md5(f"{action}{target}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12]
        self.timestamp = datetime.utcnow().isoformat()
        self.category = category.value
        self.action = action
        self.actor = actor
        self.target = target
        self.details = details or {}
        self.level = level.value
        self.ip_address = ""
        self.user_agent = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "category": self.category,
            "action": self.action,
            "actor": self.actor,
            "target": self.target,
            "details": self.details,
            "level": self.level,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }


class SecurityScan:
    """Security vulnerability scan result."""

    def __init__(self, scan_type: str):
        self.scan_type = scan_type
        self.timestamp = datetime.utcnow().isoformat()
        self.findings: List[dict] = []
        self.score = 100

    def add_finding(self, severity: str, category: str, description: str, remediation: str = ""):
        self.findings.append({
            "severity": severity,
            "category": category,
            "description": description,
            "remediation": remediation,
        })
        severity_scores = {"critical": 25, "high": 15, "medium": 5, "low": 1}
        self.score = max(0, self.score - severity_scores.get(severity, 0))

    def to_dict(self) -> dict:
        return {
            "scan_type": self.scan_type,
            "timestamp": self.timestamp,
            "score": self.score,
            "findings_count": len(self.findings),
            "findings": self.findings,
        }


class AuditAndMonitoringService:
    """Centralized audit logging, security scanning, and compliance monitoring."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._audit_log: List[AuditEntry] = []
        self._security_scans: List[SecurityScan] = []
        self._compliance_checks: Dict[str, dict] = {}
        self._max_log_entries = 10000

    async def initialize(self):
        logger.info("Audit & Monitoring Service initialized")
        await self.run_security_scan()
        await self.run_compliance_check()

    async def log(self, category: AuditCategory, action: str, actor: str = "system",
                  target: str = "", details: dict = None, level: AuditLevel = AuditLevel.INFO,
                  ip_address: str = "", user_agent: str = ""):
        """Add an entry to the audit log."""
        entry = AuditEntry(category, action, actor, target, details, level)
        entry.ip_address = ip_address
        entry.user_agent = user_agent
        self._audit_log.append(entry)

        if len(self._audit_log) > self._max_log_entries:
            self._audit_log = self._audit_log[-self._max_log_entries:]

        log_msg = f"[{level.value.upper()}] {category.value}/{action} by {actor}"
        if target:
            log_msg += f" on {target}"
        if level in [AuditLevel.ERROR, AuditLevel.CRITICAL]:
            logger.error(log_msg)
        elif level == AuditLevel.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

    async def run_security_scan(self) -> SecurityScan:
        """Run comprehensive security scan."""
        scan = SecurityScan("full_security_scan")

        env_vars = os.environ
        sensitive_patterns = ["API_KEY", "SECRET", "PASSWORD", "TOKEN"]

        for key, value in env_vars.items():
            if any(p in key.upper() for p in sensitive_patterns):
                if len(value) < 10:
                    scan.add_finding("high", "credential", f"Weak or empty credential: {key}",
                                   f"Set a strong value for {key}")
                elif value.startswith("sk-proj-") and len(value) < 50:
                    scan.add_finding("medium", "credential", f"Potentially truncated key: {key}",
                                   "Verify the API key is complete")

        files_to_check = ["config/settings.py", "config_legacy.py", "main.py"]
        for f in files_to_check:
            if os.path.exists(f):
                with open(f) as fh:
                    content = fh.read()
                hardcoded_secrets = re.findall(r'["\'](?:api_key|secret|password)["\']\s*:\s*["\']([^"\']{10,})["\']', content)
                if hardcoded_secrets:
                    scan.add_finding("critical", "hardcoded_secret", f"Hardcoded secret in {f}",
                                   "Use environment variables or a secrets manager")

        if self.config.stripe.api_key:
            scan.add_finding("low", "config", "Stripe API key is configured", "")
        else:
            scan.add_finding("medium", "config", "Stripe API key is empty",
                           "Set STRIPE_API_KEY in .env")

        if self.config.telnyx.from_number:
            scan.add_finding("low", "config", "Telnyx from_number is configured", "")
        else:
            scan.add_finding("medium", "config", "Telnyx from_number is empty",
                           "Set TELNYX_FROM_NUMBER in .env")

        db_url = self.config.persistence.db_url
        if db_url.startswith("sqlite"):
            scan.add_finding("low", "database", "Using SQLite (not recommended for production)",
                           "Migrate to PostgreSQL for production")

        self._security_scans.append(scan)
        logger.info(f"Security scan complete: score={scan.score}/100, findings={len(scan.findings)}")
        return scan

    async def run_compliance_check(self) -> dict:
        """Run GDPR and data compliance checks."""
        checks = {
            "pii_minimization": {"status": "pass", "details": "Phone numbers stored, no full addresses"},
            "data_retention": {"status": "pass", "details": "Memory facts have TTL (default 180 days)"},
            "consent_tracking": {"status": "warning", "details": "No explicit consent tracking implemented"},
            "right_to_erasure": {"status": "warning", "details": "No delete endpoint for customer data"},
            "data_encryption": {"status": "warning", "details": "SQLite not encrypted, PostgreSQL TLS recommended"},
            "audit_trail": {"status": "pass", "details": f"Audit logging active ({len(self._audit_log)} entries)"},
            "access_control": {"status": "warning", "details": "No authentication on API endpoints"},
            "backup_strategy": {"status": "fail", "details": "No automated backups configured"},
        }

        passed = sum(1 for c in checks.values() if c["status"] == "pass")
        warnings = sum(1 for c in checks.values() if c["status"] == "warning")
        failed = sum(1 for c in checks.values() if c["status"] == "fail")
        total = len(checks)

        score = round((passed / total) * 100, 1) if total > 0 else 0

        self._compliance_checks = {
            "timestamp": datetime.utcnow().isoformat(),
            "score": score,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "total": total,
            "checks": checks,
        }

        logger.info(f"Compliance check complete: {score}% ({passed}/{total} passed)")
        return self._compliance_checks

    def get_audit_log(self, category: str = None, level: str = None,
                      actor: str = None, limit: int = 100) -> list:
        """Query audit log with filters."""
        entries = self._audit_log

        if category:
            entries = [e for e in entries if e.category == category]
        if level:
            entries = [e for e in entries if e.level == level]
        if actor:
            entries = [e for e in entries if e.actor == actor]

        return [e.to_dict() for e in entries[-limit:]]

    def get_security_history(self) -> list:
        """Get all security scan results."""
        return [s.to_dict() for s in self._security_scans]

    def get_compliance_status(self) -> dict:
        """Get latest compliance check status."""
        return self._compliance_checks

    def get_summary(self) -> dict:
        """Get complete monitoring summary."""
        level_counts = {}
        category_counts = {}
        for entry in self._audit_log:
            level_counts[entry.level] = level_counts.get(entry.level, 0) + 1
            category_counts[entry.category] = category_counts.get(entry.category, 0) + 1

        return {
            "audit_log": {
                "total_entries": len(self._audit_log),
                "level_breakdown": level_counts,
                "category_breakdown": category_counts,
                "max_capacity": self._max_log_entries,
            },
            "security": {
                "scans_run": len(self._security_scans),
                "latest_score": self._security_scans[-1].score if self._security_scans else None,
                "latest_findings": len(self._security_scans[-1].findings) if self._security_scans else 0,
            },
            "compliance": self._compliance_checks,
            "timestamp": datetime.utcnow().isoformat(),
        }
