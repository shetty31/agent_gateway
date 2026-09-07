#!/usr/bin/env python3
"""Event-driven file-system watchdog and ETL orchestrator.

Monitors the Bronze raw storage layer for new JSON payloads, processes them
sequentially through an ETL that strips sensitive credentials, enriches
with chain-of-custody metadata and a standardized glossary, transforms
into a Data Cube (dimensions/facts), writes to the Silver NoSQL directory,
and moves the original to archive or quarantine depending on success.

All paths are hermetic and hardcoded relative to PROJECT_ROOT.
"""
from __future__ import annotations

import json
import logging
import queue
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer

# ---------------------------------------------------------------------------
# Configuration & Paths (hermetic — no CLI args)
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
BRONZE_DIR: Path = PROJECT_ROOT / "data" / "approved"
SILVER_DIR: Path = PROJECT_ROOT / "data" / "silver_harmonized"
ARCHIVE_DIR: Path = PROJECT_ROOT / "data" / "archive" / "bronze"
QUARANTINE_DIR: Path = PROJECT_ROOT / "data" / "quarantine" / "etl_failed"
CONFIG_DIR: Path = PROJECT_ROOT / "config"
INBOUND_SCHEMA_FILE: Path = CONFIG_DIR / "inbound_schema.json"
GLOSSARY_FILE: Path = CONFIG_DIR / "metrics_glossary.json"

PARSER_SCRIPT_VERSION = "1.0.0"

# Sensitive keys to remove from payloads (any nesting level)
SENSITIVE_KEYS = {"agent_key", "edge_token", "password", "secret"}

# Time (seconds) to wait to consider a file stable (no longer being written)
STABILITY_CHECK_INTERVAL = 0.5
STABILITY_CHECK_RETRIES = 6  # ~3 seconds max wait for file to finish writing

# Worker queue capacity
PROCESSING_QUEUE_MAXSIZE = 1000

# Ensure directories exist
for d in (BRONZE_DIR, SILVER_DIR, ARCHIVE_DIR, QUARANTINE_DIR, CONFIG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Load static artifacts (glossary and schema)
try:
    _INBOUND_SCHEMA = json.loads(INBOUND_SCHEMA_FILE.read_text(encoding="utf-8"))
except Exception:
    _INBOUND_SCHEMA = {}

try:
    _GLOSSARY = json.loads(GLOSSARY_FILE.read_text(encoding="utf-8"))
except Exception:
    _GLOSSARY = {}

# Determine required top-level fields and telemetry required fields from schema
REQUIRED_TOP_LEVEL: List[str] = []
TELEMETRY_REQUIRED: List[str] = []
try:
    REQUIRED_TOP_LEVEL = list(_INBOUND_SCHEMA.get("required", []))
    telemetry_props = _INBOUND_SCHEMA.get("properties", {}).get("telemetry", {}).get("properties", {})
    TELEMETRY_REQUIRED = list(_INBOUND_SCHEMA.get("properties", {}).get("telemetry", {}).get("required", []))
except Exception:
    REQUIRED_TOP_LEVEL = []
    TELEMETRY_REQUIRED = []

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("event_listener")


def remove_sensitive_keys(obj: Any, sensitive: Iterable[str]) -> Any:
    """Recursively remove sensitive keys from mappings.

    Returns a cleaned copy of the object.
    """
    if isinstance(obj, dict):
        return {k: remove_sensitive_keys(v, sensitive) for k, v in obj.items() if k not in sensitive}
    if isinstance(obj, list):
        return [remove_sensitive_keys(v, sensitive) for v in obj]
    return obj


def wait_until_stable(path: Path, interval: float = STABILITY_CHECK_INTERVAL, retries: int = STABILITY_CHECK_RETRIES) -> bool:
    """Wait until file size is stable for two checks or until retries exhausted."""
    try:
        last_size = path.stat().st_size
    except Exception:
        return False

    for _ in range(retries):
        time.sleep(interval)
        try:
            size = path.stat().st_size
        except Exception:
            return False
        if size == last_size:
            return True
        last_size = size
    return False


def validate_payload(payload: Dict[str, Any]) -> None:
    """Very small structural validation against known schema requirements.

    Raises KeyError or ValueError on invalid input.
    """
    # Ensure required top-level fields
    # NOTE: ETL should be permissive about auth-only fields such as 'agent_key'.
    # The gateway enforces agent_key for inbound HTTP requests; the ETL may
    # receive payloads that do not include 'agent_key' and should not fail
    # solely for that reason.
    for key in REQUIRED_TOP_LEVEL:
        if key == "agent_key":
            continue
        if key not in payload:
            raise KeyError(f"Missing required field: {key}")

    telemetry = payload.get("telemetry")
    if not isinstance(telemetry, dict):
        raise ValueError("telemetry must be an object")

    for t in TELEMETRY_REQUIRED:
        if t not in telemetry:
            raise KeyError(f"Missing telemetry field: {t}")


def build_data_cube(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a validated payload into a Data Cube JSON doc.

    The mapping separates `dimensions` from `facts` and includes metadata.
    """
    dimensions = {
        "equipment_id": payload.get("equipment_id"),
        "timestamp": payload.get("timestamp"),
        "critical_alert": payload.get("critical_alert"),
    }

    facts = payload.get("telemetry", {}).copy()

    # Start with base metadata
    metadata: Dict[str, Any] = {
        "parser_script_version": PARSER_SCRIPT_VERSION,
        "glossary_version": _GLOSSARY.get("version"),
    }

    # If the ETL injected a chain_of_custody entry, include it immutably
    if isinstance(payload.get("chain_of_custody"), dict):
        metadata["chain_of_custody"] = dict(payload.get("chain_of_custody"))

    # Preserve the glossary reference inside the Data Cube metadata
    if "_glossary" in payload:
        metadata["_glossary"] = payload.get("_glossary")

    data_cube = {
        "dimensions": dimensions,
        "facts": facts,
        "metadata": metadata,
    }

    return data_cube


def write_silver(data_cube: Dict[str, Any], dest_root: Path) -> Path:
    """Persist the data cube as a JSON document into a nested directory.

    Directory layout: <dest_root>/equipment_id=<id>/year=YYYY/month=MM/day=DD/<uuid>.json
    Returns the path written.
    """
    equipment = data_cube["dimensions"].get("equipment_id") or "unknown"
    ts = data_cube["dimensions"].get("timestamp")
    # attempt to parse timestamp to date components; fall back to now
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.now(timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)

    target_dir = (
        dest_root
        / f"equipment_id={equipment}"
        / f"year={dt.year:04d}"
        / f"month={dt.month:02d}"
        / f"day={dt.day:02d}"
    )
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{dt.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex}.json"
    target_path = target_dir / filename
    target_path.write_text(json.dumps(data_cube, ensure_ascii=False, indent=2), encoding="utf-8")
    return target_path


def process_payload_file(path: Path) -> None:
    """Main processing routine for a single file.

    Handles stability checking, parsing, ETL, persistence, and lifecycle moves.
    """
    logger.info("Processing file: %s", path)

    if not wait_until_stable(path):
        logger.warning("File did not stabilize; moving to quarantine: %s", path)
        shutil.move(str(path), str(QUARANTINE_DIR / path.name))
        return

    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except Exception as e:
        logger.exception("Failed to read/parse JSON: %s", e)
        shutil.move(str(path), str(QUARANTINE_DIR / path.name))
        return

    # Support files that contain either a single object or an array of objects
    items: List[Dict[str, Any]]
    if isinstance(payload, list):
        items = [p for p in payload if isinstance(p, dict)]
        if not items:
            logger.error("JSON array contained no object payloads: %s", path)
            shutil.move(str(path), str(QUARANTINE_DIR / path.name))
            return
    elif isinstance(payload, dict):
        items = [payload]
    else:
        logger.error("Unexpected JSON root type; expected object or array: %s", path)
        shutil.move(str(path), str(QUARANTINE_DIR / path.name))
        return

    all_ok = True
    for idx, item in enumerate(items):
        try:
            # If the upstream VRAM/writer used the wrapper shape
            # {"equipment_id": "...", "payload": { ... }},
            # unwrap it so validation operates on the actual message body.
            if isinstance(item, dict) and "payload" in item and isinstance(item["payload"], dict):
                # Create a working copy of the inner payload and promote equipment_id
                working = dict(item["payload"])  # shallow copy
                if "equipment_id" not in working and "equipment_id" in item:
                    working["equipment_id"] = item.get("equipment_id")
            else:
                # Already a plain payload document
                working = dict(item)

            # Validate the unwrapped working document
            validate_payload(working)

            # Strip sensitive keys from the working doc (do not modify original)
            cleaned = remove_sensitive_keys(working, SENSITIVE_KEYS)

            # Chain-of-custody per-record (include index when from array)
            # Resolve a stable source path relative to the project root when possible
            try:
                rel_path = str(path.resolve().relative_to(PROJECT_ROOT))
            except Exception:
                # Fall back to the literal path if resolution/relativization fails
                rel_path = str(path)

            chain_of_custody = {
                "processing_timestamp": datetime.now(timezone.utc).isoformat(),
                "parser_script_version": PARSER_SCRIPT_VERSION,
                "source_path": rel_path + (f"[{idx}]" if len(items) > 1 else ""),
            }
            cleaned["chain_of_custody"] = chain_of_custody

            # Ensure glossary is present and preserved (FAIR metadata)
            if "_glossary" not in cleaned:
                cleaned["_glossary"] = _GLOSSARY

            # Build final Data Cube and write to Silver
            cube = build_data_cube(cleaned)
            silver_path = write_silver(cube, SILVER_DIR)
            logger.info("Wrote silver document: %s", silver_path)

        except Exception as e:
            logger.exception("ETL failed for %s (index=%s): %s", path, idx, e)
            all_ok = False

    # Post-processing move based on batch success
    try:
        if all_ok:
            archive_target = ARCHIVE_DIR / path.name
            shutil.move(str(path), str(archive_target))
            logger.info("Archived original to: %s", archive_target)
        else:
            quarantine_target = QUARANTINE_DIR / path.name
            shutil.move(str(path), str(quarantine_target))
            logger.info("Moved to quarantine: %s", quarantine_target)
    except Exception as move_err:
        logger.exception("Failed to move original after processing: %s", move_err)


class BronzeEventHandler(FileSystemEventHandler):
    """Enqueues created files for processing."""

    def __init__(self, queue: queue.Queue):
        super().__init__()
        self._queue = queue

    def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() != ".json":
            logger.debug("Ignoring non-json file: %s", path)
            return
        try:
            self._queue.put(path, block=False)
            logger.info("Enqueued file: %s", path)
        except queue.Full:
            logger.error("Processing queue full. Dropping file: %s", path)


def worker_loop(q: queue.Queue, stop_event: threading.Event) -> None:
    logger.info("Worker thread started")
    while not stop_event.is_set():
        try:
            path: Path = q.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            process_payload_file(path)
        finally:
            q.task_done()
    logger.info("Worker thread stopping")


def main() -> None:
    logger.info("Starting event_listener; watching: %s", BRONZE_DIR)

    processing_queue: queue.Queue[Path] = queue.Queue(maxsize=PROCESSING_QUEUE_MAXSIZE)
    stop_event = threading.Event()

    worker = threading.Thread(target=worker_loop, args=(processing_queue, stop_event), daemon=True)
    worker.start()

    event_handler = BronzeEventHandler(processing_queue)
    observer = Observer()
    observer.schedule(event_handler, str(BRONZE_DIR), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Shutdown requested (KeyboardInterrupt)")
    finally:
        observer.stop()
        stop_event.set()
        observer.join()
        worker.join(timeout=5.0)


if __name__ == "__main__":
    main()
