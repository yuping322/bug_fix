"""Configuration management CLI commands.

This module provides CLI commands for managing platform configuration.
"""

import asyncio
from typing import Optional
from pathlib import Path
import typer

from ...core.config import ConfigManager
from ...core.logging import get_logger
from ...utils.validation import validate_config_file

logger = get_logger(__name__)

# Create the config command group
app = typer.Typer(help="Configuration management commands")


@app.command("validate")
def validate_config(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file to validate"
    ),
):
    """Validate platform configuration file."""
    # Use provided config path or get from context
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
        typer.echo(f"Validating configuration: {config_file}")
        typer.echo()

        # Validate configuration
        result = validate_config_file(config_file)

        if result.is_valid:
            typer.echo("✓ Configuration is valid")

            if result.warnings:
                typer.echo("\nWarnings:")
                for warning in result.warnings:
                    typer.echo(f"  ⚠ {warning}")

            if result.infos:
                typer.echo("\nInfo:")
                for info in result.infos:
                    typer.echo(f"  ℹ {info}")

        else:
            typer.echo("✗ Configuration is invalid", err=True)
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


@app.command("show")
def show_config(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file to show"
    ),
    section: Optional[str] = typer.Option(
        None,
        "--section",
        "-s",
        help="Show only specific section (platform, agents, workflows)"
    ),
):
    """Show platform configuration."""
    try:
        config_manager = ConfigManager()
        if config_path:
            config_manager.config_file = config_path

        platform_config = config_manager.get_config()

        if section:
            # Show specific section
            if section == "platform":
                typer.echo("Platform Configuration:")
                typer.echo(f"  Version: {platform_config.version}")
                typer.echo(f"  Workspace: {platform_config.global_.workspace_dir}")
                typer.echo(f"  Log Level: {platform_config.global_.log_level}")

            elif section == "agents":
                typer.echo("Agent Configuration:")
                if platform_config.agents:
                    for agent_name, agent_config in platform_config.agents.items():
                        typer.echo(f"  • {agent_config.name} ({agent_config.provider})")
                        typer.echo(f"    Model: {agent_config.model}")
                        typer.echo(f"    Timeout: {agent_config.timeout_seconds}s")
                        if agent_config.api_key:
                            masked_key = agent_config.api_key[:8] + "..." + agent_config.api_key[-4:] if len(agent_config.api_key) > 12 else agent_config.api_key
                            typer.echo(f"    API Key: {masked_key}")
                        typer.echo()
                else:
                    typer.echo("  No agents configured")

            elif section == "workflows":
                typer.echo("Workflow Configuration:")
                if platform_config.workflows:
                    for workflow_name, workflow_config in platform_config.workflows.items():
                        typer.echo(f"  • {workflow_config.name}")
                        typer.echo(f"    Type: {workflow_config.type}")
                        typer.echo(f"    Description: {workflow_config.description}")
                        typer.echo(f"    Steps: {len(workflow_config.steps)}")
                        typer.echo(f"    Agents: {', '.join(workflow_config.agents)}")
                        typer.echo(f"    Timeout: {workflow_config.config.get('timeout', 'default')}s")
                        typer.echo()
                else:
                    typer.echo("  No workflows configured")

            else:
                typer.echo(f"Unknown section: {section}. Use 'platform', 'agents', or 'workflows'", err=True)
                raise typer.Exit(1)

        else:
            # Show all configuration
            typer.echo("Platform Configuration:")
            typer.echo(f"  Version: {platform_config.version}")
            typer.echo(f"  Workspace: {platform_config.global_.workspace_dir}")
            typer.echo(f"  Log Level: {platform_config.global_.log_level}")
            typer.echo()

            typer.echo("Agents:")
            if platform_config.agents:
                for agent_name, agent_config in platform_config.agents.items():
                    typer.echo(f"  • {agent_config.name} ({agent_config.provider})")
            else:
                typer.echo("  No agents configured")
            typer.echo()

            typer.echo("Workflows:")
            if platform_config.workflows:
                for workflow_name, workflow_config in platform_config.workflows.items():
                    typer.echo(f"  • {workflow_config.name} ({workflow_config.type})")
            else:
                typer.echo("  No workflows configured")

    except Exception as e:
        logger.error("Failed to show configuration", error=str(e))
        typer.echo(f"Failed to show configuration: {e}", err=True)
        raise typer.Exit(1)


@app.command("set")
def set_config_value(
    key: str = typer.Argument(..., help="Configuration key (e.g., platform.name)"),
    value: str = typer.Argument(..., help="Configuration value"),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    ),
):
    """Set a configuration value."""
    try:
        config_manager = ConfigManager()
        if config_path:
            config_manager.config_file = config_path

        # Parse key path
        key_parts = key.split('.')
        if len(key_parts) < 2:
            typer.echo("Key must be in format 'section.key' (e.g., 'platform.name')", err=True)
            raise typer.Exit(1)

        section = key_parts[0]
        sub_key = '.'.join(key_parts[1:])

        # Get current configuration
        platform_config = config_manager.get_config()

        # Update value based on section
        if section == "global":
            if sub_key == "workspace_dir":
                platform_config.global_.workspace_dir = value
            elif sub_key == "log_level":
                platform_config.global_.log_level = value
            elif sub_key == "max_concurrent_workflows":
                platform_config.global_.max_concurrent_workflows = int(value)
            elif sub_key == "timeout_seconds":
                platform_config.global_.timeout_seconds = int(value)
            else:
                typer.echo(f"Unknown global key: {sub_key}", err=True)
                raise typer.Exit(1)
        elif section == "version":
            platform_config.version = value
        else:
            typer.echo(f"Setting values in section '{section}' not yet supported", err=True)
            typer.echo("Use the specific commands (agent add/update, workflow add/update) for complex changes", err=True)
            raise typer.Exit(1)

        # Save configuration
        config_manager.save_config(platform_config)

        typer.echo(f"✓ Configuration updated: {key} = {value}")

    except Exception as e:
        logger.error("Failed to set configuration value", key=key, error=str(e))
        typer.echo(f"Failed to set configuration value: {e}", err=True)
        raise typer.Exit(1)


@app.command("get")
def get_config_value(
    key: str = typer.Argument(..., help="Configuration key (e.g., platform.name)"),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    ),
):
    """Get a configuration value."""
    try:
        config_manager = ConfigManager()
        if config_path:
            config_manager.config_file = config_path

        # Parse key path
        key_parts = key.split('.')
        if len(key_parts) < 2:
            typer.echo("Key must be in format 'section.key' (e.g., 'platform.name')", err=True)
            raise typer.Exit(1)

        section = key_parts[0]
        sub_key = '.'.join(key_parts[1:])

        # Get current configuration
        platform_config = config_manager.get_config()

        # Get value based on section
        if section == "global":
            if sub_key == "workspace_dir":
                value = platform_config.global_.workspace_dir
            elif sub_key == "log_level":
                value = platform_config.global_.log_level
            elif sub_key == "max_concurrent_workflows":
                value = platform_config.global_.max_concurrent_workflows
            elif sub_key == "timeout_seconds":
                value = platform_config.global_.timeout_seconds
            else:
                typer.echo(f"Unknown global key: {sub_key}", err=True)
                raise typer.Exit(1)
        elif section == "version":
            value = platform_config.version
        else:
            typer.echo(f"Getting values from section '{section}' not yet supported", err=True)
            raise typer.Exit(1)

        typer.echo(f"{key}: {value}")

    except Exception as e:
        logger.error("Failed to get configuration value", key=key, error=str(e))
        typer.echo(f"Failed to get configuration value: {e}", err=True)
        raise typer.Exit(1)


@app.command("migrate")
def migrate_config(
    from_path: Path = typer.Argument(..., help="Path to source configuration file"),
    to_path: Path = typer.Argument(..., help="Path to target configuration file"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite target file if it exists"),
):
    """Migrate configuration from one format/file to another."""
    try:
        if to_path.exists() and not force:
            typer.echo(f"Target file already exists: {to_path}", err=True)
            typer.echo("Use --force to overwrite", err=True)
            raise typer.Exit(1)

        config_manager = ConfigManager()

        # Load source configuration
        config_manager.config_file = from_path
        platform_config = config_manager.get_config()

        # Save to target configuration
        config_manager.config_file = to_path
        config_manager.save_config(platform_config)

        typer.echo(f"✓ Configuration migrated from {from_path} to {to_path}")

    except Exception as e:
        logger.error("Failed to migrate configuration", error=str(e))
        typer.echo(f"Failed to migrate configuration: {e}", err=True)
        raise typer.Exit(1)


@app.command("backup")
def backup_config(
    backup_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path for backup file (default: config.backup.yaml)"
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file to backup"
    ),
):
    """Create a backup of the current configuration."""
    try:
        if not backup_path:
            backup_path = Path("config.backup.yaml")

        config_manager = ConfigManager()
        if config_path:
            config_manager.config_file = config_path

        # Load current configuration
        platform_config = config_manager.get_config()

        # Save backup
        original_file = config_manager.config_file
        config_manager.config_file = backup_path
        config_manager.save_config(platform_config)
        config_manager.config_file = original_file

        typer.echo(f"✓ Configuration backed up to: {backup_path}")

    except Exception as e:
        logger.error("Failed to backup configuration", error=str(e))
        typer.echo(f"Failed to backup configuration: {e}", err=True)
        raise typer.Exit(1)