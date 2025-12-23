<p align="center">
  <img src="logo.png" alt="VantageNet Logo" width="550"/>
</p>

<h1 align="center">VantageNet</h1>

<p align="center">
  <strong>Real-Time Crowd Emotion Analytics Platform</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Next.js"/>
  <img src="https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch"/>
</p>

<p align="center">
  <a href="docs/SETUP.md">Setup Guide</a> •
  <a href="docs/ARCHITECTURE.md">Architecture</a> •
  <a href="docs/API.md">API Docs</a> •
  <a href="docs/DATABASE.md">Database</a>
</p>

---

## Overview

**VantageNet** is an enterprise-grade emotion analytics platform that processes live video streams to detect faces, analyze emotions, and aggregate crowd-level sentiment in real-time. Built with a microservices architecture, it provides actionable insights through an interactive dashboard.

### Key Features

- **Live Video Processing** — MJPEG streams with real-time emotion detection overlays
- **7-Emotion Detection** — Happy, Sad, Angry, Surprised, Fear, Disgust, Neutral
- **Crowd Sentiment Analytics** — Aggregated mood scores and trend analysis
- **Smart Alerting** — Configurable rules for emotion-based triggers
- **Interactive Dashboard** — Real-time charts with auto-refresh capabilities
- **WebSocket Streaming** — Live updates pushed to connected clients

---

## Architecture

<p align="center">
  <img src="Diagrams/c4-container-emotion.png" alt="VantageNet Architecture" width="800"/>
</p>

<p align="center">
  <em>C4 Container Diagram — System Architecture Overview</em>
</p>

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/7amo10/VantageNet.git
cd VantageNet

# Start infrastructure (PostgreSQL, Redis, API Gateway)
docker compose up -d postgres redis api-gateway

# Set up Python environment
python -m venv my_env && source my_env/bin/activate
pip install -r services/emotion-detection/requirements.txt
pip install -r services/sentiment-analysis/requirements.txt
pip install -r services/video-ingestion/requirements.txt

# Start services (in separate terminals)
cd services/video-ingestion && python -m app.main      # Terminal 1
cd services/emotion-detection && python -m app.main   # Terminal 2
cd services/sentiment-analysis && python -m app.main  # Terminal 3

# Start dashboard
cd services/dashboard && npm install && npm run dev   # Terminal 4
```

For detailed setup instructions, see **[docs/SETUP.md](docs/SETUP.md)**

---

## Service Endpoints

| Service | Port | Description |
|---------|------|-------------|
| Dashboard | 3001 | React/Next.js Web UI |
| API Gateway | 8000 | REST & WebSocket API |
| Video Ingestion | 8001 | RTSP/Webcam Processing |
| Emotion Detection | 8002 | Face & Emotion ML |
| Sentiment Analysis | 8003 | Crowd Aggregation |
| PostgreSQL | 5434 | Analytics Database |
| Redis | 6380 | Stream Processing |

---

## Documentation

| Document | Description |
|----------|-------------|
| [**SETUP.md**](docs/SETUP.md) | Complete installation and configuration guide |
| [**ARCHITECTURE.md**](docs/ARCHITECTURE.md) | System design and component overview |
| [**API.md**](docs/API.md) | REST API and WebSocket endpoints |
| [**DATABASE.md**](docs/DATABASE.md) | PostgreSQL schema and queries |
| [**PERFORMANCE.md**](docs/PERFORMANCE.md) | Optimization and benchmarks |
| [**redis-streams.md**](docs/redis-streams.md) | Redis streaming architecture |

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <sub>Built for real-time emotion analytics</sub>
</p>
