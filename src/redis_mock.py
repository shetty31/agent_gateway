from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, DefaultDict, Optional


class RedisMock:
    """In-memory RPM tracker with per-equipment isolation and asyncio-safe mutations."""

    def __init__(self, window_seconds: int = 60, max_requests: int = 60, gc_interval_seconds: float = 10.0) -> None:
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.gc_interval_seconds = gc_interval_seconds
        self._state: DefaultDict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._gc_task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        if self._gc_task is None or self._gc_task.done():
            self._gc_task = asyncio.create_task(self._gc_loop())

    async def stop(self) -> None:
        if self._gc_task is not None:
            self._gc_task.cancel()
            try:
                await self._gc_task
            except asyncio.CancelledError:
                pass
            self._gc_task = None

    async def check_breach(self, equipment_id: str, payload: Optional[dict[str, Any]] = None) -> bool:
        """Return True when the equipment_id exceeds the allowed RPM window."""
        if not equipment_id:
            return False

        if isinstance(payload, dict) and payload.get("critical_alert") is True:
            return False

        async with self._lock:
            now = datetime.now(timezone.utc).timestamp()
            cutoff = now - self.window_seconds
            timestamps = self._state.get(equipment_id)

            if timestamps is None:
                self._state[equipment_id] = [now]
                return False

            filtered = [ts for ts in timestamps if ts >= cutoff]
            self._state[equipment_id] = filtered

            if not filtered:
                self._state[equipment_id] = [now]
                return False

            if len(filtered) >= self.max_requests:
                return True

            filtered.append(now)
            self._state[equipment_id] = filtered
            return False

    async def cleanup_stale_entries(self) -> None:
        async with self._lock:
            now = datetime.now(timezone.utc).timestamp()
            cutoff = now - self.window_seconds
            stale_ids = []

            for equipment_id, timestamps in list(self._state.items()):
                filtered = [ts for ts in timestamps if ts >= cutoff]
                if filtered:
                    self._state[equipment_id] = filtered
                else:
                    stale_ids.append(equipment_id)

            for equipment_id in stale_ids:
                self._state.pop(equipment_id, None)

    async def _gc_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.gc_interval_seconds)
                await self.cleanup_stale_entries()
        except asyncio.CancelledError:
            raise
