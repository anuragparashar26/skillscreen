"""Supabase client wrapper.

This module provides a thin wrapper around the Supabase client. Operations
are optional: if SUPABASE_URL or anon key are missing the functions raise
ValueError and callers should handle it gracefully.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.config import get_settings


def create_supabase_client():
    settings = get_settings()
    url = settings.supabase_url
    key = settings.supabase_anon_key
    if not url or not key:
        raise ValueError("Supabase URL or anon key not configured")
    try:
        from supabase import create_client

        client = create_client(url, key)
        return client
    except Exception as e:
        raise
