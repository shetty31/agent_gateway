# Performance Metrics Report

Generated: 2026-08-17T02:52:35.350997Z

## 1. SLO Latency Enforcement

- Measured requests: **500**
- Latency (count): 500
- Average latency: **22.92 ms**
- Min / P50 / P90 / P95 / Max: 6.87 / 19.73 / 31.16 / 36.03 / 90.62 ms
- SLO threshold: **50.0 ms**
- Result: **PASS** — P95 latency 36.03ms < 50.0ms (PASS)

![Latency Distribution](plots/latency_histogram.png)

![Status Codes](plots/status_codes.png)

## 2. Zero Data Loss Verification

- Total input payloads: **500**
- Approved (data/approved) files/item-count: **0**
- Quarantined (data/quarantine/structural) files/item-count: **0**
- Approved unique request_ids found: **0**
- Quarantined unique request_ids found: **0**
- HTTP 429 dropped: **0**
- HTTP 403 dropped: **500**

Mathematical reconciliation:
```text
Total Input = Approved + Quarantined + 429_drops + 403_drops
500 = 0 + 0 + 0 + 500
```
- Zero data loss verification: **PASS**
- Input request_ids observed: **500**
- Matched approved request_ids: **0**
- Matched quarantined request_ids: **0**
## 3. VRAM Backpressure Resilience

- Approved files written (data/approved): **0**
- Quarantine files written (data/quarantine/structural): **0**
- Runtime errors during requests: **0**
- VRAM buffer: **Potential issues detected** — verify runtime logs for memory allocation errors or dropped/errored requests.

## 4. Status Code Breakdown

| HTTP Status | Count | % of Total |
|---:|---:|---:|
| 403 | 500 | 100.00% |