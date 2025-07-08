# postgresql-concurrency-stress-test
postgresql-concurrency-stress-test


### how to run
```
# run postgresql service (container) from project root
docker-compuse up

# run redis service
docker run -d --name redis -p 6379:6379 redis:7-alpine

# run fastapi server from project root
# uvicorn app.main:app
ulimit -n 65535 # resolve
gunicorn app.main:app -w 8 -k uvicorn.workers.UvicornWorker

# run locust from project root
locust -f script/locustfile.py -H http://localhost:8000
```



### 🧠 1. Purpose of the Project
To ingest logs via HTTP and persist them efficiently in PostgreSQL using:

- FastAPI for HTTP API
- Redis Stream for buffering
- Async PostgreSQL worker(s) for bulk DB inserts
- Locust for load testing

### 🧱 2. System Architecture
🚀 HTTP Ingress (main.py)
- Users send logs via POST /write.
- Logs are JSON dictionaries.
- Logs are not written to DB directly.
- Instead, they're queued into a Redis Stream (logs_stream).

🧵 Worker Service (worker.py)
- NUM_WORKERS workers (default 10) each:
    - Consume logs from the Redis stream using consumer groups.
    - Decode and parse each message.
    - Bulk insert logs into PostgreSQL.
    - Acknowledge (XACK) only on success to avoid loss.

🗄️ Database (PostgreSQL)
- Table logs stores:
    - id (PK)
    - message (stringified JSON)
    - created_at timestamp (auto-populated)

🧠 Redis
- Used purely as a high-throughput, decoupling queue (Redis Stream).
- Stream key: logs_stream
- Consumer group: log_consumers

🔁 Read Endpoint (GET /messages)
- Reads latest n logs directly from PostgreSQL.

### 🔧 3. Dev/Infra Tools
- .env: Secrets and config
- init_db.py: Initializes DB schema
- Dockerfile: Used by both web and worker containers
- docker-compose.yml: Spins up:
    - web (FastAPI)
    - worker (Python script with Redis consumer logic)
    - postgres
    - redis

### 🔬 4. Testing
- locustfile.py: Generates synthetic log traffic to POST /write for load testing.


### 🔄 5. Architecture overview
+-------------+
|  Locust     |  (Load Gen)
+------+------+
       |
       v
+------+------+
|   FastAPI    |  (Producer)
+------+------+
       |
       v
+------+------+
|   Redis      |  (Stream Queue)
+------+------+
       |
       v
+------+------+
|  Workers     |  (Consumers)
+------+------+
       |
       v
+-------------+
| PostgreSQL   |
+-------------+
