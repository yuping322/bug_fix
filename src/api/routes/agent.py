"""Agent management API routes.

This module provides API endpoints for managing AI agents.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from ..models import (
    APIResponse,
    ErrorResponse,
    AgentHealth,
    AgentConfig,
    ValidateConfigRequest,
    ValidateConfigResponse,
)
from ...core.config import ConfigManager
from ...agents import agent_registry
from ...utils.validation import validate_agent_config

router = APIRouter()


@router.get(
    "/agents",
    response_model=APIResponse,
    summary="List Agents",
    description="Get a list of all configured agents"
)
async def list_agents(
    include_health: bool = Query(False, description="Include health status for each agent")
) -> APIResponse:
    """List all configured agents."""
    try:
        config_manager = ConfigManager()
        platform_config = config_manager.get_platform_config()

        agents_data = []
        for agent_config in platform_config.agents:
            agent_data = {
                "name": agent_config.name,
                "type": agent_config.type,
                "model": agent_config.model,
                "max_tokens": agent_config.max_tokens,
                "temperature": agent_config.temperature,
                "timeout": agent_config.timeout,
            }

            if include_health:
                # Check agent health
                try:
                    agent = agent_registry.get_agent(agent_config.name)
                    if agent:
                        healthy = await agent.health_check()
                        agent_data["healthy"] = healthy
                        agent_data["error"] = None if healthy else "Health check failed"
                    else:
                        agent_data["healthy"] = False
                        agent_data["error"] = "Agent not found"
                except Exception as e:
                    agent_data["healthy"] = False
                    agent_data["error"] = str(e)

            agents_data.append(agent_data)

        return APIResponse(
            success=True,
            data=agents_data,
            message=f"Found {len(agents_data)} agents"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list agents: {str(e)}"
        )


@router.get(
    "/agents/{agent_name}",
    response_model=APIResponse,
    summary="Get Agent",
    description="Get detailed information about a specific agent"
)
async def get_agent(agent_name: str) -> APIResponse:
    """Get information about a specific agent."""
    try:
        config_manager = ConfigManager()
        platform_config = config_manager.get_platform_config()

        # Find agent
        agent_config = None
        for agent in platform_config.agents:
            if agent.name == agent_name:
                agent_config = agent
                break

        if not agent_config:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # Get agent instance for additional info
        agent = agent_registry.get_agent(agent_name)

        agent_data = {
            "name": agent_config.name,
            "type": agent_config.type,
            "model": agent_config.model,
            "max_tokens": agent_config.max_tokens,
            "temperature": agent_config.temperature,
            "timeout": agent_config.timeout,
            "capabilities": agent.capabilities if agent else None,
        }

        return APIResponse(
            success=True,
            data=agent_data,
            message=f"Agent '{agent_name}' found"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agent: {str(e)}"
        )


@router.post(
    "/agents",
    response_model=APIResponse,
    summary="Create Agent",
    description="Create a new agent configuration"
)
async def create_agent(agent_config: AgentConfig) -> APIResponse:
    """Create a new agent."""
    try:
        config_manager = ConfigManager()
        platform_config = config_manager.get_platform_config()

        # Check if agent already exists
        existing_names = [agent.name for agent in platform_config.agents]
        if agent_config.name in existing_names:
            raise HTTPException(
                status_code=409,
                detail=f"Agent '{agent_config.name}' already exists"
            )

        # Validate agent configuration
        validation_result = validate_agent_config(agent_config.dict())
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent configuration: {', '.join(validation_result.errors)}"
            )

        # Add agent to configuration
        platform_config.agents.append(agent_config)

        # Save configuration
        config_manager.save_config(platform_config)

        return APIResponse(
            success=True,
            data=agent_config.dict(),
            message=f"Agent '{agent_config.name}' created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create agent: {str(e)}"
        )


@router.put(
    "/agents/{agent_name}",
    response_model=APIResponse,
    summary="Update Agent",
    description="Update an existing agent configuration"
)
async def update_agent(agent_name: str, agent_config: AgentConfig) -> APIResponse:
    """Update an existing agent."""
    try:
        config_manager = ConfigManager()
        platform_config = config_manager.get_platform_config()

        # Find and update agent
        agent_found = False
        for i, agent in enumerate(platform_config.agents):
            if agent.name == agent_name:
                # Validate new configuration
                validation_result = validate_agent_config(agent_config.dict())
                if not validation_result.is_valid:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid agent configuration: {', '.join(validation_result.errors)}"
                    )

                platform_config.agents[i] = agent_config
                agent_found = True
                break

        if not agent_found:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # Save configuration
        config_manager.save_config(platform_config)

        return APIResponse(
            success=True,
            data=agent_config.dict(),
            message=f"Agent '{agent_name}' updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update agent: {str(e)}"
        )


@router.delete(
    "/agents/{agent_name}",
    response_model=APIResponse,
    summary="Delete Agent",
    description="Delete an agent configuration"
)
async def delete_agent(agent_name: str) -> APIResponse:
    """Delete an agent."""
    try:
        config_manager = ConfigManager()
        platform_config = config_manager.get_platform_config()

        # Find and remove agent
        original_count = len(platform_config.agents)
        platform_config.agents = [agent for agent in platform_config.agents if agent.name != agent_name]

        if len(platform_config.agents) == original_count:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # Save configuration
        config_manager.save_config(platform_config)

        return APIResponse(
            success=True,
            message=f"Agent '{agent_name}' deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete agent: {str(e)}"
        )


@router.post(
    "/agents/{agent_name}/test",
    response_model=APIResponse,
    summary="Test Agent",
    description="Test an agent by sending a message"
)
async def test_agent(
    agent_name: str,
    message: str = Query(..., description="Test message to send to the agent")
) -> APIResponse:
    """Test an agent."""
    try:
        agent = agent_registry.get_agent(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # Test the agent
        result = await agent.execute(message)

        response_data = {
            "agent_name": agent_name,
            "message": message,
            "success": result.success,
            "response": result.result if result.success else None,
            "error": result.error if not result.success else None,
            "execution_time": getattr(result, 'execution_time', None),
            "metadata": getattr(result, 'metadata', None),
        }

        return APIResponse(
            success=result.success,
            data=response_data,
            message=f"Agent test {'successful' if result.success else 'failed'}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test agent: {str(e)}"
        )


@router.get(
    "/agents/{agent_name}/health",
    response_model=APIResponse,
    summary="Agent Health",
    description="Check the health status of a specific agent"
)
async def agent_health(agent_name: str) -> APIResponse:
    """Check agent health."""
    try:
        agent = agent_registry.get_agent(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        healthy = await agent.health_check()

        health_data = {
            "name": agent_name,
            "type": agent.type,
            "healthy": healthy,
            "capabilities": agent.capabilities,
        }

        return APIResponse(
            success=True,
            data=health_data,
            message=f"Agent '{agent_name}' is {'healthy' if healthy else 'unhealthy'}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check agent health: {str(e)}"
        )


@router.post(
    "/agents/validate",
    response_model=ValidateConfigResponse,
    summary="Validate Agent Config",
    description="Validate an agent configuration"
)
async def validate_agent(request: ValidateConfigRequest) -> ValidateConfigResponse:
    """Validate agent configuration."""
    try:
        validation_result = validate_agent_config(request.config)

        return ValidateConfigResponse(
            errors=validation_result.errors,
            warnings=validation_result.warnings,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate agent configuration: {str(e)}"
        )