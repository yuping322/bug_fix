"""Agent management CLI commands.

This module provides CLI commands for managing AI agents in the platform.
"""

import asyncio
from typing import Optional, List
import typer

from ...core.config import ConfigManager
from ...core.logging import get_logger
from ...agents import agent_registry

logger = get_logger(__name__)

# Create the agent command group
app = typer.Typer(help="Agent management commands")


@app.command("list")
def list_agents(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed agent information"),
):
    """List all configured agents."""
    try:
        config_manager = ConfigManager()
        # Use default config for now
        platform_config = config_manager.get_config()

        if not platform_config.agents:
            typer.echo("No agents configured")
            return

        typer.echo(f"Configured agents ({len(platform_config.agents)}):")
        typer.echo()

        for agent_name, agent_config in platform_config.agents.items():
            typer.echo(f"• {agent_config.name}")
            typer.echo(f"  Type: {agent_config.provider}")
            if verbose:
                typer.echo(f"  Model: {agent_config.model or 'default'}")
                typer.echo(f"  Timeout: {agent_config.timeout_seconds or 'default'}s")
                if agent_config.api_key:
                    masked_key = agent_config.api_key[:8] + "..." + agent_config.api_key[-4:] if agent_config.api_key else ""
                    typer.echo(f"  API Key: {masked_key}")
                else:
                    typer.echo("  API Key: not set")
            typer.echo()

    except Exception as e:
        logger.error("Failed to list agents", error=str(e))
        typer.echo(f"Failed to list agents: {e}", err=True)
        raise typer.Exit(1)


@app.command("test")
def test_agent(
    agent_name: str = typer.Argument(..., help="Name of the agent to test"),
    message: str = typer.Option("Hello, test message", "--message", "-m", help="Test message to send"),
):
    """Test an agent by sending a simple message."""
    try:
        config_manager = ConfigManager()
        # Use default config for now

        # Get agent from registry
        agent = agent_registry.get_agent(agent_name)
        if not agent:
            typer.echo(f"Agent '{agent_name}' not found", err=True)
            raise typer.Exit(1)

        typer.echo(f"Testing agent: {agent_name}")
        typer.echo(f"Sending message: {message}")
        typer.echo()

        # Test the agent
        result = asyncio.run(agent.execute(message))

        if result.success:
            typer.echo("✓ Agent responded successfully")
            typer.echo(f"Response: {result.result}")
            if result.metadata:
                typer.echo(f"Metadata: {result.metadata}")
        else:
            typer.echo(f"✗ Agent test failed: {result.error}", err=True)
            raise typer.Exit(1)

    except Exception as e:
        logger.error("Failed to test agent", agent=agent_name, error=str(e))
        typer.echo(f"Failed to test agent: {e}", err=True)
        raise typer.Exit(1)


@app.command("health")
def check_agent_health(
    agent_name: Optional[str] = typer.Argument(None, help="Name of the agent to check (checks all if not specified)"),
):
    """Check the health status of agents."""
    try:
        config_manager = ConfigManager()
        # Use default config for now
        platform_config = config_manager.get_config()

        if agent_name:
            # Check specific agent
            agent = agent_registry.get_agent(agent_name)
            if not agent:
                typer.echo(f"Agent '{agent_name}' not found", err=True)
                raise typer.Exit(1)

            typer.echo(f"Checking health of agent: {agent_name}")

            healthy = asyncio.run(agent.health_check())

            if healthy:
                typer.echo("✓ Agent is healthy")
            else:
                typer.echo("✗ Agent is unhealthy", err=True)
                raise typer.Exit(1)
        else:
            # Check all agents
            typer.echo("Checking health of all agents...")
            typer.echo()

            all_healthy = True
            for agent_name, agent_config in platform_config.agents.items():
                agent = agent_registry.get_agent(agent_config.name)
                if agent:
                    healthy = asyncio.run(agent.health_check())
                    status = "✓ healthy" if healthy else "✗ unhealthy"
                    typer.echo(f"• {agent_config.name}: {status}")
                    if not healthy:
                        all_healthy = False
                else:
                    typer.echo(f"• {agent_config.name}: ✗ not found")
                    all_healthy = False

            typer.echo()
            if all_healthy:
                typer.echo("All agents are healthy")
            else:
                typer.echo("Some agents are unhealthy", err=True)
                raise typer.Exit(1)

    except Exception as e:
        logger.error("Failed to check agent health", agent=agent_name, error=str(e))
        typer.echo(f"Failed to check agent health: {e}", err=True)
        raise typer.Exit(1)


@app.command("add")
def add_agent(
    name: str = typer.Option("--name", "-n", help="Agent name"),
    type: str = typer.Option("--type", "-t", help="Agent type (claude, codex, copilot)"),
    api_key: str = typer.Option("--api-key", "-k", help="API key for the agent"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name/version"),
    max_tokens: Optional[int] = typer.Option(None, "--max-tokens", help="Maximum tokens"),
    temperature: Optional[float] = typer.Option(None, "--temperature", help="Temperature setting"),
    timeout: Optional[int] = typer.Option(None, "--timeout", help="Request timeout in seconds"),
):
    """Add a new agent to the configuration."""
    try:
        from ...api.models import AgentConfig

        # Validate agent type - map to provider
        provider_map = {"claude": "anthropic", "codex": "openai", "copilot": "github"}
        if type not in provider_map:
            typer.echo(f"Invalid agent type. Must be one of: {', '.join(provider_map.keys())}", err=True)
            raise typer.Exit(1)

        # Create agent config entry for core config
        from ...core.config import AgentConfigEntry

        agent_entry = AgentConfigEntry(
            name=name,
            provider=provider_map[type],
            model=model or "claude-3-sonnet-20240229",  # default model
            api_key=api_key,
            max_tokens=max_tokens or 4096,
            temperature=temperature or 0.7,
            timeout_seconds=timeout or 60,
        )

        config_manager = ConfigManager()
        # Use default config for now

        # Add agent to configuration
        platform_config = config_manager.get_config()

        # Check if agent already exists
        if name in platform_config.agents:
            typer.echo(f"Agent '{name}' already exists", err=True)
            raise typer.Exit(1)

        platform_config.agents[name] = agent_entry

        # Save configuration
        config_manager.save_config(platform_config)

        typer.echo(f"✓ Agent '{name}' added successfully")
        typer.echo("Restart the platform to load the new agent")

    except Exception as e:
        logger.error("Failed to add agent", agent=name, error=str(e))
        typer.echo(f"Failed to add agent: {e}", err=True)
        raise typer.Exit(1)


@app.command("remove")
def remove_agent(
    agent_name: str = typer.Argument(..., help="Name of the agent to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Force removal without confirmation"),
):
    """Remove an agent from the configuration."""
    try:
        if not force:
            confirmed = typer.confirm(f"Are you sure you want to remove agent '{agent_name}'?")
            if not confirmed:
                typer.echo("Operation cancelled")
                return

        config_manager = ConfigManager()
        # Use default config for now

        platform_config = config_manager.get_config()

        # Check if agent exists
        if agent_name not in platform_config.agents:
            typer.echo(f"Agent '{agent_name}' not found", err=True)
            raise typer.Exit(1)

        # Remove agent
        del platform_config.agents[agent_name]

        # Save configuration
        config_manager.save_config(platform_config)

        typer.echo(f"✓ Agent '{agent_name}' removed successfully")
        typer.echo("Restart the platform to apply the changes")

    except Exception as e:
        logger.error("Failed to remove agent", agent=agent_name, error=str(e))
        typer.echo(f"Failed to remove agent: {e}", err=True)
        raise typer.Exit(1)


@app.command("update")
def update_agent(
    name: str = typer.Option("--name", "-n", help="Agent name"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="New API key"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="New model name/version"),
    max_tokens: Optional[int] = typer.Option(None, "--max-tokens", help="New maximum tokens"),
    temperature: Optional[float] = typer.Option(None, "--temperature", help="New temperature setting"),
    timeout: Optional[int] = typer.Option(None, "--timeout", help="New request timeout in seconds"),
):
    """Update an existing agent's configuration."""
    try:
        config_manager = ConfigManager()
        # Use default config for now

        platform_config = config_manager.get_config()

        # Find agent
        if name not in platform_config.agents:
            typer.echo(f"Agent '{name}' not found", err=True)
            raise typer.Exit(1)

        agent_config = platform_config.agents[name]

        # Update fields
        updated = False
        if api_key is not None:
            agent_config.api_key = api_key
            updated = True
        if model is not None:
            agent_config.model = model
            updated = True
        if max_tokens is not None:
            agent_config.max_tokens = max_tokens
            updated = True
        if temperature is not None:
            agent_config.temperature = temperature
            updated = True
        if timeout is not None:
            agent_config.timeout_seconds = timeout
            updated = True

        if not updated:
            typer.echo("No changes specified")
            return

        # Save configuration
        config_manager.save_config(platform_config)

        typer.echo(f"✓ Agent '{name}' updated successfully")
        typer.echo("Restart the platform to apply the changes")

    except Exception as e:
        logger.error("Failed to update agent", agent=name, error=str(e))
        typer.echo(f"Failed to update agent: {e}", err=True)
        raise typer.Exit(1)