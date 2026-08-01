#!/usr/bin/env python3
"""Acceptance-test harness for the gateway ingestion API.

Run from the project root:
    python test_injector.py
or directly target a scenario:
    python test_injector.py A
    python test_injector.py B
    python test_injector.py C
    python test_injector.py D
"""

from __future__ import annotations

import sys
import time
from typing import Any

import requests


BASE_URL = "http://127.0.0.1:8000/ingest"
VALID_AGENT_KEY = "demo-agent-key"


def print_header(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def print_result(label: str, value: Any) -> None:
    print(f"{label}: {value}")


def post_json(payload: dict[str, Any], agent_key: str | None = None, timeout: float = 3.0) -> requests.Response:
    headers = {"Content-Type": "application/json"}
    if agent_key is not None:
        headers["x-agent-key"] = agent_key
    return requests.post(BASE_URL, json=payload, headers=headers, timeout=timeout)


def scenario_a_403() -> None:
    print_header("Scenario A — 403 Test")
    payload = {
        "equipment_id": "equip-403",
        "payload": {"sensor": "temp", "value": 22},
    }
    response = post_json(payload, agent_key="bad-key")
    print_result("HTTP status", response.status_code)
    print_result("Expected", "403")
    print_result("Observed", "403" if response.status_code == 403 else "unexpected")


def scenario_b_422() -> None:
    print_header("Scenario B — 422 Test")
    payload = {
        "equipment_id": "equip-422",
        "payload": "this-should-be-a-dict",
    }
    response = post_json(payload, agent_key=VALID_AGENT_KEY)
    print_result("HTTP status", response.status_code)
    print_result("Expected", "422")
    print_result("Observed", "422" if response.status_code == 422 else "unexpected")
    print("\nPlease check the local quarantine folder at /quarantine/structural for the written payload.")


def scenario_c_429() -> None:
    print_header("Scenario C — 429 Volumetric Test")
    statuses: list[int] = []
    for index in range(1, 66):
        payload = {
            "equipment_id": "equip-429",
            "payload": {"sensor": "rpm", "value": index},
        }
        response = post_json(payload, agent_key=VALID_AGENT_KEY)
        statuses.append(response.status_code)

    print_result("Status codes", statuses)
    print_result("First 60", statuses[:60])
    print_result("Last 5", statuses[-5:])
    print_result("Expected", "First 60 -> 200, last 5 -> 429")
    print_result("Acceptance", "met" if statuses[:60].count(200) == 60 and statuses[-5:].count(429) == 5 else "not met")


def scenario_d_bypass() -> None:
    print_header("Scenario D — Bypass Test")
    statuses: list[int] = []
    for index in range(1, 101):
        payload = {
            "equipment_id": "equip-bypass",
            "payload": {"sensor": "alert", "value": index, "critical_alert": True},
        }
        response = post_json(payload, agent_key=VALID_AGENT_KEY)
        statuses.append(response.status_code)

    print_result("Status codes", statuses)
    print_result("Expected", "All 100 -> 200")
    print_result("Acceptance", "met" if statuses.count(200) == 100 else "not met")


def interactive_menu() -> None:
    print_header("Gateway Acceptance Test Injector")
    print("Choose a scenario to run against http://127.0.0.1:8000/ingest")
    print("A) 403 invalid agent_key")
    print("B) 422 invalid schema")
    print("C) 429 volumetric threshold")
    print("D) Bypass critical alert")
    print("Q) Quit")

    while True:
        choice = input("\nEnter choice [A/B/C/D/Q]: ").strip().upper()
        if choice == "A":
            scenario_a_403()
        elif choice == "B":
            scenario_b_422()
        elif choice == "C":
            scenario_c_429()
        elif choice == "D":
            scenario_d_bypass()
        elif choice in {"Q", "QUIT"}:
            print("Exiting test injector.")
            break
        else:
            print("Invalid choice. Please enter A, B, C, D, or Q.")


def main() -> int:
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().upper()
        if arg == "A":
            scenario_a_403()
        elif arg == "B":
            scenario_b_422()
        elif arg == "C":
            scenario_c_429()
        elif arg == "D":
            scenario_d_bypass()
        else:
            print("Unknown scenario. Use A, B, C, D, or no argument for the interactive menu.")
            return 2
        return 0

    interactive_menu()
    return 0


if __name__ == "__main__":
    sys.exit(main())
