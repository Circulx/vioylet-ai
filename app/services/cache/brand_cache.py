from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import get_logger
from app.graph.models.layer2_models import BrandIntelligenceOutput

logger = get_logger(__name__)


class BrandCacheService:
    """Redis cache for brand intelligence output (Layer 2)."""

    DEFAULT_TTL_SECONDS = 60 * 60 * 24  # 24 hours

    def __init__(self, redis_url: str | None = None) -> None:
        settings = get_settings()
        self._redis_url = redis_url or settings.redis_url
        self._redis: redis.Redis | None = None

    async def _client(self) -> redis.Redis | None:
        if self._redis is None:
            try:
                self._redis = redis.from_url(self._redis_url, decode_responses=True)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to connect to Redis: {e}")
                return None
        return self._redis

    def _key(self, brand_id: str, data_version: int | str | None) -> str:
        version = data_version or "current"
        return f"brand_intel:{brand_id}:{version}"

    async def get(
        self, brand_id: str, data_version: int | str | None = None
    ) -> BrandIntelligenceOutput | None:
        client = await self._client()
        if not client:
            return None
        try:
            raw = await client.get(self._key(brand_id, data_version))
            if not raw:
                return None
            return BrandIntelligenceOutput.model_validate_json(raw)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Brand cache get failed: {e}")
            return None

    async def set(
        self,
        brand_id: str,
        output: BrandIntelligenceOutput,
        data_version: int | str | None = None,
        ttl: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        client = await self._client()
        if not client:
            return
        try:
            await client.set(
                self._key(brand_id, data_version),
                output.model_dump_json(),
                ex=ttl,
            )
            logger.info("brand_cache.set", brand_id=brand_id, data_version=data_version)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Brand cache set failed: {e}")

    async def invalidate(self, brand_id: str, data_version: int | str | None = None) -> None:
        client = await self._client()
        if not client:
            return
        try:
            await client.delete(self._key(brand_id, data_version))
            logger.info("brand_cache.invalidate", brand_id=brand_id, data_version=data_version)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Brand cache invalidate failed: {e}")
