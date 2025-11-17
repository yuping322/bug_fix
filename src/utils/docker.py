"""Docker operations utility module.

This module provides utilities for Docker container operations,
including building, running, and managing containers for isolated execution.
"""

import os
import json
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass

from ..core.execution import ExecutionResult, execution_context_manager


@dataclass
class DockerImage:
    """Docker image information."""

    repository: str
    tag: str
    id: str
    size: int
    created: str

    @property
    def full_name(self) -> str:
        """Get full image name with tag."""
        return f"{self.repository}:{self.tag}"


@dataclass
class DockerContainer:
    """Docker container information."""

    id: str
    name: str
    image: str
    status: str
    ports: List[str]
    created: str


@dataclass
class DockerBuildOptions:
    """Options for Docker build operations."""

    dockerfile: str = "Dockerfile"
    build_args: Optional[Dict[str, str]] = None
    labels: Optional[Dict[str, str]] = None
    target: Optional[str] = None
    no_cache: bool = False
    pull: bool = True


@dataclass
class DockerRunOptions:
    """Options for Docker run operations."""

    detach: bool = False
    interactive: bool = False
    tty: bool = False
    remove: bool = True
    volumes: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    ports: Optional[List[str]] = None
    memory: Optional[str] = None
    cpus: Optional[float] = None
    workdir: Optional[str] = None
    user: Optional[str] = None


class DockerOperations:
    """Docker operations utility class."""

    def __init__(self):
        """Initialize Docker operations."""
        self._docker_available = self._check_docker_available()

    def is_available(self) -> bool:
        """Check if Docker is available.

        Returns:
            True if Docker is available
        """
        return self._docker_available

    def _check_docker_available(self) -> bool:
        """Check if Docker daemon is available.

        Returns:
            True if Docker is available
        """
        try:
            result = self._run_docker_command(["version"], capture_output=True)
            return result.success
        except Exception:
            return False

    async def build_image(
        self,
        context_path: Union[str, Path],
        image_name: str,
        options: Optional[DockerBuildOptions] = None
    ) -> ExecutionResult:
        """Build a Docker image.

        Args:
            context_path: Build context path
            image_name: Name for the built image
            options: Build options

        Returns:
            Build result
        """
        if not self._docker_available:
            return ExecutionResult(
                success=False,
                exit_code=1,
                stderr="Docker is not available"
            )

        cmd = ["docker", "build", "-t", image_name]

        if options:
            if options.dockerfile != "Dockerfile":
                cmd.extend(["-f", options.dockerfile])

            if options.build_args:
                for key, value in options.build_args.items():
                    cmd.extend(["--build-arg", f"{key}={value}"])

            if options.labels:
                for key, value in options.labels.items():
                    cmd.extend(["--label", f"{key}={value}"])

            if options.target:
                cmd.extend(["--target", options.target])

            if options.no_cache:
                cmd.append("--no-cache")

            if options.pull:
                cmd.append("--pull")

        cmd.append(str(context_path))

        return await self._run_docker_command_async(cmd)

    async def run_container(
        self,
        image: str,
        command: Optional[List[str]] = None,
        options: Optional[DockerRunOptions] = None,
        name: Optional[str] = None
    ) -> ExecutionResult:
        """Run a Docker container.

        Args:
            image: Docker image to run
            command: Command to run in container
            options: Run options
            name: Container name

        Returns:
            Run result
        """
        if not self._docker_available:
            return ExecutionResult(
                success=False,
                exit_code=1,
                stderr="Docker is not available"
            )

        cmd = ["docker", "run"]

        if name:
            cmd.extend(["--name", name])

        if options:
            if options.detach:
                cmd.append("-d")

            if options.interactive:
                cmd.append("-i")

            if options.tty:
                cmd.append("-t")

            if options.remove:
                cmd.append("--rm")

            if options.volumes:
                for volume in options.volumes:
                    cmd.extend(["-v", volume])

            if options.environment:
                for key, value in options.environment.items():
                    cmd.extend(["-e", f"{key}={value}"])

            if options.ports:
                for port in options.ports:
                    cmd.extend(["-p", port])

            if options.memory:
                cmd.extend(["--memory", options.memory])

            if options.cpus:
                cmd.extend(["--cpus", str(options.cpus)])

            if options.workdir:
                cmd.extend(["--workdir", options.workdir])

            if options.user:
                cmd.extend(["--user", options.user])

        cmd.append(image)

        if command:
            cmd.extend(command)

        return await self._run_docker_command_async(cmd)

    async def list_images(self, filter_pattern: Optional[str] = None) -> List[DockerImage]:
        """List Docker images.

        Args:
            filter_pattern: Filter pattern for image names

        Returns:
            List of Docker images
        """
        if not self._docker_available:
            return []

        cmd = ["docker", "images", "--format", "json"]

        if filter_pattern:
            cmd.extend(["--filter", f"reference={filter_pattern}"])

        result = await self._run_docker_command_async(cmd)

        if not result.success:
            return []

        images = []
        lines = result.stdout.strip().split('\n')

        for line in lines:
            if line.strip():
                try:
                    data = json.loads(line)
                    images.append(DockerImage(
                        repository=data.get("Repository", ""),
                        tag=data.get("Tag", ""),
                        id=data.get("ID", ""),
                        size=int(data.get("Size", 0)),
                        created=data.get("CreatedAt", "")
                    ))
                except (json.JSONDecodeError, KeyError):
                    continue

        return images

    async def list_containers(self, all_containers: bool = False) -> List[DockerContainer]:
        """List Docker containers.

        Args:
            all_containers: Include stopped containers

        Returns:
            List of Docker containers
        """
        if not self._docker_available:
            return []

        cmd = ["docker", "ps", "--format", "json"]

        if all_containers:
            cmd.append("-a")

        result = await self._run_docker_command_async(cmd)

        if not result.success:
            return []

        containers = []
        lines = result.stdout.strip().split('\n')

        for line in lines:
            if line.strip():
                try:
                    data = json.loads(line)
                    containers.append(DockerContainer(
                        id=data.get("ID", ""),
                        name=data.get("Names", ""),
                        image=data.get("Image", ""),
                        status=data.get("Status", ""),
                        ports=data.get("Ports", "").split(", ") if data.get("Ports") else [],
                        created=data.get("CreatedAt", "")
                    ))
                except (json.JSONDecodeError, KeyError):
                    continue

        return containers

    async def remove_image(self, image: str, force: bool = False) -> ExecutionResult:
        """Remove a Docker image.

        Args:
            image: Image name or ID
            force: Force removal

        Returns:
            Removal result
        """
        if not self._docker_available:
            return ExecutionResult(
                success=False,
                exit_code=1,
                stderr="Docker is not available"
            )

        cmd = ["docker", "rmi"]
        if force:
            cmd.append("--force")
        cmd.append(image)

        return await self._run_docker_command_async(cmd)

    async def stop_container(self, container: str, timeout: int = 10) -> ExecutionResult:
        """Stop a Docker container.

        Args:
            container: Container name or ID
            timeout: Stop timeout in seconds

        Returns:
            Stop result
        """
        if not self._docker_available:
            return ExecutionResult(
                success=False,
                exit_code=1,
                stderr="Docker is not available"
            )

        cmd = ["docker", "stop", "--time", str(timeout), container]
        return await self._run_docker_command_async(cmd)

    async def remove_container(self, container: str, force: bool = False) -> ExecutionResult:
        """Remove a Docker container.

        Args:
            container: Container name or ID
            force: Force removal

        Returns:
            Removal result
        """
        if not self._docker_available:
            return ExecutionResult(
                success=False,
                exit_code=1,
                stderr="Docker is not available"
            )

        cmd = ["docker", "rm"]
        if force:
            cmd.append("--force")
        cmd.append(container)

        return await self._run_docker_command_async(cmd)

    async def get_container_logs(self, container: str, follow: bool = False, tail: Optional[int] = None) -> str:
        """Get logs from a Docker container.

        Args:
            container: Container name or ID
            follow: Follow log output
            tail: Number of lines to show from the end

        Returns:
            Container logs
        """
        if not self._docker_available:
            return "Docker is not available"

        cmd = ["docker", "logs"]

        if follow:
            cmd.append("--follow")

        if tail:
            cmd.extend(["--tail", str(tail)])

        cmd.append(container)

        result = await self._run_docker_command_async(cmd)
        return result.stdout if result.success else result.stderr

    async def execute_in_container(
        self,
        container: str,
        command: Union[str, List[str]],
        interactive: bool = False
    ) -> ExecutionResult:
        """Execute a command in a running container.

        Args:
            container: Container name or ID
            command: Command to execute
            interactive: Run in interactive mode

        Returns:
            Execution result
        """
        if not self._docker_available:
            return ExecutionResult(
                success=False,
                exit_code=1,
                stderr="Docker is not available"
            )

        cmd = ["docker", "exec"]

        if interactive:
            cmd.append("-i")

        cmd.append(container)

        if isinstance(command, str):
            cmd.extend(["sh", "-c", command])
        else:
            cmd.extend(command)

        return await self._run_docker_command_async(cmd)

    def _run_docker_command(self, cmd: List[str], capture_output: bool = True) -> ExecutionResult:
        """Run a Docker command synchronously.

        Args:
            cmd: Docker command
            capture_output: Whether to capture output

        Returns:
            Command result
        """
        import subprocess

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=300
            )

            return ExecutionResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stderr="Docker command timed out"
            )
        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                exit_code=127,
                stderr="Docker command not found"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stderr=f"Docker command failed: {e}"
            )

    async def _run_docker_command_async(self, cmd: List[str]) -> ExecutionResult:
        """Run a Docker command asynchronously.

        Args:
            cmd: Docker command

        Returns:
            Command result
        """
        execution_id = f"docker_{hash(str(cmd))}"

        async with execution_context_manager.create_execution_context(
            execution_id,
            isolation_mode="subprocess"
        ) as env_context:
            return await execution_context_manager.execute_with_isolation(
                execution_id,
                cmd,
                env_context,
                timeout=600,  # 10 minutes timeout for Docker operations
                capture_output=True
            )


# Convenience functions
async def build_image(context_path: str, image_name: str) -> ExecutionResult:
    """Build a Docker image.

    Args:
        context_path: Build context path
        image_name: Image name

    Returns:
        Build result
    """
    docker_ops = DockerOperations()
    return await docker_ops.build_image(context_path, image_name)


async def run_container(image: str, command: Optional[List[str]] = None) -> ExecutionResult:
    """Run a Docker container.

    Args:
        image: Docker image
        command: Command to run

    Returns:
        Run result
    """
    docker_ops = DockerOperations()
    return await docker_ops.run_container(image, command)