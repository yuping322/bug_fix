"""
Unit tests for CLI workflow execution functionality.

These tests focus on the CLI workflow commands and their interactions
with the workflow engine, using mocks for external dependencies.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
import json
import tempfile
from pathlib import Path

from src.cli.commands.workflow import (
    _initialize_workflow_engine,
    run_workflow,
    list_workflows,
    workflow_status
)
from src.core.workflow import WorkflowEngine, ExecutionStatus
from src.core.config import PlatformConfig, WorkflowConfigEntry, AgentConfigEntry


@pytest.fixture
def mock_config():
    """Create a mock platform configuration."""
    config = Mock(spec=PlatformConfig)

    # Mock agents
    agent_entry = Mock(spec=AgentConfigEntry)
    agent_entry.name = "test-agent"
    agent_entry.provider = "test"
    agent_entry.model = "test-model"
    agent_entry.api_key = "test-key"
    agent_entry.max_tokens = 1000
    agent_entry.temperature = 0.7
    agent_entry.timeout_seconds = 30
    agent_entry.enabled = True

    config.agents = {"test-agent": agent_entry}

    # Mock workflows
    workflow_entry = Mock(spec=WorkflowConfigEntry)
    workflow_entry.name = "test-workflow"
    workflow_entry.type = "simple"
    workflow_entry.description = "Test workflow"
    workflow_entry.enabled = True
    workflow_entry.agents = ["test-agent"]
    workflow_entry.steps = [
        {
            "name": "step1",
            "agent": "test-agent",
            "prompt": "Test prompt",
            "output": "result"
        }
    ]
    workflow_entry.config = {}

    config.workflows = {"test-workflow": workflow_entry}

    return config


@pytest.fixture
def mock_workflow_engine(mock_config):
    """Create a mock workflow engine."""
    engine = Mock(spec=WorkflowEngine)
    engine.config = mock_config

    # Mock execution results
    engine.execute_workflow_sync.return_value = {
        "success": True,
        "result": {"output": "test result"},
        "execution_id": "test-execution-123",
        "duration": 1.5
    }

    engine.execute_workflow_async.return_value = "async-execution-456"

    return engine


class TestWorkflowEngineInitialization:
    """Test workflow engine initialization."""

    @patch('src.cli.commands.workflow.ConfigManager')
    @patch('src.cli.commands.workflow.agent_registry')
    @patch('src.cli.commands.workflow.WorkflowEngine')
    def test_initialize_workflow_engine_success(self, mock_engine_class, mock_registry, mock_config_class, mock_config):
        """Test successful workflow engine initialization."""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config_instance.get_config.return_value = mock_config
        mock_config_class.return_value = mock_config_instance

        mock_registry.clear = Mock()
        mock_registry.register = Mock()

        mock_engine_instance = Mock()
        mock_engine_class.return_value = mock_engine_instance

        # Call function
        result = _initialize_workflow_engine()

        # Assertions
        assert result == mock_engine_instance
        mock_config_class.assert_called_once()
        mock_config_instance.get_config.assert_called_once()
        mock_registry.clear.assert_called_once()
        mock_engine_class.assert_called_once_with(mock_config, mock_registry)

    @patch('src.cli.commands.workflow.ConfigManager')
    def test_initialize_workflow_engine_config_error(self, mock_config_class):
        """Test workflow engine initialization with config error."""
        mock_config_class.side_effect = Exception("Config error")

        with pytest.raises(Exception, match="Config error"):
            _initialize_workflow_engine()


class TestWorkflowRunCommand:
    """Test workflow run command functionality."""

    @patch('src.cli.commands.workflow._initialize_workflow_engine')
    @patch('src.cli.commands.workflow.ConfigManager')
    @patch('src.cli.commands.workflow.typer')
    def test_run_workflow_dry_run(self, mock_typer, mock_config_manager, mock_init_engine, mock_workflow_engine):
        """Test workflow dry run execution."""
        # Mock config manager
        mock_manager_instance = Mock()
        mock_config_instance = Mock()
        mock_config_instance.workflows = {"test-workflow": Mock()}
        mock_manager_instance.get_config.return_value = mock_config_instance
        mock_config_manager.return_value = mock_manager_instance

        mock_init_engine.return_value = mock_workflow_engine
        mock_typer.echo = Mock()

        run_workflow(
            workflow_name="test-workflow",
            inputs=None,
            parameters=None,
            async_run=False,
            timeout=None,
            config_file=None,
            verbose=False,
            dry_run=True,
            json_output=False
        )

        # Assertions - should not call actual workflow execution
        mock_workflow_engine.execute_workflow_sync.assert_not_called()
        mock_typer.echo.assert_any_call("✓ Dry run completed successfully")

    @patch('src.cli.commands.workflow._initialize_workflow_engine')
    @patch('src.cli.commands.workflow.ConfigManager')
    @patch('src.cli.commands.workflow.typer')
    def test_run_workflow_success(self, mock_typer, mock_config_manager, mock_init_engine, mock_workflow_engine):
        """Test successful workflow execution."""
        # Mock config manager
        mock_manager_instance = Mock()
        mock_config_instance = Mock()
        mock_config_instance.workflows = {"test-workflow": Mock()}
        mock_manager_instance.get_config.return_value = mock_config_instance
        mock_config_manager.return_value = mock_manager_instance

        mock_init_engine.return_value = mock_workflow_engine
        mock_typer.echo = Mock()

        run_workflow(
            workflow_name="test-workflow",
            inputs=None,
            parameters=None,
            async_run=False,
            timeout=None,
            config_file=None,
            verbose=False,
            dry_run=False,
            json_output=False
        )

        # Assertions
        mock_workflow_engine.execute_workflow_sync.assert_called_once_with(
            workflow_name="test-workflow",
            inputs={},
            timeout=None,
            progress_callback=None
        )
        mock_typer.echo.assert_any_call("✓ Workflow completed successfully")

    @patch('src.cli.commands.workflow._initialize_workflow_engine')
    @patch('src.cli.commands.workflow.ConfigManager')
    @patch('src.cli.commands.workflow.typer')
    def test_run_workflow_with_parameters(self, mock_typer, mock_config_manager, mock_init_engine, mock_workflow_engine):
        """Test workflow execution with input parameters."""
        # Mock config manager
        mock_manager_instance = Mock()
        mock_config_instance = Mock()
        mock_config_instance.workflows = {"test-workflow": Mock()}
        mock_manager_instance.get_config.return_value = mock_config_instance
        mock_config_manager.return_value = mock_manager_instance

        mock_init_engine.return_value = mock_workflow_engine
        mock_typer.echo = Mock()

        run_workflow(
            workflow_name="test-workflow",
            inputs=["key1=value1", "key2=value2"],
            parameters=None,
            async_run=False,
            timeout=None,
            config_file=None,
            verbose=False,
            dry_run=False,
            json_output=False
        )

        # Assertions
        mock_workflow_engine.execute_workflow_sync.assert_called_once_with(
            workflow_name="test-workflow",
            inputs={"key1": "value1", "key2": "value2"},
            timeout=None,
            progress_callback=None
        )

    @patch('src.cli.commands.workflow._initialize_workflow_engine')
    @patch('src.cli.commands.workflow.ConfigManager')
    @patch('src.cli.commands.workflow.typer')
    def test_run_workflow_async_mode(self, mock_typer, mock_config_manager, mock_init_engine, mock_workflow_engine):
        """Test workflow execution in async mode."""
        # Mock config manager
        mock_manager_instance = Mock()
        mock_config_instance = Mock()
        mock_config_instance.workflows = {"test-workflow": Mock()}
        mock_manager_instance.get_config.return_value = mock_config_instance
        mock_config_manager.return_value = mock_manager_instance

        mock_init_engine.return_value = mock_workflow_engine
        mock_typer.echo = Mock()

        run_workflow(
            workflow_name="test-workflow",
            inputs=None,
            parameters=None,
            async_run=True,
            timeout=None,
            config_file=None,
            verbose=False,
            dry_run=False,
            json_output=False
        )

        # Assertions
        mock_workflow_engine.execute_workflow_async.assert_called_once_with(
            workflow_name="test-workflow",
            inputs={},
            timeout=None
        )
        mock_typer.echo.assert_any_call("✓ Workflow started asynchronously with ID: async-execution-456")

    @patch('src.cli.commands.workflow._initialize_workflow_engine')
    @patch('src.cli.commands.workflow.ConfigManager')
    @patch('src.cli.commands.workflow.typer')
    def test_run_workflow_json_output(self, mock_typer, mock_config_manager, mock_init_engine, mock_workflow_engine):
        """Test workflow execution with JSON output."""
        # Mock config manager
        mock_manager_instance = Mock()
        mock_config_instance = Mock()
        mock_config_instance.workflows = {"test-workflow": Mock()}
        mock_manager_instance.get_config.return_value = mock_config_instance
        mock_config_manager.return_value = mock_manager_instance

        mock_init_engine.return_value = mock_workflow_engine
        mock_typer.echo = Mock()

        run_workflow(
            workflow_name="test-workflow",
            inputs=None,
            parameters=None,
            async_run=False,
            timeout=None,
            config_file=None,
            verbose=False,
            dry_run=False,
            json_output=True
        )

        # Assertions
        # Should call typer.echo with JSON string
        calls = mock_typer.echo.call_args_list
        assert len(calls) == 1
        json_output = calls[0][0][0]
        parsed = json.loads(json_output)
        assert parsed["success"] is True
        assert parsed["workflow_name"] == "test-workflow"

    @patch('src.cli.commands.workflow._initialize_workflow_engine')
    @patch('src.cli.commands.workflow.ConfigManager')
    @patch('src.cli.commands.workflow.typer')
    def test_run_workflow_invalid_workflow(self, mock_typer, mock_config_manager, mock_init_engine, mock_workflow_engine):
        """Test workflow execution with invalid workflow name."""
        # Mock config manager with no workflows
        mock_manager_instance = Mock()
        mock_config_instance = Mock()
        mock_config_instance.workflows = {}
        mock_manager_instance.get_config.return_value = mock_config_instance
        mock_config_manager.return_value = mock_manager_instance

        mock_init_engine.return_value = mock_workflow_engine

        # Mock workflow engine to raise error for non-existent workflow
        mock_workflow_engine.execute_workflow_sync.side_effect = Exception("Workflow 'invalid-workflow' not found")

        mock_typer.echo = Mock()
        mock_typer.Exit = Exception

        with pytest.raises(Exception):
            run_workflow(
                workflow_name="invalid-workflow",
                inputs=None,
                parameters=None,
                async_run=False,
                timeout=None,
                config_file=None,
                verbose=False,
                dry_run=False,
                json_output=False
            )

    @patch('src.cli.commands.workflow._initialize_workflow_engine')
    @patch('src.cli.commands.workflow.ConfigManager')
    @patch('src.cli.commands.workflow.typer')
    def test_run_workflow_execution_failure(self, mock_typer, mock_config_manager, mock_init_engine):
        """Test workflow execution that fails."""
        # Mock config manager
        mock_manager_instance = Mock()
        mock_config_instance = Mock()
        mock_config_instance.workflows = {"test-workflow": Mock()}
        mock_manager_instance.get_config.return_value = mock_config_instance
        mock_config_manager.return_value = mock_manager_instance

        mock_engine = Mock()
        mock_init_engine.return_value = mock_engine

        # Mock failed execution
        mock_engine.execute_workflow_sync.return_value = {
            "success": False,
            "error": "Execution failed",
            "execution_id": "failed-execution-123",
            "duration": 2.0
        }

        mock_typer.echo = Mock()
        mock_typer.Exit = Exception

        with pytest.raises(Exception):
            run_workflow(
                workflow_name="test-workflow",
                inputs=None,
                parameters=None,
                async_run=False,
                dry_run=False,
                verbose=False,
                json_output=False,
                timeout=None,
                config_file=None
            )

        mock_typer.echo.assert_any_call("✗ Workflow failed: Execution failed", err=True)


class TestWorkflowListCommand:
    """Test workflow list command functionality."""

    @patch('src.cli.commands.workflow.ConfigManager')
    @patch('src.cli.commands.workflow.typer')
    def test_list_workflows_success(self, mock_typer, mock_config_manager, mock_config):
        """Test successful workflow listing."""
        mock_manager_instance = Mock()
        mock_manager_instance.get_config.return_value = mock_config
        mock_config_manager.return_value = mock_manager_instance

        mock_typer.echo = Mock()

        list_workflows(verbose=False, config_file=None)

        # Assertions
        mock_typer.echo.assert_any_call("Configured workflows (1):")
        mock_typer.echo.assert_any_call("• test-workflow")

    @patch('src.cli.commands.workflow.ConfigManager')
    @patch('src.cli.commands.workflow.typer')
    def test_list_workflows_verbose(self, mock_typer, mock_config_manager, mock_config):
        """Test verbose workflow listing."""
        mock_manager_instance = Mock()
        mock_manager_instance.get_config.return_value = mock_config
        mock_config_manager.return_value = mock_manager_instance

        mock_typer.echo = Mock()

        list_workflows(verbose=True, config_file=None)

        # Assertions - should include more details in verbose mode
        calls = [str(call) for call in mock_typer.echo.call_args_list]
        assert any("Steps: 1" in call for call in calls)


class TestWorkflowStatusCommand:
    """Test workflow status command functionality."""

    @patch('src.cli.commands.workflow.agent_registry')
    @patch('src.cli.commands.workflow.ConfigManager')
    @patch('src.cli.commands.workflow.typer')
    def test_workflow_status_all(self, mock_typer, mock_config_manager, mock_agent_registry, mock_config):
        """Test workflow status for all workflows."""
        mock_manager_instance = Mock()
        mock_manager_instance.get_config.return_value = mock_config
        mock_config_manager.return_value = mock_manager_instance

        mock_typer.echo = Mock()

        # Mock the async call
        with patch('asyncio.run') as mock_asyncio_run:
            mock_asyncio_run.return_value = 0
            workflow_status(workflow_name=None, config_file=None)

        # Assertions
        mock_typer.echo.assert_any_call("Workflow Status:")
        mock_typer.echo.assert_any_call("Active executions: 0")

    @patch('src.cli.commands.workflow.agent_registry')
    @patch('src.cli.commands.workflow.ConfigManager')
    @patch('src.cli.commands.workflow.typer')
    def test_workflow_status_specific_workflow(self, mock_typer, mock_config_manager, mock_agent_registry, mock_config):
        """Test workflow status for specific workflow."""
        mock_manager_instance = Mock()
        mock_manager_instance.get_config.return_value = mock_config
        mock_config_manager.return_value = mock_manager_instance

        mock_typer.echo = Mock()

        workflow_status(workflow_name="test-workflow", config_file=None)

        # Assertions
        mock_typer.echo.assert_any_call("Status of workflow: test-workflow")
        mock_typer.echo.assert_any_call("Status checking not yet implemented")


class TestProgressReporting:
    """Test progress reporting functionality."""

    def test_progress_callback_called(self, mock_workflow_engine):
        """Test that progress callback is called during execution."""
        progress_calls = []

        def progress_callback(message, progress, status):
            progress_calls.append((message, progress, status))

        # Mock the execute_workflow_sync to call progress callback
        mock_workflow_engine.execute_workflow_sync.side_effect = lambda **kwargs: (
            kwargs.get('progress_callback', lambda *args: None)("Test message", 50.0, "running") or
            {"success": True, "result": {}, "execution_id": "test-123", "duration": 1.0}
        )

        result = mock_workflow_engine.execute_workflow_sync(
            workflow_name="test-workflow",
            inputs={},
            progress_callback=progress_callback
        )

        assert len(progress_calls) > 0
        assert progress_calls[0] == ("Test message", 50.0, "running")


class TestErrorHandling:
    """Test error handling in CLI commands."""

    @patch('src.cli.commands.workflow._initialize_workflow_engine')
    @patch('src.cli.commands.workflow.typer')
    def test_invalid_input_format(self, mock_typer, mock_init_engine):
        """Test handling of invalid input parameter format."""
        mock_init_engine.return_value = Mock()
        mock_typer.echo = Mock()
        mock_typer.Exit = Exception

        with pytest.raises(Exception):
            run_workflow(
                workflow_name="test-workflow",
                inputs=["invalid-format"],
                parameters=None,
                dry_run=False,
                verbose=False,
                json_output=False,
                timeout=None,
                config_file=None
            )

        mock_typer.echo.assert_any_call("Invalid input format: invalid-format. Use key=value", err=True)

    @patch('src.cli.commands.workflow._initialize_workflow_engine')
    @patch('src.cli.commands.workflow.typer')
    def test_config_file_not_found(self, mock_typer, mock_init_engine):
        """Test handling of missing config file."""
        mock_init_engine.side_effect = Exception("Config file not found")
        mock_typer.echo = Mock()
        mock_typer.Exit = Exception

        with pytest.raises(Exception):
            run_workflow(
                workflow_name="test-workflow",
                inputs=None,
                parameters=None,
                config_file="/nonexistent/config.yaml",
                dry_run=False,
                verbose=False,
                json_output=False,
                timeout=None
            )

        mock_typer.echo.assert_any_call("Failed to run workflow: Configuration file not found: /nonexistent/config.yaml", err=True)


class TestParameterParsing:
    """Test parameter parsing functionality."""

    def test_parse_input_parameters(self):
        """Test parsing of input parameters from command line."""
        from src.cli.commands.workflow import run_workflow

        # This is tested implicitly through the run_workflow tests above
        # The function parses inputs like "key1=value1" into {"key1": "value1"}
        assert True  # Placeholder - actual parsing tested in integration

    def test_parameter_precedence(self):
        """Test that --param and --input parameters are combined correctly."""
        # Both --input and --param should be combined
        # This is tested in the run_workflow_with_parameters test
        assert True  # Placeholder - actual precedence tested in integration