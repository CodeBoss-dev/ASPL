import json
import redis.asyncio as redis
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from src.config import REDIS_URL
from src.schemas import MonitoredSource, ChangeEvent

class MonitorService:
    def __init__(self):
        self.use_redis = False
        self.memory_store = {} # id -> MonitoredSource
        self.memory_events = [] # List[ChangeEvent]
        self.redis = None
        
        try:
            # Try to initialize Redis client, but don't connect yet
            self.redis = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
            self.use_redis = True
        except Exception as e:
            print(f"Redis init failed for MonitorService, using in-memory store: {e}")

    # --- MonitoredSource Methods ---

    async def add_source(self, source: MonitoredSource):
        """
        Add a new source to the monitor list.
        """
        if self.use_redis and self.redis:
            try:
                # Use model_dump_json for Pydantic v2
                data = source.model_dump_json()
                await self.redis.set(f"monitor:{source.id}", data)
                await self.redis.sadd("monitors:ids", str(source.id))
            except Exception as e:
                print(f"Redis add failed ({e}), using memory.")
                self.memory_store[source.id] = source
        else:
            self.memory_store[source.id] = source

    async def get_all_sources(self) -> List[MonitoredSource]:
        """
        Get all monitored sources.
        """
        sources = []
        if self.use_redis and self.redis:
            try:
                ids = await self.redis.smembers("monitors:ids")
                for _id in ids:
                    data = await self.redis.get(f"monitor:{_id}")
                    if data:
                        # Depending on the data form, might needs parsing
                        sources.append(MonitoredSource(**json.loads(data)))
            except Exception as e:
                print(f"Redis get_all failed ({e}), falling back to memory.")
                return list(self.memory_store.values())
        else:
            return list(self.memory_store.values())
        return sources

    async def delete_source(self, source_id: UUID):
        """
        Delete a monitored source.
        """
        if self.use_redis and self.redis:
            try:
                await self.redis.delete(f"monitor:{source_id}")
                await self.redis.srem("monitors:ids", str(source_id))
            except Exception as e:
                print(f"Redis delete failed ({e})")
                if source_id in self.memory_store:
                    del self.memory_store[source_id]
        else:
            if source_id in self.memory_store:
                del self.memory_store[source_id]

    # --- ChangeEvent Methods ---

    async def add_change_event(self, event: ChangeEvent):
        """
        Record a new change event.
        """
        if self.use_redis and self.redis:
            try:
                data = event.model_dump_json()
                # Use ZSET for time-based ordering
                # Score: timestamp, Member: JSON data
                timestamp = event.detected_at.timestamp()
                await self.redis.zadd("events:timeline", {data: timestamp})
            except Exception as e:
                print(f"Redis add_event failed ({e}), using memory.")
                self.memory_events.append(event)
        else:
            self.memory_events.append(event)
            # Sort helps if we append out of order, though usually we append in order.
            self.memory_events.sort(key=lambda x: x.detected_at)

    async def get_change_events(self, limit: int = 50, since_time: Optional[datetime] = None) -> List[ChangeEvent]:
        """
        Get change events, optionally filtered by time.
        """
        if self.use_redis and self.redis:
            try:
                if since_time:
                    # Get events strictly after since_time
                    min_score = since_time.timestamp() + 0.000001
                    max_score = "+inf"
                    raw_events = await self.redis.zrangebyscore("events:timeline", min=min_score, max=max_score)
                    if len(raw_events) > limit:
                        raw_events = raw_events[:limit]
                else:
                    raw_events = await self.redis.zrevrange("events:timeline", 0, limit - 1)
                
                events = [ChangeEvent(**json.loads(e)) for e in raw_events]
                return events

            except Exception as e:
                print(f"Redis get_events failed ({e}), falling back to memory.")
        
        # Memory Implementation
        filtered = self.memory_events
        if since_time:
            filtered = [e for e in filtered if e.detected_at > since_time]
        
        res = sorted(filtered, key=lambda x: x.detected_at, reverse=True)
        return res[:limit]

    # --- Subscriber Methods ---

    async def add_subscriber(self, sub: 'Subscriber'):
        if self.use_redis and self.redis:
            try:
                data = sub.model_dump_json()
                await self.redis.set(f"subscriber:{sub.id}", data)
                await self.redis.sadd("subscribers:ids", str(sub.id))
            except Exception as e:
                print(f"Redis add_subscriber failed: {e}")
                if not hasattr(self, 'memory_subscribers'): self.memory_subscribers = {}
                self.memory_subscribers[sub.id] = sub
        else:
            if not hasattr(self, 'memory_subscribers'): self.memory_subscribers = {}
            self.memory_subscribers[sub.id] = sub

    async def get_all_subscribers(self) -> List['Subscriber']:
        from src.schemas import Subscriber # Local import to avoid circular issues if any
        subs = []
        if self.use_redis and self.redis:
            try:
                ids = await self.redis.smembers("subscribers:ids")
                for _id in ids:
                    data = await self.redis.get(f"subscriber:{_id}")
                    if data:
                        subs.append(Subscriber(**json.loads(data)))
            except Exception as e:
                print(f"Redis get_subscribers failed: {e}")
                if not hasattr(self, 'memory_subscribers'): self.memory_subscribers = {}
                return list(self.memory_subscribers.values())
        else:
            if not hasattr(self, 'memory_subscribers'): self.memory_subscribers = {}
            return list(self.memory_subscribers.values())
        return subs

    async def update_subscriber(self, sub: 'Subscriber'):
        # Same as add since it overwrites
        await self.add_subscriber(sub)

    async def delete_subscriber(self, sub_id: UUID):
        if self.use_redis and self.redis:
            try:
                await self.redis.delete(f"subscriber:{sub_id}")
                await self.redis.srem("subscribers:ids", str(sub_id))
            except Exception as e:
                print(f"Redis delete_subscriber failed: {e}")
                if hasattr(self, 'memory_subscribers') and sub_id in self.memory_subscribers:
                    del self.memory_subscribers[sub_id]
        else:
            if hasattr(self, 'memory_subscribers') and sub_id in self.memory_subscribers:
                del self.memory_subscribers[sub_id]

    async def close(self):
        if self.redis:
            await self.redis.close()
