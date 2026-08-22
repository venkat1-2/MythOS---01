"""
backend/event_cache.py
======================
Simple SQLite-based TTL cache for global risk events output by the
provider + enrichment pipeline.

Keyed by a deterministic SHA-256 hash of the business exposure profile
(materials + supplier_countries + currency_exposure, sorted).
Persisted to backend/.cache/events.db to survive server restarts during demos.
"""

import os
import json
import sqlite3
import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Default 6 hours TTL (21600 seconds)
DEFAULT_TTL_SECONDS = 6 * 3600

# Path to local sqlite cache
_CACHE_DIR = Path(__file__).resolve().parent / ".cache"
_DB_PATH = _CACHE_DIR / "events.db"


def _get_ttl_seconds() -> int:
    try:
        return int(os.environ.get("EVENTS_CACHE_TTL_SECONDS", DEFAULT_TTL_SECONDS))
    except ValueError:
        logger.warning(
            "[event_cache] Invalid EVENTS_CACHE_TTL_SECONDS in env, defaulting to %d",
            DEFAULT_TTL_SECONDS,
        )
        return DEFAULT_TTL_SECONDS


def _init_db() -> None:
    """Ensure .cache directory exists and create events table if needed."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS event_cache (
                cache_key TEXT PRIMARY KEY,
                events_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
            """
        )
        conn.commit()


def cache_key_for_exposure(exposure: Dict[str, Any]) -> str:
    """
    Generate a deterministic SHA-256 cache key from an exposure profile.
    Considers sorted lowercase materials, supplier_countries, and currency_exposure.
    """
    materials = sorted({str(m).strip().lower() for m in exposure.get("materials", []) if m})
    countries = sorted({str(c).strip().lower() for c in exposure.get("supplier_countries", []) if c})
    currencies = sorted({str(c).strip().lower() for c in exposure.get("currency_exposure", []) if c})

    normalized = {
        "materials": materials,
        "supplier_countries": countries,
        "currency_exposure": currencies,
    }
    raw_str = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def get_cached_events(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve cached events if key exists and has not expired.
    Returns None if cache miss or expired.
    """
    _init_db()
    now = time.time()
    try:
        with sqlite3.connect(_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT events_json, expires_at FROM event_cache WHERE cache_key = ?",
                (cache_key,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            events_json, expires_at = row
            if now > expires_at:
                # Clean up expired entry
                cursor.execute("DELETE FROM event_cache WHERE cache_key = ?", (cache_key,))
                conn.commit()
                logger.info("[event_cache] Cache expired for key: %s", cache_key[:12])
                return None

            logger.info("[event_cache] Cache HIT for key: %s", cache_key[:12])
            return json.loads(events_json)
    except Exception as e:
        logger.error("[event_cache] Error reading from cache: %s", e)
        return None


def set_cached_events(cache_key: str, events: List[Dict[str, Any]]) -> None:
    """
    Store events list in SQLite cache with configured TTL.
    """
    _init_db()
    now = time.time()
    ttl = _get_ttl_seconds()
    expires_at = now + ttl
    events_json = json.dumps(events)

    try:
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO event_cache (cache_key, events_json, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (cache_key, events_json, now, expires_at),
            )
            conn.commit()
            logger.info(
                "[event_cache] Cached %d events for key: %s (TTL: %ds)",
                len(events),
                cache_key[:12],
                ttl,
            )
    except Exception as e:
        logger.error("[event_cache] Error writing to cache: %s", e)
