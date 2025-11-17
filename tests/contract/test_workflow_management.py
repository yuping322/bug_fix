"""Contract tests for workflow management.

This module defines the contract for workflow management functionality.
All implementations must satisfy these contracts to be considered complete.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock

from src.core.workflow_management import WorkflowManagement
from src.core.workflow import (
    WorkflowDefinition, WorkflowStep, WorkflowType, ExecutionStatus,
    WorkflowEngine, WorkflowTemplate, WorkflowExecutionError
)
from src.core.config import PlatformConfig, GlobalConfig
from src.agents.base import AgentRegistry


class WorkflowManagementContract:
    """Contract for workflow management functionality.

    This abstract class defines the interface that all workflow management
    implementations must provide.
    """

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
        raise NotImplementedError("create_workflow_definition must be implemented")

    def validate_workflow_definition(self, workflow: WorkflowDefinition) -> bool:
        """Validate a workflow definition.

        Args:
            workflow: Workflow to validate

        Returns:
            bool: True if valid

        Raises:
            WorkflowExecutionError: If validation fails
        """
        raise NotImplementedError("validate_workflow_definition must be implemented")

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
        raise NotImplementedError("execute_workflow must be implemented")

    def get_workflow_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow execution status.

        Args:
            execution_id: Execution identifier

        Returns:
            Dict with status information or None if not found
        """
        raise NotImplementedError("get_workflow_status must be implemented")

    def cancel_workflow_execution(self, execution_id: str) -> bool:
        """Cancel a workflow execution.

        Args:
            execution_id: Execution identifier

        Returns:
            bool: True if cancelled successfully
        """
        raise NotImplementedError("cancel_workflow_execution must be implemented")

    def list_workflow_executions(self) -> List[Dict[str, Any]]:
        """List all workflow executions.

        Returns:
            List of execution information dictionaries
        """
        raise NotImplementedError("list_workflow_executions must be implemented")

    def get_workflow_template(self, template_name: str) -> Optional[WorkflowTemplate]:
        """Get a workflow template by name.

        Args:
            template_name: Name of the template

        Returns:
            WorkflowTemplate instance or None if not found
        """
        raise NotImplementedError("get_workflow_template must be implemented")

    def list_workflow_templates(self) -> List[Dict[str, Any]]:
        """List available workflow templates.

        Returns:
            List of template information dictionaries
        """
        raise NotImplementedError("list_workflow_templates must be implemented")

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
        raise NotImplementedError("customize_workflow_from_template must be implemented")


class TestWorkflowManagementContract:
    """Contract tests for workflow management.

    These tests define the expected behavior of workflow management
    and will fail until implementations are provided.
    """

    @pytest.fixture
    def workflow_contract(self):
        """Create a workflow management contract instance."""
        # Create proper config
        global_config = GlobalConfig(
            workspace_dir="/tmp/test_workspace",
            log_level="INFO",
            max_concurrent_workflows=5,
            timeout_seconds=300,
        )

        config = PlatformConfig(
            global_=global_config,
            agents={},
            workflows={}
        )

        # Create agent registry with a test agent
        agent_registry = AgentRegistry()

        # Create and register a mock agent
        from src.agents.base import AgentConfig, AgentType, AgentProvider
        from unittest.mock import AsyncMock

        mock_agent = Mock()
        mock_agent.config = AgentConfig(
            name="test-agent",
            type=AgentType.LLM,
            provider=AgentProvider.ANTHROPIC,
            model="test-model",
            api_key="test-key"
        )
        mock_agent.execute = AsyncMock(return_value=Mock(content="Test response", tokens_used=10))
        mock_agent.test_connectivity = AsyncMock(return_value={"success": True, "response_time": 0.1})

        agent_registry._agents["test-agent"] = mock_agent
        agent_registry._agent_configs["test-agent"] = mock_agent.config

        return WorkflowManagement(config, agent_registry)

    @pytest.fixture
    def sample_workflow_definition(self):
        """Create a sample workflow definition."""
        steps = [
            WorkflowStep(
                id="step1",
                name="First Step",
                agent_id="test-agent",
                prompt_template="Process {{ input_data }}",
                output_key="step1_output"
            ),
            WorkflowStep(
                id="step2",
                name="Second Step",
                agent_id="test-agent",
                prompt_template="Refine {{ step1_output }}",
                output_key="final_output",
                dependencies=["step1_output"]
            )
        ]

        return WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            description="A test workflow",
            type=WorkflowType.SIMPLE,
            steps=steps
        )

    @pytest.fixture
    def sample_workflow_config(self):
        """Create sample workflow configuration."""
        return {
            "name": "Test Workflow",
            "description": "A test workflow",
            "type": "simple",
            "steps": [
                {
                    "id": "step1",
                    "name": "First Step",
                    "agent": "test-agent",
                    "prompt": "Process {{ input_data }}",
                    "output_key": "step1_output"
                },
                {
                    "id": "step2",
                    "name": "Second Step",
                    "agent": "test-agent",
                    "prompt": "Refine {{ step1_output }}",
                    "output_key": "final_output"
                }
            ]
        }

    def test_create_workflow_definition_basic(self, workflow_contract, sample_workflow_config):
        """Test basic workflow definition creation."""
        workflow = workflow_contract.create_workflow_definition(
            name="test-workflow",
            description="Test workflow",
            steps=sample_workflow_config["steps"]
        )

        assert isinstance(workflow, WorkflowDefinition)
        assert workflow.id == "test-workflow"
        assert workflow.name == "test-workflow"
        assert len(workflow.steps) == 2

    def test_create_workflow_definition_with_config(self, workflow_contract, sample_workflow_config):
        """Test workflow definition creation with custom config."""
        config = {"timeout": 600, "max_retries": 3}

        workflow = workflow_contract.create_workflow_definition(
            name="test-workflow",
            description="Test workflow",
            steps=sample_workflow_config["steps"],
            config=config
        )

        assert workflow.config == config

    def test_validate_workflow_definition_valid(self, workflow_contract, sample_workflow_definition):
        """Test validating a valid workflow definition."""
        result = workflow_contract.validate_workflow_definition(sample_workflow_definition)
        assert result is True

    def test_validate_workflow_definition_invalid(self, workflow_contract):
        """Test validating an invalid workflow definition."""
        invalid_workflow = WorkflowDefinition(
            id="",  # Invalid: empty ID
            name="Invalid Workflow",
            description="",
            steps=[]
        )

        with pytest.raises(WorkflowExecutionError):
            workflow_contract.validate_workflow_definition(invalid_workflow)

    def test_execute_workflow_basic(self, workflow_contract, sample_workflow_definition):
        """Test basic workflow execution."""
        parameters = {"input_data": "test input"}

        execution_id = workflow_contract.execute_workflow(
            workflow=sample_workflow_definition,
            parameters=parameters
        )

        assert isinstance(execution_id, str)
        assert len(execution_id) > 0

    def test_execute_workflow_with_workspace(self, workflow_contract, sample_workflow_definition):
        """Test workflow execution with custom workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            parameters = {"input_data": "test input"}

            execution_id = workflow_contract.execute_workflow(
                workflow=sample_workflow_definition,
                parameters=parameters,
                workspace_dir=temp_dir
            )

            assert isinstance(execution_id, str)

    def test_get_workflow_status_existing(self, workflow_contract, sample_workflow_definition):
        """Test getting status of existing workflow execution."""
        parameters = {"input_data": "test input"}

        execution_id = workflow_contract.execute_workflow(
            workflow=sample_workflow_definition,
            parameters=parameters
        )

        status = workflow_contract.get_workflow_status(execution_id)
        assert status is not None
        assert "status" in status
        assert "execution_id" in status

    def test_get_workflow_status_nonexistent(self, workflow_contract):
        """Test getting status of non-existent workflow execution."""
        status = workflow_contract.get_workflow_status("nonexistent-execution")
        assert status is None

    def test_cancel_workflow_execution_existing(self, workflow_contract, sample_workflow_definition):
        """Test cancelling an existing workflow execution."""
        parameters = {"input_data": "test input"}

        execution_id = workflow_contract.execute_workflow(
            workflow=sample_workflow_definition,
            parameters=parameters
        )

        # Wait a bit for execution to start
        import time
        time.sleep(0.1)

        result = workflow_contract.cancel_workflow_execution(execution_id)
        assert isinstance(result, bool)

    def test_cancel_workflow_execution_nonexistent(self, workflow_contract):
        """Test cancelling a non-existent workflow execution."""
        result = workflow_contract.cancel_workflow_execution("nonexistent-execution")
        assert result is False

    def test_list_workflow_executions(self, workflow_contract, sample_workflow_definition):
        """Test listing workflow executions."""
        # Execute a workflow first
        parameters = {"input_data": "test input"}
        execution_id = workflow_contract.execute_workflow(
            workflow=sample_workflow_definition,
            parameters=parameters
        )

        executions = workflow_contract.list_workflow_executions()
        assert isinstance(executions, list)
        assert len(executions) >= 1

        # Check structure of first execution
        execution_info = executions[0]
        assert "execution_id" in execution_info
        assert "status" in execution_info

    def test_get_workflow_template_existing(self, workflow_contract):
        """Test getting an existing workflow template."""
        template = workflow_contract.get_workflow_template("code_review")
        # Template may or may not exist, but method should not raise
        # If it exists, it should be a WorkflowTemplate instance
        if template is not None:
            assert isinstance(template, WorkflowTemplate)

    def test_get_workflow_template_nonexistent(self, workflow_contract):
        """Test getting a non-existent workflow template."""
        template = workflow_contract.get_workflow_template("nonexistent-template")
        assert template is None

    def test_list_workflow_templates(self, workflow_contract):
        """Test listing workflow templates."""
        templates = workflow_contract.list_workflow_templates()
        assert isinstance(templates, list)

        # Each template should have basic info
        for template in templates:
            assert "name" in template
            assert "description" in template

    def test_customize_workflow_from_template_existing(self, workflow_contract):
        """Test customizing workflow from existing template."""
        customizations = {
            "name": "Custom Code Review",
            "description": "Customized code review workflow",
            "config": {"strict_mode": True}
        }

        try:
            workflow = workflow_contract.customize_workflow_from_template(
                template_name="code_review",
                customizations=customizations
            )

            assert isinstance(workflow, WorkflowDefinition)
            assert workflow.name == "Custom Code Review"

        except WorkflowExecutionError:
            # If template doesn't exist, that's acceptable
            pass

    def test_customize_workflow_from_template_nonexistent(self, workflow_contract):
        """Test customizing workflow from non-existent template."""
        customizations = {"name": "Custom Workflow"}

        with pytest.raises(WorkflowExecutionError):
            workflow_contract.customize_workflow_from_template(
                template_name="nonexistent-template",
                customizations=customizations
            )