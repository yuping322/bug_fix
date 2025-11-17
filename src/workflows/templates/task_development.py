"""Task development workflow template.

This module provides a specialized workflow template for end-to-end task development
and implementation using AI agents to analyze requirements, design solutions, implement code,
and generate documentation.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from . import WorkflowTemplate


class TaskDevelopmentWorkflow(WorkflowTemplate):
    """Task development workflow implementation."""

    def __init__(self):
        super().__init__(
            name="task-development",
            description="End-to-end task development and implementation workflow",
            version="1.0.0"
        )

    def get_template_config(self) -> Dict[str, Any]:
        """Get the template configuration for task development."""
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
        """Get required input parameters for task development."""
        return ["task_description", "requirements"]

    def get_optional_inputs(self) -> List[str]:
        """Get optional input parameters for task development."""
        return ["constraints", "existing_codebase", "tech_stack", "patterns", "coding_standards"]

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate workflow inputs for task development."""
        required = self.get_required_inputs()
        if not all(key in inputs for key in required):
            return False

        # Additional validation for task description
        task_desc = inputs.get("task_description", "")
        if not isinstance(task_desc, str) or len(task_desc.strip()) < 10:
            return False

        # Validate requirements
        requirements = inputs.get("requirements", [])
        if not isinstance(requirements, list) or len(requirements) == 0:
            return False

        return True

    def preprocess_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess inputs before workflow execution."""
        processed = inputs.copy()

        # Normalize requirements to list format
        requirements = processed.get("requirements", [])
        if isinstance(requirements, str):
            processed["requirements"] = [req.strip() for req in requirements.split('\n') if req.strip()]

        # Extract codebase information
        if "existing_codebase" in processed:
            codebase = processed["existing_codebase"]
            if isinstance(codebase, str):
                # Check if it's a directory path
                try:
                    path = Path(codebase)
                    if path.exists() and path.is_dir():
                        processed["codebase_info"] = self._analyze_codebase(path)
                except (OSError, IOError):
                    pass

        # Set default tech stack if not provided
        if "tech_stack" not in processed:
            processed["tech_stack"] = ["python", "fastapi", "pytest"]

        # Set default patterns if not provided
        if "patterns" not in processed:
            processed["patterns"] = ["solid", "dependency_injection", "factory_pattern"]

        return processed

    def postprocess_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocess workflow results."""
        processed = results.copy()

        # Add development metadata
        processed["development_metadata"] = {
            "template_version": self.version,
            "development_type": "ai_assisted_implementation",
            "agents_used": self.get_template_config()["agents"],
            "completion_timestamp": None  # Would be set by execution context
        }

        # Calculate quality metrics
        if "quality_score" in results:
            score = results["quality_score"]
            processed["quality_metrics"] = self._calculate_quality_metrics(score)

        # Generate implementation summary
        processed["implementation_summary"] = self._generate_implementation_summary(results)

        # Add next steps recommendations
        processed["next_steps"] = self._generate_next_steps(results)

        return processed

    def _analyze_codebase(self, path: Path) -> Dict[str, Any]:
        """Analyze existing codebase structure."""
        info = {
            "languages": set(),
            "frameworks": set(),
            "structure": {},
            "size": 0
        }

        try:
            # Simple analysis - count files by extension
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    info["size"] += file_path.stat().st_size
                    ext = file_path.suffix.lower()

                    if ext == '.py':
                        info["languages"].add("python")
                        # Check for common frameworks
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read(1000)
                                if 'fastapi' in content:
                                    info["frameworks"].add("fastapi")
                                if 'django' in content:
                                    info["frameworks"].add("django")
                                if 'flask' in content:
                                    info["frameworks"].add("flask")
                        except:
                            pass
                    elif ext in ['.js', '.ts']:
                        info["languages"].add("javascript" if ext == '.js' else "typescript")
                    elif ext == '.java':
                        info["languages"].add("java")
                    elif ext == '.go':
                        info["languages"].add("go")

            info["languages"] = list(info["languages"])
            info["frameworks"] = list(info["frameworks"])
            info["size_mb"] = round(info["size"] / (1024 * 1024), 2)

        except Exception:
            pass

        return info

    def _calculate_quality_metrics(self, score: Any) -> Dict[str, Any]:
        """Calculate detailed quality metrics."""
        if isinstance(score, (int, float)):
            numeric_score = float(score)
        elif isinstance(score, dict):
            numeric_score = score.get("overall", 0.5)
        else:
            numeric_score = 0.5

        metrics = {
            "overall_score": numeric_score,
            "grade": self._score_to_grade(numeric_score),
            "recommendations": []
        }

        if numeric_score < 0.6:
            metrics["recommendations"].append("Consider additional code review")
        if numeric_score < 0.8:
            metrics["recommendations"].append("May need refactoring for better maintainability")

        return metrics

    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"

    def _generate_implementation_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate implementation summary."""
        summary = {
            "components_implemented": 0,
            "tests_generated": 0,
            "documentation_created": False,
            "code_lines": 0
        }

        if "code_files" in results:
            code_files = results["code_files"]
            if isinstance(code_files, list):
                summary["components_implemented"] = len(code_files)

        if "unit_tests" in results:
            tests = results["unit_tests"]
            if isinstance(tests, list):
                summary["tests_generated"] = len(tests)

        if "documentation" in results:
            summary["documentation_created"] = bool(results["documentation"])

        # Estimate lines of code (rough approximation)
        if "implementation" in results:
            impl = results["implementation"]
            if isinstance(impl, str):
                summary["code_lines"] = len(impl.split('\n'))

        return summary

    def _generate_next_steps(self, results: Dict[str, Any]) -> List[str]:
        """Generate next steps recommendations."""
        steps = []

        if "improvement_suggestions" in results:
            suggestions = results["improvement_suggestions"]
            if isinstance(suggestions, list):
                steps.extend(suggestions[:3])  # Top 3 suggestions

        # Add standard next steps
        steps.extend([
            "Run unit tests to verify implementation",
            "Perform integration testing",
            "Update project documentation",
            "Code review with team members"
        ])

        return steps[:5]  # Limit to 5 items


# Create template instance
task_development_template = TaskDevelopmentWorkflow()