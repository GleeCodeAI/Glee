.PHONY: install sync dev stdio d-up d-down d-logs d-build d-codex-auth clean

# Install dependencies
install:
	uv sync

sync: install

# Run MCP server (SSE mode for local development)
dev:
	GLEE_TRANSPORT=sse uv run python -m glee

# Run MCP server (stdio mode - called by Claude Code)
stdio:
	uv run python -m glee

# Database migrations
m:
	uv run alembic upgrade head

m-new:
	@read -p "Migration name: " name; \
	uv run alembic revision -m "$$name"

m-down:
	uv run alembic downgrade -1

# Docker
d-up:
	docker compose up -d

d-down:
	docker compose down

d-logs:
	docker compose logs -f

d-build:
	docker compose build --no-cache

# Codex auth (inside container)
d-codex-auth:
	docker exec -it glee-server codex login --device-auth

# Clean
clean:
	rm -rf .venv __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
