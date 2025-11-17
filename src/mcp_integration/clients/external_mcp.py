"""External MCP client for connecting to external MCP servers.

This module provides functionality to connect to and interact with external
MCP (Model Context Protocol) servers.
"""

import asyncio
import json
import subprocess
import sys
import os
import signal
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from pathlib import Path
import logging

from ...core.config import ConfigManager


logger = logging.getLogger(__name__)


"""External MCP client for connecting to external MCP servers.

This module provides functionality to connect to and interact with external
MCP (Model Context Protocol) servers.
"""

import asyncio
import json
import subprocess
import sys
import os
import signal
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from pathlib import Path
import logging

from ...core.config import ConfigManager


logger = logging.getLogger(__name__)


class ExternalMCPClient:
    """Client for connecting to external MCP servers."""

    def __init__(self, server_config: Optional[Dict[str, Any]] = None):
        """Initialize the external MCP client.

        Args:
            server_config: Configuration for the external MCP server (optional for multi-server client)
        """
        self.processes: Dict[str, subprocess.Popen] = {}
        self.connections: Dict[str, tuple] = {}  # (reader, writer)

        # Single server config (for backward compatibility)
        if server_config:
            self.name = server_config.get("name", "external-mcp")
            self.command = server_config.get("command", [])
            self.args = server_config.get("args", [])
            self.env = server_config.get("env", {})
            self.timeout = server_config.get("timeout", 30)
            self.working_dir = server_config.get("working_dir")

    async def start_mcp_server(self, name: str, command: str, args: List[str] = None, env: Dict[str, str] = None) -> bool:
        """Start an MCP server process.

        Args:
            name: Name of the server
            command: Command to run
            args: Command arguments
            env: Environment variables

        Returns:
            bool: True if server started successfully
        """
        try:
            if name in self.processes:
                logger.warning(f"MCP server '{name}' is already running")
                return True

            args = args or []
            env = env or {}

            # Prepare full command
            cmd = [command] + args

            # Prepare environment
            full_env = dict(os.environ)
            full_env.update(env)

            logger.info(f"Starting MCP server '{name}' with command: {' '.join(cmd)}")

            # Start the process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env,
                preexec_fn=None if sys.platform == "win32" else os.setsid
            )

            self.processes[name] = process

            # Wait a bit for the server to initialize
            await asyncio.sleep(1)

            # Check if process is still running
            if process.poll() is None:
                logger.info(f"MCP server '{name}' started successfully")
                return True
            else:
                logger.error(f"MCP server '{name}' failed to start")
                await self.stop_mcp_server(name)
                return False

        except Exception as e:
            logger.error(f"Error starting MCP server '{name}': {e}")
            return False

    async def stop_mcp_server(self, name: str) -> bool:
        """Stop an MCP server process.

        Args:
            name: Name of the server to stop

        Returns:
            bool: True if server stopped successfully
        """
        try:
            if name not in self.processes:
                return False

            process = self.processes[name]
            logger.info(f"Stopping MCP server '{name}'")

            # Terminate the process
            process.terminate()

            # Wait for process to terminate
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"MCP server '{name}' did not terminate gracefully, killing")
                process.kill()
                await process.wait()

            logger.info(f"MCP server '{name}' stopped")
            del self.processes[name]

            return True

        except Exception as e:
            logger.error(f"Error stopping MCP server '{name}': {e}")
            return False

    async def connect_to_mcp_server(self, name: str, host: str, port: int) -> bool:
        """Connect to an MCP server via TCP.

        Args:
            name: Name of the server
            host: Server host
            port: Server port

        Returns:
            bool: True if connected successfully
        """
        try:
            if name in self.connections:
                logger.warning(f"Already connected to MCP server '{name}'")
                return True

            logger.info(f"Connecting to MCP server '{name}' at {host}:{port}")

            reader, writer = await asyncio.open_connection(host, port)
            self.connections[name] = (reader, writer)

            logger.info(f"Connected to MCP server '{name}'")
            return True

        except Exception as e:
            logger.error(f"Error connecting to MCP server '{name}': {e}")
            return False

    async def disconnect_from_mcp_server(self, name: str) -> bool:
        """Disconnect from an MCP server.

        Args:
            name: Name of the server to disconnect from

        Returns:
            bool: True if disconnected successfully
        """
        try:
            if name not in self.connections:
                return False

            reader, writer = self.connections[name]
            logger.info(f"Disconnecting from MCP server '{name}'")

            writer.close()
            await writer.wait_closed()

            logger.info(f"Disconnected from MCP server '{name}'")
            del self.connections[name]

            return True

        except Exception as e:
            logger.error(f"Error disconnecting from MCP server '{name}': {e}")
            return False

    def list_running_servers(self) -> List[Dict[str, Any]]:
        """List all running MCP servers.

        Returns:
            List of running server information
        """
        servers = []
        for name, process in self.processes.items():
            servers.append({
                "name": name,
                "pid": process.pid,
                "running": process.poll() is None
            })
        return servers

    def list_connected_servers(self) -> List[str]:
        """List all connected MCP servers.

        Returns:
            List of connected server names
        """
        return list(self.connections.keys())

    async def send_message(self, server_name: str, message: Dict[str, Any]) -> bool:
        """Send a message to an MCP server.

        Args:
            server_name: Name of the server
            message: Message to send

        Returns:
            bool: True if message sent successfully
        """
        try:
            if server_name not in self.connections:
                return False

            reader, writer = self.connections[server_name]

            # Serialize message
            message_json = json.dumps(message) + "\n"

            # Send message
            asyncio.StreamWriter.write(writer, message_json.encode())
            await asyncio.StreamWriter.drain(writer)

            return True

        except Exception as e:
            logger.error(f"Error sending message to MCP server '{server_name}': {e}")
            return False

    async def receive_message(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Receive a message from an MCP server.

        Args:
            server_name: Name of the server

        Returns:
            Received message or None if no message/error
        """
        try:
            if server_name not in self.connections:
                return None

            reader, writer = self.connections[server_name]

            # Read message
            data = await asyncio.StreamReader.readuntil(reader, b'\n')
            message_json = data.decode().strip()

            # Parse message
            message = json.loads(message_json)

            return message

        except Exception as e:
            logger.error(f"Error receiving message from MCP server '{server_name}': {e}")
            return None

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
        """Call a tool on an MCP server.

        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Arguments for the tool

        Returns:
            Tool execution result or None if failed
        """
        try:
            # Send tool call request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            success = await self.send_message(server_name, request)
            if not success:
                return None

            # Receive response
            response = await self.receive_message(server_name)
            if not response:
                return None

            if "error" in response:
                logger.error(f"MCP server error: {response['error']}")
                return None

            return response

        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}' on server '{server_name}': {e}")
            return None


class ExternalMCPManager:
    """Manager for multiple external MCP servers."""

    def __init__(self, config_manager: ConfigManager):
        """Initialize the MCP manager.

        Args:
            config_manager: Configuration manager
        """
        self.config_manager = config_manager
        self.clients: Dict[str, ExternalMCPClient] = {}

    async def initialize_clients(self):
        """Initialize all configured external MCP clients."""
        config = self.config_manager.get_config()

        # Get MCP server configurations
        mcp_servers = config.deployment.get("mcp_servers", {})

        for server_name, server_config in mcp_servers.items():
            if server_config.get("enabled", True):
                client = ExternalMCPClient(server_config)
                self.clients[server_name] = client

                # Auto-start if configured
                if server_config.get("auto_start", False):
                    await client.start()

    async def get_client(self, server_name: str) -> Optional[ExternalMCPClient]:
        """Get an MCP client by name.

        Args:
            server_name: Name of the MCP server

        Returns:
            MCP client instance or None if not found
        """
        return self.clients.get(server_name)

    async def list_servers(self) -> List[Dict[str, Any]]:
        """List all configured MCP servers.

        Returns:
            List of server information
        """
        servers = []
        for name, client in self.clients.items():
            servers.append({
                "name": name,
                "running": await client.is_running(),
                "command": client.command,
                "timeout": client.timeout
            })
        return servers

    async def start_server(self, server_name: str) -> bool:
        """Start a specific MCP server.

        Args:
            server_name: Name of the server to start

        Returns:
            bool: True if started successfully
        """
        client = self.clients.get(server_name)
        if client:
            return await client.start()
        return False

    async def stop_server(self, server_name: str) -> bool:
        """Stop a specific MCP server.

        Args:
            server_name: Name of the server to stop

        Returns:
            bool: True if stopped successfully
        """
        client = self.clients.get(server_name)
        if client:
            return await client.stop()
        return False

    async def stop_all(self):
        """Stop all MCP servers."""
        tasks = []
        for client in self.clients.values():
            tasks.append(client.stop())
        await asyncio.gather(*tasks, return_exceptions=True)


# Global MCP manager instance
mcp_manager = ExternalMCPManager(ConfigManager())