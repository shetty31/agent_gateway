# AgentGuard: Enterprise IoT Abstraction Mapping

## 1. System Overview (MedTech IoT Manufacturing)

This document maps the localized components of the AgentGuard micro-emulator to their enterprise-grade cloud equivalents. This architecture governs decentralized physical IoT traffic (e.g., synthetic insulin bioreactors), ensuring that broken hardware sensors or hyperactive firmware loops do not DDoS downstream cloud compute, exhaust storage I/O, or crash downstream ETL pipelines with structurally malformed data.

## 2. Infrastructure Component Mappings

# AgentGuard: Enterprise IoT Abstraction Mapping

## 1. System Overview (MedTech IoT Manufacturing)

This document maps the localized components of the AgentGuard micro-emulator to their enterprise-grade cloud equivalents. This architecture governs decentralized physical IoT traffic (e.g., synthetic insulin bioreactors), ensuring that broken hardware sensors or hyperactive firmware loops do not DDoS downstream cloud compute, exhaust storage I/O, or crash downstream ETL pipelines with structurally malformed data.

Ultimately, this abstraction serves a dual-customer delivery model: providing FAIR-compliant, AI-ready scientific data for the Business (Customer A), and real-time hardware reliability metrics for Platform Engineering (Customer B).

## 2. Infrastructure Component Mappings

* **FastAPI Middleware ➡️ Enterprise Observability (e.g., Datadog / AWS CloudWatch)**
* **Role:** Acts as the outer-edge telemetry tracker. Intercepts all inbound traffic to log P95 latency and HTTP status codes into structured JSON files (`telemetry.log`), guaranteeing Day-2 operational visibility.


* **FastAPI Routing & Pydantic ➡️ Enterprise API Gateway (e.g., AWS API Gateway / AWS IoT Core)**
* **Role:** Acts as the edge interception proxy. It authenticates physical equipment (403 Hard Drops), enforces strict structural schema contracts, and routes malformed JSON payloads (422) directly to a local Hive-partitioned Quarantine.


* **Redis-mock + `asyncio.Lock()` ➡️ Distributed In-Memory Cache (e.g., AWS ElastiCache / Redis)**
* **Role:** Functions as the local high-speed state tracker with strict concurrency controls. It maintains the Requests-Per-Minute (RPM) volumetric counters for every localized piece of equipment, instantly triggering 429 Hard Drops if a sensor firmware crashes into a hyperactive loop.


* **Virtual VRAM (`asyncio.Queue`) ➡️ Distributed Event Streaming (e.g., Apache Kafka / AWS Kinesis)**
* **Role:** Acts as the asynchronous backpressure buffer. It absorbs massive concurrent `200 OK` factory data uploads in volatile memory and dynamically flushes them via Hive Partitioning to disk based on strict volume or time thresholds, proactively preventing localized storage I/O exhaustion.


* **Asynchronous Swarm Simulator (`load_tester.py`) ➡️ Chaos Engineering & Load Testing (e.g., AWS Fault Injection Simulator / Locust)**
* **Role:** Acts as the primary developer tool designed to violently test architectural constraints under extreme pressure. It simulates real-world hardware failures and massive concurrency to mathematically prove thread safety and validate 429 volumetric quotas.


* **Python `watchdog` ➡️ Cloud Event Triggers (e.g., AWS S3 Event Notifications)**
* **Role:** Emulates event-driven orchestration. The exact millisecond an approved equipment payload lands in the Bronze raw storage layer, it triggers the downstream ETL transformation pipeline.


* **Nested JSON Directory ➡️ NoSQL Document Store (e.g., MongoDB / Zontal)**
* **Role:** Preserves the deeply nested, hierarchical structure of the MedTech scientific observations (Data Package, Data Cube) into a harmonized Silver layer for FDA-compliant auditing.


* **Programmatic BI Script (`kpi_report_generator.py`) ➡️ Enterprise Business Intelligence (e.g., AWS QuickSight / Tableau)**
* **Role:** Acts as a Day-2 operational tool querying metadata to output System Health KPIs. It aggregates system metrics to instantly identify physical factories requiring hardware repair based on edge drop rates, serving the Platform Engineering team.


* **Anthropic MCP Server ➡️ Enterprise Interoperability API**
* **Role:** Acts as the secure programmatic adapter, fulfilling FAIR data principles (Findable, Accessible, Interoperable, Reusable) by allowing external enterprise AI systems and BI dashboards to query the Silver layer without direct database access.


* **Python Bootstrapper (`system_orchestrator.py`) ➡️ Container Orchestration (e.g., Docker Compose / Kubernetes)**
* **Role:** Solves the Day-2 "Terminal Sprawl" problem. Orchestrates the simultaneous local startup, integration, and graceful shutdown (`SIGINT` handling) of all discrete microservices via a single entrypoint.

## 3. Client Server Architecture 

```mermaid
graph TB
    %% Styles
    classDef quarantine fill:#f99,stroke:#333,stroke-width:2px;
    classDef storage fill:#bfb,stroke:#333,stroke-width:2px;
    classDef bi fill:#ff9,stroke:#333,stroke-width:2px;
    classDef profile fill:#ddd,stroke:#333,stroke-width:2px;
    classDef external fill:#bbf,stroke:#333,stroke-width:2px;
    classDef config fill:#eee,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;

    subgraph ClientSide ["1. Client Side (Test Scripts & Swarm Simulators)"]
        LT["load_tester.py<br/>(Asynchronous IoT Swarm)"]
        TI["test_injector.py<br/>(Functional UAT Runner)"]
    end

    subgraph ServerSide ["2. Edge Proxy (FastAPI Runtime)"]
        POLICY["gateway_policy.yml<br/>(IP Whitelists & RPM Quotas)"]:::config
        GW["gateway.py<br/>(API Gateway & Router)"]
        MW["FastAPI Middleware<br/>(Observability Hook)"]
        TELEMETRY["telemetry.log<br/>(Structured JSON Logs)"]:::profile
        REDIS["redis_mock.py<br/>(RPM Volumetric Counter & Lock)"]
        PYDANTIC["inbound_schema.json<br/>(Pydantic Contract Validator)"]:::config
    end

    subgraph StorageLayer ["3. Local Storage & Data Lakehouse"]
        VRAM["virtual_vram_batcher.py<br/>(Asyncio VRAM Queue)"]
        BRONZE["/bronze_raw/<br/>(Hive-Partitioned Disk)"]:::storage
        WATCHDOG["event_listener.py<br/>(Watchdog OS Event Hook)"]
        DICT["DATA_DICTIONARY_AND_CONTRACTS.md<br/>(FAIR Metrics Glossary)"]:::config
        SILVER["/silver_harmonized/<br/>(NoSQL Document Store)"]:::storage
        QFolder["/quarantine/structural/<br/>(Malformed JSON)"]:::quarantine
    end

    subgraph ProfilingAndBI ["4. Profiling, BI & Interoperability"]
        PM["performance_metrics.md<br/>(SLO Profiling Output)"]:::profile
        KPI["kpi_report_generator.py<br/>(Day-2 System Health BI)"]:::bi
        MCP["Anthropic MCP Server<br/>(AI Tooling Adapter)"]:::bi
    end
    
    AI["External AI Agent<br/>(Claude / Gemini)"]:::external

    %% 1. Client to Server Ingress
    LT -->|"Concurrent Swarm"| GW
    TI -->|"Functional Tests"| GW
    LT -.->|"Generates upon completion"| PM

    %% 2. Server Internal Routing & Defenses
    POLICY -.->|"Defines 403/429 Rules"| GW
    GW --> MW
    MW -->|"Writes P95/Status Codes"| TELEMETRY
    MW --> REDIS
    REDIS -->|"Check RPM Limit (429)"| GW
    GW --> PYDANTIC
    
    %% 3. Handling Outcomes
    PYDANTIC -->|"Malformed (422)"| QFolder
    PYDANTIC -->|"Valid (200 OK)"| VRAM

    %% 4. Storage & ETL Pipeline Flow
    VRAM -->|"Volume/Time Flush"| BRONZE
    BRONZE -->|"File Creation Event"| WATCHDOG
    DICT -.->|"Injected into Payload"| WATCHDOG
    WATCHDOG -->|"ETL, Strip Keys, Inject Chain-of-Custody"| SILVER

    %% 5. BI and Interoperability Connections
    TELEMETRY -.->|"Query Drop Rates"| KPI
    SILVER -.->|"Query Data Truth"| KPI
    SILVER -.->|"Exposed as Read-Only Resources"| MCP
    
    %% 6. AI Tooling Execution
    MCP <-->|"Exposes Tools (get_sensor_history)"| AI
    ```