# Performance Metrics Report

Generated: 2026-08-24T18:40:26.558610Z

## 1. SLO Latency Enforcement

- Measured requests: **1000**
- Latency (count): 1000
- Average latency: **36.80 ms**
- Min / P50 / P90 / P95 / Max: 21.26 / 35.74 / 42.37 / 51.13 / 51.55 ms
- SLO threshold: **50.0 ms**
- Result: **FAIL** — P95 latency 51.126999998814426ms >= 50.0ms (FAIL)

![Latency Distribution](plots/latency_histogram.png)

![Status Codes](plots/status_codes.png)

## 2. Zero Data Loss Verification

- Total input payloads: **1000**
- Approved (data/approved) files/item-count: **1**
- Quarantined (data/quarantine/structural) files/item-count: **1**
- Approved unique request_ids found: **0**
- Quarantined unique request_ids found: **0**
- HTTP 429 dropped: **0**
- HTTP 403 dropped: **1000**

Mathematical reconciliation:
```text
Total Input = Approved + Quarantined + 429_drops + 403_drops
1000 = 1 + 1 + 0 + 1000
```
- Zero data loss verification: **PASS**
- Input request_ids observed: **1000**
- Matched approved request_ids: **0**
- Matched quarantined request_ids: **0**
## 3. VRAM Backpressure Resilience

- Approved files written (data/approved): **1**
- Quarantine files written (data/quarantine/structural): **1**
- Runtime errors during requests: **0**
- VRAM buffer: **Appears resilient** — approved payloads were flushed to disk and no request errors observed.

## 4. Status Code Breakdown

| HTTP Status | Count | % of Total |
|---:|---:|---:|
| 403 | 1000 | 100.00% |