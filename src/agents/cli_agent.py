"""CLI agent implementation for subprocess-based execution.

This module provides an implementation of the CLIAgent interface for
executing CLI tools as subprocesses, such as claude code or other
command-line AI assistants.
"""

import asyncio
import subprocess
import time
from typing import Dict, Any, Optional
import os

from .base import CLIAgent, AgentConfig, AgentResponse, AgentCapabilities, AgentExecutionError


class CLIExecutionAgent(CLIAgent):
    """CLI agent implementation using subprocess execution.

    Supports executing CLI tools like claude code with proper environment
    management and output handling.
    """

    def __init__(self, config: AgentConfig):
        """Initialize the CLI agent.

        Args:
            config: Agent configuration with CLI settings

        Raises:
            ValueError: If configuration is invalid for CLI
        """
        super().__init__(config)

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
        """Execute a prompt using CLI subprocess.

        Args:
            prompt: The prompt to execute
            **kwargs: Additional execution parameters

        Returns:
            AgentResponse: Structured response from the agent

        Raises:
            AgentExecutionError: If execution fails
        """
        start_time = time.time()

        try:
            # Prepare environment variables
            env = os.environ.copy()
            if self.config.environment_variables:
                env.update(self.config.environment_variables)

            # Prepare the command
            command = self.config.command
            if kwargs.get('args'):
                command = f"{command} {kwargs['args']}"

            # Set up working directory
            cwd = self.config.working_directory or os.getcwd()

            # Execute the command
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd,
            )

            # Send prompt to stdin if needed
            stdin_data = None
            if prompt:
                stdin_data = prompt.encode('utf-8')

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(stdin_data),
                    timeout=self.config.timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise AgentExecutionError(
                    f"CLI execution timed out after {self.config.timeout_seconds} seconds",
                    agent_name=self.config.name,
                    details={"command": command, "timeout": self.config.timeout_seconds}
                )

            execution_time = time.time() - start_time

            # Check return code
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace').strip()
                raise AgentExecutionError(
                    f"CLI execution failed with return code {process.returncode}: {error_msg}",
                    agent_name=self.config.name,
                    details={
                        "command": command,
                        "returncode": process.returncode,
                        "stderr": error_msg
                    }
                )

            # Process output
            output = stdout.decode('utf-8', errors='replace').strip()

            return AgentResponse(
                content=output,
                tokens_used=0,  # CLI agents don't have token counting
                finish_reason="completed",
                metadata={
                    "command": command,
                    "returncode": process.returncode,
                    "working_directory": cwd,
                },
                execution_time=execution_time,
            )

        except subprocess.SubprocessError as e:
            execution_time = time.time() - start_time
            raise AgentExecutionError(
                f"Subprocess execution failed: {str(e)}",
                agent_name=self.config.name,
                details={"command": command, "error": str(e)}
            ) from e
        except Exception as e:
            execution_time = time.time() - start_time
            raise AgentExecutionError(
                f"Unexpected error during CLI execution: {str(e)}",
                agent_name=self.config.name,
                details={"command": command, "error": str(e)}
            ) from e

    def validate_config(self) -> bool:
        """Validate the CLI agent configuration.

        Returns:
            bool: True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Validation is handled in the base class
        return True