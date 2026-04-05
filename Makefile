.PHONY: help run migrate makemigrations shell test lint format \
       docker-build docker-up docker-down docker-logs docker-shell \
       docker-migrate docker-makemigrations docker-collectstatic docker-test superuser

# ──────────────────────────────────────────────────────────────
# Help
# ──────────────────────────────────────────────────────────────

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────────────────────────────
# Local Development (Outside Docker)
# ──────────────────────────────────────────────────────────────

run: ## Run the Django development server
	uv run python manage.py runserver

migrate: ## Apply database migrations
	uv run python manage.py migrate

makemigrations: ## Create new migrations
	uv run python manage.py makemigrations

shell: ## Open Django shell
	uv run python manage.py shell

superuser: ## Create a superuser
	uv run python manage.py createsuperuser

test: ## Run tests with pytest
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	uv run pytest tests/ -v --tb=short

check: ## Run Django system checks
	uv run python manage.py check

lint: ## Run ruff linter
	uv run ruff check .

format: ## Format code with ruff
	uv run ruff format .

# ──────────────────────────────────────────────────────────────
# Docker Development
# ──────────────────────────────────────────────────────────────

# Docker variables
DOCKER_COMPOSE = docker compose -f docker/docker-compose.dev.yml

docker-build: ## Build Docker images
	$(DOCKER_COMPOSE) build

docker-up: ## Start all containers in the background
	$(DOCKER_COMPOSE) up -d

docker-down: ## Stop and remove all containers
	$(DOCKER_COMPOSE) down

docker-logs: ## Tail container logs
	$(DOCKER_COMPOSE) logs -f

docker-ps: ## List running containers
	$(DOCKER_COMPOSE) ps

docker-shell: ## Open shell in the web container
	$(DOCKER_COMPOSE) exec web /bin/bash

docker-migrate: ## Run Django migrations inside Docker
	$(DOCKER_COMPOSE) exec web uv run python manage.py migrate

docker-makemigrations: ## Create new Django migrations inside Docker
	$(DOCKER_COMPOSE) exec web uv run python manage.py makemigrations

docker-collectstatic: ## Collect static files inside Docker
	$(DOCKER_COMPOSE) exec web uv run python manage.py collectstatic --no-input

docker-test: ## Run tests inside Docker
	$(DOCKER_COMPOSE) exec web uv run pytest tests/ -v
