import json
import redis.asyncio as redis
from typing import Optional
from src.config import REDIS_URL
from src.schemas import ArticleSchema
import os

class CacheService:
    def __init__(self):
        self.use_redis = False
        self.memory_cache = {}
        self.redis = None
        
        try:
            # Try to initialize Redis client, but don't connect yet
            self.redis = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
            self.use_redis = True
        except Exception as e:
            print(f"Redis init failed, using in-memory cache: {e}")

    async def get_article(self, url: str) -> Optional[ArticleSchema]:
        """
        Retrieve article from cache (Redis or Memory).
        """
        if self.use_redis and self.redis:
            try:
                data = await self.redis.get(url)
                if data:
                    return ArticleSchema(**json.loads(data))
            except Exception as e:
                print(f"Redis get failed ({e}), falling back to memory.")
                # Fallback to memory if Redis fails during operation
                if url in self.memory_cache:
                    return self.memory_cache[url]
        else:
            if url in self.memory_cache:
                return self.memory_cache[url]
                
        return None

    async def set_article(self, url: str, article: ArticleSchema):
        """
        Save article to cache (Redis or Memory).
        """
        if self.use_redis and self.redis:
            try:
                data = article.model_dump_json()
                await self.redis.set(url, data, ex=86400) # 24h TTL
            except Exception as e:
                print(f"Redis set failed ({e}), using memory.")
                self.memory_cache[url] = article
        else:
            self.memory_cache[url] = article

    async def close(self):
        if self.redis:
            await self.redis.close()
