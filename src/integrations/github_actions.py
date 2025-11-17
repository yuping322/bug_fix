"""GitHub Actions integration for CI/CD workflows."""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import subprocess
import tempfile

logger = logging.getLogger(__name__)


@dataclass
class GitHubActionsConfig:
    """GitHub Actions configuration."""
    token: str
    repository: str
    workflow_file: str = ".github/workflows/mao-orchestration.yml"
    api_base_url: str = "https://api.github.com"


@dataclass
class WorkflowRun:
    """GitHub Actions workflow run."""
    id: int
    name: str
    status: str
    conclusion: Optional[str]
    html_url: str
    created_at: str
    updated_at: str


class GitHubActionsIntegration:
    """GitHub Actions integration for workflow execution."""

    def __init__(self, config: Optional[GitHubActionsConfig] = None):
        """Initialize GitHub Actions integration.

        Args:
            config: GitHub Actions configuration. If None, loads from environment.
        """
        self.config = config or self._load_config()

    def _load_config(self) -> GitHubActionsConfig:
        """Load GitHub Actions configuration from environment."""
        return GitHubActionsConfig(
            token=os.getenv("GITHUB_TOKEN", ""),
            repository=os.getenv("GITHUB_REPOSITORY", ""),
            workflow_file=os.getenv("GITHUB_WORKFLOW_FILE", ".github/workflows/mao-orchestration.yml")
        )

    def create_workflow_file(self, workflow_config: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Create GitHub Actions workflow file from workflow configuration.

        Args:
            workflow_config: Workflow configuration
            output_path: Path to save workflow file. If None, uses config default.

        Returns:
            Path to created workflow file
        """
        output_path = output_path or self.config.workflow_file

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Convert workflow config to GitHub Actions format
        github_workflow = self._convert_to_github_actions(workflow_config)

        # Write workflow file
        with open(output_path, 'w') as f:
            json.dump(github_workflow, f, indent=2)

        logger.info(f"Created GitHub Actions workflow file: {output_path}")
        return output_path

    def _convert_to_github_actions(self, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MAO workflow config to GitHub Actions format."""
        return {
            "name": f"MAO Workflow: {workflow_config['name']}",
            "on": {
                "workflow_dispatch": {
                    "inputs": {
                        "workflow_name": {
                            "description": "Workflow name",
                            "required": True,
                            "default": workflow_config['name']
                        },
                        "inputs": {
                            "description": "Workflow inputs (JSON)",
                            "required": False,
                            "default": "{}"
                        }
                    }
                }
            },
            "jobs": {
                "orchestrate": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "Checkout",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "Setup Python",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "3.11"
                            }
                        },
                        {
                            "name": "Install dependencies",
                            "run": "pip install -e ."
                        },
                        {
                            "name": "Execute workflow",
                            "run": f"""
                                python -m src.cli.main workflow run \\
                                  ${{ github.event.inputs.workflow_name }} \\
                                  --input '${{ github.event.inputs.inputs }}'
                            """,
                            "env": {
                                "ANTHROPIC_API_KEY": "${{ secrets.ANTHROPIC_API_KEY }}",
                                "OPENAI_API_KEY": "${{ secrets.OPENAI_API_KEY }}",
                                "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}"
                            }
                        }
                    ]
                }
            }
        }

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
        import requests

        headers = {
            "Authorization": f"token {self.config.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"https://api.github.com/repos/{self.config.repository}/actions/workflows/{workflow_name}/dispatches"

        data = {
            "ref": ref,
            "inputs": inputs or {}
        }

        try:
            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 204:
                logger.info(f"Triggered workflow {workflow_name} on {ref}")
                return f"workflow-{workflow_name}-{ref}"
            else:
                logger.error(f"Failed to trigger workflow: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error triggering workflow: {e}")
            return None

    def get_workflow_runs(self, workflow_name: Optional[str] = None, status: Optional[str] = None) -> List[WorkflowRun]:
        """Get workflow runs.

        Args:
            workflow_name: Filter by workflow name
            status: Filter by status (queued, in_progress, completed)

        Returns:
            List of workflow runs
        """
        import requests

        headers = {
            "Authorization": f"token {self.config.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"https://api.github.com/repos/{self.config.repository}/actions/runs"

        params = {}
        if workflow_name:
            params["workflow_name"] = workflow_name
        if status:
            params["status"] = status

        try:
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                return [
                    WorkflowRun(
                        id=run["id"],
                        name=run["name"],
                        status=run["status"],
                        conclusion=run.get("conclusion"),
                        html_url=run["html_url"],
                        created_at=run["created_at"],
                        updated_at=run["updated_at"]
                    )
                    for run in data["workflow_runs"]
                ]
            else:
                logger.error(f"Failed to get workflow runs: {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error getting workflow runs: {e}")
            return []

    def get_workflow_run_logs(self, run_id: int) -> Optional[str]:
        """Get logs for a workflow run.

        Args:
            run_id: Workflow run ID

        Returns:
            Logs as string, or None if failed
        """
        import requests

        headers = {
            "Authorization": f"token {self.config.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"https://api.github.com/repos/{self.config.repository}/actions/runs/{run_id}/logs"

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Failed to get workflow logs: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error getting workflow logs: {e}")
            return None

    def cancel_workflow_run(self, run_id: int) -> bool:
        """Cancel a workflow run.

        Args:
            run_id: Workflow run ID

        Returns:
            True if cancelled successfully, False otherwise
        """
        import requests

        headers = {
            "Authorization": f"token {self.config.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"https://api.github.com/repos/{self.config.repository}/actions/runs/{run_id}/cancel"

        try:
            response = requests.post(url, headers=headers)

            if response.status_code == 202:
                logger.info(f"Cancelled workflow run {run_id}")
                return True
            else:
                logger.error(f"Failed to cancel workflow run: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error cancelling workflow run: {e}")
            return False

    def create_pr_comment(self, pr_number: int, comment: str) -> bool:
        """Create a comment on a pull request.

        Args:
            pr_number: Pull request number
            comment: Comment content

        Returns:
            True if comment created successfully, False otherwise
        """
        import requests

        headers = {
            "Authorization": f"token {self.config.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"https://api.github.com/repos/{self.config.repository}/issues/{pr_number}/comments"

        data = {"body": comment}

        try:
            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 201:
                logger.info(f"Created PR comment on #{pr_number}")
                return True
            else:
                logger.error(f"Failed to create PR comment: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error creating PR comment: {e}")
            return False

    def handle_webhook_event(self, event_type: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming GitHub webhook event.

        Args:
            event_type: GitHub event type (e.g., 'pull_request', 'issues')
            payload: Webhook payload

        Returns:
            Response data or None if event not handled
        """
        logger.info(f"Handling webhook event: {event_type}")

        try:
            if event_type == "pull_request":
                return self._handle_pull_request_event(payload)
            elif event_type == "issues":
                return self._handle_issue_event(payload)
            elif event_type == "workflow_run":
                return self._handle_workflow_run_event(payload)
            else:
                logger.info(f"Ignored unsupported event type: {event_type}")
                return None

        except Exception as e:
            logger.error(f"Error handling webhook event {event_type}: {e}")
            return None

    def _handle_pull_request_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle pull request webhook event.

        Args:
            payload: PR webhook payload

        Returns:
            Response data or None
        """
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        pr_number = pr.get("number")

        if not pr_number:
            logger.warning("PR event missing PR number")
            return None

        logger.info(f"Handling PR #{pr_number} action: {action}")

        # Handle different PR actions
        if action in ["opened", "synchronize", "reopened"]:
            # Trigger code review workflow
            workflow_id = self.trigger_workflow(
                workflow_name="code-review",
                inputs={"pr_number": str(pr_number)}
            )

            if workflow_id:
                # Add a comment indicating review started
                comment = "🤖 MAO is starting automated code review..."
                self.create_pr_comment(pr_number, comment)

                return {
                    "action": "code_review_started",
                    "pr_number": pr_number,
                    "workflow_id": workflow_id
                }

        elif action == "closed":
            logger.info(f"PR #{pr_number} closed - no action needed")

        return None

    def _handle_issue_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle issue webhook event.

        Args:
            payload: Issue webhook payload

        Returns:
            Response data or None
        """
        action = payload.get("action")
        issue = payload.get("issue", {})
        issue_number = issue.get("number")

        if not issue_number:
            logger.warning("Issue event missing issue number")
            return None

        logger.info(f"Handling issue #{issue_number} action: {action}")

        # Handle issue opened/edited for task development
        if action in ["opened", "edited"]:
            # Check if this looks like a task/development request
            title = issue.get("title", "").lower()
            body = issue.get("body", "").lower()

            if any(keyword in title or keyword in body
                   for keyword in ["task", "feature", "implement", "develop", "create"]):
                # Trigger task development workflow
                workflow_id = self.trigger_workflow(
                    workflow_name="task-development",
                    inputs={"issue_number": str(issue_number)}
                )

                if workflow_id:
                    # Add a comment indicating task development started
                    comment = "🤖 MAO is analyzing this task for development..."
                    self.create_pr_comment(issue_number, comment)

                    return {
                        "action": "task_development_started",
                        "issue_number": issue_number,
                        "workflow_id": workflow_id
                    }

        return None

    def _handle_workflow_run_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle workflow run webhook event.

        Args:
            payload: Workflow run webhook payload

        Returns:
            Response data or None
        """
        action = payload.get("action")
        workflow_run = payload.get("workflow_run", {})
        run_id = workflow_run.get("id")
        status = workflow_run.get("status")
        conclusion = workflow_run.get("conclusion")

        logger.info(f"Handling workflow run {run_id} action: {action}, status: {status}")

        # Handle workflow completion
        if action == "completed":
            # Could add logic to post completion comments, update issues, etc.
            logger.info(f"Workflow run {run_id} completed with conclusion: {conclusion}")

            # Extract PR/issue info from workflow run if available
            # This would require parsing the workflow run details

        return {
            "action": "workflow_completed",
            "run_id": run_id,
            "status": status,
            "conclusion": conclusion
        }

    def validate_webhook_signature(self, signature: str, payload: bytes, secret: str) -> bool:
        """Validate GitHub webhook signature.

        Args:
            signature: X-Hub-Signature header value
            payload: Raw webhook payload
            secret: Webhook secret

        Returns:
            True if signature is valid, False otherwise
        """
        import hmac
        import hashlib

        if not signature or not secret:
            return False

        try:
            # Extract signature from header (format: "sha256=...")
            if not signature.startswith("sha256="):
                return False

            expected_signature = signature[7:]  # Remove "sha256=" prefix

            # Calculate expected signature
            calculated_signature = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()

            # Use secure comparison
            return hmac.compare_digest(expected_signature, calculated_signature)

        except Exception as e:
            logger.error(f"Error validating webhook signature: {e}")
            return False

    def health_check(self) -> bool:
        """Check GitHub Actions integration health."""
        try:
            import requests

            headers = {
                "Authorization": f"token {self.config.token}",
                "Accept": "application/vnd.github.v3+json"
            }

            url = f"https://api.github.com/repos/{self.config.repository}"

            response = requests.get(url, headers=headers)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"GitHub Actions health check failed: {e}")
            return False