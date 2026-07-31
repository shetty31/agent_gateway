# AgentGuard Context: Master Roadmap & Deliverables (MedTech IoT Governance Edition)

**Objective**
Build an IC6-level micro-emulator of an Enterprise IoT Gateway and Scientific Data Pipeline, featuring Volumetric RPM rate-limiting, Virtual VRAM dynamic batching, an Event-Driven Data Lakehouse, FAIR-compliant NoSQL contextualization, and an MCP interoperability adapter for programmatic BI.

**Execution & Testing Protocol (AI vs. TPO)**
To simulate an enterprise environment and maintain a pristine Git timeline, development follows strict governance:

* **Version Control Strategy:** Iterative, atomic commits within dedicated feature branches (e.g., `feature/milestone-3-gateway`) per milestone. No direct active development on `main`.
* **The AI Execution Agent (Engineer):** Responsible for writing the Python syntax and autonomously generating/passing all Unit Tests (White-Box testing of isolated functions, concurrency locks, and state management).
* **The Technical Product Owner (You):** Responsible for managing the `master_spec_backlog.md` (UAT Ledger) and executing Integration/End-to-End Tests (Black-Box testing via terminal commands) to validate business logic and system outcomes.

---

### Phase 1: Foundation, Architecture & Version Control

**Milestone 1: Project Initiation & System Security Architecture**

* **Plan:** Define the strategic GTM positioning and threat vectors for decentralized MedTech IoT data ingestion. Initialize the local version control environment and virtual sandbox.
* **Deliverables:**
* `README.md` (Project overview and core IoT use cases).
* `product_strategy_prd.md` (Executive GTM, RPM quota strategy, & platform SLOs).
* Initialized Git workspace, `.gitignore`, Python Virtual Environment (`venv`), and `dependency.md` (Step Zero).



**Milestone 2: Enterprise Abstraction Mapping & Schema Contracts**

* **Plan:** Define the strict JSON payload structures for physical IoT sensors, the volumetric quota policies, and strict secrets management.
* **Deliverables:**
* `architecture.md` (System design mapping).
* `gateway_policy.yml` (Dedicated edge security file defining RPM limits and IP whitelists).
* `inbound_schema.json` (JSON schema definitions).
* `.env` file (Secrets management parsed by `pydantic-settings`).
* `master_spec_backlog.md` (Initialization of the single-source Agile backlog for UAT).



---

### Phase 2: Autonomous Edge, Governance & Hardware Reliability

**Milestone 3: FastAPI Gateway, RPM Circuit Breaker & Structural Quarantine**

* **Plan:** Build the API interception proxy. Implement a localized high-speed counter (`redis_mock.py`) with concurrency controls (`asyncio.Lock()`). The gateway must execute strict 403 Hard Drops for unauthorized IPs and 429 Hard Drops for hyperactive sensors. Malformed schemas will trigger a 422 error and route directly to a local disk quarantine via Hive partitioning.
* **Observability Requirement:** FastAPI Middleware must intercept all traffic and output structured JSON logs to `telemetry.log` capturing P95 latency and HTTP status codes.
* **Deliverables:**
* `redis_mock.py` (Local RPM rate limiter).
* `gateway.py` (FastAPI interception layer).
* Hive Partitioning utility (`/quarantine/structural/year=YYYY/month=MM/day=DD/`).



**Milestone 4: Virtual VRAM Buffer & Dynamic Batching**

* **Plan:** Implement an asyncio memory buffer to absorb extreme concurrent traffic spikes (200 OK traffic only). Data must be dynamically flushed to disk based on strict volume or time thresholds. *(Note: Qualitative Data Drift analytics are explicitly scoped out to preserve edge compute focus).*
* **Resilience Requirement:** Must include a Graceful Shutdown (`SIGINT`) handler to flush unwritten memory to disk if the server crashes.
* **Deliverables:**
* `virtual_vram_batcher.py` (Asyncio memory buffer).
* Approved Hive directory outputs (`/approved/year=YYYY/month=MM/day=DD/`).



---

### Phase 3: High-Throughput Stress Testing

**Milestone 5: IoT Swarm Simulation (The Hammer)**

* **Plan:** Build an asynchronous Python script that mimics a massive, decentralized network of autonomous MedTech sensors hitting the API Gateway concurrently to simulate real-world factory traffic spikes and broken sensor loops.
* **Deliverables:**
* `load_tester.py` (High-velocity simulated client).



**Milestone 6: System Profiling & Remediation (The Measurement)**

* **Plan:** Execute the simulation, observe how the VRAM handles backpressure, ensure the hard drops (403/429) execute in <50ms, and verify no data is lost to race conditions.
* **Deliverables:**
* `performance_metrics.md` (Log of the stress test results).
* Code remediations and architectural patches as required.



---

### Phase 4: Event-Driven Orchestration & Programmatic BI

**Milestone 7: Watchdog Event Listener (The Orchestrator)**

* **Plan:** Emulate enterprise cloud event triggers (e.g., AWS S3 Event Notifications). When a valid JSON payload is safely flushed from VRAM to the raw Bronze storage layer, the operating system must instantly detect the file and trigger the ETL transformation pipeline.
* **Deliverables:**
* `event_listener.py` (Python Watchdog OS observer).
* Basic ETL parsing logic (appends `processing_timestamp` and `parser_script_version`).



**Milestone 8: NoSQL Document Handling, MCP Server & Programmatic BI**

* **Plan:** Restructure the valid IoT payloads into a strict enterprise schema and save them as deeply nested JSONs in a Silver harmonized directory. Build a BI script to query these files for system health KPIs (e.g., Gateway Drop Rate). Wrap the directory in an Anthropic Model Context Protocol (MCP) Server adapter to allow external AI agents to securely query the database.
* **Deliverables:**
* Established `/agentguard_data/bronze_raw/` and `/agentguard_data/silver_harmonized/` directories.
* `kpi_report_generator.py` (Programmatic NoSQL BI query script).
* MCP Server configuration file (defining Exposed Resources and Allowed Tools).
* Auto-generated `DATA_DICTIONARY_AND_CONTRACTS.md`.



---

### Phase 5: Polish & Portfolio Delivery

**Milestone 9: System Integration Audits & Orchestration**

* **Plan:** Build a master bootstrapper script to orchestrate the simultaneous startup of the Gateway, VRAM Buffer, Event-Listener, and MCP adapter. Run the entire pipeline end-to-end (Cold-start) using this single entrypoint to ensure flawless integration and prevent terminal sprawl.
* **Deliverables:**
* `system_orchestrator.py` (or `start_pipeline.sh`): The master execution script.
* Remediation of any integration bugs or boot-sequence race conditions.



**Milestone 10: Final Case Study Production**

* **Plan:** Generate final developer documentation, summarizing the architectural trade-offs made during the build to present to the hiring manager. Ensure native documentation features are enabled.
* **Deliverables:**
* `ADR_LOG.md` (Architecture Decision Records).
* `DEVELOPER_QUICKSTART.md`.
* Visual validation of FastAPI's auto-generated OpenAPI (Swagger) UI at `/docs`.