# AgentGuard: Product Requirements & IoT Governance Strategy

## 1. The Executive Summary & Business Problem
As enterprise MedTech manufacturing networks scale (e.g., decentralized bioreactors producing synthetic insulin), legacy infrastructure faces a critical vulnerability: **"Shadow IoT Ingestion."** Without a centralized edge governance layer, thousands of physical factory sensors write directly to central scientific data lakes. This creates three critical business risks:
* **Infrastructure DDoS (Hyperactive Sensors):** If a bioreactor's firmware crashes and gets stuck in a retry loop, it can fire 5,000 payloads per second, triggering expensive downstream cloud ETL pipelines and DDoSing the central data lake.
* **Data Poisoning (Hardware Data Drift):** If a physical thermometer cracks, it may report biological temperatures of `9999°C`. Without edge validation, this anomalous data irreversibly corrupts the downstream scientific database.
* **Storage I/O Exhaustion:** Concurrent end-of-shift factory data uploads overwhelm cloud storage I/O, causing disk locks and dropping critical compliance data.

## 2. The Product Solution
AgentGuard is positioned as a frictionless, highly regulated "air-traffic control tower" for MedTech IoT data ingestion. It acts as an intelligent edge proxy sitting between the factory floor and the enterprise data lakehouse. 

Instead of trusting the hardware endpoint, AgentGuard provides programmatic safety. It authenticates physical equipment, enforces strict Requests-Per-Minute (RPM) volumetric quotas to prevent DDoS, validates qualitative JSON schemas to catch broken sensors, buffers hardware traffic spikes in volatile RAM, and establishes unbreakable chain-of-custody metadata for every payload.

---

## 3. Threat Model & Governance Boundaries
To protect the enterprise architecture, AgentGuard enforces strict separation of concerns at the edge proxy layer, catching physical hardware failures before data ever touches the cloud.

| Hardware Failure Vector | Governance Boundary | System Action |
| :--- | :--- | :--- |
| **Unauthorized Access** (Unregistered Equipment) | Edge Proxy Authentication | **Hard Drop (403):** Connection terminated instantly. |
| **Hyperactive Firmware Loop** (Internal DDoS) | Volumetric RPM Quota | **Hard Drop (429):** Connection terminated instantly at the edge. Protects cloud ETL compute from runaway sensor traffic. |
| **Data Drift / Broken Sensor** (Anomalous readings) | FastAPI Schema Contracts | **Soft Validation:** Payload bypassed from main pipeline, tagged with error metadata, and routed to `/quarantine/` to preserve raw observations for hardware debugging without poisoning the clean lakehouse. |
| **Storage I/O Crash** (Concurrent traffic spike) | Virtual VRAM Dynamic Batching | **Queue & Flush:** Traffic absorbed in volatile RAM and flushed to disk dynamically based on volume thresholds. |

---

## 4. Platform Value Delivery
AgentGuard serves two distinct enterprise customers, proving both hardware observability and scientific data interoperability.

* **Customer A: The Enterprise Business (The Science & Supply Chain)**
  * **The Goal:** Seamless access to clean, FDA-compliant scientific data.
  * **The Delivery:** Valid observations are transformed into a deeply nested enterprise schema (Data Package, Data Cube, Data Description) in the Silver layer. This is wrapped in an Anthropic Model Context Protocol (MCP) adapter, achieving FAIR (Findable, Accessible, Interoperable, Reusable) data principles for external BI consumption.
* **Customer B: The Platform Owner (System Health & Hardware Reliability)**
  * **The Goal:** Real-time visibility into edge hardware failures.
  * **The Delivery:** A programmatic NoSQL BI script queries the telemetry metadata to output System Health KPIs, instantly identifying specific physical factories that require hardware repair based on Quarantine Rates and 429 Quota Breaches.

---

## 5. Success Metrics & Platform SLOs
* **Volumetric Protection:** System must execute 429 Hard Drops the exact millisecond a sensor breaches its configured RPM limit.
* **Data Truth Integrity:** 100% of payloads containing out-of-bounds scientific data must be successfully diverted to Quarantine.
* **System Latency:** Gateway interception, quota tracking, and schema validation must execute in < 50ms overhead per request.
* **Data Accessibility:** Harmonized NoSQL data must be fully queryable via the MCP adapter without requiring manual data engineering intervention.
