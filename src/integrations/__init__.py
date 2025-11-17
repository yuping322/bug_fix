"""Multi-Agent Orchestration Platform - Integrations Module."""

try:
    from .function_compute import FunctionComputeIntegration
except ImportError:
    FunctionComputeIntegration = None

try:
    import importlib.util
    import os
    github_actions_path = os.path.join(os.path.dirname(__file__), 'github_actions.py')
    spec = importlib.util.spec_from_file_location('github_actions_integration', github_actions_path)
    github_actions_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(github_actions_module)
    GitHubActionsIntegration = github_actions_module.GitHubActionsIntegration
    GitHubActionsConfig = github_actions_module.GitHubActionsConfig
except ImportError:
    GitHubActionsIntegration = None
    GitHubActionsConfig = None

__all__ = [
    "FunctionComputeIntegration",
    "GitHubActionsIntegration",
    "GitHubActionsConfig",
]