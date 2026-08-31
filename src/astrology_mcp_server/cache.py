"""Result caching functionality for Astrology MCP Server.

This module handles in-memory caching of tool results with TTL expiration.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any
from threading import Lock


# Result cache configuration
RESULT_CACHE_TTL_SECONDS = 3600  # 1 hour

# In-memory cache for tool results
# Format: { result_id: { "data": ..., "created_at": timestamp, "preview": ... } }
_result_cache: dict[str, dict[str, Any]] = {}
_result_cache_lock = Lock()


def _generate_result_id(payload: dict[str, Any], prefix: str) -> str:
    """Generate a deterministic result ID based on payload hash.
    
    Args:
        payload: Dictionary containing the tool parameters
        prefix: String prefix for the result ID (e.g., "nc" for natal chart)
    
    Returns:
        A deterministic hash string starting with the prefix
    """
    # Create a hash from the payload to get consistent IDs for same inputs
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    hash_digest = hashlib.sha256(payload_str.encode()).hexdigest()[:8]
    return f"{prefix}_{hash_digest}"


def _cache_result(result_id: str, data: dict[str, Any], preview: dict[str, Any]) -> None:
    """Cache a result with its preview.
    
    Args:
        result_id: Unique identifier for this result
        data: Full result data to cache
        preview: Summary/preview data for quick decisions
    """
    with _result_cache_lock:
        _result_cache[result_id] = {
            "data": data,
            "preview": preview,
            "created_at": time.time(),
        }


def _get_cached_result(result_id: str) -> dict[str, Any] | None:
    """Get a cached result by ID.
    
    Args:
        result_id: Unique identifier for the cached result
    
    Returns:
        The cached result data if found and not expired, None otherwise
    """
    with _result_cache_lock:
        entry = _result_cache.get(result_id)
        if entry is None:
            return None
        
        # Check TTL
        if time.time() - entry["created_at"] > RESULT_CACHE_TTL_SECONDS:
            # Expired, remove it
            del _result_cache[result_id]
            return None
        
        return entry


def _cleanup_expired_results() -> int:
    """Remove expired results from cache.
    
    Returns:
        Number of results removed
    """
    current_time = time.time()
    removed = 0
    
    with _result_cache_lock:
        expired_ids = [
            rid for rid, entry in _result_cache.items()
            if current_time - entry["created_at"] > RESULT_CACHE_TTL_SECONDS
        ]
        
        for rid in expired_ids:
            del _result_cache[rid]
            removed += 1
    
    return removed
