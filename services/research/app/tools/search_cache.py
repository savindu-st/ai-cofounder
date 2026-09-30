"""Redis and In-Memory Search Cache with 24-Hour TTL.

Normalizes query strings, generates deterministic SHA-256 keys, and caches
search results to prevent redundant Tavily API calls and speed up iterative re-planning.
Gracefully degrades to an in-memory dictionary cache if Redis is unavailable.
"""

import os
import json
import hashlib
import logging
from typing import List, Optional, Dict, Any
from services.research.app.tools.web_search import SearchResult

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 86400  # 24 hours


class SearchCache:
    """Redis-backed search cache with in-memory fallback and 24-hour TTL."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        use_in_memory_fallback: bool = True
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.ttl = ttl_seconds
        self.use_in_memory_fallback = use_in_memory_fallback
        self._redis_client = None
        self._redis_disabled = False
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    def _get_redis(self):
        """Lazy initialization of async Redis client."""
        if self._redis_disabled:
            return None

        if self._redis_client is None:
            try:
                import redis.asyncio as aioredis
                self._redis_client = aioredis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0
                )
            except Exception as e:
                logger.warning(f"[SearchCache] Could not initialize Redis client ({e}). Using in-memory fallback.")
                self._redis_disabled = True
                return None
        return self._redis_client

    @staticmethod
    def normalize_query(query: str) -> str:
        """Normalizes query by lowercasing, stripping punctuation, and sorting tokens.

        Ensures 'AI market research' and 'research AI market' map to the identical cache entry.
        """
        if not query:
            return ""
        # Lowercase and clean tokens
        tokens = [token.strip().lower() for token in query.split() if token.strip()]
        # Sort tokens alphabetically to make order invariant
        tokens.sort()
        return " ".join(tokens)

    @classmethod
    def hash_key(cls, query: str) -> str:
        """Generates SHA-256 hash key from normalized query."""
        normalized = cls.normalize_query(query)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"search:sha256:{digest}"

    async def get(self, query: str) -> Optional[List[SearchResult]]:
        """Retrieves cached SearchResult list if present and not expired."""
        key = self.hash_key(query)

        # 1. Try Redis
        client = self._get_redis()
        if client is not None:
            try:
                raw_json = await client.get(key)
                if raw_json:
                    data = json.loads(raw_json)
                    return [SearchResult(**item) for item in data]
            except Exception as e:
                logger.debug(f"[SearchCache] Redis get failed for key {key}: {e}. Checking memory fallback.")
                self._redis_disabled = True

        # 2. Try In-Memory Fallback
        if self.use_in_memory_fallback and key in self._memory_cache:
            import time
            entry = self._memory_cache[key]
            if time.time() < entry["expires_at"]:
                return [SearchResult(**item) for item in entry["data"]]
            else:
                del self._memory_cache[key]

        return None

    async def set(
        self,
        query: str,
        results: List[SearchResult],
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Stores SearchResult list in cache with TTL."""
        if not results:
            return

        key = self.hash_key(query)
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl
        serialized = [
            {
                "title": r.title,
                "url": r.url,
                "content": r.content,
                "score": r.score,
                "is_fallback": r.is_fallback,
                "metadata": r.metadata
            }
            for r in results
        ]

        # 1. Try Redis
        client = self._get_redis()
        if client is not None:
            try:
                raw_json = json.dumps(serialized)
                await client.set(key, raw_json, ex=ttl)
                return
            except Exception as e:
                logger.warning(f"[SearchCache] Redis set failed for key {key}: {e}. Storing in memory fallback.")
                self._redis_disabled = True

        # 2. In-Memory Fallback
        if self.use_in_memory_fallback:
            import time
            self._memory_cache[key] = {
                "data": serialized,
                "expires_at": time.time() + ttl
            }

    async def clear(self) -> None:
        """Clears memory cache and disconnects Redis client."""
        self._memory_cache.clear()
        if self._redis_client is not None:
            try:
                await self._redis_client.close()
            except Exception:
                pass
            self._redis_client = None
