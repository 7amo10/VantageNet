"""API routers package."""
from .cameras import router as cameras_router
from .rules import router as rules_router
from .analytics import router as analytics_router

__all__ = ["cameras_router", "rules_router", "analytics_router"]
