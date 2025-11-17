"""Custom workflows tools for MCP.

This module provides tools for creating, managing, and executing custom
workflows through the MCP protocol.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
import logging
from datetime import datetime

from ...core.config import ConfigManager, WorkflowConfigEntry
from ...core.workflow import WorkflowEngine, WorkflowDefinition, WorkflowStep
from ...agents.base import agent_registry


logger = logging.getLogger(__name__)


@dataclass
class CustomWorkflow:
    """Represents a custom workflow created via MCP."""

    id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    agents: List[str]
    created_by: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    executions: List[str] = field(default_factory=list)  # Execution IDs
    tags: List[str] = field(default_factory=list)


class CustomWorkflowsManager:
    """Manager for custom workflows created via MCP."""

    def __init__(self, config_manager: ConfigManager):
        """Initialize the custom workflows manager.

        Args:
            config_manager: Configuration manager
        """
        self.config_manager = config_manager
        self.custom_workflows: Dict[str, CustomWorkflow] = {}
        self.workflow_engine: Optional[WorkflowEngine] = None

        # Add aliases for backward compatibility with tests
        self.templates: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize the custom workflows manager."""
        config = self.config_manager.get_config()
        self.workflow_engine = WorkflowEngine(config, agent_registry)

        # Load existing custom workflows from config
        await self._load_custom_workflows()

    async def _load_custom_workflows(self):
        """Load custom workflows from configuration."""
        try:
            config = self.config_manager.get_config()

            # Look for custom workflows in config
            custom_workflows_config = config.deployment.get("custom_workflows", {})

            for workflow_id, workflow_data in custom_workflows_config.items():
                workflow = CustomWorkflow(
                    id=workflow_id,
                    name=workflow_data.get("name", workflow_id),
                    description=workflow_data.get("description", ""),
                    steps=workflow_data.get("steps", []),
                    agents=workflow_data.get("agents", []),
                    created_by=workflow_data.get("created_by", "system"),
                    created_at=datetime.fromisoformat(workflow_data.get("created_at", datetime.utcnow().isoformat())),
                    updated_at=datetime.fromisoformat(workflow_data.get("updated_at", datetime.utcnow().isoformat())),
                    executions=workflow_data.get("executions", []),
                    tags=workflow_data.get("tags", [])
                )
                self.custom_workflows[workflow_id] = workflow

            logger.info(f"Loaded {len(self.custom_workflows)} custom workflows")

        except Exception as e:
            logger.error(f"Error loading custom workflows: {e}")

    async def save_custom_workflows(self):
        """Save custom workflows to configuration."""
        try:
            config = self.config_manager.get_config()

            # Convert workflows to config format
            custom_workflows_config = {}
            for workflow_id, workflow in self.custom_workflows.items():
                custom_workflows_config[workflow_id] = {
                    "name": workflow.name,
                    "description": workflow.description,
                    "steps": workflow.steps,
                    "agents": workflow.agents,
                    "created_by": workflow.created_by,
                    "created_at": workflow.created_at.isoformat(),
                    "updated_at": workflow.updated_at.isoformat(),
                    "executions": workflow.executions,
                    "tags": workflow.tags
                }

            # Update config
            if "custom_workflows" not in config.deployment:
                config.deployment["custom_workflows"] = {}

            config.deployment["custom_workflows"].update(custom_workflows_config)

            # Save config
            self.config_manager.save_config(config)

            logger.info(f"Saved {len(self.custom_workflows)} custom workflows")

        except Exception as e:
            logger.error(f"Error saving custom workflows: {e}")

    async def create_workflow(self, name: str, description: str, steps: List[Dict[str, Any]],
                            agents: List[str], created_by: str, tags: Optional[List[str]] = None) -> str:
        """Create a new custom workflow.

        Args:
            name: Workflow name
            description: Workflow description
            steps: Workflow steps configuration
            agents: Required agents
            created_by: Creator identifier
            tags: Optional tags

        Returns:
            Workflow ID
        """
        try:
            # Validate the workflow
            validation_errors = await self._validate_workflow_config(steps, agents)
            if validation_errors:
                raise ValueError(f"Workflow validation failed: {', '.join(validation_errors)}")

            # Create workflow
            workflow_id = str(uuid.uuid4())
            workflow = CustomWorkflow(
                id=workflow_id,
                name=name,
                description=description,
                steps=steps,
                agents=agents,
                created_by=created_by,
                tags=tags or []
            )

            self.custom_workflows[workflow_id] = workflow

            # Save to config
            await self.save_custom_workflows()

            logger.info(f"Created custom workflow: {name} ({workflow_id})")
            return workflow_id

        except Exception as e:
            logger.error(f"Error creating custom workflow: {e}")
            raise

    async def update_workflow(self, workflow_id: str, name: Optional[str] = None,
                            description: Optional[str] = None, steps: Optional[List[Dict[str, Any]]] = None,
                            agents: Optional[List[str]] = None, tags: Optional[List[str]] = None) -> bool:
        """Update an existing custom workflow.

        Args:
            workflow_id: Workflow ID
            name: New name (optional)
            description: New description (optional)
            steps: New steps (optional)
            agents: New agents (optional)
            tags: New tags (optional)

        Returns:
            True if updated successfully
        """
        try:
            if workflow_id not in self.custom_workflows:
                raise ValueError(f"Workflow not found: {workflow_id}")

            workflow = self.custom_workflows[workflow_id]

            # Validate new configuration if steps or agents changed
            if steps is not None or agents is not None:
                new_steps = steps if steps is not None else workflow.steps
                new_agents = agents if agents is not None else workflow.agents
                validation_errors = await self._validate_workflow_config(new_steps, new_agents)
                if validation_errors:
                    raise ValueError(f"Workflow validation failed: {', '.join(validation_errors)}")

            # Update workflow
            if name is not None:
                workflow.name = name
            if description is not None:
                workflow.description = description
            if steps is not None:
                workflow.steps = steps
            if agents is not None:
                workflow.agents = agents
            if tags is not None:
                workflow.tags = tags

            workflow.updated_at = datetime.utcnow()

            # Save to config
            await self.save_custom_workflows()

            logger.info(f"Updated custom workflow: {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating custom workflow {workflow_id}: {e}")
            raise

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a custom workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if deleted successfully
        """
        try:
            if workflow_id not in self.custom_workflows:
                raise ValueError(f"Workflow not found: {workflow_id}")

            # Check if workflow has active executions
            workflow = self.custom_workflows[workflow_id]
            if workflow.executions:
                # Check if any executions are still running
                for execution_id in workflow.executions:
                    if self.workflow_engine:
                        execution = self.workflow_engine.get_execution_status(execution_id)
                        if execution and execution.status.value == "running":
                            raise ValueError(f"Cannot delete workflow with active executions: {execution_id}")

            # Delete workflow
            del self.custom_workflows[workflow_id]

            # Save to config
            await self.save_custom_workflows()

            logger.info(f"Deleted custom workflow: {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting custom workflow {workflow_id}: {e}")
            raise

    async def execute_workflow(self, workflow_id: str, inputs: Dict[str, Any],
                             execution_user: str) -> str:
        """Execute a custom workflow.

        Args:
            workflow_id: Workflow ID
            inputs: Execution inputs
            execution_user: User executing the workflow

        Returns:
            Execution ID
        """
        try:
            if workflow_id not in self.custom_workflows:
                raise ValueError(f"Workflow not found: {workflow_id}")

            workflow = self.custom_workflows[workflow_id]

            # Create workflow definition
            steps = []
            for i, step_config in enumerate(workflow.steps):
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
                id=workflow_id,
                name=workflow.name,
                description=workflow.description,
                type="simple",  # Custom workflows are simple by default
                steps=steps,
                config={},
                metadata={"custom": True, "created_by": workflow.created_by}
            )

            # Execute workflow
            execution_id = await self.workflow_engine.execute_workflow(
                workflow=workflow_def,
                parameters=inputs
            )

            # Record execution
            workflow.executions.append(execution_id)
            workflow.updated_at = datetime.utcnow()

            # Save updated workflow
            await self.save_custom_workflows()

            logger.info(f"Executed custom workflow {workflow_id}, execution: {execution_id}")
            return execution_id

        except Exception as e:
            logger.error(f"Error executing custom workflow {workflow_id}: {e}")
            raise

    async def list_workflows(self, tags: Optional[List[str]] = None,
                           created_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """List custom workflows with optional filtering.

        Args:
            tags: Filter by tags
            created_by: Filter by creator

        Returns:
            List of workflow information
        """
        try:
            workflows = []

            for workflow in self.custom_workflows.values():
                # Apply filters
                if created_by and workflow.created_by != created_by:
                    continue

                if tags:
                    if not any(tag in workflow.tags for tag in tags):
                        continue

                # Convert to dict
                workflow_info = {
                    "id": workflow.id,
                    "name": workflow.name,
                    "description": workflow.description,
                    "agents": workflow.agents,
                    "step_count": len(workflow.steps),
                    "created_by": workflow.created_by,
                    "created_at": workflow.created_at.isoformat(),
                    "updated_at": workflow.updated_at.isoformat(),
                    "execution_count": len(workflow.executions),
                    "tags": workflow.tags
                }

                workflows.append(workflow_info)

            return workflows

        except Exception as e:
            logger.error(f"Error listing custom workflows: {e}")
            raise

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a custom workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow information or None if not found
        """
        try:
            workflow = self.custom_workflows.get(workflow_id)
            if not workflow:
                return None

            return {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "steps": workflow.steps,
                "agents": workflow.agents,
                "created_by": workflow.created_by,
                "created_at": workflow.created_at.isoformat(),
                "updated_at": workflow.updated_at.isoformat(),
                "executions": workflow.executions,
                "tags": workflow.tags
            }

        except Exception as e:
            logger.error(f"Error getting custom workflow {workflow_id}: {e}")
            raise

    async def _validate_workflow_config(self, steps: List[Dict[str, Any]], agents: List[str]) -> List[str]:
        """Validate workflow configuration.

        Args:
            steps: Workflow steps
            agents: Required agents

        Returns:
            List of validation errors
        """
        errors = []

        if not steps:
            errors.append("Workflow must have at least one step")
            return errors

        # Check that all step agents are in the agents list
        step_agents = set()
        for step in steps:
            agent = step.get("agent")
            if not agent:
                errors.append(f"Step '{step.get('name', 'unnamed')}' missing agent")
            else:
                step_agents.add(agent)

        # Check that all step agents are declared
        undeclared_agents = step_agents - set(agents)
        if undeclared_agents:
            errors.append(f"Agents used in steps but not declared: {undeclared_agents}")

        # Check that all declared agents exist
        config = self.config_manager.get_config()
        available_agents = set(config.agents.keys())
        missing_agents = set(agents) - available_agents
        if missing_agents:
            errors.append(f"Declared agents not found in configuration: {missing_agents}")

        # Validate step dependencies
        step_ids = {f"step_{i}" for i in range(len(steps))}
        for i, step in enumerate(steps):
            dependencies = step.get("dependencies", [])
            for dep in dependencies:
                if dep not in step_ids:
                    errors.append(f"Step {i} has invalid dependency: {dep}")

        return errors

    async def get_workflow_templates(self) -> List[Dict[str, Any]]:
        """Get available workflow templates for creating custom workflows.

        Returns:
            List of workflow templates
        """
        try:
            from ...workflows.templates import get_workflow_template

            templates = []

            # Get available template types
            template_types = ["code-review", "pr-automation", "task-development"]

            for template_type in template_types:
                try:
                    template = get_workflow_template(template_type)
                    if template:
                        templates.append({
                            "type": template_type,
                            "name": template.name,
                            "description": template.description,
                            "version": template.version,
                            "required_inputs": template.get_required_inputs(),
                            "optional_inputs": template.get_optional_inputs()
                        })
                except Exception as e:
                    logger.warning(f"Error loading template {template_type}: {e}")

            return templates

        except Exception as e:
            logger.error(f"Error getting workflow templates: {e}")
            raise

    def register_template(self, name: str, template: Dict[str, Any]):
        """Register a workflow template."""
        # Ensure the template has the correct name
        template = template.copy()
        template["name"] = name
        self.templates[name] = template

    def unregister_template(self, name: str):
        """Unregister a workflow template."""
        if name in self.templates:
            del self.templates[name]

    def list_templates(self) -> List[Dict[str, Any]]:
        """List registered templates."""
        return list(self.templates.values())

    def create_workflow_from_template(self, template_name: str, workflow_name: str, inputs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create workflow from template."""
        if template_name not in self.templates:
            return None

        template = self.templates[template_name]
        workflow_config = template.copy()
        workflow_config["name"] = workflow_name

        # Apply inputs
        if "steps" in workflow_config:
            for step in workflow_config["steps"]:
                if "inputs" in step:
                    if isinstance(step["inputs"], list):
                        # Convert list to dict with provided values
                        step["inputs"] = {input_name: inputs.get(input_name, "") for input_name in step["inputs"]}
                    elif isinstance(step["inputs"], dict):
                        step["inputs"].update(inputs)

        return workflow_config

    def validate_workflow_config(self, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate workflow configuration."""
        errors = []

        if not config.get("name"):
            errors.append("Workflow name is required")

        # Allow empty steps for testing
        steps = config.get("steps", [])
        if steps is None:
            errors.append("Workflow steps cannot be None")

        return len(errors) == 0, errors

    def save_custom_workflow(self, config: Dict[str, Any]) -> Optional[str]:
        """Save custom workflow."""
        is_valid, errors = self.validate_workflow_config(config)
        if not is_valid:
            return None

        import uuid
        workflow_id = str(uuid.uuid4())
        self.custom_workflows[workflow_id] = config
        return workflow_id

    def load_custom_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Load custom workflow."""
        return self.custom_workflows.get(workflow_id)

    def list_custom_workflows(self) -> List[Dict[str, Any]]:
        """List custom workflows."""
        return [{"id": wid, **self.load_custom_workflow(wid)} for wid in self.custom_workflows.keys()]

    def delete_custom_workflow(self, workflow_id: str) -> bool:
        """Delete custom workflow."""
        if workflow_id in self.custom_workflows:
            del self.custom_workflows[workflow_id]
            return True
        return False


# Alias for backward compatibility
CustomWorkflowsTool = CustomWorkflowsManager