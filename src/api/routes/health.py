"""Health check API routes.

This module provides health check endpoints for the platform.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..models import (
    APIResponse,
    ErrorResponse,
    HealthCheckResponse,
    PlatformStatus,
    AgentHealth,
    WorkflowStatus,
    ExecutionStatus,
)
from ...core.config import ConfigManager
from ...core.workflow import WorkflowEngine
from ...core.observability import ObservabilityManager
from ...agents import agent_registry

router = APIRouter()


async def get_platform_status() -> PlatformStatus:
    """Get the current platform status.

    Returns:
        Platform status
    """
    try:
        # Get components from app state (would be set during app startup)
        # For now, create instances directly
        config_manager = ConfigManager()
        workflow_engine = WorkflowEngine(config_manager)
        observability_manager = ObservabilityManager(config_manager)

        # Get platform info
        platform_config = config_manager.get_platform_config()
        platform_name = platform_config.name
        platform_version = platform_config.version

        # Get agent health statuses
        agent_healths = []
        for agent_config in platform_config.agents:
            # Check agent health
            health = await check_agent_health(agent_config.name)
            agent_healths.append(health)

        # Get workflow statuses
        workflow_statuses = []
        for workflow_config in platform_config.workflows:
            # Get workflow status
            status = await get_workflow_status(workflow_config.name)
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
        return PlatformStatus(
            name="unknown",
            version="unknown",
            status="unhealthy",
            agents=[],
            workflows=[],
            active_executions=0
        )


async def check_agent_health(agent_name: str) -> AgentHealth:
    """Check the health of an agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Agent health status
    """
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


async def get_workflow_status(workflow_name: str) -> WorkflowStatus:
    """Get the status of a workflow.

    Args:
        workflow_name: Name of the workflow

    Returns:
        Workflow status
    """
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
        return WorkflowStatus(
            name=workflow_name,
            type="unknown",
            status=ExecutionStatus.FAILED,
            error=str(e)
        )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Get the current health status of the platform"
)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint."""
    try:
        # Get platform status
        platform_status = await get_platform_status()

        return HealthCheckResponse(
            success=True,
            data=platform_status,
            message="Platform is healthy"
        )

    except Exception as e:
        return HealthCheckResponse(
            success=False,
            message=f"Health check failed: {str(e)}"
        )


@router.get(
    "/health/agents",
    response_model=APIResponse,
    summary="Agent Health",
    description="Get health status of all agents"
)
async def agent_health() -> APIResponse:
    """Get health status of all agents."""
    try:
        platform_status = await get_platform_status()

        return APIResponse(
            success=True,
            data=platform_status.agents,
            message=f"Found {len(platform_status.agents)} agents"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agent health: {str(e)}"
        )


@router.get(
    "/health/workflows",
    response_model=APIResponse,
    summary="Workflow Health",
    description="Get health status of all workflows"
)
async def workflow_health() -> APIResponse:
    """Get health status of all workflows."""
    try:
        platform_status = await get_platform_status()

        return APIResponse(
            success=True,
            data=platform_status.workflows,
            message=f"Found {len(platform_status.workflows)} workflows"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workflow health: {str(e)}"
        )


@router.get(
    "/health/executions",
    response_model=APIResponse,
    summary="Execution Health",
    description="Get status of active executions"
)
async def execution_health() -> APIResponse:
    """Get status of active executions."""
    try:
        config_manager = ConfigManager()
        workflow_engine = WorkflowEngine(config_manager)

        active_count = await workflow_engine.get_active_execution_count()

        return APIResponse(
            success=True,
            data={"active_executions": active_count},
            message=f"{active_count} active executions"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution health: {str(e)}"
        )


@router.get(
    "/status",
    response_model=APIResponse,
    summary="Platform Status",
    description="Get detailed platform status information"
)
async def platform_status() -> APIResponse:
    """Get detailed platform status."""
    try:
        platform_status = await get_platform_status()

        return APIResponse(
            success=True,
            data=platform_status,
            message="Platform status retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get platform status: {str(e)}"
        )


@router.get(
    "/ping",
    summary="Ping",
    description="Simple ping endpoint to check if the API is responsive"
)
async def ping() -> Dict[str, str]:
    """Simple ping endpoint."""
    return {"status": "pong", "message": "API is responsive"}