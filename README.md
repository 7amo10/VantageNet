# VantageNet - Emotion Analytics Platform

## Project Structure

```
VantageNet/
├── docker-compose.yml          # Docker Compose for hybrid setup
├── .env                        # Environment configuration
├── .env.example               # Example environment file
├── init-scripts/              # PostgreSQL initialization
│   └── 01-init.sql
├── scripts/
│   └── run-local-services.sh  # Script to run PyTorch services locally
├── services/
│   ├── api-gateway/           # FastAPI Gateway (containerized)
│   ├── dashboard/             # Next.js Dashboard (containerized)
│   ├── video-ingestion/       # Video Processing (local - PyTorch)
│   ├── emotion-detection/     # ML Detection (local - PyTorch)
│   └── sentiment-analysis/    # Analytics (local - PyTorch)
└── Diagrams/                  # C4 Architecture diagrams
```

## Hybrid Architecture

This project uses a **hybrid approach** to optimize for your local PyTorch installation:

### Containerized Services (Docker)
- **PostgreSQL**: Event database for emotion events & analytics
- **Redis**: Message queue for async frame processing  
- **API Gateway**: REST + WebSocket APIs
- **Dashboard**: React/Next.js real-time UI

### Local Services (your `my_env` virtual environment)
- **Video Ingestion**: RTSP stream processing
- **Emotion Detection**: YOLO + FER for face/emotion detection
- **Sentiment Analysis**: Crowd-level emotion aggregation

This saves storage and bandwidth by using your existing PyTorch installation.

## Quick Start

### 1. Start Docker Containers
```bash
# Start containerized services (PostgreSQL, Redis, API Gateway, Dashboard)
docker-compose up -d
```

### 2. Start Local Python Services
```bash
# Make script executable
chmod +x scripts/run-local-services.sh

# Start local PyTorch services
./scripts/run-local-services.sh start
```

### 3. Access Services
- **Dashboard**: http://localhost:3000
- **API Gateway**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Video Ingestion**: http://localhost:8001
- **Emotion Detection**: http://localhost:8002
- **Sentiment Analysis**: http://localhost:8003

## Environment Configuration

Copy `.env.example` to `.env` and update as needed:
```bash
cp .env.example .env
```

Key configuration:
- `PYTHON_VENV_PATH`: Path to your PyTorch virtual environment (default: `~/my_env`)
- `POSTGRES_*`: PostgreSQL connection settings
- `REDIS_*`: Redis connection settings

## Service Ports

| Service | Port | Type |
|---------|------|------|
| Dashboard | 3000 | Container |
| API Gateway | 8000 | Container |
| Video Ingestion | 8001 | Local |
| Emotion Detection | 8002 | Local |
| Sentiment Analysis | 8003 | Local |
| PostgreSQL | 5434 | Container |
| Redis | 6380 | Container |

## Managing Services

```bash
# Start Docker containers
docker-compose up -d

# View container logs
docker-compose logs -f

# Stop containers
docker-compose down

# Start local services
./scripts/run-local-services.sh start

# Stop local services
./scripts/run-local-services.sh stop

# Check service status
./scripts/run-local-services.sh status
```

## Architecture

See the `Diagrams/` folder for C4 architecture diagrams:
- `Context.puml` - System context
- `Container.puml` - Container diagram
- Sequence diagrams for each component
