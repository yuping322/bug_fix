"""PR automation workflow template.

This module provides a specialized workflow template for automated pull request
review and management using AI agents to analyze changes, review tests, and provide feedback.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from . import WorkflowTemplate


class PRAutomationWorkflow(WorkflowTemplate):
    """PR automation workflow implementation."""

    def __init__(self):
        super().__init__(
            name="pr-automation",
            description="Automated PR review and management workflow",
            version="1.0.0"
        )

    def get_template_config(self) -> Dict[str, Any]:
        """Get the template configuration for PR automation."""
        return {
            "name": "pr-automation",
            "description": "Automated pull request review and management",
            "type": "simple",
            "steps": [
                {
                    "name": "analyze-changes",
                    "description": "Analyze the changes in the pull request",
                    "agent": "claude-agent",
                    "inputs": {
                        "diff": "{{diff}}",
                        "files_changed": "{{files_changed}}",
                        "pr_description": "{{pr_description}}"
                    },
                    "outputs": ["change_analysis", "risk_assessment"],
                    "timeout": 180
                },
                {
                    "name": "review-tests",
                    "description": "Review test coverage and quality",
                    "agent": "codex-agent",
                    "inputs": {
                        "test_files": "{{test_files}}",
                        "test_coverage": "{{test_coverage}}",
                        "change_analysis": "{{change_analysis}}"
                    },
                    "outputs": ["test_review", "coverage_gaps"],
                    "timeout": 120
                },
                {
                    "name": "check-compatibility",
                    "description": "Check backward compatibility and breaking changes",
                    "agent": "claude-agent",
                    "inputs": {
                        "api_changes": "{{api_changes}}",
                        "breaking_changes": "{{breaking_changes}}",
                        "change_analysis": "{{change_analysis}}"
                    },
                    "outputs": ["compatibility_report", "migration_guide"],
                    "timeout": 90
                },
                {
                    "name": "generate-feedback",
                    "description": "Generate comprehensive PR feedback and suggestions",
                    "agent": "claude-agent",
                    "inputs": {
                        "change_analysis": "{{change_analysis}}",
                        "risk_assessment": "{{risk_assessment}}",
                        "test_review": "{{test_review}}",
                        "compatibility_report": "{{compatibility_report}}"
                    },
                    "outputs": ["pr_feedback", "approval_recommendation", "follow_up_tasks"],
                    "timeout": 120
                }
            ],
            "agents": ["claude-agent", "codex-agent"],
            "timeout": 600,
            "metadata": {
                "category": "collaboration",
                "tags": ["pr", "review", "automation"],
                "estimated_duration": "10-15 minutes"
            }
        }

    def get_required_inputs(self) -> List[str]:
        """Get required input parameters for PR automation."""
        return ["diff", "files_changed"]

    def get_optional_inputs(self) -> List[str]:
        """Get optional input parameters for PR automation."""
        return ["pr_description", "test_files", "test_coverage", "api_changes", "breaking_changes"]

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate workflow inputs for PR automation."""
        required = self.get_required_inputs()
        if not all(key in inputs for key in required):
            return False

        # Additional validation for diff
        diff = inputs.get("diff", "")
        if not isinstance(diff, str) or len(diff.strip()) == 0:
            return False

        # Validate files_changed is a list
        files_changed = inputs.get("files_changed", [])
        if not isinstance(files_changed, list) or len(files_changed) == 0:
            return False

        return True

    def preprocess_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess inputs before workflow execution."""
        processed = inputs.copy()

        # Normalize file paths
        if "files_changed" in processed:
            processed["files_changed"] = [
                str(Path(f).resolve()) for f in processed["files_changed"]
            ]

        # Extract diff statistics
        diff = processed.get("diff", "")
        processed["diff_stats"] = self._extract_diff_stats(diff)

        # Categorize changes
        processed["change_categories"] = self._categorize_changes(processed["files_changed"])

        return processed

    def postprocess_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocess workflow results."""
        processed = results.copy()

        # Add PR metadata
        processed["pr_metadata"] = {
            "template_version": self.version,
            "automation_type": "ai_pr_review",
            "agents_used": self.get_template_config()["agents"],
            "review_timestamp": None  # Would be set by execution context
        }

        # Calculate approval confidence
        if "approval_recommendation" in results:
            recommendation = results["approval_recommendation"]
            processed["approval_confidence"] = self._calculate_approval_confidence(recommendation)

        # Add action items summary
        if "follow_up_tasks" in results:
            tasks = results["follow_up_tasks"]
            processed["task_summary"] = self._summarize_tasks(tasks)

        return processed

    def _extract_diff_stats(self, diff: str) -> Dict[str, Any]:
        """Extract statistics from diff."""
        stats = {
            "lines_added": 0,
            "lines_removed": 0,
            "files_changed": 0,
            "hunks": 0
        }

        lines = diff.split('\n')
        current_file = None

        for line in lines:
            if line.startswith('+++ '):
                stats["files_changed"] += 1
                current_file = line[4:]
            elif line.startswith('@@ '):
                stats["hunks"] += 1
            elif line.startswith('+') and not line.startswith('+++'):
                stats["lines_added"] += 1
            elif line.startswith('-') and not line.startswith('---'):
                stats["lines_removed"] += 1

        return stats

    def _categorize_changes(self, files: List[str]) -> Dict[str, List[str]]:
        """Categorize changed files by type."""
        categories = {
            "source_code": [],
            "tests": [],
            "documentation": [],
            "configuration": [],
            "assets": [],
            "other": []
        }

        for file in files:
            file_lower = file.lower()
            if any(file_lower.endswith(ext) for ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs']):
                categories["source_code"].append(file)
            elif any(file_lower.endswith(ext) for ext in ['.test.', '.spec.', '_test.', '_spec.']):
                categories["tests"].append(file)
            elif any(file_lower.endswith(ext) for ext in ['.md', '.rst', '.txt', '.doc']):
                categories["documentation"].append(file)
            elif any(file_lower.endswith(ext) for ext in ['.yaml', '.yml', '.json', '.xml', '.ini', '.cfg']):
                categories["configuration"].append(file)
            elif any(file_lower.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.css', '.scss']):
                categories["assets"].append(file)
            else:
                categories["other"].append(file)

        return categories

    def _calculate_approval_confidence(self, recommendation: Dict[str, Any]) -> float:
        """Calculate approval confidence score."""
        if not isinstance(recommendation, dict):
            return 0.5

        approve = recommendation.get("approve", False)
        confidence = recommendation.get("confidence", 0.5)

        # Base confidence on approval decision
        base_confidence = 0.8 if approve else 0.3

        # Adjust based on stated confidence
        return (base_confidence + confidence) / 2

    def _summarize_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize follow-up tasks."""
        if not isinstance(tasks, list):
            return {"total": 0, "by_priority": {}, "by_type": {}}

        summary = {
            "total": len(tasks),
            "by_priority": {"high": 0, "medium": 0, "low": 0},
            "by_type": {}
        }

        for task in tasks:
            if isinstance(task, dict):
                priority = task.get("priority", "medium").lower()
                task_type = task.get("type", "general")

                if priority in summary["by_priority"]:
                    summary["by_priority"][priority] += 1

                if task_type not in summary["by_type"]:
                    summary["by_type"][task_type] = 0
                summary["by_type"][task_type] += 1

        return summary


# Create template instance
pr_automation_template = PRAutomationWorkflow()