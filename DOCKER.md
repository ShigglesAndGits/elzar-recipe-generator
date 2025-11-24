# 🐳 Elzar Docker Deployment Guide

Deploy Elzar with Docker in minutes! This guide covers everything from local testing to production deployment.

## 📋 Prerequisites

- Docker Engine 20.10+ ([Install Docker](https://docs.docker.com/engine/install/))
- Docker Compose 2.0+ (included with Docker Desktop)
- Your Grocy URL and API key
- Your LLM API key (OpenRouter, OpenAI, or Ollama)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/ShigglesAndGits/elzar-recipe-generator.git
cd elzar-recipe-generator
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required settings:**
```env
GROCY_URL=https://your-grocy-instance.com
GROCY_API_KEY=your_grocy_api_key
LLM_API_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your_llm_api_key
LLM_MODEL=google/gemini-2.0-flash-exp:free
```

### 3. Start Elzar

```bash
# Build and start (first time)
docker-compose up -d --build

# Or just start (after first build)
docker-compose up -d
```

### 4. Access Elzar

Open your browser to: **http://localhost**

That's it! 🎉

---

## 📖 Detailed Guide

### Building the Images

```bash
# Build both frontend and backend
docker-compose build

# Build only backend
docker-compose build backend

# Build only frontend
docker-compose build frontend

# Build without cache (if you have issues)
docker-compose build --no-cache
```

### Starting Services

```bash
# Start in background (detached mode)
docker-compose up -d

# Start in foreground (see logs)
docker-compose up

# Start specific service
docker-compose up -d backend
```

### Stopping Services

```bash
# Stop all services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop, remove containers, and delete volumes (⚠️ deletes database)
docker-compose down -v
```

### Viewing Logs

```bash
# View all logs
docker-compose logs

# Follow logs (live)
docker-compose logs -f

# View backend logs only
docker-compose logs backend

# View last 50 lines
docker-compose logs --tail=50

# Follow backend logs
docker-compose logs -f backend
```

### Checking Status

```bash
# View running containers
docker-compose ps

# View detailed status
docker-compose ps -a

# Check health status
docker inspect elzar-backend --format='{{.State.Health.Status}}'
docker inspect elzar-frontend --format='{{.State.Health.Status}}'
```

---

## 🔧 Configuration

### Environment Variables

All configuration is done via the `.env` file:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROCY_URL` | Yes | - | Your Grocy instance URL |
| `GROCY_API_KEY` | Yes | - | Your Grocy API key |
| `LLM_API_URL` | Yes | - | LLM API endpoint |
| `LLM_API_KEY` | Yes | - | LLM API key |
| `LLM_MODEL` | Yes | - | LLM model name |
| `MAX_RECIPE_HISTORY` | No | 50 | Max recipes to keep |
| `APPRISE_URL` | No | - | Notification service URL |
| `UNIT_PREFERENCE` | No | imperial | imperial or metric |
| `ELZAR_PORT` | No | 80 | Port to expose Elzar on |

### Changing the Port

If port 80 is already in use, change `ELZAR_PORT` in `.env`:

```env
ELZAR_PORT=8080
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

Access at: `http://localhost:8080`

### Using with Reverse Proxy

If you're using Caddy, Nginx, or Traefik:

**Caddy example:**
```caddyfile
elzar.yourdomain.com {
    reverse_proxy localhost:80
}
```

**Nginx example:**
```nginx
server {
    listen 443 ssl;
    server_name elzar.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🔄 Updating Elzar

### Update to Latest Version

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

### Update Docker Images Only

```bash
# Pull latest images (if using pre-built images)
docker-compose pull

# Restart with new images
docker-compose up -d
```

---

## 💾 Data Persistence

### Database Location

The SQLite database is stored in `./data/recipes.db` on your host machine.

This directory is mounted as a volume, so your data persists even if you:
- Stop containers
- Remove containers
- Rebuild images

### Backing Up Data

```bash
# Backup database
cp data/recipes.db data/recipes.db.backup

# Or use tar
tar -czf elzar-backup-$(date +%Y%m%d).tar.gz data/
```

### Restoring Data

```bash
# Stop services
docker-compose down

# Restore database
cp data/recipes.db.backup data/recipes.db

# Start services
docker-compose up -d
```

---

## 🐛 Troubleshooting

### Services Won't Start

**Check logs:**
```bash
docker-compose logs
```

**Common issues:**
- Port already in use → Change `ELZAR_PORT` in `.env`
- Missing `.env` file → Copy from `.env.example`
- Invalid API keys → Check your credentials

### Backend Health Check Failing

```bash
# Check backend logs
docker-compose logs backend

# Check if backend is responding
docker-compose exec backend curl http://localhost:8001/api/settings/config
```

### Frontend Can't Connect to Backend

The frontend and backend communicate via Docker's internal network. This should work automatically.

**If it doesn't:**
```bash
# Restart both services
docker-compose restart
```

### Database Permission Issues

```bash
# Fix permissions on data directory
sudo chown -R $USER:$USER data/
chmod -R 755 data/
```

### Reset Everything

```bash
# Stop and remove everything (⚠️ deletes database)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Start fresh
docker-compose up -d --build
```

---

## 🌐 Production Deployment

### Deploy to Remote Server

```bash
# SSH into your server
ssh user@your-server.com

# Install Docker (if needed)
curl -fsSL https://get.docker.com | sh

# Clone repository
git clone https://github.com/ShigglesAndGits/elzar-recipe-generator.git
cd elzar-recipe-generator

# Configure
cp .env.example .env
nano .env

# Start services
docker-compose up -d --build
```

### Firewall Configuration

Only port 80 (or your `ELZAR_PORT`) needs to be open:

```bash
# UFW
sudo ufw allow 80/tcp

# Or custom port
sudo ufw allow 8080/tcp
```

### Auto-Start on Boot

Docker Compose services with `restart: unless-stopped` will automatically start on boot.

To enable Docker to start on boot:
```bash
sudo systemctl enable docker
```

---

## 📊 Resource Usage

**Typical resource usage:**
- **Backend**: ~100-150 MB RAM
- **Frontend**: ~20-30 MB RAM (nginx)
- **Total**: ~150-200 MB RAM
- **Disk**: ~500 MB (images) + database size

**Minimum requirements:**
- 512 MB RAM
- 1 GB disk space
- 1 CPU core

---

## 🔐 Security Best Practices

1. **Use strong API keys**
2. **Keep `.env` file secure** (never commit to git)
3. **Use HTTPS in production** (reverse proxy with SSL)
4. **Keep Docker updated**: `sudo apt update && sudo apt upgrade docker-ce`
5. **Regular backups** of the `data/` directory

---

## 🆘 Getting Help

**Check logs first:**
```bash
docker-compose logs -f
```

**Common commands:**
```bash
# Restart everything
docker-compose restart

# Rebuild everything
docker-compose up -d --build

# View resource usage
docker stats

# Enter backend container
docker-compose exec backend bash

# Enter frontend container
docker-compose exec frontend sh
```

**Still stuck?**
- Check the [main README](README.md)
- Open an issue on GitHub
- Review backend logs for detailed errors

---

## 🎯 Next Steps

Once Elzar is running:

1. **Open Elzar** in your browser
2. **Go to Settings** page
3. **Test connections** (Grocy and LLM)
4. **Setup locations** (click "Setup Storage Locations")
5. **Setup units** (click "Setup All Kitchen Units & Conversions")
6. **Generate your first recipe!**

---

*Made with ❤️ and a dash of BAM! 🌶️*

