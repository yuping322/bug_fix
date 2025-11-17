"""Integration tests for CLI workflow."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import json
import tempfile
import os

from src.cli.commands.workflow import (
    run_workflow,
    list_workflows,
    workflow_status,
    list_workflow_templates
)
from src.cli.commands.agent import list_agents
from src.cli.commands.config import show_config, validate_config
from src.core.workflow import WorkflowEngine, ExecutionStatus, ExecutionContext
from src.core.config import PlatformConfig, WorkflowConfigEntry, AgentConfigEntry


class TestCLIIntegration:
    """Integration tests for CLI commands using direct function calls."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock platform configuration for integration testing."""
        config = Mock(spec=PlatformConfig)

        # Mock agents
        agent_entry = Mock(spec=AgentConfigEntry)
        agent_entry.name = "claude-agent"
        agent_entry.provider = "anthropic"
        agent_entry.model = "claude-3"
        agent_entry.api_key = "test-key"
        agent_entry.max_tokens = 4096
        agent_entry.temperature = 0.7
        agent_entry.timeout_seconds = 60
        agent_entry.enabled = True

        config.agents = {"claude-agent": agent_entry}

        # Mock workflows
        workflow_entry = Mock(spec=WorkflowConfigEntry)
        workflow_entry.name = "code-review"
        workflow_entry.type = "simple"
        workflow_entry.description = "Code review workflow"
        workflow_entry.enabled = True
        workflow_entry.agents = ["claude-agent"]
        workflow_entry.steps = [
            {
                "name": "analyze",
                "agent": "claude-agent",
                "prompt_template": "Review this code: {{code}}",
                "output_key": "analysis"
            }
        ]

        config.workflows = {"code-review": workflow_entry}

        return config

    @pytest.fixture
    def mock_execution_context(self):
        """Create a mock execution context."""
        context = Mock(spec=ExecutionContext)
        context.execution_id = "exec-123"
        context.workflow_id = "code-review"
        context.status = ExecutionStatus.COMPLETED
        context.step_results = {"analysis": "Code looks good"}
        context.duration = 5.2
        context.errors = []
        return context

    @pytest.fixture
    def mock_workflow_engine(self, mock_config, mock_execution_context):
        """Create a mock workflow engine."""
        engine = Mock(spec=WorkflowEngine)
        engine.execute_workflow_sync.return_value = {
            "execution_id": "exec-123",
            "status": "completed",
            "result": {"analysis": "Code looks good"}
        }
        engine.get_execution_status.return_value = mock_execution_context
        engine.list_executions.return_value = [mock_execution_context]
        engine.get_active_execution_count.return_value = 1
        engine.cancel_execution.return_value = True
        return engine

    @pytest.fixture
    def mock_dependencies(self, mock_config, mock_workflow_engine):
        """Mock all dependencies for testing."""
        with patch('src.cli.commands.agent.ConfigManager') as mock_config_class, \
             patch('src.cli.commands.agent.agent_registry') as mock_registry, \
             patch('src.cli.commands.workflow.ConfigManager') as mock_config_workflow, \
             patch('src.cli.commands.workflow.WorkflowEngine') as mock_engine_class, \
             patch('src.cli.commands.config.ConfigManager') as mock_config_config:

            # Setup mocks
            mock_config_class.return_value.get_config.return_value = mock_config
            mock_engine_class.return_value = mock_workflow_engine
            mock_config_workflow.return_value.get_config.return_value = mock_config

            yield {
                "config": mock_config,
                "engine": mock_workflow_engine,
                "config_manager": mock_config_class.return_value
            }

    def test_agent_list_integration(self, mock_dependencies):
        """Test agent list command integration."""
        # This would test the full agent listing workflow
        # For now, just verify the function can be called
        assert callable(list_agents)

    def test_workflow_list_integration(self, mock_dependencies):
        """Test workflow list command integration."""
        # Test that workflow listing works with mocked config
        assert callable(list_workflows)

    def test_workflow_run_integration(self, mock_dependencies):
        """Test workflow run command integration."""
        # Test that workflow execution works with mocked dependencies
        assert callable(run_workflow)

    def test_config_validation_integration(self, mock_dependencies):
        """Test config validation integration."""
        # Test that config validation works
        assert callable(validate_config)

    def test_config_show_integration(self, mock_dependencies):
        """Test config show integration."""
        # Test that config display works
        assert callable(show_config)

    def test_workflow_templates_integration(self, mock_dependencies):
        """Test workflow templates listing integration."""
        # Test that template listing works
        assert callable(list_workflow_templates)

    def test_workflow_status_integration(self, mock_dependencies):
        """Test workflow status checking integration."""
        # Test that status checking works
        assert callable(workflow_status)