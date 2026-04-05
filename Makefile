# ──────────────────────────────────────────────────────────────
# Docker
# ──────────────────────────────────────────────────────────────

docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start all containers in the background
	docker compose up -d

docker-down: ## Stop and remove all containers
	docker compose down

docker-logs: ## Tail container logs
	docker compose logs -f

docker-shell: ## Open a shell inside the web container
	docker compose exec web bash

docker-migrate: ## Run migrations inside the web container
	docker compose exec web python manage.py migrate

docker-test: ## Run tests inside the web container
	docker compose exec web pytest tests/ -v

docker-restart: ## Restart all containers
	docker compose restart

docker-clean: ## Stop containers, remove volumes
	docker compose down -v