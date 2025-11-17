"""Execution management API routes.

This module provides API endpoints for managing workflow executions.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks

from ..models import (
    APIResponse,
    ErrorResponse,
    CreateExecutionRequest,
    CreateExecutionResponse,
    GetExecutionResponse,
    ListExecutionsResponse,
    ExecutionResult,
)
from ...core.config import ConfigManager
from ...core.workflow import WorkflowEngine, ExecutionStatus
from ...agents.base import agent_registry, AgentType
from ...agents.claude import ClaudeAgent
from ...agents.codex import CodexAgent
from ...agents.copilot import CopilotAgent
from ...agents.cli_agent import CLIExecutionAgent
from ...agents.docker_agent import DockerExecutionAgent

router = APIRouter()


def create_agent_from_config(agent_config_entry) -> Optional[Any]:
    """Create an agent instance from configuration.

    Args:
        agent_config_entry: Agent configuration entry from config

    Returns:
        Agent instance or None if creation fails
    """
    from ...agents.base import AgentConfig

    # Create AgentConfig with type field
    agent_config = AgentConfig(
        name=agent_config_entry.name,
        type=getattr(agent_config_entry, 'type', AgentType.LLM),  # Default to LLM for backward compatibility
        provider=getattr(agent_config_entry, 'provider', None),
        model=getattr(agent_config_entry, 'model', None),
        api_key=getattr(agent_config_entry, 'api_key', None),
        max_tokens=getattr(agent_config_entry, 'max_tokens', 4096),
        temperature=getattr(agent_config_entry, 'temperature', 0.7),
        timeout_seconds=getattr(agent_config_entry, 'timeout_seconds', 60),
        max_retries=getattr(agent_config_entry, 'max_retries', 3),
        retry_delay=getattr(agent_config_entry, 'retry_delay', 1.0),
        command=getattr(agent_config_entry, 'command', None),
        working_directory=getattr(agent_config_entry, 'working_directory', None),
        environment_variables=getattr(agent_config_entry, 'environment_variables', None),
        docker_image=getattr(agent_config_entry, 'docker_image', None),
        docker_command=getattr(agent_config_entry, 'docker_command', None),
        docker_environment=getattr(agent_config_entry, 'docker_environment', None),
        docker_volumes=getattr(agent_config_entry, 'docker_volumes', None),
    )

    # Create agent based on type
    try:
        if agent_config.type == AgentType.LLM:
            if agent_config.provider == "anthropic":
                return ClaudeAgent(agent_config)
            elif agent_config.provider == "openai":
                return CodexAgent(agent_config)
            elif agent_config.provider == "github":
                return CopilotAgent(agent_config)
        elif agent_config.type == AgentType.CLI:
            return CLIExecutionAgent(agent_config)
        elif agent_config.type == AgentType.DOCKER:
            return DockerExecutionAgent(agent_config)

        # Unknown type or provider
        return None
    except Exception:
        # If agent creation fails, return None
        return None


@router.post(
    "/executions",
    response_model=CreateExecutionResponse,
    summary="Create Execution",
    description="Start a new workflow execution"
)
async def create_execution(
    request: CreateExecutionRequest,
    background_tasks: BackgroundTasks,
) -> CreateExecutionResponse:
    """Create and start a new workflow execution."""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Get workflow definition from config
        if request.workflow_name not in config.workflows:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow '{request.workflow_name}' not found"
            )

        workflow_config = config.workflows[request.workflow_name]

        # Create workflow definition
        from ...core.workflow import WorkflowDefinition, WorkflowStep

        steps = []
        for i, step_config in enumerate(workflow_config.steps):
            steps.append(WorkflowStep(
                id=f"step_{i}",
                name=step_config.get("name", f"Step {i}"),
                agent_id=step_config.get("agent", ""),
                prompt_template=step_config.get("prompt", ""),
                input_mappings=step_config.get("inputs", {}),
                output_key=step_config.get("output", f"output_{i}"),
                timeout_seconds=step_config.get("timeout", 300),
                retry_count=step_config.get("retry", 0),
                dependencies=step_config.get("dependencies", [])
            ))

        workflow_def = WorkflowDefinition(
            id=request.workflow_name,
            name=workflow_config.name,
            description=workflow_config.description,
            type=workflow_config.type,
            steps=steps,
            config=workflow_config.config,
            metadata=workflow_config.metadata
        )

        # Initialize agents from config if not already registered
        # TODO: Re-enable agent initialization after fixing config compatibility
        # for agent_name, agent_config_entry in config.agents.items():
        #     if agent_name not in agent_registry.list_agents():
        #         agent = create_agent_from_config(agent_config_entry)
        #         if agent:
        #             agent_registry.register(agent)

        # Initialize workflow engine
        workflow_engine = WorkflowEngine(config, agent_registry)

        if request.async_execution:
            # Run asynchronously
            execution_id = await workflow_engine.execute_workflow(
                workflow=workflow_def,
                parameters=request.inputs or {},
                execution_id=None  # Will be generated
            )

            execution_result = ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.RUNNING,
                result=None,
                error=None,
                started_at=None,
                completed_at=None,
                duration=None
            )
        else:
            # For synchronous execution, we'd need to wait for completion
            # This is simplified - in practice, sync execution might not be supported
            raise HTTPException(
                status_code=501,
                detail="Synchronous execution not yet implemented"
            )

        return CreateExecutionResponse(
            success=True,
            data=execution_result,
            message=f"Execution {'started' if request.async_execution else 'completed'} successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create execution: {str(e)}"
        )


@router.get(
    "/executions/{execution_id}",
    response_model=GetExecutionResponse,
    summary="Get Execution",
    description="Get the status and result of a workflow execution"
)
async def get_execution(execution_id: str) -> GetExecutionResponse:
    """Get execution status and result."""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        workflow_engine = WorkflowEngine(config, agent_registry)

        execution_context = workflow_engine.get_execution_status(execution_id)

        if execution_context is None:
            raise HTTPException(
                status_code=404,
                detail=f"Execution '{execution_id}' not found"
            )

        execution_result = ExecutionResult(
            execution_id=execution_context.execution_id,
            status=execution_context.status,
            result=execution_context.step_results if execution_context.status == ExecutionStatus.COMPLETED else None,
            error=execution_context.errors[0] if execution_context.errors else None,
            started_at=execution_context.start_time,
            completed_at=execution_context.end_time,
            duration=execution_context.duration
        )

        return GetExecutionResponse(
            success=True,
            data=execution_result,
            message=f"Execution '{execution_id}' found"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution: {str(e)}"
        )


@router.get(
    "/executions",
    response_model=ListExecutionsResponse,
    summary="List Executions",
    description="Get a list of workflow executions"
)
async def list_executions(
    workflow_name: Optional[str] = Query(None, description="Filter by workflow name"),
    status: Optional[str] = Query(None, description="Filter by execution status"),
    limit: int = Query(50, description="Maximum number of executions to return"),
    offset: int = Query(0, description="Number of executions to skip")
) -> ListExecutionsResponse:
    """List workflow executions."""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        workflow_engine = WorkflowEngine(config, agent_registry)

        executions = workflow_engine.list_executions()

        # Apply filters
        if workflow_name:
            executions = [e for e in executions if e.workflow_id == workflow_name]

        if status:
            executions = [e for e in executions if e.status.value == status]

        # Apply pagination
        executions = executions[offset:offset + limit]

        execution_results = []
        for execution in executions:
            execution_results.append(ExecutionResult(
                execution_id=execution.execution_id,
                status=execution.status,
                result=execution.step_results if execution.status == ExecutionStatus.COMPLETED else None,
                error=execution.errors[0] if execution.errors else None,
                started_at=execution.start_time,
                completed_at=execution.end_time,
                duration=execution.duration
            ))

        return ListExecutionsResponse(
            success=True,
            data=execution_results,
            message=f"Found {len(execution_results)} executions"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list executions: {str(e)}"
        )


@router.delete(
    "/executions/{execution_id}",
    response_model=APIResponse,
    summary="Cancel Execution",
    description="Cancel a running workflow execution"
)
async def cancel_execution(execution_id: str) -> APIResponse:
    """Cancel a running execution."""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        workflow_engine = WorkflowEngine(config, agent_registry)

        cancelled = workflow_engine.cancel_execution(execution_id)

        if cancelled:
            return APIResponse(
                success=True,
                message=f"Execution '{execution_id}' cancelled successfully"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Execution '{execution_id}' not found or not running"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel execution: {str(e)}"
        )


@router.get(
    "/executions/active",
    response_model=APIResponse,
    summary="Active Executions",
    description="Get the count of currently active executions"
)
async def get_active_executions() -> APIResponse:
    """Get active executions count."""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        workflow_engine = WorkflowEngine(config, agent_registry)

        # Count running executions
        active_count = workflow_engine.get_active_execution_count()

        return APIResponse(
            success=True,
            data={"active_executions": active_count},
            message=f"{active_count} active executions"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get active executions: {str(e)}"
        )


@router.get(
    "/executions/stats",
    response_model=APIResponse,
    summary="Execution Statistics",
    description="Get execution statistics and metrics"
)
async def get_execution_stats(
    workflow_name: Optional[str] = Query(None, description="Filter by workflow name")
) -> APIResponse:
    """Get execution statistics."""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        workflow_engine = WorkflowEngine(config, agent_registry)

        executions = workflow_engine.list_executions()

        # Apply workflow filter
        if workflow_name:
            executions = [e for e in executions if e.workflow_id == workflow_name]

        # Calculate statistics
        total_executions = len(executions)
        completed = len([e for e in executions if e.status == ExecutionStatus.COMPLETED])
        failed = len([e for e in executions if e.status == ExecutionStatus.FAILED])
        running = len([e for e in executions if e.status == ExecutionStatus.RUNNING])

        success_rate = (completed / total_executions) if total_executions > 0 else 0.0

        # Calculate average duration for completed executions
        durations = [e.duration for e in executions if e.duration is not None and e.status == ExecutionStatus.COMPLETED]
        average_duration = sum(durations) / len(durations) if durations else 0.0

        stats = {
            "total_executions": total_executions,
            "successful_executions": completed,
            "failed_executions": failed,
            "running_executions": running,
            "success_rate": success_rate,
            "average_duration": average_duration,
        }

        if workflow_name:
            stats["workflow_name"] = workflow_name

        return APIResponse(
            success=True,
            data=stats,
            message="Execution statistics retrieved"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution statistics: {str(e)}"
        )


@router.post(
    "/executions/{execution_id}/retry",
    response_model=APIResponse,
    summary="Retry Execution",
    description="Retry a failed workflow execution"
)
async def retry_execution(execution_id: str) -> APIResponse:
    """Retry a failed execution."""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        workflow_engine = WorkflowEngine(config, agent_registry)

        # Get the original execution
        original_execution = workflow_engine.get_execution_status(execution_id)

        if original_execution is None:
            raise HTTPException(
                status_code=404,
                detail=f"Execution '{execution_id}' not found"
            )

        if original_execution.status != ExecutionStatus.FAILED:
            raise HTTPException(
                status_code=400,
                detail=f"Execution '{execution_id}' is not in failed state"
            )

        # Get workflow definition
        if original_execution.workflow_id not in config.workflows:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow '{original_execution.workflow_id}' not found"
            )

        workflow_config = config.workflows[original_execution.workflow_id]

        # Create workflow definition (same as above)
        from ...core.workflow import WorkflowDefinition, WorkflowStep

        steps = []
        for i, step_config in enumerate(workflow_config.steps):
            steps.append(WorkflowStep(
                id=f"step_{i}",
                name=step_config.get("name", f"Step {i}"),
                agent_id=step_config.get("agent", ""),
                prompt_template=step_config.get("prompt", ""),
                input_mappings=step_config.get("inputs", {}),
                output_key=step_config.get("output", f"output_{i}"),
                timeout_seconds=step_config.get("timeout", 300),
                retry_count=step_config.get("retry", 0),
                dependencies=step_config.get("dependencies", [])
            ))

        workflow_def = WorkflowDefinition(
            id=original_execution.workflow_id,
            name=workflow_config.name,
            description=workflow_config.description,
            type=workflow_config.type,
            steps=steps,
            config=workflow_config.config,
            metadata=workflow_config.metadata
        )

        # Start new execution
        new_execution_id = await workflow_engine.execute_workflow(
            workflow=workflow_def,
            parameters=original_execution.parameters,
            execution_id=None
        )

        return APIResponse(
            success=True,
            data={"new_execution_id": new_execution_id},
            message=f"Retry execution started with ID: {new_execution_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retry execution: {str(e)}"
        )