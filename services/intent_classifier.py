"""
LLM-Based Intent Classifier
Replaces heuristic keyword-matching with OpenAI function calling
to classify user intent in German sales conversations.
"""

import logging
from enum import Enum
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config.settings import AppConfig

logger = logging.getLogger("stepsales.intent_classifier")


class IntentType(str, Enum):
    INTEREST = "interest"
    OBJECTION_PRICE = "objection_price"
    OBJECTION_TIME = "objection_time"
    OBJECTION_INTEREST = "objection_interest"
    QUESTION = "question"
    GOODBYE = "goodbye"
    CALLBACK = "callback"
    DECISION_POSITIVE = "decision_positive"
    DECISION_NEEDS_TIME = "decision_needs_time"
    INFO_REQUEST = "info_request"


class IntentClassification(BaseModel):
    """Structured intent classification for German sales calls."""

    intent: IntentType = Field(description="Primary user intent category")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    keywords: list[str] = Field(default_factory=list, description="Key phrases that triggered this classification")
    needs_followup: bool = Field(description="Whether this intent requires a follow-up action")
    suggested_stage: Optional[str] = Field(description="Recommended next conversation stage")


INTENT_PROMPT = """Du analysierst die Absicht eines Kunden in einem deutschen Telesales-Gespräch.

KONTEXT:
- Verkauf von Multiposting-Stellenanzeigen auf StepStone und Indeed
- Aktueller Gesprächsstand: {current_stage}
- Letzte Agent-Antwort: {agent_response}
- Kunden-Antwort: {user_input}

KLASSIFIZIERUNG:
- interest: Kunde zeigt Interesse, stellt Fragen zum Produkt
- objection_price: Kunde lehnt wegen Preis/Kosten/Budget ab
- objection_time: Kunde hat keine Zeit oder will später sprechen
- objection_interest: Kunde hat kein Interesse oder keinen Bedarf
- question: Kunde stellt sachliche Fragen
- goodbye: Kunde will auflegen oder verabschiedet sich
- callback: Kunde will zurückgerufen werden
- decision_positive: Kunde stimmt zu oder will buchen
- decision_needs_time: Kunde muss nachdenken oder sich absprechen
- info_request: Kunde will mehr Informationen (Email, Unterlagen)

Antworte NUR mit der JSON-Struktur."""


class IntentClassifier:
    """LLM-based intent classifier for sales conversations."""

    def __init__(self, config=None):
        self.config = config or AppConfig
        self.llm = ChatOpenAI(
            model=self.config.openai.model,
            temperature=0.1,
            max_tokens=200,
            api_key=self.config.openai.api_key,
        ).with_structured_output(IntentClassification)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", INTENT_PROMPT),
            ("human", "{user_input}"),
        ])

        self.chain = self.prompt | self.llm

    async def classify(self, user_input: str, current_stage: str, agent_response: str = "") -> IntentClassification:
        """Classify user intent using LLM structured output."""
        if not user_input or not user_input.strip():
            return IntentClassification(
                intent=IntentType.INFO_REQUEST,
                confidence=0.0,
                keywords=[],
                needs_followup=False,
                suggested_stage=current_stage,
            )

        try:
            result = await self.chain.ainvoke({
                "current_stage": current_stage,
                "agent_response": agent_response[:200] if agent_response else "Keine vorherige Antwort",
                "user_input": user_input,
            })

            logger.info(f"Intent: {result.intent.value} (confidence={result.confidence:.2f}, keywords={result.keywords})")
            return result

        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return IntentClassification(
                intent=IntentType.INFO_REQUEST,
                confidence=0.5,
                keywords=[],
                needs_followup=False,
                suggested_stage=current_stage,
            )

    def intent_to_stage(self, intent: IntentClassification) -> str:
        """Map intent classification to next conversation stage."""
        stage_map = {
            IntentType.INTEREST: None,
            IntentType.OBJECTION_PRICE: "objection",
            IntentType.OBJECTION_TIME: "objection",
            IntentType.OBJECTION_INTEREST: "followup",
            IntentType.QUESTION: None,
            IntentType.GOODBYE: "summary",
            IntentType.CALLBACK: "followup",
            IntentType.DECISION_POSITIVE: "close",
            IntentType.DECISION_NEEDS_TIME: "followup",
            IntentType.INFO_REQUEST: "offer",
        }

        if intent.suggested_stage:
            return intent.suggested_stage

        return stage_map.get(intent.intent)
