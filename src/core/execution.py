"""Execution context and isolation management for the multi-agent platform.

This module provides execution isolation, resource management, and context
tracking for workflow executions.
"""

import asyncio
import os
import tempfile
import time
import uuid
from typing import Dict, Any, Optional, List, Union, ContextManager
from pathlib import Path
from contextlib import contextmanager
import subprocess
import signal

from pydantic import BaseModel, Field


class ExecutionLimits(BaseModel):
    """Resource limits for execution isolation."""

    max_memory_mb: int = Field(1024, ge=128, description="Maximum memory usage in MB")
    max_cpu_percent: int = Field(80, ge=1, le=100, description="Maximum CPU usage percentage")
    max_execution_time: int = Field(3600, ge=60, description="Maximum execution time in seconds")
    max_file_size_mb: int = Field(100, ge=1, description="Maximum file size in MB")
    allow_network: bool = Field(True, description="Allow network access")
    allow_subprocess: bool = Field(True, description="Allow subprocess execution")


class ExecutionEnvironment(BaseModel):
    """Execution environment configuration."""

    working_directory: Path = Field(..., description="Working directory for execution")
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    resource_limits: ExecutionLimits = Field(default_factory=ExecutionLimits, description="Resource limits")
    isolation_mode: str = Field("subprocess", description="Isolation mode (subprocess, docker, none)")


class ExecutionResult(BaseModel):
    """Result of an execution."""

    success: bool = Field(..., description="Whether execution was successful")
    exit_code: int = Field(..., description="Process exit code")
    stdout: str = Field("", description="Standard output")
    stderr: str = Field("", description="Standard error")
    execution_time: float = Field(..., description="Execution time in seconds")
    resource_usage: Dict[str, Any] = Field(default_factory=dict, description="Resource usage statistics")
    artifacts: Dict[str, Any] = Field(default_factory=dict, description="Generated artifacts")


class ExecutionContextManager:
    """Manages execution contexts and isolation."""

    def __init__(self):
        """Initialize the execution context manager."""
        self._active_executions: Dict[str, Dict[str, Any]] = {}
        self._temp_directories: Dict[str, Path] = {}

    @contextmanager
    def create_execution_context(
        self,
        execution_id: str,
        base_workspace: Optional[Union[str, Path]] = None,
        isolation_mode: str = "subprocess",
        resource_limits: Optional[ExecutionLimits] = None
    ):
        """Create an isolated execution context.

        Args:
            execution_id: Unique execution identifier
            base_workspace: Base workspace directory
            isolation_mode: Isolation mode (subprocess, docker, none)
            resource_limits: Resource limits for execution

        Yields:
            ExecutionEnvironment: Configured execution environment
        """
        # Create temporary workspace if not provided
        if base_workspace is None:
            temp_dir = Path(tempfile.mkdtemp(prefix=f"agent_orchestration_{execution_id}_"))
            self._temp_directories[execution_id] = temp_dir
            workspace = temp_dir
        else:
            workspace = Path(base_workspace) / execution_id
            workspace.mkdir(parents=True, exist_ok=True)

        # Set up environment variables
        env_vars = os.environ.copy()
        env_vars.update({
            "AGENT_ORCHESTRATION_EXECUTION_ID": execution_id,
            "AGENT_ORCHESTRATION_WORKSPACE": str(workspace),
            "AGENT_ORCHESTRATION_ISOLATION_MODE": isolation_mode,
        })

        # Create resource limits
        if resource_limits is None:
            resource_limits = ExecutionLimits()

        # Create execution environment
        environment = ExecutionEnvironment(
            working_directory=workspace,
            environment_variables=env_vars,
            resource_limits=resource_limits,
            isolation_mode=isolation_mode,
        )

        # Track active execution
        self._active_executions[execution_id] = {
            "environment": environment,
            "start_time": time.time(),
            "status": "active",
        }

        try:
            yield environment
        finally:
            # Clean up execution tracking
            if execution_id in self._active_executions:
                self._active_executions[execution_id]["status"] = "completed"
                self._active_executions[execution_id]["end_time"] = time.time()

    async def execute_with_isolation(
        self,
        execution_id: str,
        command: Union[str, List[str]],
        environment: ExecutionEnvironment,
        timeout: Optional[int] = None,
        capture_output: bool = True
    ) -> ExecutionResult:
        """Execute a command with isolation.

        Args:
            execution_id: Execution identifier
            command: Command to execute
            environment: Execution environment
            timeout: Execution timeout in seconds
            capture_output: Whether to capture stdout/stderr

        Returns:
            ExecutionResult: Execution result
        """
        start_time = time.time()

        try:
            if environment.isolation_mode == "docker":
                result = await self._execute_in_docker(
                    execution_id, command, environment, timeout, capture_output
                )
            elif environment.isolation_mode == "subprocess":
                result = await self._execute_in_subprocess(
                    execution_id, command, environment, timeout, capture_output
                )
            else:  # none
                result = await self._execute_without_isolation(
                    execution_id, command, environment, timeout, capture_output
                )

            execution_time = time.time() - start_time
            result.execution_time = execution_time

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stderr=str(e),
                execution_time=execution_time,
                resource_usage={"error": str(e)},
            )

    async def _execute_in_docker(
        self,
        execution_id: str,
        command: Union[str, List[str]],
        environment: ExecutionEnvironment,
        timeout: Optional[int],
        capture_output: bool
    ) -> ExecutionResult:
        """Execute command in Docker container.

        Args:
            execution_id: Execution identifier
            command: Command to execute
            environment: Execution environment
            timeout: Execution timeout
            capture_output: Whether to capture output

        Returns:
            ExecutionResult: Execution result
        """
        # Prepare Docker command
        docker_cmd = [
            "docker", "run", "--rm",
            "--memory", f"{environment.resource_limits.max_memory_mb}m",
            "--cpus", f"{environment.resource_limits.max_cpu_percent / 100:.2f}",
            "--workdir", "/workspace",
            "--env", f"AGENT_ORCHESTRATION_EXECUTION_ID={execution_id}",
        ]

        # Add environment variables
        for key, value in environment.environment_variables.items():
            docker_cmd.extend(["--env", f"{key}={value}"])

        # Mount workspace
        docker_cmd.extend([
            "-v", f"{environment.working_directory}:/workspace",
            "agent-orchestration:latest"  # Placeholder image
        ])

        # Add the actual command
        if isinstance(command, str):
            docker_cmd.extend(["sh", "-c", command])
        else:
            docker_cmd.extend(command)

        # Execute Docker command
        return await self._execute_subprocess(
            docker_cmd, environment.working_directory, timeout, capture_output
        )

    async def _execute_in_subprocess(
        self,
        execution_id: str,
        command: Union[str, List[str]],
        environment: ExecutionEnvironment,
        timeout: Optional[int],
        capture_output: bool
    ) -> ExecutionResult:
        """Execute command in subprocess with resource limits.

        Args:
            execution_id: Execution identifier
            command: Command to execute
            environment: Execution environment
            timeout: Execution timeout
            capture_output: Whether to capture output

        Returns:
            ExecutionResult: Execution result
        """
        # For now, execute without advanced resource limits
        # In a production system, this would use cgroups or similar
        return await self._execute_subprocess(
            command, environment.working_directory, timeout, capture_output
        )

    async def _execute_without_isolation(
        self,
        execution_id: str,
        command: Union[str, List[str]],
        environment: ExecutionEnvironment,
        timeout: Optional[int],
        capture_output: bool
    ) -> ExecutionResult:
        """Execute command without isolation.

        Args:
            execution_id: Execution identifier
            command: Command to execute
            environment: Execution environment
            timeout: Execution timeout
            capture_output: Whether to capture output

        Returns:
            ExecutionResult: Execution result
        """
        return await self._execute_subprocess(
            command, environment.working_directory, timeout, capture_output
        )

    async def _execute_subprocess(
        self,
        command: Union[str, List[str]],
        cwd: Path,
        timeout: Optional[int],
        capture_output: bool
    ) -> ExecutionResult:
        """Execute a subprocess command.

        Args:
            command: Command to execute
            cwd: Working directory
            timeout: Execution timeout
            capture_output: Whether to capture output

        Returns:
            ExecutionResult: Execution result
        """
        try:
            # Prepare subprocess arguments
            if isinstance(command, str):
                proc_args = {"shell": True, "text": True}
            else:
                proc_args = {"text": True}

            if capture_output:
                proc_args.update({"capture_output": True})
            else:
                proc_args.update({"stdout": None, "stderr": None})

            # Execute the command
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(cwd),
                **proc_args
            )

            try:
                # Wait for completion with timeout
                await asyncio.wait_for(process.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                # Kill the process on timeout
                process.kill()
                await process.wait()
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    stderr="Command timed out",
                )

            # Get output
            stdout = ""
            stderr = ""
            if capture_output:
                stdout = process.stdout or ""
                stderr = process.stderr or ""

            return ExecutionResult(
                success=process.returncode == 0,
                exit_code=process.returncode or 0,
                stdout=stdout,
                stderr=stderr,
                resource_usage={},  # Would be populated with actual resource usage
            )

        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                exit_code=127,
                stderr=f"Command not found: {command}",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stderr=f"Execution error: {e}",
            )

    def get_active_executions(self) -> List[str]:
        """Get list of active execution IDs.

        Returns:
            List of active execution IDs
        """
        return [
            execution_id
            for execution_id, data in self._active_executions.items()
            if data["status"] == "active"
        ]

    def get_execution_info(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get information about an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Execution information or None if not found
        """
        return self._active_executions.get(execution_id)

    def cleanup_execution(self, execution_id: str):
        """Clean up resources for an execution.

        Args:
            execution_id: Execution identifier
        """
        # Remove from active executions
        if execution_id in self._active_executions:
            del self._active_executions[execution_id]

        # Clean up temporary directory
        if execution_id in self._temp_directories:
            temp_dir = self._temp_directories[execution_id]
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception:
                pass  # Ignore cleanup errors
            del self._temp_directories[execution_id]

    def cleanup_all(self):
        """Clean up all execution resources."""
        execution_ids = list(self._active_executions.keys())
        for execution_id in execution_ids:
            self.cleanup_execution(execution_id)


# Global execution context manager instance
execution_context_manager = ExecutionContextManager()