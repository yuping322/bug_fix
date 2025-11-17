"""FastAPI application for the multi-agent orchestration platform.

This module sets up the FastAPI application with all routes and middleware.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import structlog

from ..core.config import ConfigManager
from ..core.logging import get_logger, configure_logging as setup_logging
from ..core.workflow import WorkflowEngine
from ..core.observability import ObservabilityManager
from ..core.security import SecurityHeaders, InputValidator
from .models import (
    APIResponse,
    ErrorResponse,
    ValidationErrorResponse,
    HealthCheckResponse,
    PlatformStatus,
    AgentHealth,
    WorkflowStatus,
    ExecutionStatus,
)
from .routes import (
    agent_router,
    workflow_router,
    health_router,
    execution_router,
)

# Initialize logger
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting multi-agent orchestration platform")

    # Initialize core components
    try:
        # Load configuration
        config_manager = ConfigManager()
        await config_manager.load_config()

        # Setup logging
        setup_logging(config_manager.get("logging", {}))

        # Initialize workflow engine
        workflow_engine = WorkflowEngine(config_manager)

        # Initialize observability
        observability_manager = ObservabilityManager(config_manager)

        # Store in app state
        app.state.config_manager = config_manager
        app.state.workflow_engine = workflow_engine
        app.state.observability_manager = observability_manager

        logger.info("Platform initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize platform", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down multi-agent orchestration platform")

    # Cleanup resources
    try:
        if hasattr(app.state, 'workflow_engine'):
            await app.state.workflow_engine.cleanup()

        if hasattr(app.state, 'observability_manager'):
            await app.state.observability_manager.cleanup()

        logger.info("Platform shutdown complete")

    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


def create_application() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title="Multi-Agent Orchestration Platform",
        description="A platform for orchestrating AI agents in code development workflows",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add middleware
    _setup_middleware(app)

    # Add exception handlers
    _setup_exception_handlers(app)

    # Include routers
    _setup_routers(app)

    # Add health check endpoint
    @app.get("/health", response_model=HealthCheckResponse)
    async def health_check(request: Request) -> HealthCheckResponse:
        """Health check endpoint."""
        try:
            # Get platform status
            platform_status = await _get_platform_status(request.app)

            return HealthCheckResponse(
                success=True,
                data=platform_status,
                message="Platform is healthy"
            )

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return HealthCheckResponse(
                success=False,
                message=f"Health check failed: {str(e)}"
            )

    return app


def _setup_middleware(app: FastAPI) -> None:
    """Setup middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Add security headers to all responses."""
        response = await call_next(request)

        # Add security headers
        security_headers = SecurityHeaders.get_api_headers()
        for header, value in security_headers.items():
            response.headers[header] = value

        return response

    # Input validation middleware
    @app.middleware("http")
    async def validate_input(request: Request, call_next):
        """Validate and sanitize input data."""
        # Only validate POST/PUT/PATCH requests with JSON content
        if (request.method in ["POST", "PUT", "PATCH"] and
            request.headers.get("content-type", "").startswith("application/json")):

            try:
                # Read request body
                body = await request.body()

                if body:
                    # Parse JSON
                    import json
                    data = json.loads(body.decode())

                    # Validate input based on endpoint
                    if "/agents" in str(request.url):
                        # Agent-related validation
                        if "api_key" in data:
                            if not InputValidator.validate_api_key(data["api_key"]):
                                return JSONResponse(
                                    status_code=400,
                                    content={"error": "Invalid API key format"}
                                )
                    elif "/workflows" in str(request.url):
                        # Workflow-related validation
                        if "parameters" in data:
                            data["parameters"] = InputValidator.validate_workflow_input(data["parameters"])

                    # Re-encode validated data
                    validated_body = json.dumps(data).encode()
                    request._body = validated_body

            except json.JSONDecodeError:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid JSON format"}
                )
            except Exception as e:
                logger.warning("Input validation failed", error=str(e))

        response = await call_next(request)
        return response

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware (configure for production)
    if os.getenv("ENVIRONMENT") == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["your-domain.com"]  # Configure appropriately
        )


def _setup_exception_handlers(app: FastAPI) -> None:
    """Setup exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            errors.append(f"{field}: {message}")

        return JSONResponse(
            status_code=422,
            content=ValidationErrorResponse(
                errors=errors,
                warnings=[]
            ).dict()
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.detail,
                code=f"HTTP_{exc.status_code}"
            ).dict()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """Handle general exceptions."""
        logger.error("Unhandled exception", error=str(exc), path=request.url.path)

        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal server error",
                code="INTERNAL_ERROR",
                details={"type": type(exc).__name__}
            ).dict()
        )


def _setup_routers(app: FastAPI) -> None:
    """Setup routers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Include API routers
    app.include_router(
        health_router,
        prefix="/api/v1",
        tags=["health"]
    )

    app.include_router(
        agent_router,
        prefix="/api/v1",
        tags=["agents"]
    )

    app.include_router(
        workflow_router,
        prefix="/api/v1",
        tags=["workflows"]
    )

    app.include_router(
        execution_router,
        prefix="/api/v1",
        tags=["executions"]
    )


async def _get_platform_status(app: FastAPI) -> PlatformStatus:
    """Get the current platform status.

    Args:
        app: FastAPI application instance

    Returns:
        Platform status
    """
    try:
        config_manager = app.state.config_manager
        workflow_engine = app.state.workflow_engine
        observability_manager = app.state.observability_manager

        # Get platform info
        platform_config = config_manager.get_platform_config()
        platform_name = platform_config.name
        platform_version = platform_config.version

        # Get agent health statuses
        agent_healths = []
        for agent_config in platform_config.agents:
            # Check agent health (simplified)
            health = await _check_agent_health(agent_config.name)
            agent_healths.append(health)

        # Get workflow statuses
        workflow_statuses = []
        for workflow_config in platform_config.workflows:
            # Get workflow status (simplified)
            status = await _get_workflow_status(workflow_config.name)
            workflow_statuses.append(status)

        # Get active executions count
        active_executions = await workflow_engine.get_active_execution_count()

        return PlatformStatus(
            name=platform_name,
            version=platform_version,
            status="healthy",
            agents=agent_healths,
            workflows=workflow_statuses,
            active_executions=active_executions
        )

    except Exception as e:
        logger.error("Failed to get platform status", error=str(e))
        return PlatformStatus(
            name="unknown",
            version="unknown",
            status="unhealthy",
            agents=[],
            workflows=[],
            active_executions=0
        )


async def _check_agent_health(agent_name: str) -> AgentHealth:
    """Check the health of an agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Agent health status
    """
    # Simplified health check - in real implementation, this would
    # actually test the agent
    from ..agents import agent_registry

    try:
        agent = agent_registry.get_agent(agent_name)
        if agent:
            # Perform actual health check
            healthy = await agent.health_check()
            return AgentHealth(
                name=agent_name,
                type=agent.type,
                healthy=healthy,
                last_check=None,  # Would be set by observability manager
                error=None if healthy else "Health check failed"
            )
        else:
            return AgentHealth(
                name=agent_name,
                type="unknown",
                healthy=False,
                error="Agent not found"
            )
    except Exception as e:
        return AgentHealth(
            name=agent_name,
            type="unknown",
            healthy=False,
            error=str(e)
        )


async def _get_workflow_status(workflow_name: str) -> WorkflowStatus:
    """Get the status of a workflow.

    Args:
        workflow_name: Name of the workflow

    Returns:
        Workflow status
    """
    # Simplified status check - in real implementation, this would
    # get actual metrics from the observability manager
    try:
        # This would be implemented to get real workflow metrics
        return WorkflowStatus(
            name=workflow_name,
            type="simple",  # Would be determined from config
            status=ExecutionStatus.COMPLETED,
            last_execution=None,
            success_rate=1.0,
            average_duration=10.0
        )
    except Exception as e:
        logger.error("Failed to get workflow status", workflow=workflow_name, error=str(e))
        return WorkflowStatus(
            name=workflow_name,
            type="unknown",
            status=ExecutionStatus.FAILED,
            error=str(e)
        )


# Create the application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn

    # Run the application
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )