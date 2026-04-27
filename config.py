from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when required environment variables are absent or empty."""


# Keys that must be present and non-empty before the app starts.
_REQUIRED: tuple[str, ...] = ("OPENAI_API_KEY",)


@dataclass(frozen=True)
class AppConfig:
    openai_api_key: str
    serper_api_key: str
    model_name: str


def load_config(env_file: str = ".env") -> AppConfig:
    """Load .env, validate required keys, and return a frozen AppConfig.

    Raises:
        ConfigError: one or more required keys are missing or empty.
    """
    load_dotenv(env_file, override=False)

    missing = [k for k in _REQUIRED if not os.getenv(k)]
    if missing:
        raise ConfigError(
            f"Missing required environment variable(s): {', '.join(missing)}.\n"
            "Set them in your .env file or export them before running agent_fix."
        )

    return AppConfig(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        serper_api_key=os.getenv("SERPER_API_KEY", ""),
        model_name=os.getenv("MODEL_NAME", "gpt-4o-mini"),
    )
