#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:
    plt = None  # plotting is optional


def load_results(path: Path) -> List[Dict[str, Any]]:
    content = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(content, dict) and "results" in content:
        return content["results"]
    if isinstance(content, list):
        return content
    raise ValueError("Unsupported results JSON format: expect list or {results: [...]}" )


def latency_stats(latencies: Iterable[float]) -> Dict[str, Optional[float]]:
    lat = sorted([l for l in latencies if l is not None])
    if not lat:
        return {"count": 0, "min": None, "max": None, "avg": None, "p50": None, "p90": None, "p95": None}
    def pct(p: float) -> float:
        idx = max(0, min(len(lat) - 1, math.ceil((p / 100.0) * len(lat)) - 1))
        return lat[idx]
    return {
        "count": len(lat),
        "min": min(lat),
        "max": max(lat),
        "avg": mean(lat),
        "p50": median(lat),
        "p90": pct(90),
        "p95": pct(95),
    }


def scan_partition_counts(root: Path, subpath: str) -> int:
    # New behavior: return both total count and set of request ids found
    folder = root / subpath
    if not folder.exists():
        return 0
    total = 0
    for f in folder.rglob("*.json"):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(obj, list):
                total += len(obj)
            elif isinstance(obj, dict):
                total += 1
            else:
                total += 1
        except Exception:
            total += 1
    return total


def extract_request_ids(root: Path, subpath: str) -> set[str]:
    ids: set[str] = set()
    folder = root / subpath
    if not folder.exists():
        return ids

    for f in folder.rglob("*.json"):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue

        def collect_from_item(item: Any) -> None:
            if isinstance(item, dict):
                # direct request id on the item
                rid = item.get("_request_id")
                if rid:
                    ids.add(str(rid))
                    return
                # nested payload
                payload = item.get("payload")
                if isinstance(payload, dict):
                    prid = payload.get("_request_id") or payload.get("_requestid") or payload.get("request_id")
                    if prid:
                        ids.add(str(prid))
                        return
                # some payloads may embed id at different keys
                for key in ("request_id", "req_id", "_req_id"):
                    if key in item:
                        ids.add(str(item[key]))
                        return

        if isinstance(obj, list):
            for it in obj:
                collect_from_item(it)
        elif isinstance(obj, dict):
            collect_from_item(obj)

    return ids


def generate_markdown_report(
    results: List[Dict[str, Any]],
    data_root: Path,
    output_path: Path,
    slo_threshold_ms: float = 50.0,
) -> None:
    total_input = len(results)
    statuses = Counter()
    errors = Counter()
    latencies = []
    for r in results:
        status = r.get("status")
        if status is None:
            # network / timeout errors
            errors[r.get("error") or "unknown"] += 1
        else:
            statuses[int(status)] += 1
        if r.get("latency_ms") is not None:
            latencies.append(float(r.get("latency_ms")))

    latency_summary = latency_stats(latencies)
    # prepare plots if matplotlib is available
    plots_dir = output_path.parent / "plots"
    if plt is not None:
        plots_dir.mkdir(parents=True, exist_ok=True)
        try:
            if latencies:
                fig, ax = plt.subplots()
                ax.hist(latencies, bins=30, color="#3b82f6", edgecolor="#0b3d91")
                ax.set_title("Request Latency Distribution (ms)")
                ax.set_xlabel("Latency (ms)")
                ax.set_ylabel("Count")
                latency_png = plots_dir / "latency_histogram.png"
                fig.savefig(latency_png, bbox_inches="tight")
                plt.close(fig)
            else:
                latency_png = None

            if statuses:
                fig, ax = plt.subplots()
                items = sorted(statuses.items())
                keys = [str(k) for k, _ in items]
                vals = [v for _, v in items]
                ax.bar(keys, vals, color="#10b981")
                ax.set_title("HTTP Status Codes")
                ax.set_xlabel("Status")
                ax.set_ylabel("Count")
                status_png = plots_dir / "status_codes.png"
                fig.savefig(status_png, bbox_inches="tight")
                plt.close(fig)
            else:
                status_png = None
        except Exception:
            latency_png = None
            status_png = None
    else:
        latency_png = None
        status_png = None

    # scan data folders (counts + request id extraction for reconciliation)
    approved_count = scan_partition_counts(data_root, "approved")
    quarantine_count = scan_partition_counts(data_root, "quarantine/structural")
    approved_ids = extract_request_ids(data_root, "approved")
    quarantine_ids = extract_request_ids(data_root, "quarantine/structural")

    count_429 = statuses.get(429, 0)
    count_403 = statuses.get(403, 0)
    count_422 = statuses.get(422, 0)
    count_200 = statuses.get(200, 0)

    total_outputs = len(approved_ids) + len(quarantine_ids) + count_429 + count_403

    # SLO check - we approximate component overhead by overall latency
    slo_enforced = False
    slo_msg = ""
    if latency_summary["p95"] is not None and latency_summary["p95"] < slo_threshold_ms:
        slo_enforced = True
        slo_msg = f"P95 latency {latency_summary['p95']:.2f}ms < {slo_threshold_ms}ms (PASS)"
    else:
        slo_msg = f"P95 latency {latency_summary.get('p95')}ms >= {slo_threshold_ms}ms (FAIL)"

    # VRAM resilience heuristics
    vram_resilient = (approved_count > 0) and (len(errors) == 0)

    # Zero data loss math: reconcile by request ids when available
    input_ids = set()
    for r in results:
        if r.get("request_id"):
            input_ids.add(str(r.get("request_id")))

    # if request ids are present in results, use them for a stricter reconciliation
    matched_approved = set()
    matched_quarantine = set()
    unmatched_input = set()
    results_status: Dict[str, int] = {}
    if input_ids:
        for r in results:
            rid = r.get("request_id")
            if rid:
                results_status[str(rid)] = int(r.get("status")) if r.get("status") is not None else None

        matched_approved = input_ids.intersection(approved_ids)
        matched_quarantine = input_ids.intersection(quarantine_ids)

        # expected outputs include approved, quarantined, and status-coded drops
        expected_outputs_count = len(matched_approved) + len(matched_quarantine) + count_429 + count_403

        # zero loss if every input id is either present in outputs or recorded as a status-coded drop
        zero_loss = (len(input_ids) == expected_outputs_count)

        # unmatched inputs: those with status 200 (or None) that are not found in approved/quarantine
        for rid in input_ids:
            st = results_status.get(rid)
            if st == 200 and rid not in matched_approved and rid not in matched_quarantine:
                unmatched_input.add(rid)
    else:
        zero_loss = (total_input == total_outputs)

    # Build markdown
    lines: List[str] = []
    lines.append(f"# Performance Metrics Report\n")
    lines.append(f"Generated: {datetime.utcnow().isoformat()}Z\n")

    lines.append("## 1. SLO Latency Enforcement\n")
    lines.append(f"- Measured requests: **{total_input}**")
    lines.append(f"- Latency (count): {latency_summary['count']}")
    if latency_summary['avg'] is not None:
        lines.append(f"- Average latency: **{latency_summary['avg']:.2f} ms**")
        lines.append(f"- Min / P50 / P90 / P95 / Max: {latency_summary['min']:.2f} / {latency_summary['p50']:.2f} / {latency_summary['p90']:.2f} / {latency_summary['p95']:.2f} / {latency_summary['max']:.2f} ms")
    else:
        lines.append("- Latency: n/a")
    lines.append(f"- SLO threshold: **{slo_threshold_ms} ms**")
    lines.append(f"- Result: **{('PASS' if slo_enforced else 'FAIL')}** — {slo_msg}\n")

    # embed plots into report
    if latency_png:
        rel = latency_png.relative_to(output_path.parent)
        lines.append(f"![Latency Distribution]({rel})\n")
    if status_png:
        rel = status_png.relative_to(output_path.parent)
        lines.append(f"![Status Codes]({rel})\n")

    lines.append("## 2. Zero Data Loss Verification\n")
    lines.append(f"- Total input payloads: **{total_input}**")
    lines.append(f"- Approved (data/approved) files/item-count: **{approved_count}**")
    lines.append(f"- Quarantined (data/quarantine/structural) files/item-count: **{quarantine_count}**")
    lines.append(f"- Approved unique request_ids found: **{len(approved_ids)}**")
    lines.append(f"- Quarantined unique request_ids found: **{len(quarantine_ids)}**")
    lines.append(f"- HTTP 429 dropped: **{count_429}**")
    lines.append(f"- HTTP 403 dropped: **{count_403}**")
    lines.append("")
    lines.append("Mathematical reconciliation:")
    lines.append("```text")
    lines.append(f"Total Input = Approved + Quarantined + 429_drops + 403_drops")
    lines.append(f"{total_input} = {approved_count} + {quarantine_count} + {count_429} + {count_403}")
    lines.append("```")
    lines.append(f"- Zero data loss verification: **{('PASS' if zero_loss else 'FAIL')}**")
    if input_ids:
        lines.append(f"- Input request_ids observed: **{len(input_ids)}**")
        lines.append(f"- Matched approved request_ids: **{len(matched_approved)}**")
        lines.append(f"- Matched quarantined request_ids: **{len(matched_quarantine)}**")
        if unmatched_input:
            lines.append("")
            lines.append("Unmatched input request_ids (samples):")
            for uid in list(unmatched_input)[:20]:
                lines.append(f"- {uid}")
            lines.append("")
    else:
        if not zero_loss:
            lines.append(f"- Discrepancy: **{total_input - total_outputs}** (positive = missing outputs)\n")
        else:
            lines.append("- No discrepancy detected.\n")

    lines.append("## 3. VRAM Backpressure Resilience\n")
    lines.append(f"- Approved files written (data/approved): **{approved_count}**")
    lines.append(f"- Quarantine files written (data/quarantine/structural): **{quarantine_count}**")
    lines.append(f"- Runtime errors during requests: **{sum(errors.values())}**")
    if vram_resilient:
        lines.append("- VRAM buffer: **Appears resilient** — approved payloads were flushed to disk and no request errors observed.")
    else:
        lines.append("- VRAM buffer: **Potential issues detected** — verify runtime logs for memory allocation errors or dropped/errored requests.")
    lines.append("")

    lines.append("## 4. Status Code Breakdown\n")
    lines.append("| HTTP Status | Count | % of Total |\n|---:|---:|---:|")
    for status, cnt in sorted(statuses.items()):
        pct = (cnt / total_input) * 100 if total_input else 0.0
        lines.append(f"| {status} | {cnt} | {pct:.2f}% |")
    if errors:
        lines.append("\nErrors encountered (network/timeouts):\n")
        for err, cnt in errors.items():
            lines.append(f"- {err}: {cnt}")

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    # Write data manifest for the run (counts and reconciliation summary)
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "approved_count": approved_count,
        "quarantine_count": quarantine_count,
        "approved_ids_count": len(approved_ids),
        "quarantine_ids_count": len(quarantine_ids),
        "statuses": dict(statuses),
        "errors": dict(errors),
        "matched_approved_count": len(matched_approved) if isinstance(matched_approved, set) else 0,
        "matched_quarantine_count": len(matched_quarantine) if isinstance(matched_quarantine, set) else 0,
        "zero_loss": bool(zero_loss),
        "slo_pass": bool(slo_enforced),
    }
    manifest_path = output_path.parent / "data_manifest.json"
    try:
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    except Exception:
        pass


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate performance report from load tester metrics.")
    p.add_argument("--input", type=Path, required=False, help="Path to JSON results file. If omitted, looks for load_tester_results.json in CWD.")
    p.add_argument("--data-root", type=Path, default=Path.cwd() / "data", help="Root of data partitions (default: ./data)")
    p.add_argument("--output", type=Path, default=Path.cwd() / "reports" / "performance_metrics.md", help="Output markdown path")
    p.add_argument("--slo", type=float, default=50.0, help="SLO threshold in ms for p95 latency")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input or (Path.cwd() / "load_tester_results.json")
    if not input_path.exists():
        print(f"Error: results file not found at {input_path}")
        return 2
    try:
        results = load_results(input_path)
    except Exception as exc:
        print(f"Error reading results: {exc}")
        return 2

    try:
        generate_markdown_report(results, args.data_root, args.output, slo_threshold_ms=args.slo)
    except Exception as exc:
        print(f"Failed to generate report: {exc}")
        return 3

    print(f"Report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
