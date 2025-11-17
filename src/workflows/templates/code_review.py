"""Code review workflow template.

This module provides a specialized workflow template for automated code review
using multiple AI agents to analyze code quality, identify issues, and suggest improvements.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from . import WorkflowTemplate


class CodeReviewWorkflow(WorkflowTemplate):
    """Code review workflow implementation."""

    def __init__(self):
        super().__init__(
            name="code-review",
            description="Automated code review workflow using multiple AI agents",
            version="1.0.0"
        )

    def get_template_config(self) -> Dict[str, Any]:
        """Get the template configuration for code review."""
        return {
            "name": "code-review",
            "description": "Automated code review workflow",
            "type": "simple",
            "steps": [
                {
                    "name": "analyze-code",
                    "description": "Analyze code for potential issues, bugs, and improvements",
                    "agent": "claude-agent",
                    "inputs": {
                        "code": "{{code}}",
                        "language": "{{language}}",
                        "context": "{{context}}"
                    },
                    "outputs": ["analysis", "issues", "suggestions"],
                    "timeout": 120
                },
                {
                    "name": "review-style",
                    "description": "Review code style and formatting",
                    "agent": "codex-agent",
                    "inputs": {
                        "code": "{{code}}",
                        "style_guide": "{{style_guide}}",
                        "previous_analysis": "{{analysis}}"
                    },
                    "outputs": ["style_issues", "formatting_suggestions"],
                    "timeout": 90
                },
                {
                    "name": "generate-report",
                    "description": "Generate comprehensive code review report",
                    "agent": "claude-agent",
                    "inputs": {
                        "analysis": "{{analysis}}",
                        "issues": "{{issues}}",
                        "suggestions": "{{suggestions}}",
                        "style_issues": "{{style_issues}}",
                        "formatting_suggestions": "{{formatting_suggestions}}"
                    },
                    "outputs": ["review_report", "severity_score"],
                    "timeout": 60
                }
            ],
            "agents": ["claude-agent", "codex-agent"],
            "timeout": 300,
            "metadata": {
                "category": "code-quality",
                "tags": ["review", "analysis", "quality"],
                "estimated_duration": "5-10 minutes"
            }
        }

    def get_required_inputs(self) -> List[str]:
        """Get required input parameters for code review."""
        return ["code", "language"]

    def get_optional_inputs(self) -> List[str]:
        """Get optional input parameters for code review."""
        return ["context", "style_guide"]

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate workflow inputs for code review."""
        required = self.get_required_inputs()
        if not all(key in inputs for key in required):
            return False

        # Additional validation for code input
        code = inputs.get("code", "")
        if not isinstance(code, str) or len(code.strip()) == 0:
            return False

        # Validate language
        supported_languages = [
            "python", "javascript", "typescript", "java", "c++", "c#",
            "go", "rust", "php", "ruby", "swift", "kotlin", "scala"
        ]
        language = inputs.get("language", "").lower()
        if language not in supported_languages:
            return False

        return True

    def preprocess_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess inputs before workflow execution."""
        processed = inputs.copy()

        # Normalize language name
        processed["language"] = processed["language"].lower()

        # Extract code context if it's a file path
        code = processed.get("code", "")
        if isinstance(code, str) and len(code) < 1000:
            # Check if it's a file path
            try:
                path = Path(code)
                if path.exists() and path.is_file():
                    with open(path, 'r', encoding='utf-8') as f:
                        processed["code"] = f.read()
                        processed["file_path"] = str(path)
            except (OSError, IOError):
                pass  # Not a file path, use as-is

        return processed

    def postprocess_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocess workflow results."""
        processed = results.copy()

        # Add summary statistics
        if "issues" in results:
            issues = results["issues"]
            if isinstance(issues, list):
                processed["issue_count"] = len(issues)
                processed["severity_breakdown"] = self._categorize_issues(issues)

        # Add review metadata
        processed["review_metadata"] = {
            "template_version": self.version,
            "review_type": "automated_ai_review",
            "agents_used": self.get_template_config()["agents"]
        }

        return processed

    def _categorize_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize issues by severity."""
        categories = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

        for issue in issues:
            severity = issue.get("severity", "medium").lower()
            if severity in categories:
                categories[severity] += 1
            else:
                categories["medium"] += 1

        return categories


# Create template instance
code_review_template = CodeReviewWorkflow()