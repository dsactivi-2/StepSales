"""
Unified Configuration Loader for Stepsales Production System
Loads all provider keys, service settings, and runtime params from environment/.env
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

_ENV_DIR = Path(__file__).resolve().parent.parent / "environment"
load_dotenv(_ENV_DIR / ".env")
load_dotenv()


@dataclass
class TelnyxConfig:
    api_key: str = field(default_factory=lambda: os.getenv("TELNYX_API_KEY", ""))
    connection_id: str = field(default_factory=lambda: os.getenv("TELNYX_CONNECTION_ID", ""))
    from_number: str = field(default_factory=lambda: os.getenv("TELNYX_FROM_NUMBER", ""))
    webhook_secret: str = field(default_factory=lambda: os.getenv("TELNYX_WEBHOOK_SECRET", ""))
    api_base: str = "https://api.telnyx.com/v2"


@dataclass
class DeepgramConfig:
    api_key: str = field(default_factory=lambda: os.getenv("DEEPGRAM_API_KEY", ""))
    model: str = "nova-3"
    language: str = "de"
    smart_format: bool = True
    interim_results: bool = True
    eot_threshold: float = 0.5
    eot_timeout_ms: int = 1500
    sample_rate: int = 16000
    encoding: str = "linear16"
    channels: int = 1
    api_base: str = "wss://api.deepgram.com/v1/listen"


@dataclass
class ElevenLabsConfig:
    api_key: str = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY", ""))
    voice_id: str = field(default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", ""))
    model_id: str = "eleven_multilingual_v2"
    stability: float = 0.68
    similarity_boost: float = 0.78
    style: float = 0.22
    speed: float = 0.96
    use_speaker_boost: bool = True
    api_base: str = "https://api.elevenlabs.io/v1"


@dataclass
class OpenAIConfig:
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    model: str = "gpt-4o"
    temperature: float = 0.8
    max_tokens: int = 512


@dataclass
class StripeConfig:
    api_key: str = field(default_factory=lambda: os.getenv("STRIPE_API_KEY", ""))
    webhook_secret: str = field(default_factory=lambda: os.getenv("STRIPE_WEBHOOK_SECRET", ""))
    currency: str = "eur"
    default_tax_rate: float = 0.19
    api_base: str = "https://api.stripe.com/v1"


@dataclass
class PersistenceConfig:
    db_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///data/stepsales.db"))
    transcript_dir: str = field(default_factory=lambda: os.getenv("TRANSCRIPT_DIR", "data/transcripts"))


@dataclass
class RuntimeConfig:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8010"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


class AppConfig:
    telnyx = TelnyxConfig()
    deepgram = DeepgramConfig()
    elevenlabs = ElevenLabsConfig()
    openai = OpenAIConfig()
    stripe = StripeConfig()
    persistence = PersistenceConfig()
    runtime = RuntimeConfig()

    @classmethod
    def validate(cls) -> list[str]:
        errors = []
        if not cls.telnyx.api_key:
            errors.append("TELNYX_API_KEY not set")
        if not cls.telnyx.connection_id:
            errors.append("TELNYX_CONNECTION_ID not set")
        if not cls.deepgram.api_key:
            errors.append("DEEPGRAM_API_KEY not set")
        if not cls.elevenlabs.api_key:
            errors.append("ELEVENLABS_API_KEY not set")
        if not cls.elevenlabs.voice_id:
            errors.append("ELEVENLABS_VOICE_ID not set")
        if not cls.openai.api_key:
            errors.append("OPENAI_API_KEY not set")
        if not cls.stripe.api_key:
            errors.append("STRIPE_API_KEY not set")
        Path(cls.persistence.transcript_dir).mkdir(parents=True, exist_ok=True)
        return errors
