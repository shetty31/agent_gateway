from __future__ import annotations

"""Gateway runtime security pipeline.

Tier 1: authenticate the client IP and agent key.
Tier 2: enforce the per-equipment RPM limit.
Tier 3: validate the payload against the schema contract in config/inbound_schema.json.
Tier 4: on lifecycle shutdown, flush any remaining approved payloads from VRAM to disk.

Malformed or mismatched payloads are quarantined rather than hard-dropped at the network layer.
"""

import json
import os
import time
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from src.redis_mock import RedisMock
from src.virtual_vram_batcher import VramBuffer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALLOWED_IPS = {"127.0.0.1", "::1", "localhost"}


def _load_env_file() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = [part.strip() for part in line.split("=", 1)]
        if key and value and key not in os.environ:
            os.environ[key] = value.strip('"').strip("'")


def load_runtime_settings() -> dict[str, Any]:
    _load_env_file()

    agent_key_value = os.getenv("AGENT_KEY") or os.getenv("AGENT_KEYS") or "demo-agent-key"
    if agent_key_value:
        allowed_keys = {
            item.strip().strip('"').strip("'")
            for item in agent_key_value.split(",")
            if item.strip()
        }
    else:
        allowed_keys = {"demo-agent-key"}

    return {
        "allowed_agent_keys": allowed_keys,
        "max_rpm_limit": int(os.getenv("MAX_RPM_LIMIT", "60")),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug_mode": os.getenv("DEBUG_MODE", "False").lower() in {"1", "true", "yes", "on"},
    }


RUNTIME_SETTINGS = load_runtime_settings()
ALLOWED_AGENT_KEYS = RUNTIME_SETTINGS["allowed_agent_keys"]

rate_limiter = RedisMock()
# Use the repository `data/` directory for approved/quarantine outputs by default
vram_buffer = VramBuffer(storage_root=PROJECT_ROOT / "data")


def get_allowed_agent_keys() -> set[str]:
    # Return the precomputed set loaded at module import time to avoid
    # re-reading files or environment variables on every request. Calling
    # `load_runtime_settings()` per-request caused synchronous file I/O
    # and contributed to latency tail spikes under high concurrency.
    return ALLOWED_AGENT_KEYS


def _load_inbound_schema() -> dict[str, Any]:
    schema_path = PROJECT_ROOT / "config" / "inbound_schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Inbound schema not found at {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_payload_against_inbound_schema(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object")

    schema = _load_inbound_schema()
    required_top_level = schema.get("required", [])
    properties = schema.get("properties", {})

    for key in required_top_level:
        if key not in payload:
            raise ValueError(f"Missing required field: {key}")

    for key, definition in properties.items():
        if key not in payload:
            continue

        value = payload[key]
        if key == "agent_key":
            if not isinstance(value, str):
                raise ValueError("agent_key must be a string")
            continue

        if key == "equipment_id":
            if not isinstance(value, str):
                raise ValueError("equipment_id must be a string")
            continue

        if key == "timestamp":
            if not isinstance(value, str):
                raise ValueError("timestamp must be an ISO-8601 string")
            continue

        if key == "critical_alert":
            if not isinstance(value, bool):
                raise ValueError("critical_alert must be a boolean")
            continue

        if key == "telemetry":
            if not isinstance(value, dict):
                raise ValueError("telemetry must be an object")
            telemetry_schema = definition.get("properties", {})
            telemetry_required = definition.get("required", [])

            for telemetry_key in telemetry_required:
                if telemetry_key not in value:
                    raise ValueError(f"Missing required telemetry field: {telemetry_key}")

            for telemetry_key, telemetry_definition in telemetry_schema.items():
                if telemetry_key not in value:
                    continue

                field_value = value[telemetry_key]
                telemetry_type = telemetry_definition.get("type")
                if telemetry_type == "number" and not isinstance(field_value, (int, float)):
                    raise ValueError(f"telemetry.{telemetry_key} must be a number")
                if telemetry_type == "integer" and not isinstance(field_value, int):
                    raise ValueError(f"telemetry.{telemetry_key} must be an integer")
                if telemetry_type == "string" and not isinstance(field_value, str):
                    raise ValueError(f"telemetry.{telemetry_key} must be a string")
                if "enum" in telemetry_definition and field_value not in telemetry_definition["enum"]:
                    raise ValueError(f"telemetry.{telemetry_key} must be one of {telemetry_definition['enum']}")

    additional = set(payload.keys()) - set(properties.keys())
    if additional:
        raise ValueError(f"Unexpected fields: {sorted(additional)}")

    # Additional runtime check for auth key match against the current environment config.
    allowed_keys = get_allowed_agent_keys()
    if "agent_key" in payload and payload["agent_key"] not in allowed_keys:
        raise ValueError("agent_key is not authorized")


class IngestRequest(BaseModel):
    equipment_id: str
    payload: dict[str, Any]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await rate_limiter.start()
    await vram_buffer.start()
    try:
        yield
    finally:
        # Ensure VRAM buffer is synchronously flushed before shutdown
        vram_buffer.shutdown()
        await rate_limiter.stop()


app = FastAPI(title="Agent Gateway", lifespan=lifespan)


@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 3)
        status_code = response.status_code if response is not None else 500
        client_ip = request.client.host if request.client else None
        telemetry_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "client_ip": client_ip,
        }
        # Offload file writes to the default thread pool executor so that
        # request processing isn't delayed by synchronous disk I/O. This
        # reduces tail latency when many concurrent requests are being
        # processed.
        telemetry_path = PROJECT_ROOT / "logs" / "telemetry.log"
        telemetry_path.parent.mkdir(parents=True, exist_ok=True)

        def _sync_write(entry: dict[str, Any], path: Path) -> None:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")

        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, _sync_write, telemetry_entry, telemetry_path)
        except RuntimeError:
            # If no running loop is available, fall back to synchronous write
            # (best-effort — this should be rare in normal operation).
            _sync_write(telemetry_entry, telemetry_path)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    payload = await _read_request_payload(request)
    try:
        validate_payload_against_inbound_schema(payload)
    except ValueError:
        _write_quarantine_payload(payload)
        return JSONResponse(status_code=422, content={"detail": "Validation error"})
    _write_quarantine_payload(payload)
    return JSONResponse(status_code=422, content={"detail": "Validation error"})


@app.post("/ingest")
async def ingest(request: Request, payload: IngestRequest) -> JSONResponse:
    client_ip = request.client.host if request.client else "unknown"
    agent_key = request.headers.get("x-agent-key") or request.query_params.get("agent_key")

    allowed_keys = get_allowed_agent_keys()
    if not agent_key or agent_key not in allowed_keys or client_ip not in ALLOWED_IPS:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    try:
        validate_payload_against_inbound_schema(payload.model_dump())
    except ValueError:
        _write_quarantine_payload(payload.model_dump())
        return JSONResponse(status_code=422, content={"detail": "Validation error"})

    breach = await rate_limiter.check_breach(payload.equipment_id, payload.payload)
    if breach:
        return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})

    response = JSONResponse(status_code=200, content={"status": "accepted", "equipment_id": payload.equipment_id})

    # Ingest approved payloads into the in-memory VRAM buffer.
    # We schedule this as a fire-and-forget task because ingestion is asynchronous
    # and the gateway's HTTP response has already been determined as 200 OK.
    try:
        asyncio.create_task(
            vram_buffer.ingest_payload({"equipment_id": payload.equipment_id, "payload": payload.payload})
        )
    except RuntimeError:
        # If event loop is closed or unavailable, skip ingestion to avoid crashing the request
        pass

    return response


async def _read_request_payload(request: Request) -> Any:
    body = await request.body()
    if not body:
        return {}

    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"raw_body": body.decode("utf-8", errors="replace")}


def _write_quarantine_payload(payload: Any) -> None:
    now = datetime.utcnow()
    # Enforce repository-root `data/` as the single physical storage location
    # for quarantine files. No fallback to package-local paths is allowed.
    preferred_dir = PROJECT_ROOT / "data" / "quarantine" / "structural"
    partition_dir = preferred_dir / f"year={now.year}" / f"month={now.month:02d}" / f"day={now.day:02d}"

    # Let any OS-level errors surface rather than writing into the package
    # directory. This prevents pollution of the `src/` tree.
    partition_dir.mkdir(parents=True, exist_ok=True)

    file_path = partition_dir / f"{now.strftime('%H%M%S%f')}.json"
    file_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
