"""Configuration and environment helpers."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    google_api_key: Optional[str]
    supabase_url: Optional[str]
    supabase_anon_key: Optional[str]


def get_settings() -> Settings:
    """Load settings from environment and return a Settings object.

    Values can be provided via a `.env` file or environment variables.
    """
    return Settings(
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
        supabase_url=os.environ.get("SUPABASE_URL"),
        supabase_anon_key=os.environ.get("SUPABASE_ANON_KEY"),
    )


def set_google_api_key_in_env(key: Optional[str]) -> None:
    """Set the Google API key into os.environ for downstream libraries if provided.

    If `key` is None this is a no-op.
    """
    if key:
        os.environ["GOOGLE_API_KEY"] = key
