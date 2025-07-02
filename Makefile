# Makefile for Async Log Ingestion Project

# Project vars
COMPOSE=docker-compose
WEB=web
WORKER=worker

# ⛏️ Build and start services
up:
	$(COMPOSE) up --build

# 🔻 Stop services
down:
	$(COMPOSE) down

# 🧼 Stop and remove volumes
clean:
	$(COMPOSE) down -v

# 🐳 Rebuild images without cache
rebuild:
	$(COMPOSE) build --no-cache

# 🏁 Initialize the DB schema
init-db:
	$(COMPOSE) exec $(WEB) python app/init_db.py

# 🔍 View logs from all containers
logs:
	$(COMPOSE) logs -f

# 🏃 Run Locust load testing
locust:
	locust -f script/locustfile.py --host=http://localhost:8000

# 🐚 Shell into web container
web-shell:
	$(COMPOSE) exec $(WEB) sh

# 🐚 Shell into worker container
worker-shell:
	$(COMPOSE) exec $(WORKER) sh
