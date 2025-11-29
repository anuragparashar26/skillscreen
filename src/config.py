"""Configuration and environment helpers."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment."""
    supabase_url: Optional[str]
    supabase_anon_key: Optional[str]


def get_settings() -> Settings:
    """Load settings from environment and return a Settings object.

    Values can be provided via a `.env` file or environment variables.
    """
    return Settings(
        supabase_url=os.environ.get("SUPABASE_URL"),
        supabase_anon_key=os.environ.get("SUPABASE_ANON_KEY"),
    )
