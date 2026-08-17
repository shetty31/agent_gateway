from __future__ import annotations

import json
from pathlib import Path

import asyncio

import pytest

from src import gateway


def test_runtime_reads_env_and_validates_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_KEY", raising=False)
    monkeypatch.setenv("AGENT_KEY", "env-schema-key")

    settings = gateway.load_runtime_settings()
    assert settings["allowed_agent_keys"] == {"env-schema-key"}

    valid_payload = {
        "agent_key": "env-schema-key",
        "equipment_id": "equip-001",
        "timestamp": "2026-08-15T00:00:00Z",
        "critical_alert": False,
        "telemetry": {
            "temperature_c": 22.5,
            "bioreactor_rpm": 1200,
            "sensor_status": "OK",
        },
    }
    gateway.validate_payload_against_inbound_schema(valid_payload)

    invalid_payload = {
        "agent_key": "env-schema-key",
        "equipment_id": "equip-001",
        "timestamp": "2026-08-15T00:00:00Z",
        "critical_alert": False,
        "telemetry": {
            "temperature_c": "bad",
            "bioreactor_rpm": 1200,
            "sensor_status": "OK",
        },
    }
    with pytest.raises(ValueError):
        gateway.validate_payload_against_inbound_schema(invalid_payload)


def test_smoke_approved_writes(tmp_path: Path) -> None:
    # Point the VRAM buffer to a temporary storage root
    gateway.vram_buffer.storage_root = tmp_path

    async def run_ingest():
        await gateway.vram_buffer.start()
        await gateway.vram_buffer.ingest_payload({"equipment_id": "smoke-1", "payload": {"sensor": "temp", "value": 21}})
        await gateway.vram_buffer.ingest_payload({"equipment_id": "smoke-2", "payload": {"sensor": "temp", "value": 22}})
        # Force synchronous flush
        gateway.vram_buffer.shutdown()

    asyncio.run(run_ingest())

    files = list((tmp_path / "approved").rglob("*.json"))
    assert len(files) >= 1

    # Ensure that written file contains our posted payloads
    found = False
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        if any(isinstance(p, dict) and p.get("equipment_id") == "smoke-1" for p in data) and any(isinstance(p, dict) and p.get("equipment_id") == "smoke-2" for p in data):
            found = True
            break

    assert found, "No approved file contained both smoke payloads"
