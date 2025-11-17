"""CLI entry point for the multi-agent orchestration platform.

This module provides the command-line interface using Typer.
"""

import asyncio
import sys
from typing import Optional, List
from pathlib import Path
import typer

from ..core.config import ConfigManager, PlatformConfig
from ..core.logging import configure_logging as setup_logging, get_logger
from ..core.workflow import WorkflowEngine
from ..agents import agent_registry
from ..agents.base import AgentConfig, AgentType
from ..agents.claude import ClaudeAgent
from ..agents.codex import CodexAgent
from ..agents.copilot import CopilotAgent
from ..utils.validation import validate_config_file
from ..core.workflow import WorkflowDefinition, WorkflowStep, WorkflowType
from .commands import agent, workflow, config

# Initialize Typer app
app = typer.Typer(
    name="bug-fix",
    help="Multi-agent code development orchestration platform",
)

# Add subcommands
app.add_typer(agent.app, name="agent", help="Agent management commands")
app.add_typer(workflow.app, name="workflow", help="Workflow management commands")
app.add_typer(config.app, name="config", help="Configuration management commands")

# Initialize logger
logger = get_logger(__name__)


def initialize_platform(config_file: Optional[Path] = None) -> tuple[PlatformConfig, WorkflowEngine]:
    """Initialize the platform with configuration and agents.

    Args:
        config_file: Optional path to configuration file

    Returns:
        Tuple of (platform_config, workflow_engine)
    """
    # Initialize config manager
    config_manager = ConfigManager(config_file and str(config_file))

    # Load configuration
    platform_config = config_manager.get_config()

    # Initialize agents from configuration
    _initialize_agents(platform_config)

    # Create workflow engine
    workflow_engine = WorkflowEngine(platform_config, agent_registry)

    return platform_config, workflow_engine


def _initialize_agents(platform_config: PlatformConfig) -> None:
    """Initialize agents from platform configuration.

    Args:
        platform_config: Platform configuration
    """
    # Clear existing agents
    agent_registry.clear()

    # Create agents from configuration
    for agent_name, agent_entry in platform_config.agents.items():
        if not agent_entry.enabled:
            continue

        try:
            # Convert AgentConfigEntry to AgentConfig
            agent_config = AgentConfig(
                name=agent_entry.name,
                type=AgentType.LLM,  # All current agents are LLM-based
                provider=agent_entry.provider,
                model=agent_entry.model,
                api_key=agent_entry.api_key,
                max_tokens=agent_entry.max_tokens,
                temperature=agent_entry.temperature,
                timeout_seconds=agent_entry.timeout_seconds,
            )

            # Create agent instance based on provider
            if agent_entry.provider == "anthropic":
                agent = ClaudeAgent(agent_config)
            elif agent_entry.provider == "openai":
                agent = CodexAgent(agent_config)
            elif agent_entry.provider == "github":
                agent = CopilotAgent(agent_config)
            else:
                logger.warning(f"Unknown agent provider: {agent_entry.provider}")
                continue

            # Register agent
            agent_registry.register(agent)
            logger.info(f"Registered agent: {agent_name}")

        except Exception as e:
            logger.error(f"Failed to initialize agent {agent_name}: {e}")


def _convert_workflow_config(workflow_name: str, workflow_config) -> WorkflowDefinition:
    """Convert workflow configuration to WorkflowDefinition.

    Args:
        workflow_name: Name of the workflow
        workflow_config: Workflow configuration from config

    Returns:
        WorkflowDefinition: Converted workflow definition
    """
    steps = []
    for i, step_config in enumerate(workflow_config.steps):
        step = WorkflowStep(
            id=step_config.get("name", f"step-{i}"),
            name=step_config.get("name", f"Step {i}"),
            agent_id=step_config.get("agent", ""),
            prompt_template=step_config.get("prompt", ""),
            input_mappings={},  # TODO: Add input mapping support
            output_key=step_config.get("output", f"output-{i}"),
            condition=None,  # TODO: Add condition support
            timeout_seconds=step_config.get("timeout", 300),
            retry_count=step_config.get("retry", 0),
            dependencies=[],  # TODO: Add dependency support
        )
        steps.append(step)

    return WorkflowDefinition(
        id=workflow_name,
        name=workflow_config.name,
        description=workflow_config.description,
        type=WorkflowType(workflow_config.type),
        steps=steps,
        config=workflow_config.config,
        metadata=workflow_config.metadata,
    )


# Global instances (initialized on first use)
_platform_config: Optional[PlatformConfig] = None
_workflow_engine: Optional[WorkflowEngine] = None


def get_platform_config() -> PlatformConfig:
    """Get the platform configuration, initializing if necessary."""
    global _platform_config, _workflow_engine
    if _platform_config is None:
        _platform_config, _workflow_engine = initialize_platform()
    return _platform_config


def get_workflow_engine() -> WorkflowEngine:
    """Get the workflow engine, initializing if necessary."""
    global _platform_config, _workflow_engine
    if _workflow_engine is None:
        _platform_config, _workflow_engine = initialize_platform()
    return _workflow_engine


# @app.callback()
# def main(
#     config_file: Optional[Path] = typer.Option(
#         None,
#         "--config",
#         "-c",
#         help="Path to configuration file",
#         envvar="BUG_FIX_CONFIG"
#     ),
#     log_level: str = typer.Option(
#         "INFO",
#         "--log-level",
#         help="Logging level",
#         envvar="BUG_FIX_LOG_LEVEL"
#     ),
#     verbose: bool = typer.Option(
#         False,
#         "--verbose",
#         "-v",
#         help="Enable verbose output"
#     ),
#     quiet: bool = typer.Option(
#         False,
#         "--quiet",
#         "-q",
#         help="Suppress output"
#     ),
# ):
#     """Multi-agent code development orchestration platform.

#     This CLI provides tools for managing agents, workflows, and executions
#     in a multi-agent development environment.
#     """
#     # Store global options in a global context
#     global_config = {
#         "config_file": config_file,
#         "log_level": log_level.upper(),
#         "verbose": verbose,
#         "quiet": quiet
#     }

#     # Setup logging
#     log_config = {
#         "level": log_level.upper(),
#         "format": "console" if verbose else "json",
#         "quiet": quiet
#     }
#     setup_logging(log_config)

#     # Store in app state for subcommands
#     app.state = global_config


@app.command()
def init(
    config_path: Path = typer.Option(
        Path("config.yaml"),
        "--config",
        "-c",
        help="Path to create configuration file"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration file"
    ),
):
    """Initialize a new platform configuration.

    This command creates a basic configuration file with default settings
    for agents, workflows, and platform options.
    """
    if config_path.exists() and not force:
        typer.echo(f"Configuration file already exists: {config_path}", err=True)
        typer.echo("Use --force to overwrite", err=True)
        raise typer.Exit(1)

    try:
        # Create default configuration
        default_config = {
            "platform": {
                "name": "bug-fix-platform",
                "version": "1.0.0",
                "description": "Multi-agent code development orchestration platform"
            },
            "agents": [
                {
                    "name": "claude-agent",
                    "type": "claude",
                    "api_key": "${ANTHROPIC_API_KEY}",
                    "model": "claude-3-sonnet-20240229",
                    "max_tokens": 4000,
                    "temperature": 0.7,
                    "timeout": 30
                },
                {
                    "name": "codex-agent",
                    "type": "codex",
                    "api_key": "${OPENAI_API_KEY}",
                    "model": "gpt-4",
                    "max_tokens": 4000,
                    "temperature": 0.7,
                    "timeout": 30
                }
            ],
            "workflows": [
                {
                    "name": "code-review",
                    "description": "Automated code review workflow",
                    "type": "simple",
                    "steps": [
                        {
                            "name": "analyze-code",
                            "description": "Analyze code for issues",
                            "agent": "claude-agent",
                            "inputs": {},
                            "timeout": 60
                        },
                        {
                            "name": "suggest-fixes",
                            "description": "Suggest code fixes",
                            "agent": "codex-agent",
                            "inputs": {},
                            "timeout": 60
                        }
                    ],
                    "agents": ["claude-agent", "codex-agent"],
                    "timeout": 300
                }
            ],
            "logging": {
                "level": "INFO",
                "format": "json",
                "file": "logs/bug_fix.log"
            },
            "execution": {
                "isolation": "docker",
                "timeout": 600,
                "max_concurrent": 5
            }
        }

        # Write configuration file
        import yaml
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

        typer.echo(f"Configuration file created: {config_path}")
        typer.echo("\nNext steps:")
        typer.echo("1. Edit the configuration file to add your API keys")
        typer.echo("2. Run 'bug-fix config validate' to validate the configuration")
        typer.echo("3. Run 'bug-fix workflow list' to see available workflows")

    except Exception as e:
        logger.error("Failed to create configuration", error=str(e))
        typer.echo(f"Failed to create configuration: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def validate(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file to validate"
    ),
):
    """Validate platform configuration.

    This command validates the configuration file and reports any issues.
    """
    # Use provided config path or default
    config_file = config_path

    if not config_file:
        # Try default locations
        default_paths = [
            Path("config.yaml"),
            Path("config.yml"),
            Path("config.json"),
            Path("bug_fix.yaml"),
            Path("bug_fix.yml"),
        ]

        for path in default_paths:
            if path.exists():
                config_file = path
                break

    if not config_file:
        typer.echo("No configuration file found. Use --config to specify one.", err=True)
        raise typer.Exit(1)

    if not config_file.exists():
        typer.echo(f"Configuration file not found: {config_file}", err=True)
        raise typer.Exit(1)

    try:
        # Validate configuration
        result = validate_config_file(config_file)

        if result.is_valid:
            typer.echo(f"✓ Configuration is valid: {config_file}")

            if result.warnings:
                typer.echo("\nWarnings:")
                for warning in result.warnings:
                    typer.echo(f"  ⚠ {warning}")

            if result.infos:
                typer.echo("\nInfo:")
                for info in result.infos:
                    typer.echo(f"  ℹ {info}")

        else:
            typer.echo(f"✗ Configuration is invalid: {config_file}", err=True)
            typer.echo("\nErrors:")
            for error in result.errors:
                typer.echo(f"  ✗ {error}", err=True)

            if result.warnings:
                typer.echo("\nWarnings:")
                for warning in result.warnings:
                    typer.echo(f"  ⚠ {warning}", err=True)

            raise typer.Exit(1)

    except Exception as e:
        logger.error("Failed to validate configuration", error=str(e))
        typer.echo(f"Failed to validate configuration: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def run(
    workflow: str = typer.Argument(..., help="Name of workflow to run"),
    inputs: Optional[List[str]] = typer.Option(
        None,
        "--input",
        "-i",
        help="Input parameters in key=value format"
    ),
    async_run: bool = typer.Option(
        False,
        "--async",
        help="Run workflow asynchronously"
    ),
    timeout: Optional[int] = typer.Option(
        None,
        "--timeout",
        help="Workflow execution timeout in seconds"
    ),
):
    """Run a workflow.

    This command executes a workflow with the specified inputs.
    """
    try:
        # Parse inputs
        input_dict = {}
        if inputs:
            for input_str in inputs:
                if "=" not in input_str:
                    typer.echo(f"Invalid input format: {input_str}. Use key=value", err=True)
                    raise typer.Exit(1)
                key, value = input_str.split("=", 1)
                input_dict[key] = value

        # Initialize platform
        platform_config = get_platform_config()
        workflow_engine = get_workflow_engine()

        # Check if workflow exists
        if workflow not in platform_config.workflows:
            typer.echo(f"Workflow '{workflow}' not found", err=True)
            typer.echo(f"Available workflows: {', '.join(platform_config.workflows.keys())}")
            raise typer.Exit(1)

        # Convert workflow config to WorkflowDefinition
        workflow_config = platform_config.workflows[workflow]
        workflow_definition = _convert_workflow_config(workflow, workflow_config)

        # Run workflow
        typer.echo(f"Running workflow: {workflow}")

        if async_run:
            typer.echo("Running asynchronously...")
            execution_id = asyncio.run(
                workflow_engine.execute_workflow(
                    workflow=workflow_definition,
                    parameters=input_dict
                )
            )
            typer.echo(f"Execution started with ID: {execution_id}")
        else:
            execution_id = asyncio.run(
                workflow_engine.execute_workflow(
                    workflow=workflow_definition,
                    parameters=input_dict
                )
            )

            # Wait for completion and get result
            import time
            while True:
                context = workflow_engine.get_execution_status(execution_id)
                if context and context.status in ["completed", "failed", "cancelled"]:
                    break
                time.sleep(0.1)

            context = workflow_engine.get_execution_status(execution_id)
            if context.status == "completed":
                typer.echo("✓ Workflow completed successfully")
                if context.step_results:
                    typer.echo("Results:")
                    for key, value in context.step_results.items():
                        typer.echo(f"  {key}: {value[:100]}{'...' if len(str(value)) > 100 else ''}")
            else:
                typer.echo(f"✗ Workflow failed: {context.errors[0] if context.errors else 'Unknown error'}", err=True)
                raise typer.Exit(1)

    except Exception as e:
        logger.error("Failed to run workflow", workflow=workflow, error=str(e))
        typer.echo(f"Failed to run workflow: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def status():
    """Show platform status.

    This command displays the current status of the platform,
    including agent health and active workflows.
    """
    try:
        # Initialize platform
        platform_config = get_platform_config()
        workflow_engine = get_workflow_engine()

        typer.echo(f"Platform: bug-fix-platform v{platform_config.version}")
        typer.echo(f"Description: Multi-agent code development orchestration platform")
        typer.echo(f"Workspace: {platform_config.global_.workspace_dir}")
        typer.echo()

        # Show agents
        typer.echo("Agents:")
        for agent_name, agent_config in platform_config.agents.items():
            status = "✓ enabled" if agent_config.enabled else "✗ disabled"
            typer.echo(f"  • {agent_config.name} ({agent_config.provider}) - {status}")
        typer.echo()

        # Show workflows
        typer.echo("Workflows:")
        for workflow_name, workflow_config in platform_config.workflows.items():
            status = "✓ enabled" if workflow_config.enabled else "✗ disabled"
            typer.echo(f"  • {workflow_config.name}: {workflow_config.description} - {status}")
        typer.echo()

        # Show active executions
        active_count = workflow_engine.get_active_execution_count()
        typer.echo(f"Active executions: {active_count}")

    except Exception as e:
        logger.error("Failed to get status", error=str(e))
        typer.echo(f"Failed to get status: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def version():
    """Show platform version."""
    from importlib.metadata import version as get_version

    try:
        ver = get_version("bug-fix")
        typer.echo(f"bug-fix v{ver}")
    except Exception:
        typer.echo("bug-fix v1.0.0")


def main_entry():
    """Entry point for the CLI application."""
    try:
        app()
    except KeyboardInterrupt:
        typer.echo("\nInterrupted by user", err=True)
        sys.exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main_entry()