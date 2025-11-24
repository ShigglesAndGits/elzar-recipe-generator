# 🚀 Elzar Portainer Quick Start

Copy/paste this into Portainer to deploy Elzar in 2 minutes!

---

## Step 1: Docker Compose

**In Portainer:** Stacks → + Add stack → Name: `elzar` → Paste this:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: https://github.com/ShigglesAndGits/elzar-recipe-generator.git#main:backend
    container_name: elzar-backend
    restart: unless-stopped
    environment:
      - GROCY_URL=${GROCY_URL}
      - GROCY_API_KEY=${GROCY_API_KEY}
      - LLM_API_URL=${LLM_API_URL}
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_MODEL=${LLM_MODEL}
      - MAX_RECIPE_HISTORY=${MAX_RECIPE_HISTORY:-50}
      - APPRISE_URL=${APPRISE_URL:-}
      - UNIT_PREFERENCE=${UNIT_PREFERENCE:-imperial}
      - BACKEND_PORT=8001
    volumes:
      - elzar-data:/app/data
    networks:
      - elzar-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8001/api/settings/config', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  frontend:
    build:
      context: https://github.com/ShigglesAndGits/elzar-recipe-generator.git#main:frontend
    container_name: elzar-frontend
    restart: unless-stopped
    ports:
      - "${ELZAR_PORT:-80}:80"
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - elzar-network
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s

networks:
  elzar-network:
    driver: bridge

volumes:
  elzar-data:
    driver: local
```

---

## Step 2: Environment Variables

**Scroll down to "Environment variables"** and add these:

### Required (Must Fill In):

```
GROCY_URL=https://your-grocy-instance.com
GROCY_API_KEY=your_grocy_api_key_here
LLM_API_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your_llm_api_key_here
LLM_MODEL=google/gemini-2.0-flash-exp:free
```

### Optional (Can Leave Default):

```
UNIT_PREFERENCE=imperial
ELZAR_PORT=80
MAX_RECIPE_HISTORY=50
```

*(Leave `APPRISE_URL` empty unless you want notifications)*

---

## Step 3: Deploy!

Click **"Deploy the stack"** at the bottom.

Wait 3-5 minutes for build to complete.

---

## Step 4: Access

Open browser to: **http://your-server-ip:80**

---

## 🎯 First Time Setup

Once Elzar loads:

1. Go to **Settings** page
2. Click **"Test Grocy Connection"** (should be green ✓)
3. Click **"Test LLM Connection"** (should be green ✓)
4. Click **"Setup Storage Locations"** (creates Pantry & Fridge)
5. Click **"Setup All Kitchen Units & Conversions"** (creates units)
6. Go to **Generator** page
7. Click **"BAM!"** to generate your first recipe! 🌶️

---

## 🔄 To Update Later

1. Portainer → Stacks → elzar
2. Stop this stack
3. Editor tab
4. Update the stack
5. Check "Re-build image"
6. Update

---

## 💾 Your Data

Your recipes are stored in the `elzar-data` volume and persist across updates!

To backup: Portainer → Volumes → elzar-data → Browse → Download `data/recipes.db`

---

**That's it!** 🎉

*For detailed docs, see [PORTAINER.md](PORTAINER.md)*

