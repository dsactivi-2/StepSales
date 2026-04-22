#!/usr/bin/env python3
"""
Advanced Logging Configuration
Tracks every step, command, execution with detailed error logging
"""

import logging
import logging.handlers
import json
import os
from datetime import datetime
from pathlib import Path

# Create logs directory
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
LOG_FILE_MAIN = LOGS_DIR / "stepsales.log"
LOG_FILE_ERROR = LOGS_DIR / "errors.log"
LOG_FILE_AGENT = LOGS_DIR / "agent.log"
LOG_FILE_WEB = LOGS_DIR / "web_server.log"
LOG_FILE_WEBSOCKET = LOGS_DIR / "websocket.log"
LOG_FILE_JSON = LOGS_DIR / "events.jsonl"  # JSON log for parsing


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "function": record.funcName,
            "line": record.lineno,
            "module": record.module,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        # Add extra fields
        if hasattr(record, "user_action"):
            log_data["user_action"] = record.user_action
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Format logs with colors for console output"""

    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[41m",   # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)

        # Format: [LEVEL] timestamp | logger | message
        formatted = (
            f"{color}[{record.levelname:8s}]{self.RESET} "
            f"{record.created:.0f} | "
            f"{record.name:20s} | "
            f"{record.getMessage()}"
        )

        # Add exception info
        if record.exc_info:
            formatted += f"\n{self.format_exception(record)}"

        return formatted

    def format_exception(self, record: logging.LogRecord) -> str:
        """Format exception with traceback"""
        if not record.exc_info:
            return ""
        exc_type, exc_value, exc_tb = record.exc_info
        return (
            f"{self.COLORS['ERROR']}"
            f"EXCEPTION: {exc_type.__name__}: {exc_value}"
            f"{self.RESET}"
        )


def get_logger(name: str, level=logging.DEBUG) -> logging.Logger:
    """Get configured logger instance"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Console handler (colored output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    # JSON file handler (all events)
    json_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE_JSON,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    json_handler.setLevel(logging.DEBUG)
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)

    # Error file handler (errors only)
    error_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE_ERROR,
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s | %(exc_info)s"
    ))
    logger.addHandler(error_handler)

    # Module-specific file handler
    if "agent" in name.lower():
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE_AGENT,
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )
    elif "web" in name.lower():
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE_WEB,
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )
    elif "websocket" in name.lower():
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE_WEBSOCKET,
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )
    else:
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE_MAIN,
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )

    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s"
    ))
    logger.addHandler(file_handler)

    return logger


def log_step(logger: logging.Logger, step: str, details: dict = None):
    """Log a specific execution step"""
    msg = f"STEP: {step}"
    if details:
        msg += f" | {json.dumps(details)}"
    logger.info(msg, extra={"user_action": step})


def log_command(logger: logging.Logger, command: str, args: dict = None):
    """Log a command execution"""
    msg = f"COMMAND: {command}"
    if args:
        msg += f" | args={json.dumps(args)}"
    logger.info(msg)


def log_performance(logger: logging.Logger, operation: str, duration_ms: float):
    """Log performance metrics"""
    logger.info(
        f"PERFORMANCE: {operation}",
        extra={"duration_ms": duration_ms}
    )


def log_error_detailed(logger: logging.Logger, error: Exception, context: dict = None):
    """Log error with full context"""
    logger.error(
        f"ERROR: {error.__class__.__name__}: {str(error)}",
        exc_info=True,
        extra={"context": context}
    )


# Module loggers
logger_main = get_logger("stepsales")
logger_agent = get_logger("stepsales.agent")
logger_web = get_logger("stepsales.web")
logger_websocket = get_logger("stepsales.websocket")
logger_tools = get_logger("stepsales.tools")
logger_config = get_logger("stepsales.config")


if __name__ == "__main__":
    # Test logging
    logger_main.debug("Test DEBUG message")
    logger_main.info("Test INFO message")
    logger_main.warning("Test WARNING message")
    logger_main.error("Test ERROR message")

    log_step(logger_main, "Initialize System", {"version": "1.0.0"})
    log_command(logger_main, "health_check", {"timeout": 10})
    log_performance(logger_main, "api_call", 125.5)

    try:
        raise ValueError("Test exception")
    except Exception as e:
        log_error_detailed(logger_main, e, {"operation": "test"})

    print(f"\n✅ Logs saved to: {LOGS_DIR}")
    print(f"  - Main: {LOG_FILE_MAIN}")
    print(f"  - Errors: {LOG_FILE_ERROR}")
    print(f"  - Agent: {LOG_FILE_AGENT}")
    print(f"  - Web: {LOG_FILE_WEB}")
    print(f"  - WebSocket: {LOG_FILE_WEBSOCKET}")
    print(f"  - JSON Events: {LOG_FILE_JSON}")
