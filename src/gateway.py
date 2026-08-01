from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from src.redis_mock import RedisMock


ALLOWED_AGENT_KEYS = {"demo-agent-key"}
ALLOWED_IPS = {"127.0.0.1", "::1", "localhost"}

rate_limiter = RedisMock()


class IngestRequest(BaseModel):
    equipment_id: str
    payload: dict[str, Any]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await rate_limiter.start()
    try:
        yield
    finally:
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
        telemetry_path = Path(__file__).resolve().parent / "telemetry.log"
        telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        with telemetry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(telemetry_entry, sort_keys=True) + "\n")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    payload = await _read_request_payload(request)
    _write_quarantine_payload(payload)
    return JSONResponse(status_code=422, content={"detail": "Validation error"})


@app.post("/ingest")
async def ingest(request: Request, payload: IngestRequest) -> JSONResponse:
    client_ip = request.client.host if request.client else "unknown"
    agent_key = request.headers.get("x-agent-key") or request.query_params.get("agent_key")

    if not agent_key or agent_key not in ALLOWED_AGENT_KEYS or client_ip not in ALLOWED_IPS:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    breach = await rate_limiter.check_breach(payload.equipment_id, payload.payload)
    if breach:
        return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})

    return JSONResponse(status_code=200, content={"status": "accepted", "equipment_id": payload.equipment_id})


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
    partition_dir = Path("/quarantine/structural") / f"year={now.year}" / f"month={now.month:02d}" / f"day={now.day:02d}"

    try:
        partition_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        fallback_dir = Path(__file__).resolve().parent / "quarantine" / "structural" / f"year={now.year}" / f"month={now.month:02d}" / f"day={now.day:02d}"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        partition_dir = fallback_dir

    file_path = partition_dir / f"{now.strftime('%H%M%S%f')}.json"
    file_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
