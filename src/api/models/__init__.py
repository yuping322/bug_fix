"""API data models.

This module contains Pydantic models for API requests and responses.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class AgentType(str, Enum):
    """Agent types."""

    CLAUDE = "claude"
    CODEX = "codex"
    COPILOT = "copilot"


class WorkflowType(str, Enum):
    """Workflow types."""

    SIMPLE = "simple"
    LANGGRAPH = "langgraph"


class ExecutionStatus(str, Enum):
    """Execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentConfig(BaseModel):
    """Agent configuration model."""

    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    type: AgentType = Field(..., description="Agent type")
    api_key: str = Field(..., min_length=10, description="API key for the agent")
    model: Optional[str] = Field(None, min_length=1, description="Model name/version")
    max_tokens: Optional[int] = Field(None, ge=1, le=100000, description="Maximum tokens")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature setting")
    timeout: Optional[int] = Field(None, ge=1, le=300, description="Request timeout in seconds")

    model_config = ConfigDict(
        use_enum_values=True,
    )


class WorkflowStep(BaseModel):
    """Workflow step model."""

    name: str = Field(..., min_length=1, max_length=100, description="Step name")
    description: Optional[str] = Field(None, max_length=500, description="Step description")
    agent: str = Field(..., min_length=1, description="Agent to execute this step")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Step inputs")
    outputs: Optional[List[str]] = Field(None, description="Expected outputs")
    timeout: Optional[int] = Field(None, ge=1, le=3600, description="Step timeout in seconds")


class WorkflowConfig(BaseModel):
    """Workflow configuration model."""

    name: str = Field(..., min_length=1, max_length=100, description="Workflow name")
    description: Optional[str] = Field(None, max_length=500, description="Workflow description")
    type: WorkflowType = Field(..., description="Workflow type")
    steps: List[WorkflowStep] = Field(..., min_length=1, description="Workflow steps")
    agents: List[str] = Field(..., min_length=1, description="Required agents")
    timeout: Optional[int] = Field(None, ge=1, le=3600, description="Workflow timeout in seconds")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(
        use_enum_values=True,
    )


class PlatformConfig(BaseModel):
    """Platform configuration model."""

    name: str = Field(..., min_length=1, max_length=100, description="Platform name")
    version: str = Field(..., min_length=1, description="Platform version")
    description: Optional[str] = Field(None, max_length=500, description="Platform description")
    agents: List[AgentConfig] = Field(default_factory=list, description="Configured agents")
    workflows: List[WorkflowConfig] = Field(default_factory=list, description="Configured workflows")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Platform settings")


class ExecutionRequest(BaseModel):
    """Execution request model."""

    workflow_name: str = Field(..., min_length=1, description="Name of workflow to execute")
    inputs: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Execution inputs")
    timeout: Optional[int] = Field(None, ge=1, le=3600, description="Execution timeout")
    async_execution: bool = Field(False, description="Whether to execute asynchronously")


class ExecutionResult(BaseModel):
    """Execution result model."""

    execution_id: str = Field(..., min_length=1, description="Execution ID")
    status: ExecutionStatus = Field(..., description="Execution status")
    result: Optional[Any] = Field(None, description="Execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None, description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution completion time")
    duration: Optional[float] = Field(None, ge=0, description="Execution duration in seconds")

    model_config = ConfigDict(
        use_enum_values=True,
    )


class AgentHealth(BaseModel):
    """Agent health status model."""

    name: str = Field(..., min_length=1, description="Agent name")
    type: AgentType = Field(..., description="Agent type")
    healthy: bool = Field(..., description="Health status")
    last_check: Optional[datetime] = Field(None, description="Last health check time")
    error: Optional[str] = Field(None, description="Health check error")
    latency: Optional[float] = Field(None, ge=0, description="Response latency in seconds")

    model_config = ConfigDict(
        use_enum_values=True,
    )


class WorkflowStatus(BaseModel):
    """Workflow status model."""

    name: str = Field(..., min_length=1, description="Workflow name")
    type: WorkflowType = Field(..., description="Workflow type")
    status: ExecutionStatus = Field(..., description="Current status")
    last_execution: Optional[datetime] = Field(None, description="Last execution time")
    success_rate: Optional[float] = Field(None, ge=0, le=1, description="Success rate (0-1)")
    average_duration: Optional[float] = Field(None, ge=0, description="Average execution duration")

    model_config = ConfigDict(
        use_enum_values=True,
    )


class PlatformStatus(BaseModel):
    """Platform status model."""

    name: str = Field(..., min_length=1, description="Platform name")
    version: str = Field(..., min_length=1, description="Platform version")
    status: str = Field(..., description="Overall status")
    uptime: Optional[float] = Field(None, ge=0, description="Uptime in seconds")
    agents: List[AgentHealth] = Field(default_factory=list, description="Agent health statuses")
    workflows: List[WorkflowStatus] = Field(default_factory=list, description="Workflow statuses")
    active_executions: int = Field(0, ge=0, description="Number of active executions")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class ValidationErrorResponse(BaseModel):
    """Validation error response model."""

    errors: List[str] = Field(..., description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")


class APIResponse(BaseModel):
    """Generic API response model."""

    success: bool = Field(..., description="Success status")
    data: Optional[Any] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


# Request/Response models for specific endpoints
class CreateExecutionRequest(ExecutionRequest):
    """Request model for creating an execution."""

    pass


class CreateExecutionResponse(APIResponse):
    """Response model for creating an execution."""

    data: Optional[ExecutionResult] = Field(None, description="Execution result")


class GetExecutionResponse(APIResponse):
    """Response model for getting execution status."""

    data: Optional[ExecutionResult] = Field(None, description="Execution result")


class ListExecutionsResponse(APIResponse):
    """Response model for listing executions."""

    data: Optional[List[ExecutionResult]] = Field(None, description="List of executions")


class HealthCheckResponse(APIResponse):
    """Response model for health check."""

    data: Optional[PlatformStatus] = Field(None, description="Platform status")


class ListAgentsResponse(APIResponse):
    """Response model for listing agents."""

    data: Optional[List[AgentHealth]] = Field(None, description="List of agents")


class ListWorkflowsResponse(APIResponse):
    """Response model for listing workflows."""

    data: Optional[List[WorkflowStatus]] = Field(None, description="List of workflows")


class ValidateConfigRequest(BaseModel):
    """Request model for config validation."""

    config: Dict[str, Any] = Field(..., description="Configuration to validate")


class ValidateConfigResponse(APIResponse):
    """Response model for config validation."""

    data: Optional[ValidationErrorResponse] = Field(None, description="Validation result")


# Additional response models for API endpoints
class AgentResponse(BaseModel):
    """Agent response model."""

    name: str = Field(..., description="Agent name")
    type: AgentType = Field(..., description="Agent type")
    provider: str = Field(..., description="AI provider")
    model: Optional[str] = Field(None, description="Model name")
    healthy: bool = Field(..., description="Health status")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    config: Optional[Dict[str, Any]] = Field(None, description="Agent configuration")


class AgentListResponse(APIResponse):
    """Response model for listing agents."""

    data: Optional[List[AgentResponse]] = Field(None, description="List of agents")


class WorkflowResponse(BaseModel):
    """Workflow response model."""

    name: str = Field(..., description="Workflow name")
    type: WorkflowType = Field(..., description="Workflow type")
    description: Optional[str] = Field(None, description="Workflow description")
    step_count: int = Field(..., description="Number of steps")
    agents: List[str] = Field(default_factory=list, description="Required agents")
    enabled: bool = Field(..., description="Whether workflow is enabled")


class WorkflowListResponse(APIResponse):
    """Response model for listing workflows."""

    data: Optional[List[WorkflowResponse]] = Field(None, description="List of workflows")


class ExecutionResponse(BaseModel):
    """Execution response model."""

    execution_id: str = Field(..., description="Execution ID")
    workflow_name: str = Field(..., description="Workflow name")
    status: ExecutionStatus = Field(..., description="Execution status")
    results: Optional[Dict[str, Any]] = Field(None, description="Execution results")
    error: Optional[str] = Field(None, description="Error message")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    duration: Optional[float] = Field(None, description="Duration in seconds")


class ExecutionListResponse(APIResponse):
    """Response model for listing executions."""

    data: Optional[List[ExecutionResponse]] = Field(None, description="List of executions")


class HealthResponse(APIResponse):
    """Response model for health check."""

    data: Optional[PlatformStatus] = Field(None, description="Platform health status")