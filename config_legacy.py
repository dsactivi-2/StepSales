#!/usr/bin/env python3
"""
Configuration management for Stepsales Telesales Agent
"""

import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass
class OpenAIConfig:
    """OpenAI Realtime API Configuration"""
    api_key: str
    model: str = "gpt-realtime-1.5"
    voice: str = "shimmer"  # Warm, conversational tone
    max_output_tokens: int = 512
    instructions_template: str = ""
    temperature: float = 0.7


@dataclass
class StepstoneConfig:
    """Stepstone Integration Configuration"""
    server_path: Optional[str] = None  # Path to mcp-stepstone server
    default_zip_code: str = "40210"  # Düsseldorf
    default_radius: int = 15  # km
    request_timeout: int = 10  # seconds


@dataclass
class TelesalesConfig:
    """Telesales Agent Configuration"""
    # Call settings
    max_call_duration: int = 900  # 15 minutes
    vad_threshold: float = 0.5
    silence_duration_ms: int = 1200

    # Language & Voice
    language: str = "de"
    voice_speed: float = 1.0

    # CRM Integration
    crm_enabled: bool = False
    crm_api_key: Optional[str] = None

    # Persistence
    data_dir: str = "./data"
    save_transcripts: bool = True
    transcript_dir: str = "./data/transcripts"

    # Logging
    log_level: str = "INFO"


@dataclass
class RuntimeConfig:
    """Runtime/web server configuration"""
    host: str = "0.0.0.0"
    port: int = 8000


class Config:
    """Master configuration loader"""

    openai = OpenAIConfig(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("OPENAI_MODEL", "gpt-realtime-1.5"),
        voice=os.getenv("VOICE", "shimmer"),
        max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "512")),
        temperature=float(os.getenv("TEMPERATURE", "0.7")),
    )

    stepstone = StepstoneConfig(
        server_path=os.getenv("STEPSTONE_SERVER_PATH"),
        default_zip_code=os.getenv("DEFAULT_ZIP_CODE", "40210"),
        default_radius=int(os.getenv("DEFAULT_RADIUS", "15")),
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "10")),
    )

    telesales = TelesalesConfig(
        max_call_duration=int(os.getenv("MAX_CALL_DURATION", "900")),
        crm_enabled=os.getenv("CRM_ENABLED", "false").lower() == "true",
        crm_api_key=os.getenv("CRM_API_KEY"),
        data_dir=os.getenv("DATA_DIR", "./data"),
        save_transcripts=os.getenv("SAVE_TRANSCRIPTS", "true").lower() == "true",
        transcript_dir=os.getenv("TRANSCRIPT_DIR", "./data/transcripts"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

    runtime = RuntimeConfig(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )

    @classmethod
    def validate(cls) -> bool:
        """Validate critical configuration and prepare runtime paths"""
        if not cls.openai.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        if cls.runtime.port <= 0 or cls.runtime.port > 65535:
            raise ValueError(f"Invalid PORT configured: {cls.runtime.port}")

        if cls.telesales.save_transcripts:
            transcript_path = Path(cls.telesales.transcript_dir)
            transcript_path.mkdir(parents=True, exist_ok=True)

        data_path = Path(cls.telesales.data_dir)
        data_path.mkdir(parents=True, exist_ok=True)

        return True
