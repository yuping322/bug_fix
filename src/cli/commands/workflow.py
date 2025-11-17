"""Workflow management CLI commands.

This module provides CLI commands for managing workflows in the platform.
"""

import asyncio
from typing import Optional, List
from pathlib import Path
import typer

from ...core.config import ConfigManager
from ...core.logging import get_logger
from ...core.workflow import WorkflowEngine
from ...workflows.templates import get_template, list_templates, get_template_info
from ...agents import agent_registry
from ...agents.base import AgentConfig, AgentType
from ...agents.claude import ClaudeAgent
from ...agents.codex import CodexAgent
from ...agents.copilot import CopilotAgent

logger = get_logger(__name__)

# Create the workflow command group
app = typer.Typer(help="Workflow management commands")


def _initialize_workflow_engine(config_file: Optional[str] = None) -> WorkflowEngine:
    """Initialize workflow engine with agents."""
    config_manager = ConfigManager(config_file)

    # Load configuration
    platform_config = config_manager.get_config()

    # Initialize agents from configuration
    agent_registry.clear()

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

    # Create workflow engine
    return WorkflowEngine(platform_config, agent_registry)


@app.command("list")
def list_workflows(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed workflow information"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Path to configuration file"),
):
    """List all configured workflows."""
    try:
        config_manager = ConfigManager()
        if config_file:
            config_manager.config_file = config_file

        platform_config = config_manager.get_config()

        if not platform_config.workflows:
            typer.echo("No workflows configured")
            return

        typer.echo(f"Configured workflows ({len(platform_config.workflows)}):")
        typer.echo()

        for workflow_name, workflow_config in platform_config.workflows.items():
            typer.echo(f"• {workflow_config.name}")
            typer.echo(f"  Type: {workflow_config.type}")
            typer.echo(f"  Description: {workflow_config.description or 'N/A'}")
            if verbose:
                typer.echo(f"  Steps: {len(workflow_config.steps)}")
                typer.echo(f"  Agents: {', '.join(workflow_config.agents)}")
                typer.echo(f"  Timeout: {workflow_config.config.get('timeout', 'default')}s")
            typer.echo()

    except Exception as e:
        logger.error("Failed to list workflows", error=str(e))
        typer.echo(f"Failed to list workflows: {e}", err=True)
        raise typer.Exit(1)


@app.command("run")
def run_workflow(
    workflow_name: str = typer.Argument(..., help="Name of workflow to run"),
    inputs: Optional[List[str]] = typer.Option(
        None,
        "--input",
        "-i",
        help="Input parameters in key=value format"
    ),
    parameters: Optional[List[str]] = typer.Option(
        None,
        "--param",
        "-p",
        help="Workflow parameters in key=value format (alias for --input)"
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
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Path to configuration file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Perform dry run without actual execution"),
    json_output: bool = typer.Option(False, "--json", help="Output results in JSON format"),
):
    """Run a workflow with specified inputs."""
    import time
    import json as json_lib

    try:
        # Combine inputs and parameters
        all_inputs = []
        if inputs:
            all_inputs.extend(inputs)
        if parameters:
            all_inputs.extend(parameters)

        # Parse inputs
        input_dict = {}
        if all_inputs:
            for input_str in all_inputs:
                if "=" not in input_str:
                    typer.echo(f"Invalid input format: {input_str}. Use key=value", err=True)
                    raise typer.Exit(1)
                key, value = input_str.split("=", 1)
                input_dict[key] = value

        # Initialize platform
        config_manager = ConfigManager()
        if config_file:
            config_manager.config_file = config_file

        platform_config = config_manager.get_config()

        # Check if workflow exists
        if workflow_name not in platform_config.workflows:
            error_msg = f"Workflow '{workflow_name}' not found"
            if json_output:
                result = {
                    "success": False,
                    "workflow_name": workflow_name,
                    "execution_id": None,
                    "output": None,
                    "duration": 0.0,
                    "error": error_msg
                }
                typer.echo(json_lib.dumps(result, indent=2))
            else:
                typer.echo(error_msg, err=True)
            raise typer.Exit(1)

        # Dry run mode
        if dry_run:
            if verbose:
                typer.echo(f"Dry run for workflow: {workflow_name}")
                typer.echo(f"Parameters: {input_dict}")
                typer.echo(f"Configuration file: {config_file or 'default'}")

            result = {
                "success": True,
                "workflow_name": workflow_name,
                "execution_id": f"dry-run-{int(time.time())}",
                "output": {"message": "Dry run completed successfully", "parameters": input_dict},
                "duration": 0.0,
                "error": None
            }

            if json_output:
                typer.echo(json_lib.dumps(result, indent=2))
            else:
                typer.echo("✓ Dry run completed successfully")
                if verbose:
                    typer.echo(f"Workflow: {workflow_name}")
                    typer.echo(f"Parameters: {input_dict}")
            return

        # Initialize workflow engine
        workflow_engine = _initialize_workflow_engine(config_file)

        start_time = time.time()

        if verbose:
            typer.echo(f"Running workflow: {workflow_name}")
            if input_dict:
                typer.echo(f"Parameters: {input_dict}")
            if timeout:
                typer.echo(f"Timeout: {timeout}s")

        if async_run:
            if verbose:
                typer.echo("Running asynchronously...")
            execution_id = asyncio.run(
                workflow_engine.execute_workflow_async(
                    workflow_name=workflow_name,
                    inputs=input_dict,
                    timeout=timeout
                )
            )

            result = {
                "success": True,
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "output": {"message": "Workflow started asynchronously", "execution_id": execution_id},
                "duration": time.time() - start_time,
                "error": None
            }

            if json_output:
                typer.echo(json_lib.dumps(result, indent=2))
            else:
                typer.echo(f"✓ Workflow started asynchronously with ID: {execution_id}")
            return

        # Synchronous execution
        try:
            import time
            start_time = time.time()

            if verbose:
                typer.echo("Starting workflow execution...")

            # Progress callback for verbose mode
            def progress_callback(message: str, progress: float, status: str):
                if verbose:
                    status_icon = {
                        "running": "⏳",
                        "completed": "✓",
                        "failed": "✗",
                        "cancelled": "⏹"
                    }.get(status, "ℹ")
                    typer.echo(f"{status_icon} {message} ({progress:.1f}%)")

            result = workflow_engine.execute_workflow_sync(
                workflow_name=workflow_name,
                inputs=input_dict,
                timeout=timeout,
                progress_callback=progress_callback if verbose else None
            )

            duration = result["duration"]

            if result["success"]:
                output_result = {
                    "success": True,
                    "workflow_name": workflow_name,
                    "execution_id": result.get("execution_id", f"sync-{int(time.time())}"),
                    "output": result.get("result"),
                    "duration": duration,
                    "error": None
                }

                if json_output:
                    typer.echo(json_lib.dumps(output_result, indent=2, default=str))
                else:
                    typer.echo("✓ Workflow completed successfully")
                    if verbose and result.get("result"):
                        typer.echo(f"Result: {result['result']}")
                    typer.echo(".2f")
            else:
                error_msg = result.get("error", "Unknown error")
                output_result = {
                    "success": False,
                    "workflow_name": workflow_name,
                    "execution_id": result.get("execution_id", f"sync-{int(time.time())}"),
                    "output": None,
                    "duration": duration,
                    "error": error_msg
                }

                if json_output:
                    typer.echo(json_lib.dumps(output_result, indent=2, default=str))
                else:
                    typer.echo(f"✗ Workflow failed: {error_msg}", err=True)
                raise typer.Exit(1)

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)

            result = {
                "success": False,
                "workflow_name": workflow_name,
                "execution_id": f"error-{int(time.time())}",
                "output": None,
                "duration": duration,
                "error": error_msg
            }

            if json_output:
                typer.echo(json_lib.dumps(result, indent=2, default=str))
            else:
                typer.echo(f"✗ Workflow execution failed: {error_msg}", err=True)
            raise typer.Exit(1)

    except Exception as e:
        logger.error("Failed to run workflow", workflow=workflow_name, error=str(e))
        if not json_output:
            typer.echo(f"Failed to run workflow: {e}", err=True)
        raise typer.Exit(1)


@app.command("status")
def workflow_status(
    workflow_name: Optional[str] = typer.Argument(None, help="Name of workflow to check (shows all if not specified)"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Path to configuration file"),
):
    """Check the status of workflows."""
    try:
        config_manager = ConfigManager()
        if config_file:
            config_manager.config_file = config_file

        workflow_engine = WorkflowEngine(config_manager.get_config(), agent_registry)

        if workflow_name:
            # Check specific workflow
            typer.echo(f"Status of workflow: {workflow_name}")
            # This would need to be implemented to get workflow status
            typer.echo("Status checking not yet implemented")
        else:
            # Show all workflows status
            platform_config = config_manager.get_config()

            typer.echo("Workflow Status:")
            typer.echo()

            for workflow_name, workflow_config in platform_config.workflows.items():
                typer.echo(f"• {workflow_config.name}")
                typer.echo(f"  Status: configured")
                typer.echo(f"  Type: {workflow_config.type}")
                typer.echo(f"  Agents: {', '.join(workflow_config.agents)}")
                typer.echo()

            # Show active executions
            active_count = asyncio.run(workflow_engine.get_active_execution_count())
            typer.echo(f"Active executions: {active_count}")

    except Exception as e:
        logger.error("Failed to get workflow status", workflow=workflow_name, error=str(e))
        typer.echo(f"Failed to get workflow status: {e}", err=True)
        raise typer.Exit(1)


@app.command("templates")
def list_workflow_templates(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed template information"),
):
    """List available workflow templates."""
    try:
        templates = list_templates()

        if not templates:
            typer.echo("No workflow templates available")
            return

        typer.echo(f"Available workflow templates ({len(templates)}):")
        typer.echo()

        for template_name in templates:
            template_info = get_template_info(template_name)

            typer.echo(f"• {template_info['name']}")
            typer.echo(f"  Description: {template_info['description']}")
            typer.echo(f"  Category: {template_info['category']}")
            typer.echo(f"  Tags: {', '.join(template_info['tags'])}")

            if verbose:
                typer.echo(f"  Version: {template_info['version']}")
                typer.echo(f"  Estimated Duration: {template_info['estimated_duration']}")
                typer.echo(f"  Steps: {template_info['steps']}")
                typer.echo(f"  Required Inputs: {', '.join(template_info['required_inputs'])}")
                typer.echo(f"  Optional Inputs: {', '.join(template_info['optional_inputs'])}")
                typer.echo(f"  Agents: {', '.join(template_info['agents'])}")
                typer.echo(f"  Timeout: {template_info['timeout']}s")

            typer.echo()

    except Exception as e:
        logger.error("Failed to list workflow templates", error=str(e))
        typer.echo(f"Failed to list workflow templates: {e}", err=True)
        raise typer.Exit(1)


@app.command("create")
def create_workflow_from_template(
    template_name: str = typer.Argument(..., help="Name of template to use"),
    workflow_name: str = typer.Option("--name", "-n", help="Name for the new workflow"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Workflow description"),
):
    """Create a new workflow from a template."""
    try:
        # Get template
        template = get_template(template_name)

        config_manager = ConfigManager()
        # Use default config for now

        platform_config = config_manager.get_config()

        # Check if workflow already exists
        if workflow_name in platform_config.workflows:
            typer.echo(f"Workflow '{workflow_name}' already exists", err=True)
            raise typer.Exit(1)

        # Create workflow from template
        template_config = template.get_template_config()
        template_config["name"] = workflow_name

        if description:
            template_config["description"] = description

        # Convert to WorkflowConfigEntry for core config
        from ...core.config import WorkflowConfigEntry

        workflow_entry = WorkflowConfigEntry(
            name=template_config["name"],
            type=template_config["type"],
            description=template_config.get("description", ""),
            agents=template_config["agents"],
            steps=template_config["steps"],
            config={"timeout": template_config.get("timeout")},
        )

        # Add to platform config
        platform_config.workflows[workflow_name] = workflow_entry

        # Save configuration
        config_manager.save_config(platform_config)

        typer.echo(f"✓ Workflow '{workflow_name}' created from template '{template_name}'")
        typer.echo("Restart the platform to load the new workflow")

    except Exception as e:
        logger.error("Failed to create workflow from template", template=template_name, workflow=workflow_name, error=str(e))
        typer.echo(f"Failed to create workflow from template: {e}", err=True)
        raise typer.Exit(1)


@app.command("remove")
def remove_workflow(
    workflow_name: str = typer.Argument(..., help="Name of the workflow to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Force removal without confirmation"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Path to configuration file"),
):
    """Remove a workflow from the configuration."""
    try:
        if not force:
            confirmed = typer.confirm(f"Are you sure you want to remove workflow '{workflow_name}'?")
            if not confirmed:
                typer.echo("Operation cancelled")
                return

        config_manager = ConfigManager()
        if config_file:
            config_manager.config_file = config_file

        platform_config = config_manager.get_config()

        # Check if workflow exists
        if workflow_name not in platform_config.workflows:
            typer.echo(f"Workflow '{workflow_name}' not found", err=True)
            raise typer.Exit(1)

        # Remove workflow
        del platform_config.workflows[workflow_name]

        # Save configuration
        config_manager.save_config(platform_config)

        typer.echo(f"✓ Workflow '{workflow_name}' removed successfully")
        typer.echo("Restart the platform to apply the changes")

    except Exception as e:
        logger.error("Failed to remove workflow", workflow=workflow_name, error=str(e))
        typer.echo(f"Failed to remove workflow: {e}", err=True)
        raise typer.Exit(1)


@app.command("executions")
def list_executions(
    workflow_name: Optional[str] = typer.Option(None, "--workflow", "-w", help="Filter by workflow name"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of executions to show"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Path to configuration file"),
):
    """List recent workflow executions."""
    try:
        config_manager = ConfigManager()
        if config_file:
            config_manager.config_file = config_file

        workflow_engine = WorkflowEngine(config_manager.get_config(), agent_registry)

        # This would need to be implemented to get execution history
        typer.echo("Execution history not yet implemented")
        typer.echo("Active executions:")

        active_count = asyncio.run(workflow_engine.get_active_execution_count())
        typer.echo(f"  Total active: {active_count}")

    except Exception as e:
        logger.error("Failed to list executions", error=str(e))
        typer.echo(f"Failed to list executions: {e}", err=True)
        raise typer.Exit(1)


@app.command("cancel")
def cancel_execution(
    execution_id: str = typer.Argument(..., help="ID of the execution to cancel"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Path to configuration file"),
):
    """Cancel a running workflow execution."""
    try:
        config_manager = ConfigManager()
        if config_file:
            config_manager.config_file = config_file

        workflow_engine = WorkflowEngine(config_manager.get_config(), agent_registry)

        # This would need to be implemented to cancel executions
        typer.echo(f"Cancelling execution: {execution_id}")
        typer.echo("Execution cancellation not yet implemented")

    except Exception as e:
        logger.error("Failed to cancel execution", execution_id=execution_id, error=str(e))
        typer.echo(f"Failed to cancel execution: {e}", err=True)
        raise typer.Exit(1)