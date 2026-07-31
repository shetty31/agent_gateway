# AgentGuard: Enterprise IoT Abstraction Mapping

## 1. System Overview (MedTech IoT Manufacturing)

This document maps the localized components of the AgentGuard micro-emulator to their enterprise-grade cloud equivalents. This architecture governs decentralized physical IoT traffic (e.g., synthetic insulin bioreactors), ensuring that broken hardware sensors or hyperactive firmware loops do not DDoS downstream cloud compute, exhaust storage I/O, or crash downstream ETL pipelines with structurally malformed data.

## 2. Infrastructure Component Mappings

* **FastAPI Middleware ➡️ Enterprise Observability (e.g., Datadog / AWS CloudWatch)**
* **Role:** Acts as the outer-edge telemetry tracker. Intercepts all inbound traffic to log P95 latency and HTTP status codes into structured JSON files (`telemetry.log`), guaranteeing Day-2 operational visibility.


* **FastAPI Routing & Pydantic ➡️ Enterprise API Gateway (e.g., AWS API Gateway / AWS IoT Core)**
* **Role:** Acts as the edge interception proxy. It authenticates physical equipment (403 Hard Drops), enforces strict structural schema contracts, and routes malformed JSON payloads (422) directly to a local Hive-partitioned Quarantine.


* **Redis-mock + `asyncio.Lock()` ➡️ Distributed In-Memory Cache (e.g., AWS ElastiCache / Redis)**
* **Role:** Functions as the local high-speed state tracker with strict concurrency controls. It maintains the Requests-Per-Minute (RPM) volumetric counters for every localized piece of equipment, instantly triggering 429 Hard Drops if a sensor firmware crashes into a hyperactive loop.


* **Virtual VRAM (`asyncio.Queue`) ➡️ Distributed Event Streaming (e.g., Apache Kafka / AWS Kinesis)**
* **Role:** Acts as the asynchronous backpressure buffer. It absorbs massive concurrent `200 OK` factory data uploads in volatile memory and dynamically flushes them via Hive Partitioning to disk based on strict volume or time thresholds, proactively preventing localized storage I/O exhaustion.


* **Python `watchdog` ➡️ Cloud Event Triggers (e.g., AWS S3 Event Notifications)**
* **Role:** Emulates event-driven orchestration. The exact millisecond an approved equipment payload lands in the Bronze raw storage layer, it triggers the downstream ETL transformation pipeline.


* **Nested JSON Directory ➡️ NoSQL Document Store (e.g., MongoDB / Zontal)**
* **Role:** Preserves the deeply nested, hierarchical structure of the MedTech scientific observations (Data Package, Data Cube) into a harmonized Silver layer for FDA-compliant auditing.


* **Anthropic MCP Server ➡️ Enterprise Interoperability API**
* **Role:** Acts as the secure programmatic adapter, fulfilling FAIR data principles (Findable, Accessible, Interoperable, Reusable) by allowing external enterprise AI systems and BI dashboards to query the Silver layer without direct database access.


* **Python Bootstrapper (`system_orchestrator.py`) ➡️ Container Orchestration (e.g., Docker Compose / Kubernetes)**
* **Role:** Solves the Day-2 "Terminal Sprawl" problem. Orchestrates the simultaneous local startup, integration, and graceful shutdown (`SIGINT` handling) of all discrete microservices via a single entrypoint.