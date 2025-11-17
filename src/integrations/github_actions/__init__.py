"""GitHub Actions workflow templates."""

import os
from typing import Dict, Any, Optional
from pathlib import Path


class GitHubActionTemplate:
    """Base class for GitHub Actions workflow templates."""

    def __init__(self, name: str, description: str):
        """Initialize template.

        Args:
            name: Template name
            description: Template description
        """
        self.name = name
        self.description = description

    def get_workflow_config(self, **kwargs) -> Dict[str, Any]:
        """Get workflow configuration.

        Args:
            **kwargs: Template-specific parameters

        Returns:
            Workflow configuration dictionary
        """
        raise NotImplementedError("get_workflow_config must be implemented")

    def get_required_inputs(self) -> list[str]:
        """Get required input parameters.

        Returns:
            List of required input names
        """
        return []

    def get_optional_inputs(self) -> list[str]:
        """Get optional input parameters.

        Returns:
            List of optional input names
        """
        return []


class CodeReviewTemplate(GitHubActionTemplate):
    """GitHub Actions template for automated code review."""

    def __init__(self):
        """Initialize code review template."""
        super().__init__(
            "code-review",
            "Automated code review workflow using MAO agents"
        )

    def get_workflow_config(self, **kwargs) -> Dict[str, Any]:
        """Get code review workflow configuration."""
        return {
            "name": "MAO Code Review",
            "on": {
                "pull_request": {
                    "types": ["opened", "synchronize", "reopened"]
                },
                "workflow_dispatch": {
                    "inputs": {
                        "pr_number": {
                            "description": "Pull request number",
                            "required": False
                        }
                    }
                }
            },
            "jobs": {
                "review": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "Checkout",
                            "uses": "actions/checkout@v4",
                            "with": {
                                "fetch-depth": 0
                            }
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
                            "name": "Run Code Review",
                            "run": """
                                # Get PR number
                                if [ -n "${{ github.event.pull_request.number }}" ]; then
                                    PR_NUMBER=${{ github.event.pull_request.number }}
                                elif [ -n "${{ github.event.inputs.pr_number }}" ]; then
                                    PR_NUMBER=${{ github.event.inputs.pr_number }}
                                else
                                    echo "No PR number found"
                                    exit 1
                                fi

                                # Run MAO code review workflow
                                python -m src.cli.main workflow run code-review \\
                                  --pr $PR_NUMBER \\
                                  --repo ${{ github.repository }}
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

    def get_required_inputs(self) -> list[str]:
        """Get required inputs for code review."""
        return []

    def get_optional_inputs(self) -> list[str]:
        """Get optional inputs for code review."""
        return ["pr_number"]


class PRAutomationTemplate(GitHubActionTemplate):
    """GitHub Actions template for PR automation."""

    def __init__(self):
        """Initialize PR automation template."""
        super().__init__(
            "pr-automation",
            "Automated PR management and updates using MAO agents"
        )

    def get_workflow_config(self, **kwargs) -> Dict[str, Any]:
        """Get PR automation workflow configuration."""
        return {
            "name": "MAO PR Automation",
            "on": {
                "pull_request": {
                    "types": ["opened", "synchronize", "reopened", "edited"]
                },
                "workflow_dispatch": {
                    "inputs": {
                        "pr_number": {
                            "description": "Pull request number",
                            "required": False
                        },
                        "action": {
                            "description": "Automation action (update_labels, update_description, etc.)",
                            "required": False,
                            "default": "update_labels"
                        }
                    }
                }
            },
            "jobs": {
                "automate": {
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
                            "name": "Run PR Automation",
                            "run": """
                                # Get PR number
                                if [ -n "${{ github.event.pull_request.number }}" ]; then
                                    PR_NUMBER=${{ github.event.pull_request.number }}
                                elif [ -n "${{ github.event.inputs.pr_number }}" ]; then
                                    PR_NUMBER=${{ github.event.inputs.pr_number }}
                                else
                                    echo "No PR number found"
                                    exit 1
                                fi

                                # Get action
                                ACTION=${{ github.event.inputs.action || 'update_labels' }}

                                # Run MAO PR automation workflow
                                python -m src.cli.main workflow run pr-automation \\
                                  --pr $PR_NUMBER \\
                                  --action $ACTION \\
                                  --repo ${{ github.repository }}
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

    def get_required_inputs(self) -> list[str]:
        """Get required inputs for PR automation."""
        return []

    def get_optional_inputs(self) -> list[str]:
        """Get optional inputs for PR automation."""
        return ["pr_number", "action"]


class TaskDevelopmentTemplate(GitHubActionTemplate):
    """GitHub Actions template for task development."""

    def __init__(self):
        """Initialize task development template."""
        super().__init__(
            "task-development",
            "Automated task breakdown and development using MAO agents"
        )

    def get_workflow_config(self, **kwargs) -> Dict[str, Any]:
        """Get task development workflow configuration."""
        return {
            "name": "MAO Task Development",
            "on": {
                "issues": {
                    "types": ["opened", "edited"]
                },
                "workflow_dispatch": {
                    "inputs": {
                        "issue_number": {
                            "description": "Issue number",
                            "required": False
                        },
                        "task_description": {
                            "description": "Task description",
                            "required": False
                        }
                    }
                }
            },
            "jobs": {
                "develop": {
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
                            "name": "Run Task Development",
                            "run": """
                                # Get issue number or task description
                                if [ -n "${{ github.event.issue.number }}" ]; then
                                    ISSUE_NUMBER=${{ github.event.issue.number }}
                                    TASK_DESC=""
                                elif [ -n "${{ github.event.inputs.issue_number }}" ]; then
                                    ISSUE_NUMBER=${{ github.event.inputs.issue_number }}
                                    TASK_DESC="${{ github.event.inputs.task_description }}"
                                else
                                    echo "No issue number or task description provided"
                                    exit 1
                                fi

                                # Run MAO task development workflow
                                python -m src.cli.main workflow run task-development \\
                                  --issue $ISSUE_NUMBER \\
                                  --description "$TASK_DESC" \\
                                  --repo ${{ github.repository }}
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

    def get_required_inputs(self) -> list[str]:
        """Get required inputs for task development."""
        return []

    def get_optional_inputs(self) -> list[str]:
        """Get optional inputs for task development."""
        return ["issue_number", "task_description"]


# Template registry
TEMPLATE_REGISTRY = {
    "code-review": CodeReviewTemplate(),
    "pr-automation": PRAutomationTemplate(),
    "task-development": TaskDevelopmentTemplate(),
}


def get_template(template_name: str) -> Optional[GitHubActionTemplate]:
    """Get a GitHub Actions template by name.

    Args:
        template_name: Name of the template

    Returns:
        Template instance or None if not found
    """
    return TEMPLATE_REGISTRY.get(template_name)


def list_templates() -> Dict[str, Dict[str, Any]]:
    """List available GitHub Actions templates.

    Returns:
        Dictionary of template information
    """
    templates = {}
    for name, template in TEMPLATE_REGISTRY.items():
        templates[name] = {
            "name": name,
            "description": template.description,
            "required_inputs": template.get_required_inputs(),
            "optional_inputs": template.get_optional_inputs()
        }
    return templates