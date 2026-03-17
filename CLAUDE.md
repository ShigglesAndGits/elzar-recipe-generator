# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Elzar is a self-hosted web app that generates recipes using AI based on Grocy inventory. It connects to OpenAI-compatible LLMs (OpenRouter, Ollama, etc.) and provides meal planning, inventory management, and dietary profile support.

## Development Commands

### Backend (FastAPI + Python 3.9+)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev          # Dev server on port 5173, proxies /api to backend:8001
npm run build        # Production build to dist/
```

### Docker (combined single-container)
```bash
cd docker
docker build -t elzar:latest -f Dockerfile ../
docker-compose up -d --build
```

### No test framework or linter is configured.

## Architecture

**Backend** (`backend/app/`):
- **main.py** — FastAPI app, CORS (allows all origins), mounts all routers under `/api/`
- **database.py** — Async SQLite via aiosqlite. Tables: `recipes`, `dietary_profiles`, `meal_plans`, `meal_plan_recipes`, `settings`, `ideas`, `chat_sessions`, `chat_messages`, `prep_cook_sessions`, `debriefs`, `recipe_nutrient_ratings`, `user_preferences`. Schema migrations are inline ALTER TABLE statements.
- **models.py** — Pydantic request/response models
- **config.py** — `Settings` class using pydantic-settings, reads from env vars
- **utils/config_manager.py** — Hybrid config: env vars provide defaults, `settings` DB table provides runtime overrides via `get_effective_config()`. Changes take effect immediately without restart.
- **utils/recipe_parser.py** — Extracts metadata (cuisine, time, effort, calories, cost, nutrient ratings) from LLM recipe text. Defines `NUTRIENTS` canonical list.

**Backend Services** (`backend/app/services/`):
- **grocy_client.py** — Grocy API wrapper (stock, products, recipes, shopping lists, unit conversions)
- **llm_client.py** — OpenAI-compatible LLM client. Builds system/user prompts for recipe generation and meal planning. Supports an "Elzar personality" toggle vs clean format.
- **inventory_matcher.py** — AI-powered product matching from free text to Grocy products with confidence scoring
- **vision_client.py** — Vision model integration for pantry image scanning
- **notification.py** — Apprise notification wrapper

**Backend Routers** (`backend/app/routers/`): `recipes`, `history`, `profiles`, `preferences`, `ideas`, `settings`, `inventory`, `mealplans`, `prepcook`, `chat`, `nutrition`

**Frontend** (`frontend/src/`):
- **api.js** — Axios client; base URL derived from `window.location` for proxy compatibility
- **App.jsx** — React Router navigation, sidebar, responsive layout
- **contexts/ServiceStatusContext.jsx** — Provides Grocy/LLM connection status to components
- **Pages**: Chat (landing), Generator, MealPlanner, InventoryManager, Ideas, Nutrition, History, Profiles, Settings

## Key Configuration

Required env vars: `GROCY_URL`, `GROCY_API_KEY`, `LLM_API_URL`, `LLM_API_KEY`, `LLM_MODEL`

Optional: `LLM_MAX_TOKENS` (default 16000), `APPRISE_URL`, `UNIT_PREFERENCE` (metric/imperial), `VISION_API_URL`/`VISION_API_KEY`/`VISION_MODEL`, `MAX_RECIPE_HISTORY` (default 1000)

All settings can be overridden at runtime via the Settings UI (stored in SQLite `settings` table).

## Data Storage

- SQLite database at `data/recipes.db` (created on first run)
- LanceDB vector storage at `lancedb/`

## Deployment

Supports Docker Compose (recommended), single combined Docker image (nginx + supervisord + uvicorn), or manual systemd services. See `DOCKER.md`, `PORTAINER.md`, `QUICKSTART.md` for details.

## Frontend Dev Proxy

Vite dev server proxies `/api` requests to `http://localhost:8001` (configured in `frontend/vite.config.js`).

## Working Rules

- **Always update README.md** when adding or changing features, configuration, or deployment steps. The README is the primary user-facing documentation and must stay in sync with the codebase.
- **Be a creative partner.** The user values criticism, suggestions, ideas, and perspective. When building features, proactively flag concerns, suggest improvements, and pause for discussion when something could work better. Don't just execute — think critically and contribute to design decisions.
- **Commit after each feature.** Create a git commit when a feature is complete, before moving on to the next one.
