"""Integration tests for GitHub Actions integration."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from integrations import GitHubActionsIntegration, GitHubActionsConfig


class TestGitHubActionsIntegration:
    """Integration tests for GitHub Actions functionality."""

    @pytest.fixture
    def github_integration(self):
        """Create GitHub Actions integration instance."""
        config = GitHubActionsConfig(
            token="test-token",
            repository="test-org/test-repo"
        )
        return GitHubActionsIntegration(config)

    def test_workflow_file_creation_and_triggering(self, github_integration):
        """Test creating workflow file and triggering workflow."""
        workflow_config = {
            "name": "test-integration-workflow",
            "description": "Integration test workflow",
            "type": "simple",
            "steps": [
                {
                    "id": "step1",
                    "name": "Test Step",
                    "agent": "test-agent",
                    "prompt": "Test prompt",
                    "output_key": "result"
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "workflow.yml")

            # Create workflow file
            result_path = github_integration.create_workflow_file(
                workflow_config=workflow_config,
                output_path=output_path
            )

            assert result_path == output_path
            assert os.path.exists(result_path)

            # Verify file content
            with open(result_path, 'r') as f:
                content = f.read()
                assert "MAO Workflow: test-integration-workflow" in content
                assert "checkout" in content

    @patch('requests.post')
    def test_workflow_triggering_integration(self, mock_post, github_integration):
        """Test workflow triggering with mocked HTTP calls."""
        mock_post.return_value.status_code = 204

        result = github_integration.trigger_workflow("test-workflow")

        assert result is not None
        mock_post.assert_called_once()

        # Verify the call was made to the correct endpoint
        call_args = mock_post.call_args
        url = call_args[0][0]
        assert "test-org/test-repo" in url
        assert "test-workflow" in url

    @patch('requests.get')
    def test_workflow_runs_retrieval(self, mock_get, github_integration):
        """Test retrieving workflow runs."""
        mock_response = {
            "workflow_runs": [
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
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        runs = github_integration.get_workflow_runs()

        assert len(runs) == 1
        assert runs[0].id == 123
        assert runs[0].status == "completed"

    @patch('requests.post')
    def test_pr_comment_creation(self, mock_post, github_integration):
        """Test creating PR comments."""
        mock_post.return_value.status_code = 201

        result = github_integration.create_pr_comment(42, "Test comment")

        assert result is True
        mock_post.assert_called_once()

        # Verify comment content
        call_args = mock_post.call_args
        posted_data = call_args[1]['json']
        assert posted_data['body'] == "Test comment"

    def test_webhook_pull_request_handling(self, github_integration):
        """Test handling pull request webhook events."""
        with patch.object(github_integration, 'trigger_workflow') as mock_trigger, \
             patch.object(github_integration, 'create_pr_comment') as mock_comment:

            mock_trigger.return_value = "workflow-123"

            payload = {
                "action": "opened",
                "pull_request": {
                    "number": 42,
                    "title": "Test PR",
                    "body": "Test description"
                }
            }

            result = github_integration.handle_webhook_event("pull_request", payload)

            assert result is not None
            assert result["action"] == "code_review_started"
            assert result["pr_number"] == 42

            mock_trigger.assert_called_once_with(
                workflow_name="code-review",
                inputs={"pr_number": "42"}
            )
            mock_comment.assert_called_once()

    def test_webhook_issue_handling(self, github_integration):
        """Test handling issue webhook events."""
        with patch.object(github_integration, 'trigger_workflow') as mock_trigger, \
             patch.object(github_integration, 'create_pr_comment') as mock_comment:

            mock_trigger.return_value = "workflow-456"

            payload = {
                "action": "opened",
                "issue": {
                    "number": 123,
                    "title": "Implement new feature",
                    "body": "This is a task that needs development"
                }
            }

            result = github_integration.handle_webhook_event("issues", payload)

            assert result is not None
            assert result["action"] == "task_development_started"
            assert result["issue_number"] == 123

            mock_trigger.assert_called_once_with(
                workflow_name="task-development",
                inputs={"issue_number": "123"}
            )

    def test_webhook_signature_validation(self, github_integration):
        """Test webhook signature validation."""
        import hmac
        import hashlib

        secret = "test-secret"
        payload = b'{"test": "data"}'

        # Create valid signature
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={signature}"

        result = github_integration.validate_webhook_signature(
            signature_header, payload, secret
        )

        assert result is True

        # Test invalid signature
        result = github_integration.validate_webhook_signature(
            "sha256=invalid", payload, secret
        )

        assert result is False

    @patch('requests.get')
    def test_health_check_integration(self, mock_get, github_integration):
        """Test health check functionality."""
        mock_get.return_value.status_code = 200

        result = github_integration.health_check()

        assert result is True
        mock_get.assert_called_once()

        # Verify correct repository endpoint
        call_args = mock_get.call_args
        url = call_args[0][0]
        assert "test-org/test-repo" in url

    def test_action_templates_available(self):
        """Test that action templates are available."""
        from integrations.github_actions import list_templates, get_template

        templates = list_templates()

        assert isinstance(templates, dict)
        assert "code-review" in templates
        assert "pr-automation" in templates
        assert "task-development" in templates

        # Test getting specific template
        template = get_template("code-review")
        assert template is not None
        assert template.name == "code-review"

        # Test template configuration
        config = template.get_workflow_config()
        assert "name" in config
        assert "on" in config
        assert "jobs" in config

    def test_template_workflow_configs(self):
        """Test that templates generate valid workflow configurations."""
        from integrations.github_actions import TEMPLATE_REGISTRY

        for name, template in TEMPLATE_REGISTRY.items():
            config = template.get_workflow_config()

            # All templates should have basic structure
            assert "name" in config
            assert "on" in config
            assert "jobs" in config

            # Should have MAO in the name
            assert "MAO" in config["name"]

            # Should have jobs with steps
            jobs = config["jobs"]
            assert len(jobs) > 0

            for job_name, job_config in jobs.items():
                assert "runs-on" in job_config
                assert "steps" in job_config
                assert len(job_config["steps"]) > 0