"""Application configuration."""

import os
from dataclasses import dataclass, field

ENV_PATH = r"D:\Punokawan V2\.env"


def _load_env() -> dict:
    config = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    config[key.strip()] = val.strip()
    return config


_env = _load_env()


@dataclass
class Settings:
    APP_NAME: str = "Punokawan V2 API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    # JWT
    JWT_SECRET: str = field(default_factory=lambda: _env.get("JWT_SECRET", "punokawan-v2-secret-change-me"))
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # Database
    DATABASE_PATH: str = r"D:\Punokawan V2\web\data\signals.db"

    # MCP Servers
    MCP_MARKET_ANALYSIS_URL: str = "http://127.0.0.1:8082/sse"
    MCP_LEARNING_URL: str = "http://127.0.0.1:8083/sse"
    MCP_RISK_URL: str = "http://127.0.0.1:8084/sse"
    MCP_METATRADER_URL: str = "http://127.0.0.1:8081/sse"

    # Trial
    TRIAL_DAYS: int = 14

    # Signal delay for free users (seconds)
    FREE_SIGNAL_DELAY: int = 300

    # CORS
    CORS_ORIGINS: list = field(default_factory=lambda: ["*"])


settings = Settings()
