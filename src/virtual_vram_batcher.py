from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class VramBuffer:
    """Asynchronous in-memory buffer for approved IoT telemetry payloads.

    The buffer accepts only payloads that have already passed upstream validation.
    It batches them in volatile memory and writes them to disk whenever either the
    queue reaches a configured threshold or a time-based flush interval elapses.
    A shutdown path ensures any unwritten payloads are persisted before exit.
    """

    def __init__(
        self,
        flush_threshold: int = 500,
        flush_interval: float = 10.0,
        storage_root: Path | str | None = None,
        output_dir_name: str = "approved",
    ) -> None:
        self.flush_threshold = flush_threshold
        self.flush_interval = flush_interval
        self.output_dir_name = output_dir_name
        # Default storage root is the repository `data/` directory so that
        # hive-partitioned outputs land under `data/approved/...` by default.
        self.storage_root = (
            Path(storage_root)
            if storage_root is not None
            else PROJECT_ROOT / "data"
        )
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._monitor_task: asyncio.Task[None] | None = None
        self._shutdown_requested = False
        self._last_flush_monotonic = time.monotonic()

    async def start(self) -> None:
        """Start the background temporal monitor task."""
        if self._monitor_task is None or self._monitor_task.done():
            self._shutdown_requested = False
            self._monitor_task = asyncio.create_task(self._temporal_monitor())

    async def ingest_payload(self, payload: dict[str, Any]) -> None:
        """Queue a payload that has already received an HTTP 200 response."""
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dictionary")

        await self._queue.put(payload)
        if self._queue.qsize() >= self.flush_threshold:
            await self._flush_to_disk()

    async def _flush_to_disk(self) -> None:
        """Drain the queue and write the buffered payloads to disk."""
        payloads = self._drain_queue()
        if not payloads:
            return

        now = datetime.now(timezone.utc)
        partition_dir = self.storage_root / self.output_dir_name / f"year={now.year}" / f"month={now.month:02d}" / f"day={now.day:02d}"
        partition_dir.mkdir(parents=True, exist_ok=True)

        timestamp = now.strftime("%Y%m%d%H%M%S%f")
        filename = f"{timestamp}_{uuid.uuid4().hex}.json"
        destination = partition_dir / filename
        destination.write_text(json.dumps(payloads, indent=2, sort_keys=True), encoding="utf-8")
        self._last_flush_monotonic = time.monotonic()
        # Log flush metadata to a repo-local flush log for post-run reconciliation
        try:
            logs_dir = PROJECT_ROOT / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            flush_log = logs_dir / "vram_flushes.log"
            sample_ids = []
            for p in payloads[:10]:
                # payloads may be dicts with nested payload dicts
                rid = None
                if isinstance(p, dict):
                    if "_request_id" in p:
                        rid = p.get("_request_id")
                    elif isinstance(p.get("payload"), dict):
                        rid = p.get("payload").get("_request_id")
                if rid:
                    sample_ids.append(rid)
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "file": str(destination),
                "count": len(payloads),
                "sample_request_ids": sample_ids,
            }
            with flush_log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
        except Exception:
            pass

    def _drain_queue(self) -> list[dict[str, Any]]:
        """Remove all currently queued payloads in a single batch."""
        payloads: list[dict[str, Any]] = []
        while True:
            try:
                payloads.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return payloads

    async def _temporal_monitor(self) -> None:
        """Continuously flush the buffer when the interval elapses."""
        while not self._shutdown_requested:
            await asyncio.sleep(self.flush_interval)
            if self._shutdown_requested:
                break
            if not self._queue.empty():
                await self._flush_to_disk()

    def shutdown(self) -> None:
        """Cancel the monitor task and persist any remaining queue contents."""
        self._shutdown_requested = True
        if self._monitor_task is not None and not self._monitor_task.done():
            self._monitor_task.cancel()

        self._flush_to_disk_sync()

    def _flush_to_disk_sync(self) -> None:
        """Synchronous flush helper used by shutdown() for zero-data-loss behavior."""
        payloads = self._drain_queue()
        if not payloads:
            return

        now = datetime.now(timezone.utc)
        partition_dir = self.storage_root / self.output_dir_name / f"year={now.year}" / f"month={now.month:02d}" / f"day={now.day:02d}"
        partition_dir.mkdir(parents=True, exist_ok=True)

        timestamp = now.strftime("%Y%m%d%H%M%S%f")
        filename = f"{timestamp}_{uuid.uuid4().hex}.json"
        destination = partition_dir / filename
        destination.write_text(json.dumps(payloads, indent=2, sort_keys=True), encoding="utf-8")
        self._last_flush_monotonic = time.monotonic()
