"""Workflow orchestration engine for the multi-agent platform.

This module provides the core workflow execution engine that coordinates
multiple agents to perform complex development tasks.
"""

import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List, Union, Callable
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import json

from pydantic import BaseModel, Field

from .config import PlatformConfig
from ..agents.base import BaseAgent, AgentRegistry, AgentExecutionError


class WorkflowTemplate:
    """Base class for workflow templates.

    Provides a standard interface for workflow templates that can be
    instantiated and configured for different use cases.
    """

    def __init__(self, name: str, description: str, version: str = "1.0.0"):
        """Initialize workflow template.

        Args:
            name: Template name
            description: Template description
            version: Template version
        """
        self.name = name
        self.description = description
        self.version = version

    def get_template_config(self) -> Dict[str, Any]:
        """Get the template configuration.

        Returns:
            Template configuration dictionary
        """
        raise NotImplementedError("Subclasses must implement get_template_config")

    def get_required_inputs(self) -> List[str]:
        """Get required input parameters.

        Returns:
            List of required input parameter names
        """
        raise NotImplementedError("Subclasses must implement get_required_inputs")

    def get_optional_inputs(self) -> List[str]:
        """Get optional input parameters.

        Returns:
            List of optional input parameter names
        """
        return []

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate workflow inputs.

        Args:
            inputs: Input parameters to validate

        Returns:
            True if inputs are valid, False otherwise
        """
        required = self.get_required_inputs()
        return all(key in inputs for key in required)


class WorkflowType(str, Enum):
    """Enumeration of supported workflow types."""
    SIMPLE = "simple"
    LANGGRAPH = "langgraph"


class ExecutionStatus(str, Enum):
    """Enumeration of workflow execution statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStep(BaseModel):
    """Definition of a single workflow step."""

    id: str = Field(..., description="Unique step identifier")
    name: str = Field(..., description="Human-readable step name")
    agent_id: str = Field(..., description="Agent to execute this step")
    prompt_template: str = Field(..., description="Jinja2 template for the prompt")
    input_mappings: Dict[str, str] = Field(default_factory=dict, description="Input parameter mappings")
    output_key: str = Field(..., description="Key to store step output")
    condition: Optional[str] = Field(None, description="Condition for step execution")
    timeout_seconds: int = Field(300, ge=10, le=3600, description="Step timeout")
    retry_count: int = Field(0, ge=0, le=5, description="Number of retries on failure")
    dependencies: List[str] = Field(default_factory=list, description="Required previous step outputs")


class WorkflowDefinition(BaseModel):
    """Definition of a complete workflow."""

    id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Human-readable workflow name")
    description: str = Field("", description="Workflow description")
    type: WorkflowType = Field(WorkflowType.SIMPLE, description="Workflow type")
    steps: List[WorkflowStep] = Field(default_factory=list, description="Ordered list of steps")
    config: Dict[str, Any] = Field(default_factory=dict, description="Workflow-specific configuration")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


@dataclass
class ExecutionContext:
    """Context for workflow execution."""

    execution_id: str
    workflow_id: str
    workspace_dir: Path
    parameters: Dict[str, Any] = field(default_factory=dict)
    shared_config: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    step_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    def add_log(self, level: str, message: str, step_id: Optional[str] = None, **metadata):
        """Add a log entry to the execution context."""
        log_entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "step_id": step_id,
            **metadata
        }
        self.logs.append(log_entry)

    def to_dict(self) -> Dict[str, Any]:
        """Convert execution context to dictionary."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "workspace_dir": str(self.workspace_dir),
            "parameters": self.parameters,
            "shared_config": self.shared_config,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status.value,
            "step_results": self.step_results,
            "errors": self.errors,
            "logs": self.logs,
            "duration": self.duration,
        }


class WorkflowExecutionError(Exception):
    """Exception raised when workflow execution fails."""

    def __init__(self, message: str, execution_id: str, step_id: Optional[str] = None, details: Dict[str, Any] = None):
        """Initialize the exception.

        Args:
            message: Error message
            execution_id: Execution identifier
            step_id: Step that failed (optional)
            details: Additional error details
        """
        super().__init__(message)
        self.execution_id = execution_id
        self.step_id = step_id
        self.details = details or {}


class WorkflowEngine:
    """Core workflow orchestration engine."""

    def __init__(self, config: PlatformConfig, agent_registry: AgentRegistry):
        """Initialize the workflow engine.

        Args:
            config: Platform configuration
            agent_registry: Registry of available agents
        """
        self.config = config
        self.agent_registry = agent_registry
        self._executions: Dict[str, ExecutionContext] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        parameters: Dict[str, Any],
        workspace_dir: Optional[Union[str, Path]] = None,
        execution_id: Optional[str] = None
    ) -> str:
        """Execute a workflow asynchronously.

        Args:
            workflow: Workflow definition to execute
            parameters: Execution parameters
            workspace_dir: Workspace directory (uses config default if not provided)
            execution_id: Optional execution ID (generated if not provided)

        Returns:
            str: Execution ID for tracking

        Raises:
            WorkflowExecutionError: If execution cannot be started
        """
        # Generate execution ID if not provided
        if execution_id is None:
            execution_id = str(uuid.uuid4())

        # Determine workspace directory
        if workspace_dir is None:
            workspace_dir = Path(self.config.global_.workspace_dir)
        else:
            workspace_dir = Path(workspace_dir)

        # Create execution context
        context = ExecutionContext(
            execution_id=execution_id,
            workflow_id=workflow.id,
            workspace_dir=workspace_dir,
            parameters=parameters,
            shared_config=workflow.config.copy(),
            status=ExecutionStatus.PENDING,
        )

        # Validate workflow and parameters
        self._validate_workflow(workflow, context)

        # Store execution context
        self._executions[execution_id] = context

        # Start execution task
        task = asyncio.create_task(self._execute_workflow_async(workflow, context))
        self._running_tasks[execution_id] = task

        context.add_log("INFO", f"Started workflow execution: {workflow.name}")
        context.status = ExecutionStatus.RUNNING

        return execution_id

    async def execute_workflow_async(
        self,
        workflow_name: str,
        inputs: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> str:
        """Execute a workflow asynchronously by name.

        Args:
            workflow_name: Name of the workflow to execute
            inputs: Input parameters for the workflow
            timeout: Optional timeout in seconds

        Returns:
            str: Execution ID for tracking

        Raises:
            WorkflowExecutionError: If workflow not found or execution fails
        """
        # Get workflow definition from config
        if workflow_name not in self.config.workflows:
            raise WorkflowExecutionError(f"Workflow '{workflow_name}' not found", "", None)

        workflow_config = self.config.workflows[workflow_name]

        # Convert config to WorkflowDefinition
        workflow_def = self._config_to_workflow_definition(workflow_name, workflow_config)

        # Execute workflow
        execution_id = await self.execute_workflow(
            workflow=workflow_def,
            parameters=inputs,
            execution_id=None
        )

        return execution_id

    def execute_workflow_sync(
        self,
        workflow_name: str,
        inputs: Dict[str, Any],
        timeout: Optional[int] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None
    ) -> Dict[str, Any]:
        """Execute a workflow synchronously by name.

        Args:
            workflow_name: Name of the workflow to execute
            inputs: Input parameters for the workflow
            timeout: Optional timeout in seconds
            progress_callback: Optional callback for progress updates (message, progress_percent, status)

        Returns:
            Dict containing execution results

        Raises:
            WorkflowExecutionError: If workflow not found or execution fails
        """
        import time

        # Get workflow definition from config
        if workflow_name not in self.config.workflows:
            raise WorkflowExecutionError(f"Workflow '{workflow_name}' not found", "", None)

        workflow_config = self.config.workflows[workflow_name]

        # Convert config to WorkflowDefinition
        workflow_def = self._config_to_workflow_definition(workflow_name, workflow_config)

        # Execute workflow synchronously
        start_time = time.time()

        try:
            execution_id = asyncio.run(
                self.execute_workflow(
                    workflow=workflow_def,
                    parameters=inputs,
                    execution_id=None
                )
            )

            # Report initial progress
            if progress_callback:
                progress_callback("Workflow started", 0.0, "running")

            total_steps = len(workflow_def.steps)
            completed_steps = 0

            # Wait for completion with progress updates
            while True:
                context = self.get_execution_status(execution_id)
                if context:
                    # Calculate progress based on completed steps
                    current_completed = sum(1 for log in context.logs if "Step completed" in log.get("message", ""))
                    if current_completed != completed_steps:
                        completed_steps = current_completed
                        progress = min(100.0, (completed_steps / total_steps) * 100.0) if total_steps > 0 else 100.0

                        # Get current step info
                        current_step = "unknown"
                        for log in reversed(context.logs):
                            if "Executing step" in log.get("message", ""):
                                current_step = log.get("step_id", "unknown")
                                break

                        if progress_callback:
                            progress_callback(f"Executing step: {current_step}", progress, context.status.value)

                    if context.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                        # Final progress update
                        if progress_callback:
                            if context.status == ExecutionStatus.COMPLETED:
                                progress_callback("Workflow completed", 100.0, "completed")
                            elif context.status == ExecutionStatus.FAILED:
                                progress_callback("Workflow failed", 100.0, "failed")
                            else:
                                progress_callback("Workflow cancelled", 100.0, "cancelled")
                        break

                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    # Cancel execution
                    self.cancel_execution(execution_id)
                    return {
                        "success": False,
                        "error": f"Workflow execution timed out after {timeout} seconds",
                        "execution_id": execution_id,
                        "duration": time.time() - start_time
                    }

                asyncio.run(asyncio.sleep(0.1))

            context = self.get_execution_status(execution_id)
            duration = time.time() - start_time

            if context.status == ExecutionStatus.COMPLETED:
                return {
                    "success": True,
                    "result": context.step_results,
                    "execution_id": execution_id,
                    "duration": duration
                }
            else:
                return {
                    "success": False,
                    "error": "; ".join(context.errors) if context.errors else "Unknown error",
                    "execution_id": execution_id,
                    "duration": duration
                }

        except Exception as e:
            duration = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "execution_id": f"error-{int(time.time())}",
                "duration": duration
            }

    def _config_to_workflow_definition(self, name: str, config_entry) -> WorkflowDefinition:
        """Convert workflow config entry to WorkflowDefinition.

        Args:
            name: Workflow name
            config_entry: Configuration entry

        Returns:
            WorkflowDefinition instance
        """
        # Convert config steps to WorkflowStep objects
        steps = []
        for step_config in config_entry.steps:
            step = WorkflowStep(
                id=step_config.get("id", step_config.get("name", f"step_{len(steps)}")),
                name=step_config.get("name", step_config.get("id", f"step_{len(steps)}")),
                agent_id=step_config.get("agent", step_config.get("agent_id", "")),
                prompt_template=step_config.get("prompt", step_config.get("prompt_template", "")),
                input_mappings=step_config.get("input_mappings", {}),
                output_key=step_config.get("output_key", step_config.get("output", f"output_{len(steps)}")),
                condition=step_config.get("condition"),
                retry_count=step_config.get("retry_count", 0),
                timeout=step_config.get("timeout")
            )
            steps.append(step)

        return WorkflowDefinition(
            id=name,
            name=config_entry.name,
            description=config_entry.description,
            type=WorkflowType(config_entry.type),
            steps=steps,
            config=config_entry.config or {},
            metadata={}
        )

    def _validate_workflow(self, workflow: WorkflowDefinition, context: ExecutionContext):
        """Validate workflow before execution.

        Args:
            workflow: Workflow to validate
            context: Execution context

        Raises:
            WorkflowExecutionError: If validation fails
        """
        # Check that all required agents are available
        for step in workflow.steps:
            if step.agent_id not in self.agent_registry._agents:
                raise WorkflowExecutionError(
                    f"Agent '{step.agent_id}' not found for step '{step.id}'",
                    context.execution_id,
                    step.id
                )

        # Validate workspace directory
        if not context.workspace_dir.exists():
            try:
                context.workspace_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise WorkflowExecutionError(
                    f"Cannot create workspace directory: {e}",
                    context.execution_id
                )

        # Validate parameters
        # TODO: Add parameter schema validation

    async def _execute_workflow_async(self, workflow: WorkflowDefinition, context: ExecutionContext):
        """Execute workflow asynchronously.

        Args:
            workflow: Workflow definition
            context: Execution context
        """
        try:
            if workflow.type == WorkflowType.SIMPLE:
                await self._execute_simple_workflow(workflow, context)
            elif workflow.type == WorkflowType.LANGGRAPH:
                await self._execute_langgraph_workflow(workflow, context)
            else:
                raise WorkflowExecutionError(
                    f"Unsupported workflow type: {workflow.type}",
                    context.execution_id
                )

            context.status = ExecutionStatus.COMPLETED
            context.end_time = time.time()
            context.add_log("INFO", f"Workflow completed successfully: {workflow.name}")

        except Exception as e:
            context.status = ExecutionStatus.FAILED
            context.end_time = time.time()
            context.errors.append(str(e))
            context.add_log("ERROR", f"Workflow failed: {e}", error=str(e))

        finally:
            # Clean up running task
            if context.execution_id in self._running_tasks:
                del self._running_tasks[context.execution_id]

    async def _execute_simple_workflow(self, workflow: WorkflowDefinition, context: ExecutionContext):
        """Execute a simple sequential workflow.

        Args:
            workflow: Simple workflow definition
            context: Execution context
        """
        for step in workflow.steps:
            # Check if step should be executed based on condition
            if not self._should_execute_step(step, context):
                context.add_log("INFO", f"Skipping step: {step.name}", step_id=step.id)
                continue

            # Execute step
            await self._execute_step(step, context)

    async def _execute_langgraph_workflow(self, workflow: WorkflowDefinition, context: ExecutionContext):
        """Execute a LangGraph-based workflow.

        Args:
            workflow: LangGraph workflow definition
            context: Execution context
        """
        # TODO: Implement LangGraph execution
        # For now, fall back to simple execution
        context.add_log("WARNING", "LangGraph execution not implemented, falling back to simple execution")
        await self._execute_simple_workflow(workflow, context)

    def _should_execute_step(self, step: WorkflowStep, context: ExecutionContext) -> bool:
        """Determine if a step should be executed.

        Args:
            step: Workflow step
            context: Execution context

        Returns:
            bool: True if step should execute
        """
        if not step.condition:
            return True

        # Simple condition evaluation (can be extended)
        # For now, support basic variable checks
        try:
            # Evaluate condition as a simple expression
            condition = step.condition

            # Replace variable references with actual values
            for key, value in context.step_results.items():
                condition = condition.replace(f"{{{{ {key} }}}}", str(value))

            # Simple evaluation (very basic for now)
            if condition.startswith("{{") and condition.endswith("}}"):
                var_name = condition[2:-2].strip()
                return bool(context.step_results.get(var_name))

            return True  # Default to executing if condition is complex

        except Exception:
            # If condition evaluation fails, execute the step
            return True

    async def _execute_step(self, step: WorkflowStep, context: ExecutionContext):
        """Execute a single workflow step.

        Args:
            step: Step to execute
            context: Execution context

        Raises:
            WorkflowExecutionError: If step execution fails
        """
        context.add_log("INFO", f"Executing step: {step.name}", step_id=step.id)

        # Get the agent
        agent = self.agent_registry.get_agent(step.agent_id)

        # Prepare the prompt
        prompt = self._prepare_prompt(step, context)

        # Execute with retries
        last_error = None
        for attempt in range(step.retry_count + 1):
            try:
                start_time = time.time()
                response = await agent.execute(prompt)
                execution_time = time.time() - start_time

                # Store result
                context.step_results[step.output_key] = response.content

                context.add_log(
                    "INFO",
                    f"Step completed: {step.name}",
                    step_id=step.id,
                    execution_time=execution_time,
                    tokens_used=response.tokens_used
                )

                return

            except AgentExecutionError as e:
                last_error = e
                context.add_log(
                    "WARNING",
                    f"Step attempt {attempt + 1} failed: {e}",
                    step_id=step.id,
                    error=str(e)
                )

                if attempt < step.retry_count:
                    await asyncio.sleep(1 * (2 ** attempt))  # Exponential backoff

        # All retries failed
        error_msg = f"Step failed after {step.retry_count + 1} attempts: {last_error}"
        context.add_log("ERROR", error_msg, step_id=step.id)
        raise WorkflowExecutionError(error_msg, context.execution_id, step.id, {"last_error": str(last_error)})

    def _prepare_prompt(self, step: WorkflowStep, context: ExecutionContext) -> str:
        """Prepare the prompt for a step execution.

        Args:
            step: Workflow step
            context: Execution context

        Returns:
            str: Prepared prompt
        """
        prompt = step.prompt_template

        # Replace parameter placeholders
        for param_key, param_value in context.parameters.items():
            prompt = prompt.replace(f"{{{{ {param_key} }}}}", str(param_value))

        # Replace step result placeholders
        for result_key, result_value in context.step_results.items():
            prompt = prompt.replace(f"{{{{ {result_key} }}}}", str(result_value))

        # Replace input mappings
        for input_key, source_key in step.input_mappings.items():
            if source_key in context.step_results:
                value = context.step_results[source_key]
            elif source_key in context.parameters:
                value = context.parameters[source_key]
            else:
                value = ""
            prompt = prompt.replace(f"{{{{ {input_key} }}}}", str(value))

        return prompt

    def get_execution_status(self, execution_id: str) -> Optional[ExecutionContext]:
        """Get the status of a workflow execution.

        Args:
            execution_id: Execution identifier

        Returns:
            ExecutionContext or None if not found
        """
        return self._executions.get(execution_id)

    def list_executions(self) -> List[ExecutionContext]:
        """List all workflow executions.

        Returns:
            List of execution contexts
        """
        return list(self._executions.values())

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running workflow execution.

        Args:
            execution_id: Execution identifier

        Returns:
            bool: True if cancelled successfully
        """
        if execution_id in self._running_tasks:
            task = self._running_tasks[execution_id]
            if not task.done():
                task.cancel()
                if execution_id in self._executions:
                    self._executions[execution_id].status = ExecutionStatus.CANCELLED
                    self._executions[execution_id].add_log("INFO", "Execution cancelled by user")
                return True
        return False

    def get_active_execution_count(self) -> int:
        """Get the count of currently active (running) executions.

        Returns:
            int: Number of active executions
        """
        return len([e for e in self._executions.values() if e.status == ExecutionStatus.RUNNING])


# Global workflow engine instance
workflow_engine = WorkflowEngine(None, None)  # Will be initialized with proper config