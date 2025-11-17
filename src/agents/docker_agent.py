"""Docker agent implementation for containerized execution.

This module provides an implementation of the DockerAgent interface for
executing agents in Docker containers with proper environment management
and MCP server integration.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, List
import os

import docker
from docker.errors import ImageNotFound

from .base import DockerAgent, AgentConfig, AgentResponse, AgentCapabilities, AgentExecutionError


class DockerExecutionAgent(DockerAgent):
    """Docker agent implementation using containerized execution.

    Supports executing agents in Docker containers with MCP server integration
    and proper environment management.
    """

    def __init__(self, config: AgentConfig):
        """Initialize the Docker agent.

        Args:
            config: Agent configuration with Docker settings

        Raises:
            ValueError: If configuration is invalid for Docker
        """
        super().__init__(config)

        # Initialize Docker client - don't fail if Docker is not available
        # This allows testing configuration validation without Docker running
        try:
            self.client = docker.from_env()
            self.client.ping()
            self.docker_available = True
        except (docker.errors.DockerException, ValueError):
            self.client = None
            self.docker_available = False

        # Ensure Docker image is available if Docker is running
        if self.docker_available:
            self.ensure_image()

    def ensure_image(self):
        """Ensure Docker image is available by pulling if necessary."""
        if not self.docker_available or not self.client:
            return

        try:
            self.client.images.get(self.config.docker_image)
        except ImageNotFound:
            try:
                self.client.images.pull(self.config.docker_image)
            except docker.errors.DockerException:
                # Don't fail if image pull fails - allow execution to handle it
                pass

    def get_capabilities(self) -> AgentCapabilities:
        """Return the capabilities supported by this agent.

        Returns:
            AgentCapabilities: Object describing agent capabilities
        """
        return AgentCapabilities(
            code_review=True,
            code_generation=True,
            task_planning=True,
            documentation=True,
            testing=True,
            debugging=True,
            refactoring=True,
            analysis=True,
        )

    async def execute(self, prompt: str, **kwargs) -> AgentResponse:
        """Execute a prompt in a Docker container.

        Args:
            prompt: The prompt to execute
            **kwargs: Additional execution parameters (mcp_servers, allowed_tools, etc.)

        Returns:
            AgentResponse: Structured response from the agent

        Raises:
            AgentExecutionError: If execution fails
        """
        start_time = time.time()

        try:
            # Prepare environment variables
            environment = dict(os.environ)
            if self.config.docker_environment:
                environment.update(self.config.docker_environment)

            # Add execution-specific environment variables
            environment['AGENT_PROMPT'] = prompt

            # Add MCP servers if provided
            mcp_servers = kwargs.get('mcp_servers', {})
            if mcp_servers:
                environment['MCP_SERVERS'] = json.dumps(mcp_servers)

            # Add allowed tools if provided
            allowed_tools = kwargs.get('allowed_tools', [])
            if allowed_tools:
                environment['ALLOWED_TOOLS'] = json.dumps(allowed_tools)

            # Add system prompt if provided
            system_prompt = kwargs.get('system_prompt')
            if system_prompt:
                environment['AGENT_SYSTEM_PROMPT'] = system_prompt

            # Prepare volume mounts
            volumes = {}
            if self.config.docker_volumes:
                volumes.update(self.config.docker_volumes)

            # Generate unique container name
            container_name = f"agent_{self.config.name}_{uuid.uuid4().hex[:8]}"

            # Run container
            container = self.client.containers.run(
                image=self.config.docker_image,
                name=container_name,
                command=self.config.docker_command,
                environment=environment,
                volumes=volumes,
                stdout=True,
                stderr=True,
                stream=True,
                detach=False,
                remove=True,
            )

            # Collect output
            output_lines = []
            for chunk in container:
                if chunk:
                    line = chunk.decode('utf-8', errors='replace').strip()
                    output_lines.append(line)

            execution_time = time.time() - start_time

            # Process output
            output = '\n'.join(output_lines)

            return AgentResponse(
                content=output,
                tokens_used=0,  # Docker agents don't have token counting
                finish_reason="completed",
                metadata={
                    "container_name": container_name,
                    "docker_image": self.config.docker_image,
                    "command": self.config.docker_command,
                    "mcp_servers": list(mcp_servers.keys()) if mcp_servers else [],
                    "allowed_tools_count": len(allowed_tools) if allowed_tools else 0,
                },
                execution_time=execution_time,
            )

        except docker.errors.ContainerError as e:
            execution_time = time.time() - start_time
            stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
            raise AgentExecutionError(
                f"Docker container execution failed: {stderr}",
                agent_name=self.config.name,
                details={
                    "docker_image": self.config.docker_image,
                    "command": self.config.docker_command,
                    "stderr": stderr
                }
            ) from e
        except docker.errors.DockerException as e:
            execution_time = time.time() - start_time
            raise AgentExecutionError(
                f"Docker execution failed: {str(e)}",
                agent_name=self.config.name,
                details={
                    "docker_image": self.config.docker_image,
                    "command": self.config.docker_command,
                    "error": str(e)
                }
            ) from e
        except Exception as e:
            execution_time = time.time() - start_time
            raise AgentExecutionError(
                f"Unexpected error during Docker execution: {str(e)}",
                agent_name=self.config.name,
                details={
                    "docker_image": self.config.docker_image,
                    "command": self.config.docker_command,
                    "error": str(e)
                }
            ) from e

    def validate_config(self) -> bool:
        """Validate the Docker agent configuration.

        Returns:
            bool: True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Validation is handled in the base class
        return True