"""API route modules.

This package contains the FastAPI route implementations for the platform API.
"""

from .health import router as health_router
from .agent import router as agent_router
from .workflow import router as workflow_router
from .execution import router as execution_router

__all__ = ["health_router", "agent_router", "workflow_router", "execution_router"]