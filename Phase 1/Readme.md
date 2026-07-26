# AgentGuard: Enterprise IoT Edge Governance & Data Pipeline

## Executive Summary & Core Use Case
AgentGuard is an end-to-end edge governance proxy and Medallion data pipeline built for high-throughput MedTech IoT environments. 

**The Business Problem:** In decentralized manufacturing (e.g., autonomous bioreactors producing synthetic insulin), if a physical sensor's firmware crashes and gets stuck in a retry loop, it can flood the network with malformed, high-velocity payloads. Without strict edge governance, this "Shadow IoT" traffic triggers expensive downstream cloud ETL jobs, exhausts storage I/O, and permanently poisons the central scientific data lakehouse.

**The Solution:** AgentGuard acts as the strict "air-traffic control tower" at the extreme edge. It authenticates physical equipment, enforces Requests-Per-Minute (RPM) volumetric quotas to prevent internal infrastructure DDoS attacks, quarantines anomalous scientific data to protect data truth, buffers hardware traffic spikes in volatile RAM, and perfectly standardizes clean data for programmatic BI and external interoperability.

---

## System Architecture & Pipeline Orchestration
This micro-emulator maps localized Python components directly to enterprise-grade cloud paradigms (e.g., AWS API Gateway, ElastiCache, Kafka, S3 Event Notifications).

1. **Edge Ingestion & QoS Routing (FastAPI + Redis):** Intercepts all equipment payloads. Authenticates endpoints and enforces strict volumetric RPM quotas. 
2. **Backpressure Buffer (Asyncio VRAM):** Surviving traffic is asynchronously buffered in volatile memory and dynamically flushed to disk, preventing storage I/O locks during concurrent factory data uploads.
3. **Event-Driven ETL (Watchdog OS Listener):** The exact millisecond raw data lands in the Bronze storage layer, a localized event listener triggers the transformation pipeline, validating the schema and appending immutable chain-of-custody metadata.
4. **Programmatic BI & Interoperability (NoSQL + MCP):** Clean data is harmonized into a Silver directory. A localized BI script queries system health KPIs (e.g., 429 Hard Drop Rates), and an Anthropic Model Context Protocol (MCP) adapter exposes the FAIR-compliant scientific data for secure external query.

---

## Hardware Failure Remediation Logic
AgentGuard is explicitly designed to catch physical hardware failures before they reach the cloud computing layer.

* **Unauthorized Equipment:** Unregistered sensors missing authorization instantly trigger a **403 Hard Drop**.
* **Hyperactive Firmware (DDoS Risk):** Broken sensors exceeding their baseline RPM quota trigger a **429 Hard Drop**, protecting downstream compute.
* **Data Drift (Broken Thermometers):** Sensors reporting structurally anomalous readings (e.g., `9999°C`) fail strict schema validation. They are diverted via soft-routing to a **`/quarantine/`** directory to preserve raw observations for hardware debugging without poisoning the clean lakehouse.
