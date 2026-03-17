# Elzar - Single Container Dockerfile
# Combines React frontend + FastAPI backend in one image
# Uses supervisord to manage both Nginx and Uvicorn processes

# =============================================================================
# Stage 1: Build Frontend
# =============================================================================
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# Copy package files for better layer caching
COPY frontend/package*.json ./

# Install dependencies (using npm install since no lock file exists)
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build production bundle
RUN npm run build

# =============================================================================
# Stage 2: Production Image (Python + Nginx + Supervisord)
# =============================================================================
FROM python:3.11-slim

LABEL maintainer="Elzar Recipe Generator"
LABEL description="AI-powered recipe generator for Grocy - BAM!"
LABEL version="1.1.0"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory for backend
WORKDIR /app

# Copy Python requirements and install dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/app ./app

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Copy configuration files
COPY docker/nginx.conf /etc/nginx/sites-available/default
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/entrypoint.sh /entrypoint.sh

# Make entrypoint executable
RUN chmod +x /entrypoint.sh

# Remove default nginx config that might conflict
RUN rm -f /etc/nginx/sites-enabled/default \
    && ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Create nginx log directory and set permissions
RUN mkdir -p /var/log/nginx /var/log/supervisor \
    && touch /var/log/nginx/access.log /var/log/nginx/error.log

# Expose port 80 (configurable via ELZAR_PORT in compose)
EXPOSE 80

# Health check - verify both services are responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Volume for persistent data
VOLUME ["/app/data"]

# Start supervisord via entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
