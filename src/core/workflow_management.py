"""Workflow management implementation.

This        # Load built-in templates
        try:
            # Load available templates
            template_classes = [
                ("code-review", get_template("code-review")),
                ("pr-automation", get_template("pr-automation")),
                ("task-development", get_template("task-development")),
            ]

            for name, template_class in template_classes:
                if template_class:
                    try:
                        template_instance = template_class()
                        self._templates[name] = template_instance
                    except Exception:
                        # Skip templates that can't be instantiated
                        pass
        except ImportError:
            # Templates module may not be available
            pass concrete implementation of workflow management
functionality for the multi-agent orchestration platform.
"""

from typing import Dict, Any, List, Optional
import uuid
import time
from pathlib import Path

from src.core.workflow import (
    WorkflowDefinition, WorkflowStep, WorkflowType, ExecutionStatus,
    WorkflowEngine, WorkflowTemplate, WorkflowExecutionError
)
from src.core.config import PlatformConfig
from src.agents.base import AgentRegistry
from src.workflows.templates import get_template


class WorkflowManagement:
    """Concrete implementation of workflow management functionality.

    Provides centralized management of workflow definitions, templates,
    and execution lifecycle.
    """

    def __init__(self, config: PlatformConfig, agent_registry: AgentRegistry):
        """Initialize workflow management.

        Args:
            config: Platform configuration
            agent_registry: Agent registry instance
        """
        self.config = config
        self.agent_registry = agent_registry
        self.workflow_engine = WorkflowEngine(config, agent_registry)
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._templates: Dict[str, WorkflowTemplate] = {}

        # Load built-in templates
        self._load_templates()

    def _load_templates(self):
        """Load built-in workflow templates."""
        try:
            # Load available templates
            template_classes = [
                ("code_review", get_template("code-review")),
                ("pr_automation", get_template("pr-automation")),
                ("task_development", get_template("task-development")),
            ]

            for name, template_class in template_classes:
                if template_class:
                    try:
                        template_instance = template_class()
                        self._templates[name] = template_instance
                    except Exception:
                        # Skip templates that can't be instantiated
                        pass
        except ImportError:
            # Templates module may not be available
            pass

    def create_workflow_definition(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        workflow_type: WorkflowType = WorkflowType.SIMPLE,
        config: Optional[Dict[str, Any]] = None
    ) -> WorkflowDefinition:
        """Create a workflow definition.

        Args:
            name: Workflow name
            description: Workflow description
            steps: List of step configurations
            workflow_type: Type of workflow
            config: Additional configuration

        Returns:
            WorkflowDefinition instance

        Raises:
            WorkflowExecutionError: If creation fails
        """
        try:
            # Generate unique ID - use name as ID for consistency with config system
            workflow_id = name

            # Convert step configs to WorkflowStep objects
            workflow_steps = []
            for i, step_config in enumerate(steps):
                step = WorkflowStep(
                    id=step_config.get("id", f"step_{i}"),
                    name=step_config.get("name", step_config.get("id", f"Step {i+1}")),
                    agent_id=step_config.get("agent", step_config.get("agent_id", "")),
                    prompt_template=step_config.get("prompt", step_config.get("prompt_template", "")),
                    input_mappings=step_config.get("input_mappings", {}),
                    output_key=step_config.get("output_key", step_config.get("output", f"output_{i}")),
                    condition=step_config.get("condition"),
                    timeout_seconds=step_config.get("timeout_seconds", step_config.get("timeout", 300)),
                    retry_count=step_config.get("retry_count", 0),
                    dependencies=step_config.get("dependencies", [])
                )
                workflow_steps.append(step)

            # Create workflow definition
            workflow = WorkflowDefinition(
                id=workflow_id,
                name=name,
                description=description,
                type=workflow_type,
                steps=workflow_steps,
                config=config or {},
                metadata={
                    "created_at": time.time(),
                    "created_by": "workflow_management"
                }
            )

            # Validate the workflow
            self.validate_workflow_definition(workflow)

            # Store the workflow
            self._workflows[workflow_id] = workflow

            return workflow

        except Exception as e:
            raise WorkflowExecutionError(f"Failed to create workflow: {str(e)}", "")

    def validate_workflow_definition(self, workflow: WorkflowDefinition) -> bool:
        """Validate a workflow definition.

        Args:
            workflow: Workflow to validate

        Returns:
            bool: True if valid

        Raises:
            WorkflowExecutionError: If validation fails
        """
        # Validate basic structure
        if not workflow.id or not workflow.id.strip():
            raise WorkflowExecutionError("Workflow ID cannot be empty", workflow.id)

        if not workflow.name or not workflow.name.strip():
            raise WorkflowExecutionError("Workflow name cannot be empty", workflow.id)

        if not workflow.steps:
            raise WorkflowExecutionError("Workflow must have at least one step", workflow.id)

        # Validate steps
        step_ids = set()
        for step in workflow.steps:
            # Check for duplicate step IDs
            if step.id in step_ids:
                raise WorkflowExecutionError(f"Duplicate step ID: {step.id}", workflow.id)
            step_ids.add(step.id)

            # Validate step fields
            if not step.id or not step.id.strip():
                raise WorkflowExecutionError("Step ID cannot be empty", workflow.id)

            if not step.name or not step.name.strip():
                raise WorkflowExecutionError("Step name cannot be empty", workflow.id)

            if not step.agent_id or not step.agent_id.strip():
                raise WorkflowExecutionError(f"Step '{step.id}' must specify an agent", workflow.id)

            if not step.prompt_template or not step.prompt_template.strip():
                raise WorkflowExecutionError(f"Step '{step.id}' must have a prompt template", workflow.id)

            if not step.output_key or not step.output_key.strip():
                raise WorkflowExecutionError(f"Step '{step.id}' must have an output key", workflow.id)

            # Validate agent exists
            if step.agent_id not in self.agent_registry._agents:
                raise WorkflowExecutionError(f"Agent '{step.agent_id}' not found for step '{step.id}'", workflow.id)

        # Validate dependencies
        for step in workflow.steps:
            for dep in step.dependencies:
                if dep not in [s.output_key for s in workflow.steps]:
                    raise WorkflowExecutionError(f"Dependency '{dep}' not found for step '{step.id}'", workflow.id)

        return True

    def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        parameters: Dict[str, Any],
        workspace_dir: Optional[str] = None
    ) -> str:
        """Execute a workflow.

        Args:
            workflow: Workflow to execute
            parameters: Execution parameters
            workspace_dir: Workspace directory

        Returns:
            str: Execution ID

        Raises:
            WorkflowExecutionError: If execution fails
        """
        try:
            # Use asyncio to run the async execution
            import asyncio

            async def run_execution():
                return await self.workflow_engine.execute_workflow(
                    workflow=workflow,
                    parameters=parameters,
                    workspace_dir=workspace_dir
                )

            execution_id = asyncio.run(run_execution())
            return execution_id

        except Exception as e:
            raise WorkflowExecutionError(f"Failed to execute workflow: {str(e)}", "")

    def get_workflow_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow execution status.

        Args:
            execution_id: Execution identifier

        Returns:
            Dict with status information or None if not found
        """
        context = self.workflow_engine.get_execution_status(execution_id)
        if context is None:
            return None

        return {
            "execution_id": context.execution_id,
            "workflow_id": context.workflow_id,
            "status": context.status.value,
            "start_time": context.start_time,
            "end_time": context.end_time,
            "duration": context.duration,
            "parameters": context.parameters,
            "step_results": context.step_results,
            "errors": context.errors,
            "logs": context.logs
        }

    def cancel_workflow_execution(self, execution_id: str) -> bool:
        """Cancel a workflow execution.

        Args:
            execution_id: Execution identifier

        Returns:
            bool: True if cancelled successfully
        """
        return self.workflow_engine.cancel_execution(execution_id)

    def list_workflow_executions(self) -> List[Dict[str, Any]]:
        """List all workflow executions.

        Returns:
            List of execution information dictionaries
        """
        executions = []
        for context in self.workflow_engine.list_executions():
            executions.append({
                "execution_id": context.execution_id,
                "workflow_id": context.workflow_id,
                "status": context.status.value,
                "start_time": context.start_time,
                "end_time": context.end_time,
                "duration": context.duration,
                "parameters": context.parameters,
                "errors": context.errors
            })
        return executions

    def get_workflow_template(self, template_name: str) -> Optional[WorkflowTemplate]:
        """Get a workflow template by name.

        Args:
            template_name: Name of the template

        Returns:
            WorkflowTemplate instance or None if not found
        """
        return self._templates.get(template_name)

    def list_workflow_templates(self) -> List[Dict[str, Any]]:
        """List available workflow templates.

        Returns:
            List of template information dictionaries
        """
        templates = []
        for name, template in self._templates.items():
            templates.append({
                "name": name,
                "description": template.description,
                "version": template.version,
                "required_inputs": template.get_required_inputs(),
                "optional_inputs": template.get_optional_inputs()
            })
        return templates

    def customize_workflow_from_template(
        self,
        template_name: str,
        customizations: Dict[str, Any]
    ) -> WorkflowDefinition:
        """Create a customized workflow from a template.

        Args:
            template_name: Name of the template
            customizations: Customization parameters

        Returns:
            Customized WorkflowDefinition

        Raises:
            WorkflowExecutionError: If customization fails
        """
        template = self.get_workflow_template(template_name)
        if template is None:
            raise WorkflowExecutionError(f"Template '{template_name}' not found", "")

        try:
            # Get template configuration
            template_config = template.get_template_config()

            # Apply customizations
            name = customizations.get("name", template_config.get("name", f"Custom {template_name}"))
            description = customizations.get("description", template_config.get("description", template.description))
            workflow_type = WorkflowType(customizations.get("type", template_config.get("type", "simple")))
            config = customizations.get("config", template_config.get("config", {}))

            # Get steps from template config
            steps = template_config.get("steps", [])

            # Create workflow definition
            workflow = self.create_workflow_definition(
                name=name,
                description=description,
                steps=steps,
                workflow_type=workflow_type,
                config=config
            )

            return workflow

        except Exception as e:
            raise WorkflowExecutionError(f"Failed to customize template: {str(e)}", "")

    def get_workflow_definition(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get a workflow definition by ID.

        Args:
            workflow_id: Workflow identifier

        Returns:
            WorkflowDefinition or None if not found
        """
        return self._workflows.get(workflow_id)

    def list_workflow_definitions(self) -> List[Dict[str, Any]]:
        """List all workflow definitions.

        Returns:
            List of workflow information dictionaries
        """
        workflows = []
        for workflow_id, workflow in self._workflows.items():
            workflows.append({
                "id": workflow_id,
                "name": workflow.name,
                "description": workflow.description,
                "type": workflow.type.value,
                "steps_count": len(workflow.steps),
                "created_at": workflow.metadata.get("created_at")
            })
        return workflows

    def delete_workflow_definition(self, workflow_id: str) -> bool:
        """Delete a workflow definition.

        Args:
            workflow_id: Workflow identifier

        Returns:
            bool: True if deleted successfully
        """
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False