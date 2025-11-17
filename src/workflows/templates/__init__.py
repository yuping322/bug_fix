"""Workflow templates for common development tasks.

This module provides pre-built workflow templates for common
code development scenarios like code review, PR automation, and task development.
"""

from typing import Dict, Any, List
from pathlib import Path

from ...core.workflow import WorkflowTemplate


class CodeReviewTemplate(WorkflowTemplate):
    """Template for automated code review workflows."""

    def __init__(self):
        super().__init__(
            name="code-review",
            description="Automated code review workflow using multiple AI agents",
            version="1.0.0"
        )

    def get_template_config(self) -> Dict[str, Any]:
        """Get the template configuration."""
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
        """Get required input parameters."""
        return ["code", "language"]

    def get_optional_inputs(self) -> List[str]:
        """Get optional input parameters."""
        return ["context", "style_guide"]

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate workflow inputs."""
        required = self.get_required_inputs()
        return all(key in inputs for key in required)


class PRAutomationTemplate(WorkflowTemplate):
    """Template for pull request automation workflows."""

    def __init__(self):
        super().__init__(
            name="pr-automation",
            description="Automated PR review and management workflow",
            version="1.0.0"
        )

    def get_template_config(self) -> Dict[str, Any]:
        """Get the template configuration."""
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
        """Get required input parameters."""
        return ["diff", "files_changed"]

    def get_optional_inputs(self) -> List[str]:
        """Get optional input parameters."""
        return ["pr_description", "test_files", "test_coverage", "api_changes", "breaking_changes"]

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate workflow inputs."""
        required = self.get_required_inputs()
        return all(key in inputs for key in required)


class TaskDevelopmentTemplate(WorkflowTemplate):
    """Template for task development and implementation workflows."""

    def __init__(self):
        super().__init__(
            name="task-development",
            description="End-to-end task development and implementation workflow",
            version="1.0.0"
        )

    def get_template_config(self) -> Dict[str, Any]:
        """Get the template configuration."""
        return {
            "name": "task-development",
            "description": "Complete task development and implementation workflow",
            "type": "simple",
            "steps": [
                {
                    "name": "analyze-requirements",
                    "description": "Analyze task requirements and constraints",
                    "agent": "claude-agent",
                    "inputs": {
                        "task_description": "{{task_description}}",
                        "requirements": "{{requirements}}",
                        "constraints": "{{constraints}}",
                        "existing_codebase": "{{existing_codebase}}"
                    },
                    "outputs": ["requirement_analysis", "technical_approach", "estimated_effort"],
                    "timeout": 120
                },
                {
                    "name": "design-solution",
                    "description": "Design the technical solution and architecture",
                    "agent": "claude-agent",
                    "inputs": {
                        "requirement_analysis": "{{requirement_analysis}}",
                        "technical_approach": "{{technical_approach}}",
                        "tech_stack": "{{tech_stack}}",
                        "patterns": "{{patterns}}"
                    },
                    "outputs": ["solution_design", "architecture_diagram", "component_breakdown"],
                    "timeout": 150
                },
                {
                    "name": "implement-code",
                    "description": "Implement the solution code",
                    "agent": "codex-agent",
                    "inputs": {
                        "solution_design": "{{solution_design}}",
                        "component_breakdown": "{{component_breakdown}}",
                        "coding_standards": "{{coding_standards}}",
                        "existing_codebase": "{{existing_codebase}}"
                    },
                    "outputs": ["implementation", "code_files", "unit_tests"],
                    "timeout": 300
                },
                {
                    "name": "review-implementation",
                    "description": "Review the implementation for quality and correctness",
                    "agent": "claude-agent",
                    "inputs": {
                        "implementation": "{{implementation}}",
                        "code_files": "{{code_files}}",
                        "unit_tests": "{{unit_tests}}",
                        "requirements": "{{requirements}}",
                        "solution_design": "{{solution_design}}"
                    },
                    "outputs": ["code_review", "quality_score", "improvement_suggestions"],
                    "timeout": 120
                },
                {
                    "name": "generate-documentation",
                    "description": "Generate documentation and usage examples",
                    "agent": "claude-agent",
                    "inputs": {
                        "implementation": "{{implementation}}",
                        "solution_design": "{{solution_design}}",
                        "code_files": "{{code_files}}",
                        "requirements": "{{requirements}}"
                    },
                    "outputs": ["documentation", "usage_examples", "api_reference"],
                    "timeout": 90
                }
            ],
            "agents": ["claude-agent", "codex-agent"],
            "timeout": 900,
            "metadata": {
                "category": "development",
                "tags": ["implementation", "design", "documentation"],
                "estimated_duration": "15-30 minutes"
            }
        }

    def get_required_inputs(self) -> List[str]:
        """Get required input parameters."""
        return ["task_description", "requirements"]

    def get_optional_inputs(self) -> List[str]:
        """Get optional input parameters."""
        return ["constraints", "existing_codebase", "tech_stack", "patterns", "coding_standards"]

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate workflow inputs."""
        required = self.get_required_inputs()
        return all(key in inputs for key in required)


# Registry of available templates
TEMPLATE_REGISTRY = {
    "code-review": CodeReviewTemplate,
    "pr-automation": PRAutomationTemplate,
    "task-development": TaskDevelopmentTemplate,
}


def get_template(template_name: str) -> WorkflowTemplate:
    """Get a workflow template by name.

    Args:
        template_name: Name of the template

    Returns:
        Workflow template instance

    Raises:
        ValueError: If template not found
    """
    if template_name not in TEMPLATE_REGISTRY:
        available = list(TEMPLATE_REGISTRY.keys())
        raise ValueError(f"Template '{template_name}' not found. Available: {available}")

    return TEMPLATE_REGISTRY[template_name]()


def list_templates() -> List[str]:
    """List available workflow templates.

    Returns:
        List of template names
    """
    return list(TEMPLATE_REGISTRY.keys())


def get_template_info(template_name: str) -> Dict[str, Any]:
    """Get information about a workflow template.

    Args:
        template_name: Name of the template

    Returns:
        Template information dictionary
    """
    template = get_template(template_name)
    config = template.get_template_config()

    return {
        "name": template.name,
        "description": template.description,
        "version": template.version,
        "category": config.get("metadata", {}).get("category", "general"),
        "tags": config.get("metadata", {}).get("tags", []),
        "estimated_duration": config.get("metadata", {}).get("estimated_duration", "unknown"),
        "required_inputs": template.get_required_inputs(),
        "optional_inputs": template.get_optional_inputs(),
        "agents": config.get("agents", []),
        "steps": len(config.get("steps", [])),
        "timeout": config.get("timeout", 0)
    }