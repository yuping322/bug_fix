"""CLI contract implementations for workflow execution.

This module provides concrete implementations of CLI workflow execution contracts
that can be used by contract tests.
"""

import subprocess
import json
import tempfile
import os
from typing import Dict, Any, Optional
from pathlib import Path
import time

from src.core.config import ConfigManager
from src.core.logging import get_logger

logger = get_logger(__name__)


class CLIWorkflowExecutionContractImpl:
    """Concrete implementation of CLI workflow execution contract."""

    def __init__(self, cli_command: Optional[str] = None):
        """Initialize CLI contract implementation.

        Args:
            cli_command: CLI command to use (default: python -m src.cli.main)
        """
        self.cli_command = cli_command or ["python", "-m", "src.cli.main"]

    def execute_workflow_cli(
        self,
        workflow_name: str,
        config_file: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        dry_run: bool = False,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow via CLI interface.

        Args:
            workflow_name: Name of the workflow to execute
            config_file: Path to configuration file
            parameters: Workflow parameters
            verbose: Enable verbose output
            dry_run: Perform dry run without actual execution
            timeout: Execution timeout in seconds

        Returns:
            Dict containing execution results
        """
        try:
            # Build command
            cmd = self.cli_command + ["workflow", "run", workflow_name]

            # Add config file
            if config_file:
                cmd.extend(["--config", config_file])

            # Add parameters
            if parameters:
                for key, value in parameters.items():
                    cmd.extend(["--input", f"{key}={value}"])

            # Add flags
            if verbose:
                cmd.append("--verbose")
            if dry_run:
                cmd.extend(["--dry-run"])
            if timeout:
                cmd.extend(["--timeout", str(timeout)])

            # Execute command
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or 300,  # Default 5 minute timeout
                cwd=os.getcwd()
            )
            duration = time.time() - start_time

            # Parse output
            success = result.returncode == 0
            output = {}

            if success:
                # Try to parse JSON output if present
                try:
                    # Look for JSON in output
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip().startswith('{'):
                            output = json.loads(line)
                            break
                    else:
                        # No JSON found, use raw output
                        output = {"message": result.stdout.strip()}
                except json.JSONDecodeError:
                    output = {"message": result.stdout.strip()}
            else:
                output = {"error": result.stderr.strip() or result.stdout.strip()}

            return {
                "success": success,
                "workflow_name": workflow_name,
                "execution_id": f"cli-{int(start_time)}",
                "output": output,
                "duration": duration,
                "error": result.stderr.strip() if not success else None
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "workflow_name": workflow_name,
                "execution_id": f"cli-timeout-{int(time.time())}",
                "output": None,
                "duration": timeout or 300,
                "error": f"Command timed out after {timeout or 300} seconds"
            }
        except Exception as e:
            logger.error("Failed to execute workflow via CLI", workflow=workflow_name, error=str(e))
            return {
                "success": False,
                "workflow_name": workflow_name,
                "execution_id": f"cli-error-{int(time.time())}",
                "output": None,
                "duration": 0.0,
                "error": str(e)
            }

    def list_available_workflows_cli(self) -> Dict[str, Any]:
        """
        List all available workflows via CLI.

        Returns:
            Dict containing workflow list
        """
        try:
            # Build command
            cmd = self.cli_command + ["workflow", "list"]

            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )

            if result.returncode != 0:
                return {
                    "workflows": [],
                    "count": 0,
                    "error": result.stderr.strip()
                }

            # Parse output to extract workflow names
            workflows = []
            lines = result.stdout.strip().split('\n')
            in_workflow_section = False

            for line in lines:
                line = line.strip()
                if "Configured workflows" in line:
                    in_workflow_section = True
                    continue
                elif in_workflow_section and line.startswith("•"):
                    # Extract workflow name from "• workflow-name"
                    workflow_name = line[2:].strip()
                    workflows.append(workflow_name)

            return {
                "workflows": workflows,
                "count": len(workflows)
            }

        except Exception as e:
            logger.error("Failed to list workflows via CLI", error=str(e))
            return {
                "workflows": [],
                "count": 0,
                "error": str(e)
            }

    def get_workflow_status_cli(self, execution_id: str) -> Dict[str, Any]:
        """
        Get status of a workflow execution via CLI.

        Args:
            execution_id: Unique execution identifier

        Returns:
            Dict containing status information
        """
        try:
            # Build command
            cmd = self.cli_command + ["workflow", "status", execution_id]

            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )

            if result.returncode != 0:
                return {
                    "execution_id": execution_id,
                    "status": "unknown",
                    "progress": 0,
                    "error": result.stderr.strip()
                }

            # Parse status output
            status_info = {
                "execution_id": execution_id,
                "status": "unknown",
                "progress": 0,
                "current_step": None,
                "start_time": None,
                "end_time": None,
                "error": None
            }

            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip().lower()
                if "completed" in line:
                    status_info["status"] = "completed"
                    status_info["progress"] = 100
                elif "running" in line:
                    status_info["status"] = "running"
                    status_info["progress"] = 50
                elif "failed" in line:
                    status_info["status"] = "failed"
                    status_info["progress"] = 0
                elif "pending" in line:
                    status_info["status"] = "pending"
                    status_info["progress"] = 0

            return status_info

        except Exception as e:
            logger.error("Failed to get workflow status via CLI", execution_id=execution_id, error=str(e))
            return {
                "execution_id": execution_id,
                "status": "error",
                "progress": 0,
                "error": str(e)
            }