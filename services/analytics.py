"""
Analytics Service - KPIs, Forecasting, and Reporting
Tracks sales performance metrics, conversion rates, and revenue forecasting
for the Stepsales platform.
"""

import logging
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from config.settings import AppConfig

logger = logging.getLogger("stepsales.analytics")


class KPI:
    """Represents a single Key Performance Indicator."""

    def __init__(self, name: str, value: float, target: float, unit: str = "%"):
        self.name = name
        self.value = value
        self.target = target
        self.unit = unit
        self.timestamp = datetime.utcnow().isoformat()

    @property
    def achievement(self) -> float:
        if self.target == 0:
            return 100.0
        return round((self.value / self.target) * 100, 1)

    @property
    def status(self) -> str:
        if self.achievement >= 100:
            return "on_track"
        elif self.achievement >= 80:
            return "at_risk"
        else:
            return "off_track"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "target": self.target,
            "unit": self.unit,
            "achievement": self.achievement,
            "status": self.status,
            "timestamp": self.timestamp,
        }


class ConversionFunnel:
    """Tracks conversion rates across the sales funnel."""

    def __init__(self):
        self.stages: Dict[str, int] = {
            "leads_generated": 0,
            "calls_made": 0,
            "calls_connected": 0,
            "qualified": 0,
            "offers_sent": 0,
            "deals_won": 0,
            "deals_lost": 0,
        }

    @property
    def conversion_rates(self) -> Dict[str, float]:
        rates = {}
        stages_list = list(self.stages.keys())
        for i, stage in enumerate(stages_list):
            if self.stages[stage] > 0:
                if i < len(stages_list) - 2:
                    next_stage = stages_list[i + 1]
                    rates[f"{stage}_to_{next_stage}"] = round(
                        (self.stages[next_stage] / self.stages[stage]) * 100, 1
                    ) if self.stages[stage] > 0 else 0
        return rates

    @property
    def overall_conversion(self) -> float:
        if self.stages["leads_generated"] == 0:
            return 0.0
        return round((self.stages["deals_won"] / self.stages["leads_generated"]) * 100, 1)

    @property
    def win_rate(self) -> float:
        total_closed = self.stages["deals_won"] + self.stages["deals_lost"]
        if total_closed == 0:
            return 0.0
        return round((self.stages["deals_won"] / total_closed) * 100, 1)

    def to_dict(self) -> dict:
        return {
            "stages": self.stages,
            "conversion_rates": self.conversion_rates,
            "overall_conversion": self.overall_conversion,
            "win_rate": self.win_rate,
        }


class ForecastResult:
    """Revenue forecast based on pipeline data."""

    def __init__(self):
        self.current_mrr: float = 0
        self.projected_mrr: float = 0
        self.pipeline_value: float = 0
        self.weighted_pipeline: float = 0
        self.deals_in_pipeline: int = 0
        self.avg_deal_size: float = 0
        self.forecast_accuracy: float = 0

    def to_dict(self) -> dict:
        return {
            "current_mrr": self.current_mrr,
            "projected_mrr": self.projected_mrr,
            "pipeline_value": self.pipeline_value,
            "weighted_pipeline": self.weighted_pipeline,
            "deals_in_pipeline": self.deals_in_pipeline,
            "avg_deal_size": self.avg_deal_size,
            "forecast_accuracy": self.forecast_accuracy,
            "growth_rate": round(((self.projected_mrr - self.current_mrr) / max(self.current_mrr, 1)) * 100, 1),
        }


class AnalyticsService:
    """KPI tracking, conversion funnel analysis, and revenue forecasting."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._call_durations: List[float] = []
        self._deal_sizes: List[float] = []
        self._objection_counts: Dict[str, int] = defaultdict(int)
        self._stage_counts: Dict[str, int] = defaultdict(int)
        self._daily_calls: Dict[str, int] = defaultdict(int)
        self._daily_revenue: Dict[str, float] = defaultdict(float)
        self._funnel = ConversionFunnel()
        self._forecast = ForecastResult()
        self._total_revenue: float = 0
        self._total_calls: int = 0
        self._total_leads: int = 0

    async def initialize(self):
        logger.info("Analytics Service initialized")

    def record_call(self, duration_seconds: float, final_stage: str, deal_value: float = 0):
        """Record a completed call for analytics."""
        self._total_calls += 1
        self._call_durations.append(duration_seconds)
        self._stage_counts[final_stage] += 1

        today = datetime.utcnow().strftime("%Y-%m-%d")
        self._daily_calls[today] += 1

        if deal_value > 0:
            self._deal_sizes.append(deal_value)
            self._total_revenue += deal_value
            self._daily_revenue[today] += deal_value

        self._funnel.stages["calls_made"] += 1
        if final_stage in ["close", "summary"]:
            self._funnel.stages["calls_connected"] += 1

        logger.info(f"Call recorded: {duration_seconds}s, stage={final_stage}, value={deal_value} EUR")

    def record_lead(self, source: str = "outbound"):
        """Record a new lead."""
        self._total_leads += 1
        self._funnel.stages["leads_generated"] += 1

    def record_objection(self, objection_type: str):
        """Record an objection encountered during a call."""
        self._objection_counts[objection_type] += 1

    def record_stage(self, stage: str):
        """Record a lead reaching a specific funnel stage."""
        stage_mapping = {
            "qualified": "qualified",
            "offer": "offers_sent",
            "close": "deals_won",
            "followup": "deals_lost",
        }
        if stage in stage_mapping:
            self._funnel.stages[stage_mapping[stage]] += 1

    def get_kpis(self) -> List[KPI]:
        """Calculate current KPIs."""
        kpis = []

        avg_duration = statistics.mean(self._call_durations) if self._call_durations else 0
        kpis.append(KPI(
            name="Avg Call Duration",
            value=round(avg_duration, 0),
            target=300,
            unit="seconds",
        ))

        today = datetime.utcnow().strftime("%Y-%m-%d")
        today_calls = self._daily_calls.get(today, 0)
        kpis.append(KPI(
            name="Calls Today",
            value=today_calls,
            target=20,
            unit="calls",
        ))

        kpis.append(KPI(
            name="Total Revenue",
            value=round(self._total_revenue, 0),
            target=50000,
            unit="EUR",
        ))

        conn_rate = 0
        if self._funnel.stages["calls_made"] > 0:
            conn_rate = round(
                (self._funnel.stages["calls_connected"] / self._funnel.stages["calls_made"]) * 100, 1
            )
        kpis.append(KPI(
            name="Connection Rate",
            value=conn_rate,
            target=40,
        ))

        kpis.append(KPI(
            name="Win Rate",
            value=self._funnel.win_rate,
            target=25,
        ))

        kpis.append(KPI(
            name="Overall Conversion",
            value=self._funnel.overall_conversion,
            target=5,
        ))

        if self._deal_sizes:
            avg_deal = statistics.mean(self._deal_sizes)
            kpis.append(KPI(
                name="Avg Deal Size",
                value=round(avg_deal, 0),
                target=799,
                unit="EUR",
            ))

        return kpis

    def get_funnel(self) -> dict:
        """Get the current conversion funnel."""
        return self._funnel.to_dict()

    def get_forecast(self) -> dict:
        """Generate revenue forecast."""
        self._forecast.current_mrr = self._total_revenue
        self._forecast.pipeline_value = sum(self._deal_sizes[-10:]) if self._deal_sizes else 0
        self._forecast.deals_in_pipeline = self._funnel.stages["offers_sent"] - self._funnel.stages["deals_won"]
        self._forecast.avg_deal_size = statistics.mean(self._deal_sizes) if self._deal_sizes else 0
        self._forecast.weighted_pipeline = self._forecast.pipeline_value * (self._funnel.win_rate / 100) if self._funnel.win_rate > 0 else 0
        self._forecast.projected_mrr = self._forecast.current_mrr + (self._forecast.weighted_pipeline * 0.3)

        return self._forecast.to_dict()

    def get_objection_analysis(self) -> dict:
        """Get breakdown of objection types."""
        total = sum(self._objection_counts.values())
        return {
            "total_objections": total,
            "breakdown": dict(self._objection_counts),
            "top_objections": sorted(
                self._objection_counts.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

    def get_daily_trend(self, days: int = 7) -> dict:
        """Get daily call and revenue trends."""
        calls = {}
        revenue = {}

        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            calls[date] = self._daily_calls.get(date, 0)
            revenue[date] = round(self._daily_revenue.get(date, 0), 0)

        return {
            "calls": calls,
            "revenue": revenue,
            "period_days": days,
        }

    def get_summary(self) -> dict:
        """Get complete analytics summary."""
        return {
            "kpis": [k.to_dict() for k in self.get_kpis()],
            "funnel": self.get_funnel(),
            "forecast": self.get_forecast(),
            "objections": self.get_objection_analysis(),
            "total_calls": self._total_calls,
            "total_leads": self._total_leads,
            "total_revenue": round(self._total_revenue, 0),
            "generated_at": datetime.utcnow().isoformat(),
        }
