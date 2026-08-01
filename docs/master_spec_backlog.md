### **Milestone 3: FastAPI Gateway & RPM Circuit Breaker**

#### **Component 1: `redis_mock.py` (Enterprise Distributed Cache Simulator)**

**User Story:**

> **As a** Platform Reliability Engineer,
> **I want to** implement an isolated, concurrency-safe in-memory rate limiter with automated garbage collection and life-safety bypasses,
> **so that** I can strictly enforce a 60 Requests-Per-Minute (RPM) limit per sensor without race conditions, while guaranteeing that critical hardware failure alerts are never blocked from reaching the cloud.

**Acceptance Criteria (Gherkin Format):**

* **AC 1 (State Management)**
* **Given** multiple sensors are transmitting data to the gateway,
* **When** the rate limiter ingests the traffic,
* **Then** it must accurately isolate and track the volumetric RPM for each unique `equipment_id` independently.


* **AC 2 (Concurrency)**
* **Given** a massive concurrent traffic spike from the factory floor,
* **When** multiple requests for the same `equipment_id` arrive at the exact same millisecond,
* **Then** state mutations must be strictly protected by an `asyncio.Lock()` to prevent race conditions and ensure the count remains mathematically perfect.


* **AC 3 (Enforcement)**
* **Given** a specific `equipment_id` is bound to a 60 RPM limit,
* **When** the 61st request is received within a single rolling minute,
* **Then** the service must instantly flag an explicit breach condition.


* **AC 4 (Bypass)**
* **Given** an incoming sensor payload,
* **When** the payload contains the boolean flag `critical_alert: true`,
* **Then** the system must bypass the rate counter completely and never flag a volumetric breach.


* **AC 5 (Garbage Collection)**
* **Given** the rate limiter is actively tracking traffic in memory,
* **When** exactly 60 seconds have elapsed since a specific `equipment_id`'s window began,
* **Then** the memory cleanup protocol must clear the stale data and reset the counter for that ID back to 0.



---

#### **Component 2: `gateway.py` (API Interception Proxy)**

**User Story:**

> **As a** Cyber Security & Data Architect,
> **I want to** deploy an API proxy that enforces strict security authentication, reliability circuit-breaking, and data schema integrity,
> **so that** unauthorized bad actors are blocked, system overloads are mitigated, and malformed data is safely quarantined to a data lake without crashing the core systems.

**Acceptance Criteria (Gherkin Format):**

* **AC 1 (Security - 403 Hard Drop)**
* **Given** an inbound HTTP POST request hitting the gateway,
* **When** the request originates from an unauthorized IP address OR is missing a valid `agent_key`,
* **Then** the gateway must instantly reject the request and return an HTTP `403 Forbidden` status.


* **AC 2 (Reliability - 429 Hard Drop)**
* **Given** a valid, authenticated HTTP request,
* **When** the gateway queries `redis_mock.py` and receives a breach flag indicating the RPM limit is exceeded,
* **Then** the gateway must instantly terminate the connection and return an HTTP `429 Too Many Requests` status.


* **AC 3 (Integrity - 422 Quarantine)**
* **Given** an incoming JSON payload that passes security and rate-limit checks,
* **When** the payload fails strict Pydantic structural validation (e.g., providing a string instead of a float),
* **Then** the gateway must return an HTTP `422 Unprocessable Entity` status AND dynamically route the raw payload to the local disk using the Hive partition structure: `/quarantine/structural/year=YYYY/month=MM/day=DD/`.


* **AC 4 (Observability)**
* **Given** traffic is actively flowing through the gateway endpoint,
* **When** any request completes its lifecycle (whether successful or dropped),
* **Then** the FastAPI middleware must generate a structured JSON log entry in `telemetry.log` capturing the exact request latency and the final HTTP status code.

### **Milestone 4: Virtual VRAM Buffer & Dynamic Batching**

#### **Component 3: `virtual_vram_batcher.py` (Asyncio Memory Buffer)**

**User Story:**

> **As a** Data Infrastructure Engineer,
> **I want to** implement an asynchronous memory buffer that dynamically batches approved payloads based on volume and time, while enforcing a graceful shutdown protocol,
> **so that** we prevent storage I/O exhaustion from rapid concurrent writes, guarantee zero data loss during server restarts, and securely route validated data into an analytics-ready folder structure.

**Acceptance Criteria (Gherkin Format):**

* **AC 1 (Intake Validation)**
* **Given** incoming telemetry traffic is being processed by the API gateway,
* **When** an incoming payload is evaluated for storage,
* **Then** the VRAM queue must strictly ingest *only* payloads that successfully received an HTTP `200 OK` status, ignoring any traffic that was dropped (403, 429) or quarantined (422).


* **AC 2 (Volumetric Flush)**
* **Given** the VRAM buffer is actively queueing approved payloads in volatile memory,
* **When** the internal queue volume reaches exactly 500 unwritten payloads,
* **Then** the system must autonomously and immediately trigger a bulk flush of all contents to the local disk.


* **AC 3 (Temporal Flush)**
* **Given** the VRAM buffer contains at least one, but fewer than 500, unwritten payloads,
* **When** exactly 10 seconds have elapsed since the last disk flush,
* **Then** the system must autonomously trigger a bulk flush of all remaining contents to the local disk to prevent data staleness.


* **AC 4 (Resilience)**
* **Given** the application is running with unwritten payloads actively sitting in the volatile RAM queue,
* **When** the operating system issues a termination signal (such as a `SIGINT` or `SIGTERM` from pressing `Ctrl+C`),
* **Then** the graceful shutdown handler must intercept the signal, block the immediate termination, and successfully flush all remaining payloads to disk before allowing the server process to exit.


* **AC 5 (Storage Routing)**
* **Given** a batch of approved payloads is executing its flush-to-disk protocol,
* **When** the file write operation occurs,
* **Then** the data must be securely saved to the local disk strictly following the Hive partition directory structure: `/approved/year=YYYY/month=MM/day=DD/`.
