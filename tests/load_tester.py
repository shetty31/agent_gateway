#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
import random
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp


@dataclass(frozen=True)
class LoadTesterConfig:
    url: str
    scenario: str
    total_requests: int
    concurrency: int
    timeout: float
    agent_key: str
    extra_payload: str | None
    save_results: bool = False
    results_output: str | Path | None = None


@dataclass
class RequestResult:
    status: int | None
    latency_ms: float | None
    error: str | None
    request_id: str | None = None


def parse_args() -> LoadTesterConfig:
    parser = argparse.ArgumentParser(
        description="Asynchronous IoT load tester for the FastAPI API Gateway."
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/ingest",
        help="Target ingestion endpoint URL.",
    )
    parser.add_argument(
        "--scenario",
        choices=["approved", "forbidden", "quarantine", "rate_limit", "mixed"],
        default="approved",
        help="Load testing scenario to execute.",
    )
    parser.add_argument(
        "--total-requests",
        type=int,
        default=100,
        help="Total number of POST requests to dispatch.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=50,
        help="Maximum number of concurrent outbound requests.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--agent-key",
        default=os.getenv("AGENT_KEY", "demo-agent-key"),
        help="Agent key to attach to each request header. Defaults to AGENT_KEY or demo-agent-key.",
    )
    parser.add_argument(
        "--extra-payload",
        default=None,
        help="Optional JSON string to merge into each payload body.",
    )
    parser.add_argument(
        "--save-results",
        action="store_true",
        help="Write per-request results to a JSON file (use --results-output to set path).",
    )
    parser.add_argument(
        "--results-output",
        default="load_tester_results.json",
        help="Path to write JSON results when --save-results is provided.",
    )

    args = parser.parse_args()
    return LoadTesterConfig(
        url=args.url,
        scenario=args.scenario,
        total_requests=args.total_requests,
        concurrency=args.concurrency,
        timeout=args.timeout,
        agent_key=args.agent_key,
        extra_payload=args.extra_payload,
        save_results=args.save_results,
        results_output=args.results_output,
    )


def _serialize_results(results: list[RequestResult]) -> list[dict[str, Any]]:
    return [
        {
            "status": (res.status if res.status is not None else None),
            "latency_ms": (res.latency_ms if res.latency_ms is not None else None),
            "error": res.error,
            "request_id": res.request_id,
        }
        for res in results
    ]


def build_payload(index: int, scenario: str, extra_payload: str | None) -> dict[str, Any]:
    timestamp_str = datetime.utcnow().isoformat() + "Z"
    
    # The FDA-compliant "Golden Payload" inner structure
    golden_payload = {
        "timestamp": timestamp_str,
        "critical_alert": False,
        "telemetry": {
            "temperature_c": 37.5,
            "bioreactor_rpm": 250,
            "sensor_status": "OK"
        }
    }

    if scenario == "forbidden":
        # Keep payload schema-compliant; auth will be rejected by agent key
        payload_body: Any = golden_payload
        equip_id = f"load-test-forbidden-{index % 5}"
    elif scenario == "quarantine":
        payload_body = "invalid-payload"
        equip_id = f"load-test-quarantine-{index % 5}"
        
    elif scenario == "rate_limit":
        # MUST use a single static ID to quickly breach the 60 RPM limit
        payload_body = golden_payload
        equip_id = "load-test-rate_limit-STATIC"
        
    else: # "approved"
        # MUST distribute across many IDs so no single ID breaches the 60 RPM limit
        payload_body = golden_payload
        equip_id = f"load-test-approved-{index % 100}"

    base_payload: dict[str, Any] = {
        "equipment_id": equip_id,
        "payload": payload_body,
    }

    if scenario == "mixed":
        variant = index % 4
        if variant == 0:
            base_payload["equipment_id"] = "load-test-approved-mixed"
            base_payload["payload"] = golden_payload
        elif variant == 1:
            base_payload["equipment_id"] = "load-test-429-STATIC"
            base_payload["payload"] = golden_payload
        elif variant == 2:
            base_payload["equipment_id"] = "load-test-422"
            base_payload["payload"] = "malformed"
        else:
            base_payload["equipment_id"] = "load-test-403"
            base_payload["payload"] = golden_payload

    if extra_payload is not None:
        try:
            extra_data = json.loads(extra_payload)
            if isinstance(extra_data, dict) and isinstance(base_payload["payload"], dict):
                base_payload["payload"].update(extra_data)
        except json.JSONDecodeError:
            pass

    return base_payload


def choose_agent_key(index: int, base_key: str, scenario: str) -> str:
    if scenario == "forbidden":
        return "invalid-key"
    if scenario == "mixed" and index % 4 == 3:
        return "invalid-key"
    return base_key


async def send_one_request(
    session: aiohttp.ClientSession,
    url: str,
    payload: dict[str, Any],
    agent_key: str,
    timeout: float,
) -> RequestResult:
    headers = {
        "Content-Type": "application/json",
        "x-agent-key": agent_key,
    }
    start = time.perf_counter()
    try:
        async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
            await response.text()
            latency_ms = (time.perf_counter() - start) * 1000.0
            return RequestResult(status=response.status, latency_ms=latency_ms, error=None)
    except asyncio.TimeoutError:
        latency_ms = (time.perf_counter() - start) * 1000.0
        return RequestResult(status=None, latency_ms=latency_ms, error="timeout")
    except aiohttp.ClientError as exc:
        latency_ms = (time.perf_counter() - start) * 1000.0
        return RequestResult(status=None, latency_ms=latency_ms, error=str(exc))
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000.0
        return RequestResult(status=None, latency_ms=latency_ms, error=f"unexpected: {exc}")


async def run_load_test(config: LoadTesterConfig) -> list[RequestResult]:
    connector = aiohttp.TCPConnector(limit=config.concurrency, force_close=True)
    timeout = aiohttp.ClientTimeout(total=None)

    semaphore = asyncio.Semaphore(config.concurrency)
    results: list[RequestResult] = []

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async def worker(index: int) -> None:
            async with semaphore:
                payload = build_payload(index, config.scenario, config.extra_payload)
                # Do NOT mutate the payload to add request ids (would violate inbound schema)
                req_id = uuid.uuid4().hex
                agent_key = choose_agent_key(index, config.agent_key, config.scenario)
                result = await send_one_request(session, config.url, payload, agent_key, config.timeout)
                # attach request id locally for correlation only
                result.request_id = req_id
                results.append(result)

        tasks = [worker(i) for i in range(config.total_requests)]
        await asyncio.gather(*tasks)

    return results


def summarize_results(results: list[RequestResult], elapsed_seconds: float) -> None:
    print("\nLoad Test Summary")
    print("=" * 60)
    print(f"Total duration   : {elapsed_seconds:.2f} seconds")
    print(f"Total requests   : {len(results)}")

    completed = [res for res in results if res.status is not None]
    errors = [res for res in results if res.error is not None]
    latencies = [res.latency_ms for res in completed if res.latency_ms is not None]

    if latencies:
        print(f"Average latency  : {sum(latencies) / len(latencies):.2f} ms")
        print(f"Min latency      : {min(latencies):.2f} ms")
        print(f"Max latency      : {max(latencies):.2f} ms")
    else:
        print("Average latency  : n/a")

    status_counts = Counter(res.status for res in completed)
    for status in sorted(status_counts):
        print(f"HTTP {status:<3}        : {status_counts[status]}" )

    if errors:
        error_counts = Counter(res.error for res in errors)
        print("\nErrors:")
        for error, count in error_counts.items():
            print(f"  {error}: {count}")

    print("=" * 60)
    print("Finished load test.")


def validate_config(config: LoadTesterConfig) -> None:
    if config.total_requests <= 0:
        raise ValueError("--total-requests must be a positive integer")
    if config.concurrency <= 0:
        raise ValueError("--concurrency must be a positive integer")
    if config.timeout <= 0.0:
        raise ValueError("--timeout must be a positive number")


def main() -> int:
    try:
        config = parse_args()
        validate_config(config)
        start = time.perf_counter()
        results = asyncio.run(run_load_test(config))
        elapsed = time.perf_counter() - start
        summarize_results(results, elapsed)
        if getattr(config, "save_results", False):
            out_path = Path(getattr(config, "results_output", "load_tester_results.json"))
            payload = {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "config": {
                    "url": config.url,
                    "scenario": config.scenario,
                    "total_requests": config.total_requests,
                    "concurrency": config.concurrency,
                    "timeout": config.timeout,
                    "agent_key": config.agent_key,
                },
                "results": _serialize_results(results),
            }
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"Saved results to {out_path}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())