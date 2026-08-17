import asyncio
import json
from pathlib import Path

from src.virtual_vram_batcher import VramBuffer


def test_threshold_flush_writes_partitioned_files(tmp_path: Path) -> None:
    async def run_test() -> None:
        buffer = VramBuffer(flush_threshold=2, flush_interval=60.0, storage_root=tmp_path)
        await buffer.start()

        await buffer.ingest_payload({"sensor": "temp", "value": 21})
        await buffer.ingest_payload({"sensor": "temp", "value": 22})

        await asyncio.sleep(0.05)

        files = list((tmp_path / "approved").rglob("*.json"))
        assert len(files) == 1

        written_payloads = json.loads(files[0].read_text(encoding="utf-8"))
        assert written_payloads == [
            {"sensor": "temp", "value": 21},
            {"sensor": "temp", "value": 22},
        ]
        buffer.shutdown()

    asyncio.run(run_test())


def test_temporal_monitor_flushes_after_interval(tmp_path: Path) -> None:
    async def run_test() -> None:
        buffer = VramBuffer(flush_threshold=10, flush_interval=0.05, storage_root=tmp_path)
        await buffer.start()

        await buffer.ingest_payload({"sensor": "pressure", "value": 101})
        await asyncio.sleep(0.12)

        files = list((tmp_path / "approved").rglob("*.json"))
        assert len(files) == 1
        buffer.shutdown()

    asyncio.run(run_test())


def test_shutdown_flushes_remaining_queue(tmp_path: Path) -> None:
    async def run_test() -> None:
        buffer = VramBuffer(flush_threshold=10, flush_interval=60.0, storage_root=tmp_path)
        await buffer.start()

        await buffer.ingest_payload({"sensor": "humidity", "value": 55})
        buffer.shutdown()

        files = list((tmp_path / "approved").rglob("*.json"))
        assert len(files) == 1

        written_payloads = json.loads(files[0].read_text(encoding="utf-8"))
        assert written_payloads == [{"sensor": "humidity", "value": 55}]

    asyncio.run(run_test())
