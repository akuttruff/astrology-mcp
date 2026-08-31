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

# Cache diagnostics
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "expired": 0,
    "total_cached": 0,
}


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
    try:
        from astrology_mcp_server import logger
    except ImportError:
        # Fallback if logger not available (e.g., in tests)
        import logging
        logger = logging.getLogger(__name__)
    
    with _result_cache_lock:
        # Clean up any existing entry first
        if result_id in _result_cache:
            del _result_cache[result_id]
        
        _result_cache[result_id] = {
            "data": data,
            "preview": preview,
            "created_at": time.time(),
        }
        _cache_stats["total_cached"] += 1
        
    logger.info(f"Cached result: {result_id} (age: 0s, TTL: {RESULT_CACHE_TTL_SECONDS}s)")


def _get_cached_result(result_id: str) -> dict[str, Any] | None:
    """Get a cached result by ID.

    Args:
        result_id: Unique identifier for the cached result

    Returns:
        The cached result data if found and not expired, None otherwise
    """
    try:
        from astrology_mcp_server import logger
    except ImportError:
        import logging
        logger = logging.getLogger(__name__)

    current_time = time.time()
    
    with _result_cache_lock:
        entry = _result_cache.get(result_id)
        
        if entry is None:
            _cache_stats["misses"] += 1
            logger.debug(f"Cache miss: {result_id} (not found)")
            return None

        # Check TTL
        age = current_time - entry["created_at"]
        
        if age > RESULT_CACHE_TTL_SECONDS:
            # Expired, remove it
            del _result_cache[result_id]
            _cache_stats["expired"] += 1
            _cache_stats["misses"] += 1
            logger.warning(f"Cache miss: {result_id} (expired after {age:.0f}s, TTL: {RESULT_CACHE_TTL_SECONDS}s)")
            return None
        
        _cache_stats["hits"] += 1
        logger.debug(f"Cache hit: {result_id} (age: {age:.0f}s)")
        return entry


def _cleanup_expired_results() -> int:
    """Remove expired results from cache.

    Returns:
        Number of results removed
    """
    try:
        from astrology_mcp_server import logger
    except ImportError:
        import logging
        logger = logging.getLogger(__name__)

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
            logger.info(f"Cleaned up expired cache entry: {rid}")

    if removed > 0:
        logger.info(f"Cache cleanup: removed {removed} expired entries")

    return removed


def _get_cache_stats() -> dict[str, int]:
    """Get cache statistics for debugging.

    Returns:
        Dictionary with cache metrics
    """
    with _result_cache_lock:
        return {
            "hits": _cache_stats["hits"],
            "misses": _cache_stats["misses"],
            "expired": _cache_stats["expired"],
            "total_cached": len(_result_cache),
        }


def _get_cached_result_with_reason(result_id: str) -> tuple[dict[str, Any] | None, str]:
    """Get a cached result by ID with detailed reason for miss.

    Returns:
        Tuple of (entry, reason)
        - entry: The cached data if found and not expired
        - reason: "hit", "not_found", or "expired"
    """
    try:
        from astrology_mcp_server import logger
    except ImportError:
        import logging
        logger = logging.getLogger(__name__)

    current_time = time.time()

    with _result_cache_lock:
        entry = _result_cache.get(result_id)

        if entry is None:
            _cache_stats["misses"] += 1
            logger.debug(f"Cache miss: {result_id} (not found)")
            return None, "not_found"

        # Check TTL
        age = current_time - entry["created_at"]

        if age > RESULT_CACHE_TTL_SECONDS:
            # Expired, remove it
            del _result_cache[result_id]
            _cache_stats["expired"] += 1
            _cache_stats["misses"] += 1
            logger.warning(f"Cache miss: {result_id} (expired after {age:.0f}s, TTL: {RESULT_CACHE_TTL_SECONDS}s)")
            return None, "expired"

        _cache_stats["hits"] += 1
        logger.debug(f"Cache hit: {result_id} (age: {age:.0f}s)")
        return entry, "hit"


def _clear_cache() -> None:
    """Clear all cache entries. Use for testing or emergency reset."""
    try:
        from astrology_mcp_server import logger
    except ImportError:
        import logging
        logger = logging.getLogger(__name__)

    with _result_cache_lock:
        count = len(_result_cache)
        _result_cache.clear()
        logger.warning(f"Cleared cache: removed {count} entries")
