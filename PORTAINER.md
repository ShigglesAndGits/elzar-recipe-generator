# 🐳 Elzar Portainer Deployment Guide

Deploy Elzar using Portainer's Stack feature - the easiest way to manage Docker containers with a web UI!

## 📋 Prerequisites

- Portainer installed and running
- Access to Portainer web UI
- Your Grocy URL and API key
- Your LLM API key (OpenRouter, OpenAI, or Ollama)

---

## 🚀 Deployment Steps

### Step 1: Access Portainer

Open your Portainer web UI (usually `http://your-server:9000`)

### Step 2: Create New Stack

1. Click **"Stacks"** in the left sidebar
2. Click **"+ Add stack"** button
3. Name it: **`elzar`**

### Step 3: Paste Docker Compose

In the **"Web editor"** section, paste this:

```yaml
version: '3.8'

services:
  # Backend - FastAPI application
  backend:
    image: ghcr.io/shigglesandgits/elzar-backend:latest
    container_name: elzar-backend
    restart: unless-stopped
    environment:
      - GROCY_URL=${GROCY_URL}
      - GROCY_API_KEY=${GROCY_API_KEY}
      - LLM_API_URL=${LLM_API_URL}
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_MODEL=${LLM_MODEL}
      - MAX_RECIPE_HISTORY=${MAX_RECIPE_HISTORY}
      - APPRISE_URL=${APPRISE_URL}
      - UNIT_PREFERENCE=${UNIT_PREFERENCE}
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

  # Frontend - React + Nginx
  frontend:
    image: ghcr.io/shigglesandgits/elzar-frontend:latest
    container_name: elzar-frontend
    restart: unless-stopped
    ports:
      - "${ELZAR_PORT}:80"
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

**OR** if you want to build from source instead of using pre-built images, use this:

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
      - MAX_RECIPE_HISTORY=${MAX_RECIPE_HISTORY}
      - APPRISE_URL=${APPRISE_URL}
      - UNIT_PREFERENCE=${UNIT_PREFERENCE}
      - BACKEND_PORT=8001
    volumes:
      - elzar-data:/app/data
    networks:
      - elzar-network

  frontend:
    build:
      context: https://github.com/ShigglesAndGits/elzar-recipe-generator.git#main:frontend
    container_name: elzar-frontend
    restart: unless-stopped
    ports:
      - "${ELZAR_PORT}:80"
    depends_on:
      - backend
    networks:
      - elzar-network

networks:
  elzar-network:
    driver: bridge

volumes:
  elzar-data:
    driver: local
```

### Step 4: Add Environment Variables

Scroll down to **"Environment variables"** section.

Click **"+ add an environment variable"** for each of these:

#### Required Variables:

| Name | Value | Example |
|------|-------|---------|
| `GROCY_URL` | Your Grocy instance URL | `https://groceries.bironfamily.net` |
| `GROCY_API_KEY` | Your Grocy API key | `abc123def456...` |
| `LLM_API_URL` | Your LLM API endpoint | `https://openrouter.ai/api/v1` |
| `LLM_API_KEY` | Your LLM API key | `sk-or-v1-...` |
| `LLM_MODEL` | LLM model to use | `google/gemini-2.0-flash-exp:free` |

#### Optional Variables:

| Name | Value | Default | Description |
|------|-------|---------|-------------|
| `MAX_RECIPE_HISTORY` | `50` | `50` | Max recipes to keep |
| `APPRISE_URL` | Leave empty | - | Notification URL |
| `UNIT_PREFERENCE` | `imperial` | `imperial` | `imperial` or `metric` |
| `ELZAR_PORT` | `80` | `80` | Port to expose Elzar on |

**Screenshot of what it should look like:**
```
Name: GROCY_URL                Value: https://groceries.bironfamily.net
Name: GROCY_API_KEY            Value: your_api_key_here
Name: LLM_API_URL              Value: https://openrouter.ai/api/v1
Name: LLM_API_KEY              Value: your_llm_key_here
Name: LLM_MODEL                Value: google/gemini-2.0-flash-exp:free
Name: UNIT_PREFERENCE          Value: imperial
Name: ELZAR_PORT               Value: 80
```

### Step 5: Deploy!

1. Scroll to bottom
2. Click **"Deploy the stack"**
3. Wait 2-5 minutes for containers to build/download and start

### Step 6: Access Elzar

Open your browser to: **http://your-server-ip:80**

(Or whatever port you set for `ELZAR_PORT`)

---

## 🔄 Updating Elzar

### Method 1: Pull Latest Images (Recommended)

1. Go to **Stacks** → **elzar**
2. Click **"Stop this stack"**
3. Click **"Editor"** tab
4. Click **"Update the stack"** (no changes needed)
5. Check **"Re-pull image and redeploy"**
6. Click **"Update"**

### Method 2: Rebuild from Source

1. Go to **Stacks** → **elzar**
2. Click **"Stop this stack"**
3. Click **"Editor"** tab
4. Click **"Update the stack"**
5. Check **"Re-build image"**
6. Click **"Update"**

---

## 📊 Monitoring

### View Logs

1. Go to **Stacks** → **elzar**
2. Click on container name (`elzar-backend` or `elzar-frontend`)
3. Click **"Logs"** tab
4. Enable **"Auto-refresh"** to see live logs

### Check Health

1. Go to **Stacks** → **elzar**
2. Look for green "healthy" status on both containers
3. If unhealthy, check logs for errors

### Resource Usage

1. Go to **Stacks** → **elzar**
2. Click on container name
3. Click **"Stats"** tab
4. View CPU, memory, and network usage

---

## 🔧 Configuration Changes

### Change Environment Variables

1. Go to **Stacks** → **elzar**
2. Click **"Editor"** tab
3. Scroll to **"Environment variables"** section
4. Edit values (e.g., change LLM model, add Apprise URL)
5. Click **"Update the stack"**
6. Containers will restart with new settings

**No need to redeploy or rebuild!** Changes take effect immediately.

---

## 💾 Data Backup

Your recipe database is stored in the `elzar-data` volume.

### Backup Database

1. Go to **Volumes** in Portainer
2. Find **"elzar-data"**
3. Click **"Browse"**
4. Navigate to `data/recipes.db`
5. Download the file

### Restore Database

1. Go to **Volumes** → **elzar-data** → **Browse**
2. Upload your backup `recipes.db` file
3. Restart the stack

---

## 🐛 Troubleshooting

### Containers Won't Start

**Check logs:**
1. Go to **Stacks** → **elzar**
2. Click on failing container
3. Click **"Logs"** tab

**Common issues:**
- Missing environment variables → Add them in stack editor
- Port already in use → Change `ELZAR_PORT` to `8080` or another port
- Invalid API keys → Check your Grocy/LLM credentials

### Backend Health Check Failing

1. Check backend logs for errors
2. Verify `GROCY_URL` and `GROCY_API_KEY` are correct
3. Verify `LLM_API_URL` and `LLM_API_KEY` are correct
4. Test connections in Elzar Settings page

### Can't Access Web UI

1. Check firewall: `sudo ufw allow 80/tcp` (or your custom port)
2. Verify `ELZAR_PORT` is set correctly
3. Check if frontend container is running
4. Check frontend logs for errors

### Database Lost After Update

The `elzar-data` volume persists across updates. If you lost data:
1. Check **Volumes** → **elzar-data** → **Browse**
2. Look for `data/recipes.db`
3. If missing, restore from backup

---

## 🔐 Security Best Practices

1. **Use strong API keys**
2. **Don't expose Portainer to the internet** without authentication
3. **Use HTTPS** with a reverse proxy (Caddy, Nginx, Traefik)
4. **Regular backups** of the `elzar-data` volume
5. **Keep Docker updated** via Portainer's update feature

---

## 🌐 Using with Reverse Proxy

If you're using a reverse proxy in front of Elzar:

### Caddy Example

```caddyfile
elzar.yourdomain.com {
    reverse_proxy localhost:80
}
```

### Nginx Proxy Manager

1. Add new proxy host
2. Domain: `elzar.yourdomain.com`
3. Forward to: `localhost` port `80`
4. Enable SSL

### Traefik (in docker-compose)

Add these labels to the `frontend` service in Portainer:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.elzar.rule=Host(`elzar.yourdomain.com`)"
  - "traefik.http.routers.elzar.entrypoints=websecure"
  - "traefik.http.routers.elzar.tls.certresolver=letsencrypt"
```

---

## 📱 Mobile Access

Elzar is mobile-friendly! Just access it from your phone's browser:

`http://your-server-ip:80`

Or if you set up a domain:

`https://elzar.yourdomain.com`

---

## 🎯 Next Steps

Once Elzar is running:

1. **Open Elzar** in your browser
2. **Go to Settings** page
3. **Test connections** (Grocy and LLM)
4. **Setup locations** (click "Setup Storage Locations")
5. **Setup units** (click "Setup All Kitchen Units & Conversions")
6. **Create dietary profiles** (if needed)
7. **Generate your first recipe!** 🌶️

---

## 💡 Tips

- **Port conflicts?** Change `ELZAR_PORT` to `8080` or any free port
- **Using Ollama locally?** Set `LLM_API_URL` to `http://host.docker.internal:11434/v1`
- **Want notifications?** Set up Apprise and add `APPRISE_URL`
- **Prefer metric?** Set `UNIT_PREFERENCE` to `metric`

---

## 🆘 Getting Help

**Check logs first:**
1. Portainer → Stacks → elzar → Container → Logs

**Still stuck?**
- Check [DOCKER.md](DOCKER.md) for general Docker troubleshooting
- Check [README.md](README.md) for feature documentation
- Open an issue on GitHub

---

*Made with ❤️ and a dash of BAM! 🌶️*

