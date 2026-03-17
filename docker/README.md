# Elzar Docker (Single Container)

This directory contains a unified single-container Docker setup for Elzar.

## Quick Start

```bash
# Navigate to this directory
cd docker

# Copy and configure environment
cp .env.example .env
nano .env  # Fill in your Grocy and LLM credentials

# Build and run
docker compose up -d

# View logs
docker compose logs -f

# Access Elzar
open http://localhost
```

## Architecture

```
┌─────────────────────────────────────────┐
│           Single Container              │
│                                         │
│  ┌─────────────┐    ┌────────────────┐  │
│  │   Nginx     │───▶│   Uvicorn/     │  │
│  │   :80       │    │   FastAPI      │  │
│  │             │    │   :8001        │  │
│  └─────────────┘    └────────────────┘  │
│         │                   │           │
│         ▼                   ▼           │
│  /usr/share/nginx/html   /app/data/     │
│  (React static files)    (SQLite DB)    │
└─────────────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build (Node → Python+Nginx) |
| `docker-compose.yml` | Single-service orchestration |
| `nginx.conf` | Nginx config with API proxy to localhost |
| `supervisord.conf` | Process manager for Nginx + Uvicorn |
| `entrypoint.sh` | Startup script with validation |
| `.env.example` | Environment variable template |
| `.dockerignore` | Files excluded from build context |

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GROCY_URL` | Your Grocy instance URL | `https://grocy.example.com` |
| `GROCY_API_KEY` | Grocy API key | `abc123...` |
| `LLM_API_URL` | LLM API endpoint | `https://openrouter.ai/api/v1` |
| `LLM_API_KEY` | LLM API key | `sk-or-...` |
| `LLM_MODEL` | Model identifier | `google/gemini-2.0-flash-exp:free` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ELZAR_PORT` | `80` | Host port to expose |
| `MAX_RECIPE_HISTORY` | `50` | Max recipes to keep |
| `UNIT_PREFERENCE` | `imperial` | `imperial` or `metric` |
| `APPRISE_URL` | (empty) | Notification service URL |

## Commands

```bash
# Build without cache
docker compose build --no-cache

# Run in foreground (see logs)
docker compose up

# Run detached
docker compose up -d

# Stop
docker compose down

# Stop and remove volumes
docker compose down -v

# View logs
docker compose logs -f elzar

# Shell into container
docker exec -it elzar /bin/bash

# Check health
docker inspect elzar --format='{{.State.Health.Status}}'
```

## Data Persistence

The SQLite database is stored in `./data/recipes.db` and mounted as a volume. Your recipe history persists across container restarts.

## LLM Provider Examples

### OpenRouter (Recommended - has free models)
```env
LLM_API_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-your-key
LLM_MODEL=google/gemini-2.0-flash-exp:free
```

### OpenAI
```env
LLM_API_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-openai-key
LLM_MODEL=gpt-4o
```

### Ollama (Local)
```env
LLM_API_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=llama3.2
```

## Troubleshooting

### Container won't start
Check logs: `docker compose logs elzar`

Common issues:
- Missing required environment variables
- Invalid Grocy URL or API key
- Port 80 already in use (change `ELZAR_PORT`)

### Can't connect to Grocy
- Ensure Grocy URL is accessible from Docker network
- For local Grocy, use `host.docker.internal` instead of `localhost`

### Recipe generation fails
- Test LLM connection in Settings page
- Check API key and model name are correct
- Some models have rate limits

## Comparison: Single vs Multi-Container

| Aspect | Single Container | Multi-Container |
|--------|------------------|-----------------|
| Simplicity | ✅ One image | Two images |
| Deployment | ✅ Simpler | More complex |
| Scaling | ❌ All-or-nothing | Can scale independently |
| Debugging | Slightly harder | Easier isolation |
| Image Size | ~250MB | ~300MB total |
