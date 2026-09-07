#!/usr/bin/env python3
"""NoSQL KPI report generator for system health (Day-2 ops).

Reads `logs/telemetry.log` and `data/silver_harmonized/` to produce
aggregated KPIs: successes, security drops (403), quarantines (422),
and quota breaches (429). Outputs to terminal and writes
reports/system_health_kpis.md.

Design notes:
- Time-boxed scanning via `--days` to avoid OOM when scanning large stores.
- Defensive parsing of all JSON with `.get()` fallbacks.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, Tuple, Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate System Health KPIs from logs and silver NoSQL cubes.")
    p.add_argument("--days", type=int, default=7, help="Look-back window in days (default: 7)")
    p.add_argument("--log-path", type=Path, default=Path("logs/telemetry.log"), help="Path to telemetry.log")
    p.add_argument("--silver-dir", type=Path, default=Path("data/silver_harmonized"), help="Silver directory")
    p.add_argument("--quarantine-dir", type=Path, default=Path("data/quarantine/etl_failed"), help="Quarantine directory")
    p.add_argument("--output", type=Path, default=Path("reports/system_health_kpis.md"), help="Output markdown report path")
    return p.parse_args()


def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def load_telemetry_log(path: Path, cutoff: datetime) -> Tuple[Counter, Dict[str, Counter]]:
    """Return a Counter of status codes and mapping client_ip -> Counter(status_code).

    Only includes entries whose `timestamp` is >= cutoff when present. If timestamp absent,
    the entry is included conservatively.
    """
    status_counts: Counter = Counter()
    ip_status: Dict[str, Counter] = defaultdict(Counter)

    if not path.exists():
        return status_counts, ip_status

    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                # Some lines may be non-json; skip
                continue

            ts = _parse_iso(rec.get("timestamp") or "")
            if ts is not None and ts < cutoff:
                continue

            code = rec.get("status_code")
            if isinstance(code, int):
                status_counts[code] += 1
                client_ip = rec.get("client_ip") or "unknown"
                ip_status[client_ip][code] += 1

    return status_counts, ip_status


def scan_silver(silver_dir: Path, cutoff: datetime) -> Counter:
    """Count successful payloads per equipment_id from silver Data Cubes.

    Returns Counter mapping equipment_id -> success_count.
    """
    counts: Counter = Counter()
    if not silver_dir.exists():
        return counts

    for root, _, files in os.walk(silver_dir):
        for fn in files:
            fp = Path(root) / fn
            try:
                mtime = datetime.fromtimestamp(fp.stat().st_mtime, tz=timezone.utc)
            except Exception:
                continue
            if mtime < cutoff:
                continue
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            equipment = data.get("dimensions", {}).get("equipment_id") or "unknown"
            counts[equipment] += 1

    return counts


def scan_quarantine(quarantine_dir: Path, cutoff: datetime) -> Counter:
    """Count quarantined payloads per equipment_id by inspecting quarantine JSON files."""
    counts: Counter = Counter()
    if not quarantine_dir.exists():
        return counts

    for root, _, files in os.walk(quarantine_dir):
        for fn in files:
            fp = Path(root) / fn
            try:
                mtime = datetime.fromtimestamp(fp.stat().st_mtime, tz=timezone.utc)
            except Exception:
                continue
            if mtime < cutoff:
                continue
            try:
                raw = fp.read_text(encoding="utf-8")
                doc = json.loads(raw)
            except Exception:
                continue

            # Attempt to extract equipment_id from multiple plausible locations
            equipment = None
            if isinstance(doc, dict):
                equipment = doc.get("equipment_id")
                if not equipment and isinstance(doc.get("payload"), dict):
                    equipment = doc.get("payload", {}).get("equipment_id")
                if not equipment and isinstance(doc.get("payload"), dict):
                    equipment = doc.get("payload", {}).get("equipment_id")
            if not equipment:
                equipment = "unknown"
            counts[equipment] += 1

    return counts


def render_table(rows: Iterable[Tuple[str, int, int, int]]) -> str:
    """Return a simple ASCII table for rows: (equipment, success, quarantine, security_drops)
    The rows should be pre-sorted by importance.
    """
    hdr = f"{'Equipment':<30} | {'Successes':>9} | {'Quarantines':>11} | {'SecurityDrops(403)':>18} | {'QuotaBreaches(429)':>18}\n"
    sep = "-" * (len(hdr) - 1) + "\n"
    lines = [hdr, sep]
    for equipment, succ, quarant, sec_drop in rows:
        lines.append(f"{equipment:<30} | {succ:9d} | {quarant:11d} | {sec_drop:18d} | {'n/a':>18}\n")
    return "".join(lines)


def write_markdown(output: Path, summary: Dict[str, Any], per_equipment: Iterable[Tuple[str, int, int, int]]):
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        fh.write("# System Health KPIs\n\n")
        fh.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n")
        fh.write("## Summary\n\n")
        fh.write(f"- Lookback days: {summary['days']}\n")
        fh.write(f"- Log entries scanned: {summary['log_entries']}\n")
        fh.write(f"- Total successes (silver files): {summary['total_successes']}\n")
        fh.write(f"- Total quarantined files: {summary['total_quarantines']}\n")
        fh.write(f"- Status counts: {json.dumps(summary['status_counts'], indent=2)}\n\n")
        fh.write("## Per-Equipment KPI Snapshot\n\n")
        fh.write("| Equipment | Successes | Quarantines | SecurityDrops(403) | QuotaBreaches(429) |\n")
        fh.write("|---|---:|---:|---:|---:|\n")
        for equipment, succ, quarant, sec_drop in per_equipment:
            fh.write(f"| {equipment} | {succ} | {quarant} | {sec_drop} | n/a |\n")


def main() -> int:
    args = parse_args()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=int(args.days))

    status_counts, ip_status = load_telemetry_log(Path(args.log_path), cutoff)
    silver_counts = scan_silver(Path(args.silver_dir), cutoff)
    quarantine_counts = scan_quarantine(Path(args.quarantine_dir), cutoff)

    total_successes = sum(silver_counts.values())
    total_quarantines = sum(quarantine_counts.values())
    total_log_entries = sum(status_counts.values())

    # Build per-equipment merged view
    equipment_keys = set(silver_counts) | set(quarantine_counts)
    per_equipment = []
    for eq in sorted(equipment_keys):
        per_equipment.append((eq, int(silver_counts.get(eq, 0)), int(quarantine_counts.get(eq, 0)), 0))

    # Identify top client IPs for 403 and 429
    top_403_ips = sorted(((ip, c.get(403, 0)) for ip, c in ip_status.items()), key=lambda x: -x[1])[:5]
    top_429_ips = sorted(((ip, c.get(429, 0)) for ip, c in ip_status.items()), key=lambda x: -x[1])[:5]

    # Print summary to terminal
    print("System Health KPI Report")
    print("Lookback days:", args.days)
    print()
    print("Overall status counts:")
    for code, cnt in sorted(status_counts.items()):
        print(f"  HTTP {code}: {cnt}")
    print()
    print("Top quarantined equipment:")
    for eq, cnt in quarantine_counts.most_common(10):
        print(f"  {eq}: {cnt}")
    print()
    print("Top client IPs with 403 (security drops):")
    for ip, cnt in top_403_ips:
        if cnt:
            print(f"  {ip}: {cnt}")
    print()
    print("Top client IPs with 429 (quota breaches):")
    for ip, cnt in top_429_ips:
        if cnt:
            print(f"  {ip}: {cnt}")

    # Terminal table for per-equipment (trim to top 25 by quarantines then successes)
    per_equipment_sorted = sorted(per_equipment, key=lambda r: (-r[2], -r[1]))[:25]
    print("\nPer-equipment snapshot:\n")
    print(render_table(per_equipment_sorted))

    # Persist executive summary
    summary = {
        "days": args.days,
        "log_entries": total_log_entries,
        "total_successes": total_successes,
        "total_quarantines": total_quarantines,
        "status_counts": dict(status_counts),
    }
    write_markdown(Path(args.output), summary, per_equipment_sorted)
    print(f"Wrote report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
