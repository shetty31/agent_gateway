# AgentGuard Context: Master Roadmap & Deliverables (MedTech IoT Governance Edition)

## Objective
Build an IC6-level micro-emulator of an Enterprise IoT Gateway and Scientific Data Pipeline, featuring Volumetric RPM rate-limiting, Virtual VRAM dynamic batching, an Event-Driven Data Lakehouse, FAIR-compliant NoSQL contextualization, and an MCP interoperability adapter for programmatic BI.

---

## Phase 1: Foundation, Architecture & Version Control 

**Milestone 1: Project Initiation & System Security Architecture**
* **Plan:** Define the strategic GTM positioning and threat vectors for decentralized MedTech IoT data ingestion. Initialize the local version control environment.
* **Deliverables:**
  * `README.md` (Project overview and core IoT use cases).
  * `product_strategy_prd.md` (Executive GTM, RPM quota strategy, & platform SLOs).
  * Initialized Git workspace and `.gitignore`.

**Milestone 2: Enterprise Abstraction Mapping & Schema Contracts**
* **Plan:** Define the strict JSON payload structures for physical IoT sensors and the volumetric quota policies the system will enforce at the edge.
* **Deliverables:**
  * `architecture.md` (System design mapping localized tools to enterprise cloud equivalents).
  * `policy_config.yaml` (Defines RPM rate limits, authentication, and enforcement actions).
  * `inbound_schema.json` (JSON schema definitions for inbound MedTech equipment payloads).

---

## Phase 2: Autonomous Edge, Governance & Hardware Reliability 

**Milestone 3: FastAPI Gateway & RPM Circuit Breaker**
* **Plan:** Build the API interception proxy. Implement a localized high-speed counter (Redis-mock) to enforce Requests-Per-Minute (RPM) quotas on IoT hardware. The gateway must execute strict 403 HTTP rejections for unauthorized IPs and 429 HTTP rejections for hyperactive/broken sensors exceeding their volumetric quota.
* **Deliverables:**
  * `gateway.py` (FastAPI interception layer).
  * `redis_mock.py` (Local RPM rate limiter and quota tracker).

**Milestone 4: Soft Validation (Quarantine) & Volatile Hardware Buffer**
* **Plan:** Build qualitative schema validation to detect data drift (e.g., broken thermometers reporting anomalous values). Route malformed payloads to a `/quarantine/` directory to preserve raw observations without poisoning the data lake. Implement an `asyncio` VRAM buffer to absorb extreme concurrent traffic spikes and prevent downstream disk I/O exhaustion.
* **Deliverables:**
  * `virtual_vram_batcher.py` (Asyncio memory buffer).
  * Integrated quarantine routing logic in `gateway.py`.

---

## Phase 3: High-Throughput Stress Testing

**Milestone 5: IoT Swarm Simulation**
* **Plan:** Build an asynchronous Python script that mimics a massive, decentralized network of autonomous MedTech sensors hitting the API Gateway concurrently to simulate real-world factory traffic spikes and broken sensor loops.
* **Deliverables:**
  * `load_tester.py` (High-velocity simulated client).

**Milestone 6: System Profiling & Remediation**
* **Plan:** Execute the simulation, observe how the system handles backpressure, ensure the hard drops (403/429) execute in <50ms, and verify no data is lost to race conditions.
* **Deliverables:**
  * `performance_metrics.md` (Log of the stress test results).
  * Code remediations and architectural patches as required.

---

## Phase 4: Event-Driven Orchestration & Programmatic BI

**Milestone 7: Watchdog Event Listener (The Orchestrator)**
* **Plan:** Emulate enterprise cloud event triggers (e.g., AWS S3 Event Notifications). When a valid JSON payload is safely flushed from VRAM to the raw Bronze storage layer, the operating system must instantly detect the file and trigger the ETL transformation pipeline.
* **Deliverables:**
  * `event_listener.py` (Python Watchdog OS observer).
  * Basic ETL parsing logic (appends `processing_timestamp` and `parser_script_version`).

**Milestone 8: NoSQL Document Handling, MCP Server & Programmatic BI**
* **Plan:** Restructure the valid IoT payloads into a strict enterprise schema and save them as deeply nested JSONs in a Silver harmonized directory. Build a BI script to query these files for system health KPIs (e.g., Gateway Drop Rate, Quarantine Volume). Wrap the directory in an Anthropic Model Context Protocol (MCP) Server adapter to allow external AI agents to securely query the database.
* **Deliverables:**
  * Established `/agentguard_data/bronze_raw/` and `/agentguard_data/silver_harmonized/` directories.
  * `kpi_report_generator.py` (Programmatic NoSQL BI query script).
  * MCP Server configuration file.
  * Auto-generated `DATA_DICTIONARY_AND_CONTRACTS.md`.

---

## Phase 5: Polish & Portfolio Delivery

**Milestone 9: System Integration Audits**
* **Plan:** Run the entire pipeline from end-to-end (Cold-start) to ensure the FastAPI Gateway, VRAM Buffer, Event-Listener, and MCP adapter orchestrate flawlessly together.
* **Deliverables:**
  * Remediation of any integration bugs or boot-sequence race conditions.

**Milestone 10: Final Case Study Production**
* **Plan:** Generate final developer documentation, summarizing the architectural trade-offs made during the build to present to the hiring manager.
* **Deliverables:**
  * `ADR_LOG.md` (Architecture Decision Records).
  * `DEVELOPER_QUICKSTART.md`.
