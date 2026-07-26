# AgentGuard: Enterprise IoT Abstraction Mapping

## 1. System Overview (MedTech IoT Manufacturing)
This document maps the localized components of the AgentGuard micro-emulator to their enterprise-grade cloud equivalents. This architecture governs decentralized physical IoT traffic (e.g., synthetic insulin bioreactors), ensuring that broken hardware sensors or hyperactive firmware loops do not DDoS downstream cloud compute or poison the scientific data lake.

## 2. Infrastructure Component Mappings

* **FastAPI ➡️ Enterprise API Gateway (e.g., AWS API Gateway / AWS IoT Core)**
  * **Role:** Acts as the edge interception proxy. It authenticates physical equipment, enforces payload schema contracts to catch data drift (broken thermometers), and softly routes anomalous data to Quarantine.
* **Redis-mock ➡️ Distributed In-Memory Cache (e.g., AWS ElastiCache / Redis)**
  * **Role:** Functions as the local high-speed state tracker. It maintains the Requests-Per-Minute (RPM) volumetric counters for every localized piece of equipment, instantly triggering 429 Hard Drops if a sensor firmware crashes into a hyperactive loop.
* **Virtual VRAM (`asyncio.Queue`) ➡️ Distributed Event Streaming (e.g., Apache Kafka / AWS Kinesis)**
  * **Role:** Acts as the asynchronous backpressure buffer. It absorbs massive concurrent factory data uploads in volatile memory and dynamically flushes them to disk, proactively preventing localized storage I/O exhaustion.
* **Python `watchdog` ➡️ Cloud Event Triggers (e.g., AWS S3 Event Notifications)**
  * **Role:** Emulates event-driven orchestration. The exact millisecond an approved equipment payload lands in the Bronze raw storage layer, it triggers the downstream ETL transformation pipeline.
* **Nested JSON Directory ➡️ NoSQL Document Store (e.g., MongoDB / Zontal)**
  * **Role:** Preserves the deeply nested, hierarchical structure of the MedTech scientific observations (Data Package, Data Cube) into a harmonized Silver layer for FDA-compliant auditing.
* **Anthropic MCP Server ➡️ Enterprise Interoperability API**
  * **Role:** Acts as the secure programmatic adapter, fulfilling FAIR data principles (Findable, Accessible, Interoperable, Reusable) by allowing external enterprise AI systems and BI dashboards to query the Silver layer without direct database access.
