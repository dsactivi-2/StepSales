"""
Agent Coach Service - Realtime Coaching + QA-Scoring
Analyzes agent performance during calls, provides coaching hints,
and generates QA scores based on conversation quality metrics.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.settings import AppConfig

logger = logging.getLogger("stepsales.agent_coach")


class QACriteria:
    """QA scoring criteria for sales calls."""

    GREETING_QUALITY = ("Begruung", 10, "Professionelle, freundliche Begruung mit Namen und Firma")
    NEEDS_ANALYSIS = ("Bedarfsanalyse", 20, "Aktives Zuhoren, gezielte Ruckfragen, Schmerzpunkte erkannt")
    PRODUCT_KNOWLEDGE = ("Produktwissen", 15, "Korrekte Informationen zu Paketen, Preisen, Vorteilen")
    OBJECTION_HANDLING = ("Einwandbehandlung", 20, "Empathisch, faktenbasiert, Losungsorientiert")
    CLOSING_ATTEMPT = ("Abschlussversuch", 15, "Konkreter CTA, nachster Schritt definiert")
    TONE_PACE = ("Tonfall & Tempo", 10, "Naturlich, klar, angemessenes Sprechtempo")
    COMPLIANCE = ("Compliance", 10, "Keine falschen Versprechen, DSGVO, Transparenz")


class CoachingHint:
    """A realtime coaching hint for the agent."""

    def __init__(self, category: str, message: str, priority: str = "info"):
        self.category = category
        self.message = message
        self.priority = priority
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "message": self.message,
            "priority": self.priority,
            "timestamp": self.timestamp,
        }


class CallQualityScore:
    """Quality score for a completed call."""

    def __init__(self):
        self.scores: Dict[str, int] = {}
        self.max_scores: Dict[str, int] = {}
        self.hints: List[CoachingHint] = []
        self.call_id: str = ""
        self.ended_at: str = ""

    @property
    def total_score(self) -> int:
        return sum(self.scores.values())

    @property
    def max_total(self) -> int:
        return sum(self.max_scores.values())

    @property
    def percentage(self) -> float:
        if self.max_total == 0:
            return 0.0
        return round((self.total_score / self.max_total) * 100, 1)

    @property
    def grade(self) -> str:
        pct = self.percentage
        if pct >= 90:
            return "A+"
        elif pct >= 80:
            return "A"
        elif pct >= 70:
            return "B"
        elif pct >= 60:
            return "C"
        elif pct >= 50:
            return "D"
        else:
            return "F"

    def to_dict(self) -> dict:
        return {
            "call_id": self.call_id,
            "total_score": self.total_score,
            "max_total": self.max_total,
            "percentage": self.percentage,
            "grade": self.grade,
            "scores": self.scores,
            "hints": [h.to_dict() for h in self.hints],
            "ended_at": self.ended_at,
        }


class AgentCoachService:
    """Realtime coaching and QA scoring for sales agents."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self._active_sessions: Dict[str, dict] = {}
        self._qa_history: List[CallQualityScore] = []

    def start_session(self, call_id: str) -> dict:
        """Start a coaching session for a call."""
        self._active_sessions[call_id] = {
            "call_id": call_id,
            "started_at": datetime.utcnow().isoformat(),
            "turn_count": 0,
            "user_turns": 0,
            "agent_turns": 0,
            "objections_detected": 0,
            "closing_attempts": 0,
            "questions_asked": 0,
            "hints_given": [],
            "transcript": [],
        }
        logger.info(f"Coaching session started: {call_id}")
        return {"status": "started", "call_id": call_id}

    def analyze_turn(self, call_id: str, speaker: str, text: str, stage: str) -> List[CoachingHint]:
        """Analyze a single turn and generate coaching hints."""
        if call_id not in self._active_sessions:
            self.start_session(call_id)

        session = self._active_sessions.get(call_id)
        if not session:
            return []

        session["turn_count"] += 1
        session["transcript"].append({"speaker": speaker, "text": text, "stage": stage})

        if speaker == "user":
            session["user_turns"] += 1
        else:
            session["agent_turns"] += 1

        hints = []
        text_lower = text.lower()

        if speaker == "agent":
            if session["turn_count"] <= 2 and not any(w in text_lower for w in ["hallo", "guten tag", "freut mich"]):
                hints.append(CoachingHint(
                    "greeting", "Begruung fehlt oder unpersonlich - Namen verwenden!", "warning"
                ))

            if "?" not in text and session["agent_turns"] >= 3:
                hints.append(CoachingHint(
                    "engagement", "Seit mehreren Turns keine Ruckfrage gestellt - aktiv nachfragen!", "info"
                ))

            if any(w in text_lower for w in ["kosten", "preis", "euro", "betrag"]):
                session["closing_attempts"] += 1

            if "?" in text:
                session["questions_asked"] += 1

            if len(text) > 300:
                hints.append(CoachingHint(
                    "brevity", "Antwort zu lang ({chars} Zeichen) - kurzer fassen!".format(chars=len(text)), "warning"
                ))

        else:
            if any(w in text_lower for w in ["zu teuer", "preis", "kosten", "budget"]):
                session["objections_detected"] += 1
                hints.append(CoachingHint(
                    "objection", "Preis-Einwand! ROI betonen: 'Was kostet eine vakante Stelle?'", "critical"
                ))

            if any(w in text_lower for w in ["kein interesse", "kein bedarf"]):
                hints.append(CoachingHint(
                    "objection", "Kein Interesse! Door-Opener: 'Wie schreiben Sie aktuell aus?'", "critical"
                ))

            if any(w in text_lower for w in ["ja", "gerne", "okay", "deal", "passt"]):
                hints.append(CoachingHint(
                    "closing", "Kaufsignal! Jetzt Abschluss versuchen: 'Premium oder Enterprise?'", "critical"
                ))

        for hint in hints:
            session["hints_given"].append(hint.to_dict())

        return hints

    def score_call(self, call_id: str, transcript: list = None) -> CallQualityScore:
        """Generate QA score for a completed call."""
        session = self._active_sessions.get(call_id)
        if not session:
            session = {
                "user_turns": 0,
                "agent_turns": 0,
                "objections_detected": 0,
                "closing_attempts": 0,
                "questions_asked": 0,
                "transcript": transcript or [],
            }

        score = CallQualityScore()
        score.call_id = call_id
        score.ended_at = datetime.utcnow().isoformat()

        user_turns = session.get("user_turns", len([t for t in session.get("transcript", []) if t.get("speaker") == "user"]))
        agent_turns = session.get("agent_turns", len([t for t in session.get("transcript", []) if t.get("speaker") == "agent"]))
        objections = session.get("objections_detected", 0)
        closings = session.get("closing_attempts", 0)
        questions = session.get("questions_asked", 0)

        total_turns = user_turns + agent_turns

        score.max_scores["greeting"] = QACriteria.GREETING_QUALITY[1]
        score.max_scores["needs_analysis"] = QACriteria.NEEDS_ANALYSIS[1]
        score.max_scores["product_knowledge"] = QACriteria.PRODUCT_KNOWLEDGE[1]
        score.max_scores["objection_handling"] = QACriteria.OBJECTION_HANDLING[1]
        score.max_scores["closing"] = QACriteria.CLOSING_ATTEMPT[1]
        score.max_scores["tone_pace"] = QACriteria.TONE_PACE[1]
        score.max_scores["compliance"] = QACriteria.COMPLIANCE[1]

        score.scores["greeting"] = min(QACriteria.GREETING_QUALITY[1], 10 if agent_turns > 0 else 0)
        score.scores["needs_analysis"] = min(QACriteria.NEEDS_ANALYSIS[1], questions * 5 if questions > 0 else 5)
        score.scores["product_knowledge"] = min(QACriteria.PRODUCT_KNOWLEDGE[1], 15 if agent_turns > 2 else 5)
        score.scores["objection_handling"] = min(QACriteria.OBJECTION_HANDLING[1], 20 if objections > 0 else 10)
        score.scores["closing"] = min(QACriteria.CLOSING_ATTEMPT[1], closings * 5 if closings > 0 else 0)
        score.scores["tone_pace"] = min(QACriteria.TONE_PACE[1], 10 if total_turns > 2 else 5)
        score.scores["compliance"] = QACriteria.COMPLIANCE[1]

        if objections == 0 and user_turns > 3:
            score.hints.append(CoachingHint(
                "coaching", "Keine Einwande erkannt - moglicherweise nicht genugend auf Kunden eingegangen.", "info"
            ))

        if closings == 0 and agent_turns > 5:
            score.hints.append(CoachingHint(
                "closing", "Kein Abschlussversuch bei {turns} Agent-Turns - aktiver closen!".format(turns=agent_turns), "warning"
            ))

        if questions == 0 and user_turns > 2:
            score.hints.append(CoachingHint(
                "engagement", "Keine Ruckfragen gestellt - Bedarfsanalyse vertiefen!", "warning"
            ))

        self._qa_history.append(score)
        self._active_sessions.pop(call_id, None)

        logger.info(f"QA Score for {call_id}: {score.total_score}/{score.max_total} ({score.percentage}%) - Grade: {score.grade}")
        return score

    def get_session_stats(self, call_id: str) -> dict:
        """Get realtime stats for an active coaching session."""
        session = self._active_sessions.get(call_id)
        if not session:
            return {"error": "Session not found"}

        return {
            "call_id": call_id,
            "turn_count": session["turn_count"],
            "user_turns": session["user_turns"],
            "agent_turns": session["agent_turns"],
            "objections_detected": session["objections_detected"],
            "closing_attempts": session["closing_attempts"],
            "questions_asked": session["questions_asked"],
            "hints_given": len(session["hints_given"]),
            "started_at": session["started_at"],
        }

    def get_qa_history(self, limit: int = 20) -> List[dict]:
        """Get recent QA scores."""
        return [s.to_dict() for s in self._qa_history[-limit:]]

    def get_avg_score(self) -> dict:
        """Get average QA score across all completed calls."""
        if not self._qa_history:
            return {"count": 0, "avg_percentage": 0, "avg_grade": "N/A"}

        avg_pct = sum(s.percentage for s in self._qa_history) / len(self._qa_history)
        avg_score = sum(s.total_score for s in self._qa_history) / len(self._qa_history)
        return {
            "count": len(self._qa_history),
            "avg_percentage": round(avg_pct, 1),
            "avg_total": round(avg_score, 1),
        }
