"""
Contract tests for CLI workflow execution functionality.

These tests define the expected behavior and interface for CLI workflow execution
without depending on specific implementations. They serve as a contract that
implementation must fulfill.
"""

import pytest
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
import subprocess
import json


class CLIWorkflowExecutionContract:
    """Contract for CLI workflow execution functionality."""

    def execute_workflow_cli(
        self,
        workflow_name: str,
        config_file: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        dry_run: bool = False,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow via CLI interface.

        Args:
            workflow_name: Name of the workflow to execute
            config_file: Path to configuration file
            parameters: Workflow parameters
            verbose: Enable verbose output
            dry_run: Perform dry run without actual execution
            timeout: Execution timeout in seconds

        Returns:
            Dict containing execution results with keys:
            - success: bool indicating if execution succeeded
            - workflow_name: name of executed workflow
            - execution_id: unique execution identifier
            - output: workflow execution output
            - duration: execution duration in seconds
            - error: error message if execution failed
        """
        raise NotImplementedError("execute_workflow_cli must be implemented")

    def list_available_workflows_cli(self) -> Dict[str, Any]:
        """
        List all available workflows via CLI.

        Returns:
            Dict containing workflow list with keys:
            - workflows: list of workflow names
            - count: number of available workflows
        """
        raise NotImplementedError("list_available_workflows_cli must be implemented")

    def get_workflow_status_cli(self, execution_id: str) -> Dict[str, Any]:
        """
        Get status of a workflow execution via CLI.

        Args:
            execution_id: Unique execution identifier

        Returns:
            Dict containing status information with keys:
            - execution_id: execution identifier
            - status: current status (pending, running, completed, failed)
            - progress: progress percentage (0-100)
            - current_step: current executing step name
            - start_time: execution start timestamp
            - end_time: execution end timestamp (if completed)
            - error: error message (if failed)
        """
        raise NotImplementedError("get_workflow_status_cli must be implemented")


@pytest.fixture
def sample_config_file():
    """Create a temporary sample configuration file."""
    config_content = """
version: "1.0"
environment: "test"

agents:
  test-agent:
    name: "test-agent"
    provider: "test"
    model: "test-model"
    api_key: "test-key"

workflows:
  test-workflow:
    name: "test-workflow"
    description: "Test workflow for contract testing"
    type: "simple"
    agent: "test-agent"
    steps:
      - name: "step1"
        action: "test_action"
        parameters:
          message: "Hello World"
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        return f.name


"""
Contract tests for CLI workflow execution functionality.

These tests define the expected behavior and interface for CLI workflow execution
without depending on specific implementations. They serve as a contract that
implementation must fulfill.
"""

import pytest
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
import subprocess
import json


class CLIWorkflowExecutionContract:
    """Contract for CLI workflow execution functionality."""

    def execute_workflow_cli(
        self,
        workflow_name: str,
        config_file: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        dry_run: bool = False,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow via CLI interface.

        Args:
            workflow_name: Name of the workflow to execute
            config_file: Path to configuration file
            parameters: Workflow parameters
            verbose: Enable verbose output
            dry_run: Perform dry run without actual execution
            timeout: Execution timeout in seconds

        Returns:
            Dict containing execution results with keys:
            - success: bool indicating if execution succeeded
            - workflow_name: name of executed workflow
            - execution_id: unique execution identifier
            - output: workflow execution output
            - duration: execution duration in seconds
            - error: error message if execution failed
        """
        raise NotImplementedError("execute_workflow_cli must be implemented")

    def list_available_workflows_cli(self) -> Dict[str, Any]:
        """
        List all available workflows via CLI.

        Returns:
            Dict containing workflow list with keys:
            - workflows: list of workflow names
            - count: number of available workflows
        """
        raise NotImplementedError("list_available_workflows_cli must be implemented")

    def get_workflow_status_cli(self, execution_id: str) -> Dict[str, Any]:
        """
        Get status of a workflow execution via CLI.

        Args:
            execution_id: Unique execution identifier

        Returns:
            Dict containing status information with keys:
            - execution_id: execution identifier
            - status: current status (pending, running, completed, failed)
            - progress: progress percentage (0-100)
            - current_step: current executing step name
            - start_time: execution start timestamp
            - end_time: execution end timestamp (if completed)
            - error: error message (if failed)
        """
        raise NotImplementedError("get_workflow_status_cli must be implemented")


@pytest.fixture
def sample_config_file():
    """Create a temporary sample configuration file."""
    config_content = """
version: "1.0"
environment: "test"

agents:
  test-agent:
    name: "test-agent"
    provider: "test"
    model: "test-model"
    api_key: "test-key"

workflows:
  test-workflow:
    name: "test-workflow"
    description: "Test workflow for contract testing"
    type: "simple"
    agent: "test-agent"
    steps:
      - name: "step1"
        action: "test_action"
        parameters:
          message: "Hello World"
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        return f.name


@pytest.fixture
def cli_contract():
    """Fixture providing CLI contract implementation."""
    # Import the actual implementation
    try:
        from src.cli.contract import CLIWorkflowExecutionContractImpl
        return CLIWorkflowExecutionContractImpl()
    except ImportError:
        # Fallback to abstract contract if implementation not available
        return CLIWorkflowExecutionContract()


class TestCLIWorkflowExecutionContract:
    """Contract tests for CLI workflow execution."""

    def test_execute_workflow_cli_basic(self, cli_contract, sample_config_file):
        """Test basic workflow execution via CLI."""
        result = cli_contract.execute_workflow_cli(
            workflow_name="test-workflow",
            config_file=sample_config_file
        )

        assert isinstance(result, dict)
        assert "success" in result
        assert "workflow_name" in result
        assert "execution_id" in result
        assert "output" in result
        assert "duration" in result

        if not result["success"]:
            assert "error" in result

    def test_execute_workflow_cli_with_parameters(self, cli_contract, sample_config_file):
        """Test workflow execution with custom parameters."""
        parameters = {"custom_param": "test_value"}

        result = cli_contract.execute_workflow_cli(
            workflow_name="test-workflow",
            config_file=sample_config_file,
            parameters=parameters
        )

        assert isinstance(result, dict)
        assert result["workflow_name"] == "test-workflow"

    def test_execute_workflow_cli_dry_run(self, cli_contract, sample_config_file):
        """Test workflow dry run execution."""
        result = cli_contract.execute_workflow_cli(
            workflow_name="test-workflow",
            config_file=sample_config_file,
            dry_run=True
        )

        assert isinstance(result, dict)
        assert result["workflow_name"] == "test-workflow"
        # Dry run should not actually execute but should validate

    def test_execute_workflow_cli_verbose(self, cli_contract, sample_config_file):
        """Test workflow execution with verbose output."""
        result = cli_contract.execute_workflow_cli(
            workflow_name="test-workflow",
            config_file=sample_config_file,
            verbose=True
        )

        assert isinstance(result, dict)
        # Verbose mode should include additional logging/output

    def test_execute_workflow_cli_invalid_workflow(self, cli_contract, sample_config_file):
        """Test execution of non-existent workflow."""
        result = cli_contract.execute_workflow_cli(
            workflow_name="non-existent-workflow",
            config_file=sample_config_file
        )

        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result

    def test_execute_workflow_cli_invalid_config(self, cli_contract):
        """Test execution with invalid configuration file."""
        result = cli_contract.execute_workflow_cli(
            workflow_name="test-workflow",
            config_file="/non/existent/config.yaml"
        )

        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result

    def test_list_available_workflows_cli(self, cli_contract, sample_config_file):
        """Test listing available workflows via CLI."""
        result = cli_contract.list_available_workflows_cli()

        assert isinstance(result, dict)
        assert "workflows" in result
        assert "count" in result
        assert isinstance(result["workflows"], list)
        assert isinstance(result["count"], int)
        assert result["count"] == len(result["workflows"])

    def test_get_workflow_status_cli(self, cli_contract):
        """Test getting workflow execution status via CLI."""
        # First execute a workflow to get an execution ID
        execution_result = cli_contract.execute_workflow_cli("test-workflow")
        execution_id = execution_result.get("execution_id")

        if execution_id:
            status_result = cli_contract.get_workflow_status_cli(execution_id)

            assert isinstance(status_result, dict)
            assert status_result["execution_id"] == execution_id
            assert "status" in status_result
            assert status_result["status"] in ["pending", "running", "completed", "failed"]
            assert "progress" in status_result
            assert 0 <= status_result["progress"] <= 100

    def test_execute_workflow_cli_timeout(self, cli_contract, sample_config_file):
        """Test workflow execution with timeout."""
        result = cli_contract.execute_workflow_cli(
            workflow_name="test-workflow",
            config_file=sample_config_file,
            timeout=1  # Very short timeout
        )

        assert isinstance(result, dict)
        # Should either complete within timeout or fail with timeout error

    def test_workflow_execution_output_format(self, cli_contract, sample_config_file):
        """Test that workflow execution returns properly formatted output."""
        result = cli_contract.execute_workflow_cli(
            workflow_name="test-workflow",
            config_file=sample_config_file
        )

        assert isinstance(result, dict)

        # Validate output structure
        if result["success"]:
            assert "output" in result
            # Output should be serializable (for CLI consumption)
            try:
                json.dumps(result["output"])
            except (TypeError, ValueError):
                pytest.fail("Workflow output is not JSON serializable")

    def test_workflow_execution_id_uniqueness(self, cli_contract, sample_config_file):
        """Test that execution IDs are unique across multiple executions."""
        execution_ids = set()

        # Execute workflow multiple times
        for _ in range(3):
            result = cli_contract.execute_workflow_cli(
                workflow_name="test-workflow",
                config_file=sample_config_file
            )
            if result["success"]:
                execution_id = result.get("execution_id")
                assert execution_id is not None
                assert execution_id not in execution_ids
                execution_ids.add(execution_id)


# Integration test that can be run against actual CLI binary
class TestCLIWorkflowExecutionIntegration:
    """Integration tests that run against actual CLI binary."""

    def test_cli_binary_exists_and_runs(self):
        """Test that CLI binary exists and can show help."""
        try:
            result = subprocess.run(
                ["python", "-m", "src.cli.main", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert result.returncode == 0
            assert "workflow" in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("CLI binary not available or not implemented yet")

    def test_cli_workflow_command_available(self):
        """Test that workflow command is available in CLI."""
        try:
            result = subprocess.run(
                ["python", "-m", "src.cli.main", "workflow", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert result.returncode == 0
            assert "run" in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("CLI workflow command not implemented yet")

    def test_cli_workflow_run_command_available(self):
        """Test that workflow run subcommand is available."""
        try:
            result = subprocess.run(
                ["python", "-m", "src.cli.main", "workflow", "run", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("CLI workflow run command not implemented yet")