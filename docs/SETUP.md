# VantageNet Development Setup Guide

This guide will help you set up VantageNet for local development.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Environment Variables](#environment-variables)
- [Running the System](#running-the-system)
- [Troubleshooting](#troubleshooting)
- [Verification](#verification)

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

1. **Docker & Docker Compose**
   - Docker Engine 20.10+ or Docker Desktop
   - Docker Compose v2.0+
   - Verify installation:
     ```bash
     docker --version
     docker compose version
     ```

2. **Python 3.11+**
   - Required for local Python services (emotion-detection, sentiment-analysis, video-ingestion)
   - Verify installation:
     ```bash
     python --version  # or python3 --version
     ```

3. **Node.js 18+**
   - Required for the dashboard service
   - Verify installation:
     ```bash
     node --version
     npm --version
     ```

4. **Git**
   - For cloning the repository
   - Verify installation:
     ```bash
     git --version
     ```

### System Requirements

- **RAM**: Minimum 4GB, Recommended 8GB+
- **Disk Space**: At least 5GB free
- **OS**: Linux (Ubuntu 20.04+), macOS (10.15+), or Windows 10/11 with WSL2

## Quick Start

For experienced developers, here's the fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/7amo10/VantageNet.git
cd VantageNet

# Start infrastructure services (PostgreSQL, Redis, API Gateway)
docker compose up -d postgres redis api-gateway

# Set up Python environment
python -m venv my_env
source my_env/bin/activate  # On Windows: my_env\Scripts\activate
pip install -r services/emotion-detection/requirements.txt
pip install -r services/sentiment-analysis/requirements.txt
pip install -r services/video-ingestion/requirements.txt

# Start local Python services (in separate terminals)
cd services/video-ingestion && python -m app.main
cd services/emotion-detection && python -m app.main
cd services/sentiment-analysis && python -m app.main

# Install and start dashboard
cd services/dashboard
npm install
npm run dev

# Access the dashboard at http://localhost:3001
```

## Detailed Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/7amo10/VantageNet.git
cd VantageNet
```

### Step 2: Review the Architecture

VantageNet uses a **hybrid Docker Compose setup**:

- **Containerized**: PostgreSQL, Redis, API Gateway, Dashboard (Node.js)
- **Local (my_env)**: Emotion Detection (PyTorch), Sentiment Analysis, Video Ingestion

This hybrid approach saves storage/bandwidth by using your local PyTorch installation instead of including it in Docker images.

### Step 3: Environment Configuration

VantageNet uses default values that work out-of-the-box, but you can customize them:

#### Optional: Create `.env` File

Create a `.env` file in the project root (copy from `.env.example` if available):

```bash
# PostgreSQL Configuration
POSTGRES_USER=vantage
POSTGRES_PASSWORD=vantage_secret
POSTGRES_DB=vantage_db
DATABASE_URL=postgresql://vantage:vantage_secret@localhost:5434/vantage_db

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6380

# API Gateway
API_PORT=8000

# Dashboard
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/live
```

**Note**: If you don't create a `.env` file, the system will use these default values automatically.

### Step 4: Start Infrastructure Services

Start PostgreSQL, Redis, and API Gateway in Docker:

```bash
docker compose up -d postgres redis api-gateway
```

Wait for services to be healthy:

```bash
docker compose ps
```

You should see:
```
NAME               STATUS          PORTS
vantage-postgres   Up (healthy)    0.0.0.0:5434->5432/tcp
vantage-redis      Up (healthy)    0.0.0.0:6380->6379/tcp
vantage-api-gw     Up (healthy)    0.0.0.0:8000->8000/tcp
```

### Step 5: Initialize Database

The database schema is automatically initialized when PostgreSQL starts using the script in `init-scripts/01-init.sql`.

Verify database initialization:

```bash
docker exec vantage-postgres psql -U vantage -d vantage_db -c "\dt"
```

You should see 5 tables:
- cameras
- emotions
- rules
- alerts
- sentiment_stats

### Step 6: Initialize Redis Streams

Redis streams are automatically created on first use, but you can initialize them manually:

```bash
# Option 1: Using the init script (requires redis-cli installed locally)
REDIS_HOST=localhost REDIS_PORT=6380 ./scripts/init-redis-streams.sh

# Option 2: Using Docker exec
docker exec vantage-redis sh -c 'redis-cli XADD emotion:events \* type init message "Stream initialized" timestamp $(date +%s) && redis-cli XGROUP CREATE emotion:events emotion-detector-group 0 MKSTREAM && redis-cli XGROUP CREATE emotion:events sentiment-analyzer-group 0 MKSTREAM && redis-cli XADD sentiment:crowd \* type init message "Stream initialized" timestamp $(date +%s) && redis-cli XGROUP CREATE sentiment:crowd api-gateway-group 0 MKSTREAM'
```

### Step 7: Set Up Python Environment

Create a virtual environment for local Python services:

```bash
# Create virtual environment
python -m venv my_env

# Activate it
source my_env/bin/activate  # On Windows: my_env\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

Install dependencies for all Python services:

```bash
# Install emotion-detection dependencies (includes PyTorch)
pip install -r services/emotion-detection/requirements.txt

# Install sentiment-analysis dependencies
pip install -r services/sentiment-analysis/requirements.txt

# Install video-ingestion dependencies
pip install -r services/video-ingestion/requirements.txt
```

**Note**: The emotion-detection service requires PyTorch with DeepFace. Installation may take several minutes.

### Step 8: Download ML Models

Download the YOLOv8 model for face detection:

```bash
cd services/emotion-detection
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

Or download manually from [YOLOv8 releases](https://github.com/ultralytics/ultralytics/releases) and place in `services/emotion-detection/`.

### Step 9: Start Local Python Services

Open **3 separate terminals** and activate the virtual environment in each:

**Terminal 1 - Video Ingestion Service:**
```bash
cd VantageNet
source my_env/bin/activate
cd services/video-ingestion
python -m app.main
```

**Terminal 2 - Emotion Detection Service:**
```bash
cd VantageNet
source my_env/bin/activate
cd services/emotion-detection
python -m app.main
```

**Terminal 3 - Sentiment Analysis Service:**
```bash
cd VantageNet
source my_env/bin/activate
cd services/sentiment-analysis
python -m app.main
```

### Step 10: Set Up Dashboard

In a **4th terminal**:

```bash
cd services/dashboard

# Install dependencies
npm install

# Create .env.local file
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/live
EOF

# Start development server
npm run dev
```

The dashboard will start on `http://localhost:3001` (or 3000 if available).

## Environment Variables

### PostgreSQL Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `vantage` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `vantage_secret` | PostgreSQL password |
| `POSTGRES_DB` | `vantage_db` | Database name |
| `DATABASE_URL` | `postgresql://vantage:vantage_secret@localhost:5434/vantage_db` | Full connection string |

### Redis Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis host address |
| `REDIS_PORT` | `6380` | Redis port |

### API Gateway Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | `8000` | API Gateway HTTP port |
| `DATABASE_URL` | (see above) | PostgreSQL connection |
| `REDIS_HOST` | `localhost` | Redis connection |
| `REDIS_PORT` | `6380` | Redis port |

### Dashboard Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API Gateway base URL |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000/ws/live` | WebSocket endpoint |

### Python Services Variables

All Python services use:
- `DATABASE_URL`: PostgreSQL connection
- `REDIS_HOST`: Redis host
- `REDIS_PORT`: Redis port

## Running the System

### Full System Startup

To start the entire VantageNet system:

1. **Start Docker services**:
   ```bash
   docker compose up -d postgres redis api-gateway
   ```

2. **Start Python services** (in 3 terminals with `my_env` activated):
   ```bash
   # Terminal 1
   cd services/video-ingestion && python -m app.main
   
   # Terminal 2
   cd services/emotion-detection && python -m app.main
   
   # Terminal 3
   cd services/sentiment-analysis && python -m app.main
   ```

3. **Start Dashboard** (in 4th terminal):
   ```bash
   cd services/dashboard && npm run dev
   ```

### Accessing Services

After startup, you can access:

- **Dashboard**: http://localhost:3001
- **API Gateway**: http://localhost:8000
  - Swagger Docs: http://localhost:8000/docs
  - Health Check: http://localhost:8000/health
- **PostgreSQL**: localhost:5434
  - Connect with: `psql -h localhost -p 5434 -U vantage -d vantage_db`
- **Redis**: localhost:6380
  - Connect with: `redis-cli -h localhost -p 6380`

### Stopping Services

**Stop Docker services**:
```bash
docker compose down
```

**Stop Python services**:
- Press `Ctrl+C` in each terminal running Python services

**Stop Dashboard**:
- Press `Ctrl+C` in the dashboard terminal

## Troubleshooting

### Port Already in Use

**Problem**: Error like `Bind for 0.0.0.0:5434 failed: port is already allocated`

**Solution**:
```bash
# Find what's using the port
lsof -i :5434  # or netstat -tulpn | grep 5434

# Kill the process or change the port in docker-compose.yml
# For example, change postgres port to 5435:
# ports:
#   - "5435:5432"
```

### Docker Container Won't Start

**Problem**: Container exits immediately or health check fails

**Solution**:
```bash
# Check container logs
docker compose logs postgres
docker compose logs redis
docker compose logs api-gateway

# Restart the service
docker compose restart <service-name>

# If that doesn't work, remove and recreate
docker compose down
docker compose up -d
```

### Python Import Errors

**Problem**: `ModuleNotFoundError` when starting Python services

**Solution**:
```bash
# Ensure virtual environment is activated
source my_env/bin/activate

# Reinstall dependencies
pip install -r services/emotion-detection/requirements.txt
pip install -r services/sentiment-analysis/requirements.txt
pip install -r services/video-ingestion/requirements.txt

# Verify installation
pip list | grep torch
pip list | grep deepface
```

### Database Connection Refused

**Problem**: `connection refused` or `could not connect to server`

**Solution**:
```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Check if it's healthy
docker exec vantage-postgres pg_isready -U vantage

# Verify port is correct (5434, not 5432)
# Update DATABASE_URL if needed:
export DATABASE_URL="postgresql://vantage:vantage_secret@localhost:5434/vantage_db"
```

### Redis Connection Errors

**Problem**: `Error connecting to Redis`

**Solution**:
```bash
# Check if Redis is running
docker compose ps redis

# Test connection
docker exec vantage-redis redis-cli ping
# Should return: PONG

# Verify port is correct (6380, not 6379)
export REDIS_PORT=6380
```

### Dashboard Not Loading

**Problem**: Dashboard shows blank page or connection errors

**Solution**:
```bash
# Check if API Gateway is running
curl http://localhost:8000/health

# Verify .env.local exists and has correct values
cd services/dashboard
cat .env.local

# Clear Next.js cache and rebuild
rm -rf .next
npm run dev
```

### YOLOv8 Model Not Found

**Problem**: `FileNotFoundError: yolov8n.pt not found`

**Solution**:
```bash
cd services/emotion-detection
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
# Or download manually and place in emotion-detection directory
```

### Memory Issues

**Problem**: Services crashing with OOM (Out of Memory) errors

**Solution**:
```bash
# Increase Docker memory limit (Docker Desktop → Settings → Resources)
# Recommended: 4GB minimum, 8GB+ preferred

# Or reduce memory usage by limiting services:
# In docker-compose.yml, add memory limits:
# deploy:
#   resources:
#     limits:
#       memory: 512M
```

### Permission Denied on Scripts

**Problem**: `Permission denied` when running scripts

**Solution**:
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Or run with bash explicitly
bash scripts/init-redis-streams.sh
```

## Verification

### Verify Docker Services

```bash
# Check all services are running
docker compose ps

# Check logs for errors
docker compose logs --tail=50

# Test API Gateway
curl http://localhost:8000/health
```

### Verify Database

```bash
# Connect to PostgreSQL
docker exec -it vantage-postgres psql -U vantage -d vantage_db

# List tables
\dt

# Check cameras table
SELECT * FROM cameras;

# Exit
\q
```

### Verify Redis Streams

```bash
# Check stream existence
docker exec vantage-redis redis-cli XINFO STREAM emotion:events
docker exec vantage-redis redis-cli XINFO STREAM sentiment:crowd

# Check consumer groups
docker exec vantage-redis redis-cli XINFO GROUPS emotion:events
docker exec vantage-redis redis-cli XINFO GROUPS sentiment:crowd

# Monitor Redis streams in real-time
./scripts/redis-monitor.sh
```

### Verify Python Services

Each Python service should output:
```
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:PORT
```

### Verify Dashboard

1. Open http://localhost:3001 in your browser
2. You should see the VantageNet dashboard
3. Check browser console for errors (F12)
4. Navigate between pages (Analytics, Rules, Settings)

### End-to-End Test

```bash
# 1. Register a camera via API
curl -X POST http://localhost:8000/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-camera",
    "rtsp_url": "rtsp://example.com/stream",
    "location": "Test Lab",
    "active": true
  }'

# 2. Check if camera appears in database
docker exec vantage-postgres psql -U vantage -d vantage_db -c "SELECT * FROM cameras;"

# 3. Check Redis streams are receiving data
docker exec vantage-redis redis-cli XLEN emotion:events
docker exec vantage-redis redis-cli XLEN sentiment:crowd

# 4. View dashboard and verify camera appears
# Open http://localhost:3001 and check the cameras list
```

## Next Steps

- Read [ARCHITECTURE.md](./ARCHITECTURE.md) to understand the system design
- Check [API.md](./API.md) for API documentation
- Review [DATABASE.md](./DATABASE.md) for database schema details
- See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines

## Getting Help

- **Issues**: Check [GitHub Issues](https://github.com/7amo10/VantageNet/issues)
- **Documentation**: Review other docs in `/docs` folder
- **Logs**: Always check `docker compose logs` for detailed error messages

## Summary of Ports

| Service | Port | Protocol |
|---------|------|----------|
| Dashboard | 3001 | HTTP |
| API Gateway | 8000 | HTTP/WebSocket |
| PostgreSQL | 5434 | PostgreSQL |
| Redis | 6380 | Redis |
| Video Ingestion | 8001 | HTTP (internal) |
| Emotion Detection | 8002 | HTTP (internal) |
| Sentiment Analysis | 8003 | HTTP (internal) |
