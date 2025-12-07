# Contributing to VantageNet

Welcome to VantageNet! This guide will help you contribute effectively to the project. Whether you're fixing bugs, adding features, or improving documentation, following these guidelines ensures consistency and quality.

---

## Table of Contents

- [Development Environment](#development-environment)
- [Code Style Guidelines](#code-style-guidelines)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Adding New Services](#adding-new-services)
- [Adding Features](#adding-features)
- [Testing](#testing)
- [Documentation](#documentation)
- [Common Tasks](#common-tasks)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Getting Help](#getting-help)

---

## Development Environment

### Prerequisites

Ensure you have the following installed:

- **Docker** 24.0+ and **Docker Compose** 2.20+
- **Python** 3.11+ with `pip` and `venv`
- **Node.js** 18+ with `npm`
- **Git** 2.40+
- Code editor (VS Code recommended with Python, Docker, and ESLint extensions)

### Setup

```bash
# Clone repository
git clone https://github.com/7amo10/VantageNet.git
cd VantageNet

# Follow SETUP.md for complete setup
# Quick version:
docker compose up -d postgres redis
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r services/*/requirements.txt
cd services/dashboard && npm install
```

Refer to [SETUP.md](docs/SETUP.md) for detailed instructions.

---

## Code Style Guidelines

### Python (Backend Services)

VantageNet follows **PEP 8** with some project-specific conventions.

#### Formatting

- **Formatter:** Black (line length: 88)
- **Import Order:** Standard library → Third-party → Local (use `isort`)
- **Quotes:** Double quotes for strings
- **Line Length:** 88 characters (Black default)

```python
# Good
from typing import List, Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException

from app.config import settings
from app.models import EmotionEvent


def detect_faces(frame: np.ndarray) -> List[dict]:
    """
    Detect faces in a video frame.

    Args:
        frame: Input frame as numpy array (BGR format)

    Returns:
        List of detected faces with bounding boxes

    Raises:
        ValueError: If frame is empty or invalid
    """
    if frame is None or frame.size == 0:
        raise ValueError("Invalid frame provided")

    # Implementation here
    return faces
```

#### Type Hints

**Always use type hints** for function signatures:

```python
# Good
def calculate_sentiment(emotions: List[str], confidences: List[float]) -> float:
    pass

# Bad
def calculate_sentiment(emotions, confidences):
    pass
```

#### Docstrings

Use **Google-style docstrings** for all public functions and classes:

```python
def process_frame(frame_id: str, image: np.ndarray, camera_id: str) -> dict:
    """
    Process a video frame for emotion detection.

    Args:
        frame_id: Unique identifier for the frame
        image: Frame image as numpy array
        camera_id: UUID of the source camera

    Returns:
        Dictionary containing detected emotions and metadata:
        {
            "frame_id": str,
            "emotions": List[dict],
            "timestamp": str
        }

    Raises:
        ValueError: If frame_id is empty or image is invalid
        RuntimeError: If ML model fails to load
    """
    pass
```

#### Naming Conventions

- **Functions/Variables:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** Prefix with `_`

```python
# Good
MAX_RETRIES = 3

class EmotionDetector:
    def __init__(self):
        self._model = None
    
    def detect_emotion(self, frame: np.ndarray) -> str:
        pass

# Bad
maxRetries = 3

class emotion_detector:
    def DetectEmotion(self, Frame):
        pass
```

#### Error Handling

Use specific exceptions with descriptive messages:

```python
# Good
if not camera_id:
    raise ValueError(f"Camera ID cannot be empty")

try:
    result = process_frame(frame)
except cv2.error as e:
    logger.error(f"OpenCV error processing frame: {e}")
    raise RuntimeError(f"Failed to process frame: {e}") from e

# Bad
if not camera_id:
    raise Exception("Error")

try:
    result = process_frame(frame)
except:
    pass
```

#### Logging

Use structured logging with appropriate levels:

```python
import logging

logger = logging.getLogger(__name__)

# Good
logger.info(f"Processing frame {frame_id} from camera {camera_id}")
logger.warning(f"Low confidence detection: {confidence:.2f}")
logger.error(f"Failed to detect faces in frame {frame_id}: {error}", exc_info=True)

# Bad
print(f"Processing frame {frame_id}")
logger.info("Error occurred")
```

#### Configuration

Use Pydantic settings for configuration:

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_host: str = "localhost"
    redis_port: int = 6379
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

### TypeScript (Dashboard)

VantageNet uses **ESLint** and **Prettier** for TypeScript/React code.

#### Formatting

- **Formatter:** Prettier (2 spaces, single quotes for strings)
- **Linter:** ESLint with React and TypeScript rules
- **Line Length:** 100 characters

```typescript
// Good
import { useState, useEffect } from 'react';
import { getAnalytics, AnalyticsData } from '@/services/api';

interface DashboardProps {
  cameraId: string;
  interval?: number;
}

export default function Dashboard({ cameraId, interval = 5000 }: DashboardProps) {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const analytics = await getAnalytics(cameraId);
        setData(analytics);
      } catch (error) {
        console.error('Failed to fetch analytics:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [cameraId]);

  if (loading) return <div>Loading...</div>;
  
  return <div>{/* Component JSX */}</div>;
}
```

#### Type Safety

**Always define types/interfaces** for props and state:

```typescript
// Good
interface Camera {
  id: string;
  name: string;
  location: string;
  active: boolean;
}

interface CameraListProps {
  cameras: Camera[];
  onSelect: (camera: Camera) => void;
}

// Bad
function CameraList({ cameras, onSelect }) {
  // No types
}
```

#### Naming Conventions

- **Components:** `PascalCase`
- **Functions/Variables:** `camelCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Files:** `kebab-case.tsx`

```typescript
// Good
const MAX_RETRIES = 3;

function useCameraData(cameraId: string) {
  // Custom hook
}

export default function CameraView() {
  // Component
}

// File: camera-view.tsx
```

#### React Best Practices

```typescript
// Use functional components with hooks
function CameraStatus({ cameraId }: { cameraId: string }) {
  const [status, setStatus] = useState<'active' | 'inactive'>('inactive');

  // Cleanup effects
  useEffect(() => {
    const ws = connectWebSocket(cameraId);
    
    return () => {
      ws.close();
    };
  }, [cameraId]);

  // Memoize expensive computations
  const processedData = useMemo(() => {
    return expensiveCalculation(data);
  }, [data]);

  return <div>{status}</div>;
}
```

---

### SQL

#### Formatting

- **Keywords:** UPPERCASE
- **Identifiers:** lowercase_snake_case
- **Indentation:** 4 spaces

```sql
-- Good
SELECT 
    c.name as camera_name,
    e.emotion,
    COUNT(*) as count
FROM emotions e
JOIN cameras c ON e.camera_id = c.id
WHERE 
    e.timestamp > NOW() - INTERVAL '1 hour'
    AND e.confidence > 0.8
GROUP BY c.name, e.emotion
ORDER BY count DESC
LIMIT 10;

-- Bad
select c.name as CameraName, e.emotion, count(*) from emotions e join cameras c on e.camera_id=c.id where e.timestamp>now()-interval '1 hour' group by c.name, e.emotion;
```

#### Naming Conventions

- **Tables:** Plural lowercase (`cameras`, `emotions`)
- **Columns:** `snake_case`
- **Indexes:** `idx_<table>_<columns>` (e.g., `idx_emotions_camera_id`)
- **Foreign Keys:** `fk_<table>_<column>` (e.g., `fk_emotions_camera_id`)

---

## Project Structure

```
VantageNet/
├── services/               # Microservices
│   ├── video-ingestion/    # Video capture and frame extraction
│   │   └── app/
│   │       ├── main.py
│   │       ├── camera_manager.py
│   │       ├── video_capture.py
│   │       └── redis_client.py
│   ├── emotion-detection/  # Face detection and emotion recognition
│   │   └── app/
│   │       ├── main.py
│   │       ├── processor.py
│   │       ├── model_loader.py
│   │       └── redis_consumer.py
│   ├── sentiment-analysis/ # Sentiment aggregation and rules engine
│   │   └── app/
│   │       ├── main.py
│   │       ├── aggregator.py
│   │       ├── rules_engine.py
│   │       └── redis_consumer.py
│   ├── api-gateway/        # REST API and WebSocket server
│   │   └── app/
│   │       ├── main.py
│   │       ├── routers/
│   │       └── websocket_manager.py
│   └── dashboard/          # Next.js frontend
│       └── src/
│           ├── app/
│           ├── components/
│           └── services/
├── database/               # Database migrations
│   └── migrations/
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── config/                 # Configuration files
├── docker-compose.yml      # Docker Compose orchestration
└── README.md
```

### Service Organization

Each service follows this structure:

```
service-name/
├── Dockerfile
├── requirements.txt (or package.json)
├── README.md
└── app/
    ├── __init__.py
    ├── main.py              # Entry point
    ├── config.py            # Configuration
    ├── models.py            # Data models
    └── [service-specific modules]
```

---

## Development Workflow

### Branch Naming

```
Sprint-{N}-VANTA-{X}
```

**Examples:**

- `Sprint-1-VANTA-9` (for issue VANTA-9 in Sprint 1)
- `Sprint-2-VANTA-15`

### Commit Messages

Follow **Conventional Commits** format:

```
<type>: <subject>

<body>

<footer>
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
# Good
git commit -m "feat: Add camera health check endpoint

Implements GET /api/cameras/{id}/health endpoint that returns
camera connection status and last frame timestamp.

Refs: #VANTA-12"

git commit -m "fix: Handle Redis connection timeouts

Adds retry logic with exponential backoff for Redis connections.
Prevents service crashes on temporary network issues.

Fixes: #VANTA-23"

# Bad
git commit -m "update code"
git commit -m "fix bug"
```

### Git Workflow

1. **Create feature branch from Sprint-N:**

```bash
git checkout Sprint-1
git pull origin Sprint-1
git checkout -b Sprint-1-VANTA-X
```

2. **Make changes and commit:**

```bash
git add .
git commit -m "feat: Implement feature X"
```

3. **Keep branch updated:**

```bash
git fetch origin
git rebase origin/Sprint-1
```

4. **Push branch:**

```bash
git push -u origin Sprint-1-VANTA-X
```

5. **Create Pull Request** on GitHub targeting `Sprint-1` branch

---

## Adding New Services

### Step-by-Step Guide

#### 1. Create Service Directory

```bash
mkdir -p services/new-service/app
cd services/new-service
```

#### 2. Create Required Files

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ app/

# Run service
CMD ["python", "-m", "app.main"]
```

**requirements.txt:**

```txt
fastapi==0.109.0
uvicorn[standard]==0.26.0
pydantic==2.5.3
pydantic-settings==2.1.0
redis==5.0.1
psycopg2-binary==2.9.9
```

**app/config.py:**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "new-service"
    redis_host: str = "localhost"
    redis_port: int = 6379
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**app/main.py:**

```python
import logging
from fastapi import FastAPI

from app.config import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.service_name)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.service_name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**README.md:**

```markdown
# New Service

## Purpose

Brief description of what this service does.

## Configuration

Environment variables:
- `REDIS_HOST`: Redis server host (default: localhost)
- `REDIS_PORT`: Redis server port (default: 6379)

## Running

```bash
python -m app.main
```

## Testing

```bash
pytest tests/
```
```

#### 3. Update docker-compose.yml

```yaml
services:
  # ... existing services ...
  
  new-service:
    build:
      context: ./services/new-service
      dockerfile: Dockerfile
    container_name: vantage-new-service
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - LOG_LEVEL=INFO
    depends_on:
      - redis
      - postgres
    networks:
      - vantage-network
    restart: unless-stopped
```

#### 4. Implement Service Logic

```python
# app/processor.py
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class NewServiceProcessor:
    def __init__(self):
        logger.info("Initializing NewServiceProcessor")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming data.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Processed data dictionary
        """
        logger.debug(f"Processing data: {data}")
        # Implementation here
        return {"result": "processed"}
```

#### 5. Add Tests

```bash
mkdir tests
touch tests/test_processor.py
```

```python
# tests/test_processor.py
import pytest
from app.processor import NewServiceProcessor

def test_processor_initialization():
    processor = NewServiceProcessor()
    assert processor is not None

def test_process_valid_data():
    processor = NewServiceProcessor()
    result = processor.process({"key": "value"})
    assert "result" in result
```

#### 6. Update Documentation

Add service to:

- `docs/ARCHITECTURE.md` - Service description, resource requirements
- `docs/SETUP.md` - Setup instructions
- `docs/API.md` - API endpoints (if applicable)
- `README.md` - Brief mention

#### 7. Test Service

```bash
# Build and run
docker compose up -d new-service

# Check logs
docker logs vantage-new-service

# Test health endpoint
curl http://localhost:8000/health
```

#### 8. Create Pull Request

```bash
git add services/new-service docker-compose.yml docs/
git commit -m "feat: Add new-service for X functionality

Implements new-service that handles Y by doing Z.

- Dockerfile with Python 3.11
- FastAPI app with health check
- Redis integration for data streaming
- Unit tests with 85% coverage
- Updated documentation

Refs: #VANTA-X"
git push -u origin Sprint-1-VANTA-X
```

---

## Adding Features

### Adding a Camera Endpoint

**Example:** Add endpoint to get camera statistics

1. **Define Model** in `services/api-gateway/app/models.py`:

```python
from pydantic import BaseModel

class CameraStats(BaseModel):
    camera_id: str
    total_frames: int
    total_faces: int
    avg_confidence: float
    last_frame_at: str
```

2. **Add Endpoint** in `services/api-gateway/app/routers/cameras.py`:

```python
@router.get("/{camera_id}/stats", response_model=CameraStats)
async def get_camera_stats(camera_id: str):
    """Get statistics for a specific camera."""
    # Query database
    query = """
        SELECT 
            COUNT(DISTINCT frame_id) as total_frames,
            COUNT(DISTINCT face_id) as total_faces,
            AVG(confidence) as avg_confidence,
            MAX(timestamp) as last_frame_at
        FROM emotions
        WHERE camera_id = %s AND timestamp > NOW() - INTERVAL '24 hours'
    """
    result = await db.fetch_one(query, camera_id)
    
    return CameraStats(
        camera_id=camera_id,
        total_frames=result["total_frames"],
        total_faces=result["total_faces"],
        avg_confidence=result["avg_confidence"],
        last_frame_at=result["last_frame_at"].isoformat()
    )
```

3. **Update API Documentation** in `docs/API.md`

4. **Add Test:**

```python
# tests/test_cameras.py
def test_get_camera_stats(client):
    response = client.get(f"/api/cameras/{camera_id}/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_frames" in data
    assert "avg_confidence" in data
```

### Adding a New Emotion

**Example:** Add "contempt" emotion

1. **Update Database Schema** in `init-scripts/01-init.sql`:

```sql
-- Add to supported emotions list in comments
-- Supported: happy, sad, angry, neutral, surprised, fear, disgust, contempt
```

2. **Update ML Model** in `services/emotion-detection/app/processor.py`:

```python
SUPPORTED_EMOTIONS = [
    "happy", "sad", "angry", "neutral", 
    "surprised", "fear", "disgust", "contempt"
]
```

3. **Update Sentiment Calculation** in `services/sentiment-analysis/app/aggregator.py`:

```python
EMOTION_WEIGHTS = {
    "happy": 1.0,
    "surprised": 0.5,
    "neutral": 0.0,
    "contempt": -0.3,  # Add new emotion
    "sad": -0.5,
    "fear": -0.7,
    "angry": -0.8,
    "disgust": -1.0
}
```

4. **Update Dashboard** in `services/dashboard/src/components/EmotionChart.tsx`:

```typescript
const EMOTION_COLORS = {
  happy: '#10b981',
  sad: '#3b82f6',
  angry: '#ef4444',
  neutral: '#6b7280',
  surprised: '#f59e0b',
  fear: '#8b5cf6',
  disgust: '#ec4899',
  contempt: '#f97316', // Add new emotion
};
```

5. **Update Documentation**

### Adding a Rule Type

**Example:** Add "face_count" rule type

1. **Update Models** in `services/sentiment-analysis/app/models.py`:

```python
class RuleType(str, Enum):
    SENTIMENT = "sentiment"
    FACE_COUNT = "face_count"  # Add new type
```

2. **Implement Rule Logic** in `services/sentiment-analysis/app/rules_engine.py`:

```python
def evaluate_rule(rule: Rule, data: dict) -> bool:
    if rule.type == RuleType.SENTIMENT:
        return evaluate_sentiment_rule(rule, data)
    elif rule.type == RuleType.FACE_COUNT:
        return evaluate_face_count_rule(rule, data)
    else:
        logger.warning(f"Unknown rule type: {rule.type}")
        return False

def evaluate_face_count_rule(rule: Rule, data: dict) -> bool:
    """Evaluate face count rule."""
    face_count = data.get("total_faces", 0)
    threshold = rule.condition_json.get("threshold", 10)
    operator = rule.condition_json.get("operator", ">")
    
    if operator == ">":
        return face_count > threshold
    elif operator == "<":
        return face_count < threshold
    # ... other operators
```

3. **Update API** to accept new rule type

4. **Add Dashboard UI** for creating face_count rules

---

## Testing

### Python Services

VantageNet uses **pytest** for Python testing.

#### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_processor.py

# Run specific test
pytest tests/test_processor.py::test_process_valid_data

# Run with verbose output
pytest -v
```

#### Writing Tests

```python
# tests/test_aggregator.py
import pytest
from app.aggregator import SentimentAggregator

@pytest.fixture
def aggregator():
    """Fixture for SentimentAggregator instance."""
    return SentimentAggregator()

def test_calculate_sentiment_all_happy(aggregator):
    """Test sentiment calculation with all happy emotions."""
    emotions = [
        {"emotion": "happy", "confidence": 0.9},
        {"emotion": "happy", "confidence": 0.85},
        {"emotion": "happy", "confidence": 0.95}
    ]
    sentiment = aggregator.calculate_sentiment(emotions)
    assert sentiment > 0.8
    assert sentiment <= 1.0

def test_calculate_sentiment_empty_list(aggregator):
    """Test sentiment calculation with empty emotion list."""
    with pytest.raises(ValueError):
        aggregator.calculate_sentiment([])

@pytest.mark.asyncio
async def test_async_process_frame(aggregator):
    """Test asynchronous frame processing."""
    result = await aggregator.process_frame("frame_123", [])
    assert "sentiment_score" in result
```

#### Test Coverage Requirements

- **Minimum Coverage:** 80% for all services
- **Critical Paths:** 100% (emotion detection, sentiment calculation, rules engine)

```bash
# Generate coverage report
pytest --cov=app --cov-report=html tests/

# Open report in browser
open htmlcov/index.html
```

### TypeScript/React Testing

VantageNet uses **Jest** and **React Testing Library**.

#### Running Tests

```bash
cd services/dashboard

# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch

# Run specific test
npm test -- Camera.test.tsx
```

#### Writing Tests

```typescript
// src/components/CameraList.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import CameraList from './CameraList';

describe('CameraList', () => {
  const mockCameras = [
    { id: '1', name: 'Camera 1', active: true },
    { id: '2', name: 'Camera 2', active: false },
  ];

  it('renders camera list', () => {
    render(<CameraList cameras={mockCameras} onSelect={() => {}} />);
    expect(screen.getByText('Camera 1')).toBeInTheDocument();
    expect(screen.getByText('Camera 2')).toBeInTheDocument();
  });

  it('calls onSelect when camera is clicked', () => {
    const handleSelect = jest.fn();
    render(<CameraList cameras={mockCameras} onSelect={handleSelect} />);
    
    fireEvent.click(screen.getByText('Camera 1'));
    expect(handleSelect).toHaveBeenCalledWith(mockCameras[0]);
  });

  it('displays active status correctly', () => {
    render(<CameraList cameras={mockCameras} onSelect={() => {}} />);
    const activeIndicator = screen.getByTestId('camera-1-status');
    expect(activeIndicator).toHaveClass('active');
  });
});
```

### Integration Tests

Before running integration tests, validate that all services are healthy and can communicate:

```bash
# Verify all services are healthy first
./scripts/health_check.sh

# Only proceed if health check passes (exit code 0)
if [ $? -eq 0 ]; then
    echo "✓ Services healthy, proceeding with integration tests"
else
    echo "✗ Services unhealthy, fix issues before testing"
    exit 1
fi
```

Test service interactions using Docker Compose test environment.

```bash
# Start test environment
docker compose -f docker-compose.test.yml up -d

# Wait for services to initialize
sleep 30

# Verify service discovery and health
./scripts/health_check.sh

# Run integration tests
pytest tests/integration/

# Cleanup
docker compose -f docker-compose.test.yml down -v
```

**Health Check Integration:**
- Run `health_check.sh` before integration tests to validate service discovery
- Validates Docker network communication (service-to-service)
- Checks PostgreSQL and Redis connectivity
- Verifies health endpoints respond correctly
- Ensures no network timeouts or port conflicts
- Exit code 0 = safe to run tests, 1 = fix issues first

### End-to-End Tests

Use **Playwright** for E2E testing (future implementation).

```bash
# Install Playwright
npm install -D @playwright/test

# Run E2E tests
npx playwright test

# Run with UI
npx playwright test --ui
```

---

## Documentation

### When to Update Documentation

**Always update documentation when you:**

1. Add a new service
2. Add/modify API endpoints
3. Change environment variables or configuration
4. Add dependencies or system requirements
5. Modify database schema
6. Change deployment procedures

### Documentation Files

- **README.md**: Project overview and quick start
- **docs/SETUP.md**: Detailed setup instructions
- **docs/ARCHITECTURE.md**: System architecture and design decisions
- **docs/API.md**: REST and WebSocket API documentation
- **docs/DATABASE.md**: Database schema and query examples
- **CONTRIBUTING.md**: This file

### Documentation Standards

- Use **Markdown** for all documentation
- Include **code examples** that are copy-paste ready
- Use **ASCII diagrams** for architecture (PlantUML for complex diagrams)
- Keep documentation **in sync** with code
- Add **links** between related documentation
- Use **tables** for structured data (environment variables, endpoints)

### Example: Documenting a New Endpoint

In `docs/API.md`:

```markdown
### Get Camera Statistics

Returns statistics for a specific camera over the last 24 hours.

**Endpoint:** `GET /api/cameras/{camera_id}/stats`

**Parameters:**

| Parameter  | Type   | Required | Description           |
|------------|--------|----------|-----------------------|
| camera_id  | string | Yes      | UUID of the camera    |

**Response:**

```json
{
  "camera_id": "123e4567-e89b-12d3-a456-426614174000",
  "total_frames": 86400,
  "total_faces": 1234,
  "avg_confidence": 0.8652,
  "last_frame_at": "2025-12-15T14:30:00Z"
}
```

**Example:**

```bash
curl http://localhost:8000/api/cameras/123e4567-e89b-12d3-a456-426614174000/stats
```

**Errors:**

- `404 Not Found`: Camera not found
- `500 Internal Server Error`: Database error
```

---

## Common Tasks

### Health Check All Services

Run the automated health check to verify all services are running and communicating:

```bash
# Run comprehensive health check
./scripts/health_check.sh
```

This script validates:
- Docker container status
- PostgreSQL and Redis connectivity
- All service health endpoints
- Service discovery (Docker network DNS resolution)
- Inter-service communication
- Redis Streams configuration

**Exit codes:**
- `0` - All services healthy
- `1` - One or more services unhealthy

Use this script:
- After starting services to confirm everything is running
- Before committing to ensure your changes don't break services
- In CI/CD pipelines for automated testing
- When troubleshooting connectivity issues

### Start Development Environment

```bash
# Start infrastructure
docker compose up -d postgres redis

# Start Python services
cd services/video-ingestion && python -m app.main &
cd services/emotion-detection && python -m app.main &
cd services/sentiment-analysis && python -m app.main &
cd services/api-gateway && python -m app.main &

# Start dashboard
cd services/dashboard && npm run dev

# Verify all services are healthy
./scripts/health_check.sh
```

### Run Database Migration

```bash
# Create migration
cd database
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Check Service Logs

```bash
# Docker services
docker logs vantage-postgres
docker logs vantage-redis
docker logs -f vantage-api-gateway  # Follow mode

# Python services (if running locally)
tail -f logs/emotion-detection.log
```

### Reset Database

```bash
# Drop and recreate
docker compose down -v
docker compose up -d postgres

# Database will be initialized from init-scripts/01-init.sql
```

### Update Dependencies

**Python:**

```bash
# Update requirements.txt
pip install --upgrade package-name
pip freeze > requirements.txt

# Or use pip-tools
pip-compile --upgrade requirements.in
```

**Node.js:**

```bash
cd services/dashboard
npm update
npm audit fix
```

### Run Code Formatters

**Python:**

```bash
# Black
black services/

# isort (import sorting)
isort services/

# Check only (no changes)
black --check services/
```

**TypeScript:**

```bash
cd services/dashboard

# Prettier
npm run format

# ESLint
npm run lint
npm run lint:fix
```

### Profile Performance

**Python:**

```bash
# cProfile
python -m cProfile -o output.prof -m app.main

# Analyze with snakeviz
pip install snakeviz
snakeviz output.prof
```

**Database:**

```sql
-- Enable query logging in postgresql.conf
log_statement = 'all'
log_duration = on

-- Or use EXPLAIN ANALYZE
EXPLAIN ANALYZE SELECT * FROM emotions WHERE camera_id = '...';
```

---

## Pull Request Guidelines

### Before Creating PR

- [ ] Code follows style guidelines (run Black, ESLint)
- [ ] All tests pass (`pytest`, `npm test`)
- [ ] Test coverage >= 80%
- [ ] Documentation updated
- [ ] No console.log or print() statements
- [ ] Commit messages follow conventions
- [ ] Branch is up to date with target branch

### PR Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issue

Refs: #VANTA-X

## Changes Made

- Item 1
- Item 2

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Screenshots (if applicable)

[Add screenshots for UI changes]

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings introduced
- [ ] Tests added for new features
- [ ] All tests pass
```

### PR Review Process

1. **Submit PR** targeting appropriate Sprint branch
2. **Automated Checks**: GitHub Actions runs tests and linting
3. **Code Review**: Team member reviews code
4. **Address Feedback**: Make requested changes
5. **Approval**: PR approved by reviewer
6. **Merge**: Squash and merge into Sprint branch

---

## Getting Help

### Resources

- **Documentation:** [docs/](docs/)
- **Architecture Diagrams:** [Diagrams/](Diagrams/)
- **GitHub Issues:** https://github.com/7amo10/VantageNet/issues
- **Project Board:** Plane (http://your-plane-instance.com)

### Communication

- **Issues:** For bugs and feature requests
- **Pull Requests:** For code discussions
- **Email:** team@vantagenet.example (replace with actual)

### Common Problems

**Problem:** Docker container won't start

```bash
# Check logs
docker logs vantage-service-name

# Rebuild container
docker compose build service-name
docker compose up -d service-name
```

**Problem:** Import errors in Python

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r services/service-name/requirements.txt
```

**Problem:** Dashboard won't compile

```bash
cd services/dashboard

# Clear cache
rm -rf .next node_modules
npm install
npm run build
```

**Problem:** Database connection errors

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
docker exec vantage-postgres psql -U vantage -d vantage_db -c "SELECT 1;"
```

---

## Code of Conduct

### Our Standards

- **Respectful Communication:** Treat all contributors with respect
- **Constructive Feedback:** Focus on code, not individuals
- **Collaboration:** Help each other succeed
- **Quality:** Maintain high code quality standards

### Review Etiquette

**When Reviewing:**

- Be specific and actionable
- Explain *why* changes are needed
- Acknowledge good work
- Ask questions rather than making demands

**When Receiving Feedback:**

- Don't take criticism personally
- Ask for clarification if needed
- Thank reviewers for their time
- Make requested changes promptly

---

## License

VantageNet is proprietary software. All contributions remain the property of the VantageNet development team.

---

**Thank you for contributing to VantageNet! 🎉**

For questions, reach out to the team or open an issue on GitHub.
