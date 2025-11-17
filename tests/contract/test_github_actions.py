"""Contract tests for GitHub Actions integration.

These tests define the expected behavior of GitHub Actions integration
and will fail until implementations are provided.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional, List

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from integrations import (
    GitHubActionsIntegration,
    GitHubActionsConfig
)

# Import WorkflowRun from the github_actions module
import importlib.util
import os
github_actions_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'integrations', 'github_actions.py')
spec = importlib.util.spec_from_file_location('github_actions_integration', github_actions_path)
github_actions_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(github_actions_module)
WorkflowRun = github_actions_module.WorkflowRun


class GitHubActionsContract:
    """Contract for GitHub Actions integration functionality.

    This abstract class defines the interface that all GitHub Actions integration
    implementations must provide.
    """

    def create_workflow_file(self, workflow_config: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Create GitHub Actions workflow file from workflow configuration.

        Args:
            workflow_config: Workflow configuration
            output_path: Path to save workflow file

        Returns:
            Path to created workflow file

        Raises:
            Exception: If creation fails
        """
        raise NotImplementedError("create_workflow_file must be implemented")

    def trigger_workflow(self, workflow_name: str, inputs: Optional[Dict[str, Any]] = None,
                        ref: str = "main") -> Optional[str]:
        """Trigger GitHub Actions workflow execution.

        Args:
            workflow_name: Name of the workflow to trigger
            inputs: Workflow inputs
            ref: Git reference (branch/tag)

        Returns:
            Workflow run ID if successful, None otherwise
        """
        raise NotImplementedError("trigger_workflow must be implemented")

    def get_workflow_runs(self, workflow_name: Optional[str] = None, status: Optional[str] = None) -> List[WorkflowRun]:
        """Get workflow runs.

        Args:
            workflow_name: Filter by workflow name
            status: Filter by status (queued, in_progress, completed)

        Returns:
            List of workflow runs
        """
        raise NotImplementedError("get_workflow_runs must be implemented")

    def get_workflow_run_logs(self, run_id: int) -> Optional[str]:
        """Get logs for a workflow run.

        Args:
            run_id: Workflow run ID

        Returns:
            Logs as string, or None if failed
        """
        raise NotImplementedError("get_workflow_run_logs must be implemented")

    def cancel_workflow_run(self, run_id: int) -> bool:
        """Cancel a workflow run.

        Args:
            run_id: Workflow run ID

        Returns:
            True if cancelled successfully, False otherwise
        """
        raise NotImplementedError("cancel_workflow_run must be implemented")

    def create_pr_comment(self, pr_number: int, comment: str) -> bool:
        """Create a comment on a pull request.

        Args:
            pr_number: Pull request number
            comment: Comment content

        Returns:
            True if comment created successfully, False otherwise
        """
        raise NotImplementedError("create_pr_comment must be implemented")

    def health_check(self) -> bool:
        """Check GitHub Actions integration health.

        Returns:
            True if healthy, False otherwise
        """
        raise NotImplementedError("health_check must be implemented")


class TestGitHubActionsContract:
    """Contract tests for GitHub Actions integration.

    These tests define the expected behavior of GitHub Actions integration
    and will fail until implementations are provided.
    """

    @pytest.fixture
    def github_contract(self):
        """Create a GitHub Actions integration contract instance."""
        config = GitHubActionsConfig(
            token="test-token",
            repository="test-org/test-repo",
            workflow_file=".github/workflows/test-workflow.yml"
        )
        return GitHubActionsIntegration(config)

    @pytest.fixture
    def sample_workflow_config(self):
        """Create sample workflow configuration."""
        return {
            "name": "test-workflow",
            "description": "Test workflow for GitHub Actions",
            "type": "simple",
            "steps": [
                {
                    "id": "step1",
                    "name": "Checkout",
                    "agent": "test-agent",
                    "prompt": "Checkout code",
                    "output_key": "checkout_result"
                },
                {
                    "id": "step2",
                    "name": "Test",
                    "agent": "test-agent",
                    "prompt": "Run tests",
                    "output_key": "test_result"
                }
            ]
        }

    def test_create_workflow_file_basic(self, github_contract, sample_workflow_config):
        """Test basic GitHub Actions workflow file creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "workflow.yml")

            result_path = github_contract.create_workflow_file(
                workflow_config=sample_workflow_config,
                output_path=output_path
            )

            assert result_path == output_path
            assert os.path.exists(result_path)

            # Verify file contains expected content
            with open(result_path, 'r') as f:
                content = f.read()
                assert "MAO Workflow: test-workflow" in content
                assert "workflow_dispatch" in content
                assert "checkout" in content

    def test_create_workflow_file_default_path(self, github_contract, sample_workflow_config):
        """Test workflow file creation with default path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory so default path works
            original_cwd = os.getcwd()
            os.chdir(temp_dir)

            try:
                result_path = github_contract.create_workflow_file(
                    workflow_config=sample_workflow_config
                )

                assert result_path == github_contract.config.workflow_file
                assert os.path.exists(result_path)
            finally:
                os.chdir(original_cwd)

    def test_trigger_workflow_basic(self, github_contract):
        """Test basic workflow triggering."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 204

            result = github_contract.trigger_workflow("test-workflow")

            assert result is not None
            assert "test-workflow" in result
            mock_post.assert_called_once()

    def test_trigger_workflow_with_inputs(self, github_contract):
        """Test workflow triggering with inputs."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 204

            inputs = {"param1": "value1", "param2": "value2"}
            result = github_contract.trigger_workflow(
                workflow_name="test-workflow",
                inputs=inputs,
                ref="develop"
            )

            assert result is not None
            mock_post.assert_called_once()

            # Verify the call included inputs
            call_args = mock_post.call_args
            assert call_args[1]['json']['inputs'] == inputs
            assert call_args[1]['json']['ref'] == "develop"

    def test_trigger_workflow_failure(self, github_contract):
        """Test workflow triggering failure."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 400
            mock_post.return_value.text = "Bad Request"

            result = github_contract.trigger_workflow("test-workflow")

            assert result is None

    def test_get_workflow_runs_basic(self, github_contract):
        """Test getting workflow runs."""
        mock_runs = [
            {
                "id": 123,
                "name": "Test Workflow",
                "status": "completed",
                "conclusion": "success",
                "html_url": "https://github.com/test-org/test-repo/actions/runs/123",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:05:00Z"
            }
        ]

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"workflow_runs": mock_runs}

            runs = github_contract.get_workflow_runs()

            assert len(runs) == 1
            # Check that it's a WorkflowRun-like object with the expected attributes
            run = runs[0]
            assert hasattr(run, 'id') and run.id == 123
            assert hasattr(run, 'name') and run.name == "Test Workflow"
            assert hasattr(run, 'status') and run.status == "completed"
            assert hasattr(run, 'conclusion') and run.conclusion == "success"
            assert hasattr(run, 'html_url') and "github.com" in run.html_url

    def test_get_workflow_runs_filtered(self, github_contract):
        """Test getting workflow runs with filters."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"workflow_runs": []}

            runs = github_contract.get_workflow_runs(
                workflow_name="test-workflow",
                status="completed"
            )

            assert isinstance(runs, list)
            mock_get.assert_called_once()

            # Verify query parameters
            call_args = mock_get.call_args
            assert "workflow_name" in call_args[1]['params']
            assert "status" in call_args[1]['params']

    def test_get_workflow_run_logs_success(self, github_contract):
        """Test getting workflow run logs successfully."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = "Workflow logs content"

            logs = github_contract.get_workflow_run_logs(123)

            assert logs == "Workflow logs content"
            mock_get.assert_called_once()

    def test_get_workflow_run_logs_failure(self, github_contract):
        """Test getting workflow run logs failure."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 404
            mock_get.return_value.text = "Not Found"

            logs = github_contract.get_workflow_run_logs(123)

            assert logs is None

    def test_cancel_workflow_run_success(self, github_contract):
        """Test cancelling workflow run successfully."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 202

            result = github_contract.cancel_workflow_run(123)

            assert result is True
            mock_post.assert_called_once()

    def test_cancel_workflow_run_failure(self, github_contract):
        """Test cancelling workflow run failure."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 404
            mock_post.return_value.text = "Not Found"

            result = github_contract.cancel_workflow_run(123)

            assert result is False

    def test_create_pr_comment_success(self, github_contract):
        """Test creating PR comment successfully."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 201

            result = github_contract.create_pr_comment(42, "Test comment")

            assert result is True
            mock_post.assert_called_once()

            # Verify the comment content
            call_args = mock_post.call_args
            assert call_args[1]['json']['body'] == "Test comment"

    def test_create_pr_comment_failure(self, github_contract):
        """Test creating PR comment failure."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 403
            mock_post.return_value.text = "Forbidden"

            result = github_contract.create_pr_comment(42, "Test comment")

            assert result is False

    def test_health_check_success(self, github_contract):
        """Test health check success."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200

            result = github_contract.health_check()

            assert result is True

    def test_health_check_failure(self, github_contract):
        """Test health check failure."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 404

            result = github_contract.health_check()

            assert result is False