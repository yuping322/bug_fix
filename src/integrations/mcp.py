"""MCP (Model Context Protocol) integration for external tool connections."""

import asyncio
import json
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass
import websockets
import aiohttp

from ...core.config import ConfigManager
from ...core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPResource:
    """MCP resource definition."""
    uri: str
    name: str
    description: str
    mime_type: str


@dataclass
class MCPMessage:
    """MCP message structure."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPClient:
    """MCP client for connecting to external MCP servers."""

    def __init__(self, server_url: str, session_id: Optional[str] = None):
        """Initialize MCP client.

        Args:
            server_url: MCP server WebSocket URL
            session_id: Optional session identifier
        """
        self.server_url = server_url
        self.session_id = session_id
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.message_id = 0
        self.pending_requests: Dict[int, asyncio.Future] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.notification_handlers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}

    async def connect(self) -> None:
        """Connect to MCP server."""
        try:
            self.websocket = await websockets.connect(self.server_url)
            logger.info(f"Connected to MCP server: {self.server_url}")

            # Start message handling loop
            asyncio.create_task(self._handle_messages())

            # Initialize connection
            await self._initialize()

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("Disconnected from MCP server")

    async def _handle_messages(self) -> None:
        """Handle incoming messages from MCP server."""
        try:
            while self.websocket and not self.websocket.closed:
                message = await self.websocket.recv()
                data = json.loads(message)

                message_obj = MCPMessage(**data)

                if message_obj.id is not None:
                    # Response to a request
                    if message_obj.id in self.pending_requests:
                        future = self.pending_requests.pop(message_obj.id)
                        if message_obj.error:
                            future.set_exception(Exception(message_obj.error.get("message", "MCP error")))
                        else:
                            future.set_result(message_obj.result)
                else:
                    # Notification
                    await self._handle_notification(message_obj.method, message_obj.params or {})

        except Exception as e:
            logger.error(f"Error handling MCP messages: {e}")

    async def _handle_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Handle MCP notification."""
        if method in self.notification_handlers:
            for handler in self.notification_handlers[method]:
                try:
                    await handler(params)
                except Exception as e:
                    logger.error(f"Error in notification handler for {method}: {e}")

    async def _initialize(self) -> None:
        """Initialize MCP connection."""
        result = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "logging": {}
            },
            "clientInfo": {
                "name": "mao-orchestration",
                "version": "1.0.0"
            }
        })

        # Store server capabilities
        self.server_capabilities = result.get("capabilities", {})

        # List available tools and resources
        await self._list_tools()
        await self._list_resources()

        logger.info("MCP connection initialized")

    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Send MCP request and wait for response."""
        if not self.websocket:
            raise Exception("Not connected to MCP server")

        self.message_id += 1
        message = MCPMessage(
            id=self.message_id,
            method=method,
            params=params
        )

        future = asyncio.Future()
        self.pending_requests[self.message_id] = future

        await self.websocket.send(json.dumps(message.__dict__))
        return await future

    async def _list_tools(self) -> None:
        """List available MCP tools."""
        try:
            result = await self._send_request("tools/list")
            tools = result.get("tools", [])

            self.tools = {
                tool["name"]: MCPTool(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {})
                )
                for tool in tools
            }

            logger.info(f"Loaded {len(self.tools)} MCP tools")

        except Exception as e:
            logger.error(f"Failed to list MCP tools: {e}")

    async def _list_resources(self) -> None:
        """List available MCP resources."""
        try:
            result = await self._send_request("resources/list")
            resources = result.get("resources", [])

            self.resources = {
                resource["uri"]: MCPResource(
                    uri=resource["uri"],
                    name=resource.get("name", ""),
                    description=resource.get("description", ""),
                    mime_type=resource.get("mimeType", "")
                )
                for resource in resources
            }

            logger.info(f"Loaded {len(self.resources)} MCP resources")

        except Exception as e:
            logger.error(f"Failed to list MCP resources: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not available")

        result = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })

        return result

    async def read_resource(self, uri: str) -> bytes:
        """Read MCP resource.

        Args:
            uri: Resource URI

        Returns:
            Resource content as bytes
        """
        if uri not in self.resources:
            raise ValueError(f"Resource '{uri}' not available")

        result = await self._send_request("resources/read", {"uri": uri})
        return result.get("contents", b"")

    def add_notification_handler(self, method: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Add notification handler.

        Args:
            method: Notification method name
            handler: Async handler function
        """
        if method not in self.notification_handlers:
            self.notification_handlers[method] = []
        self.notification_handlers[method].append(handler)

    def get_available_tools(self) -> List[MCPTool]:
        """Get list of available tools."""
        return list(self.tools.values())

    def get_available_resources(self) -> List[MCPResource]:
        """Get list of available resources."""
        return list(self.resources.values())


class MCPIntegration:
    """MCP integration manager for multiple MCP servers."""

    def __init__(self, config_manager: ConfigManager):
        """Initialize MCP integration.

        Args:
            config_manager: Configuration manager
        """
        self.config_manager = config_manager
        self.clients: Dict[str, MCPClient] = {}
        self.logger = get_logger(__name__)

    async def connect_server(self, server_name: str, server_url: str) -> None:
        """Connect to MCP server.

        Args:
            server_name: Server identifier
            server_url: MCP server URL
        """
        client = MCPClient(server_url)
        await client.connect()
        self.clients[server_name] = client
        self.logger.info(f"Connected to MCP server: {server_name}")

    async def disconnect_server(self, server_name: str) -> None:
        """Disconnect from MCP server.

        Args:
            server_name: Server identifier
        """
        if server_name in self.clients:
            await self.clients[server_name].disconnect()
            del self.clients[server_name]
            self.logger.info(f"Disconnected from MCP server: {server_name}")

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call tool on specific MCP server.

        Args:
            server_name: Server identifier
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if server_name not in self.clients:
            raise ValueError(f"MCP server '{server_name}' not connected")

        return await self.clients[server_name].call_tool(tool_name, arguments)

    async def read_resource(self, server_name: str, uri: str) -> bytes:
        """Read resource from specific MCP server.

        Args:
            server_name: Server identifier
            uri: Resource URI

        Returns:
            Resource content
        """
        if server_name not in self.clients:
            raise ValueError(f"MCP server '{server_name}' not connected")

        return await self.clients[server_name].read_resource(uri)

    def get_available_tools(self, server_name: Optional[str] = None) -> Dict[str, List[MCPTool]]:
        """Get available tools from all or specific server.

        Args:
            server_name: Optional server name filter

        Returns:
            Dictionary of server names to tool lists
        """
        if server_name:
            if server_name not in self.clients:
                return {}
            return {server_name: self.clients[server_name].get_available_tools()}

        return {
            name: client.get_available_tools()
            for name, client in self.clients.items()
        }

    def get_available_resources(self, server_name: Optional[str] = None) -> Dict[str, List[MCPResource]]:
        """Get available resources from all or specific server.

        Args:
            server_name: Optional server name filter

        Returns:
            Dictionary of server names to resource lists
        """
        if server_name:
            if server_name not in self.clients:
                return {}
            return {server_name: self.clients[server_name].get_available_resources()}

        return {
            name: client.get_available_resources()
            for name, client in self.clients.items()
        }

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all MCP connections."""
        health_status = {}
        for server_name, client in self.clients.items():
            try:
                # Simple health check - try to list tools
                await client._list_tools()
                health_status[server_name] = True
            except Exception:
                health_status[server_name] = False

        return health_status

    async def cleanup(self) -> None:
        """Clean up all MCP connections."""
        for server_name in list(self.clients.keys()):
            try:
                await self.disconnect_server(server_name)
            except Exception as e:
                self.logger.error(f"Error disconnecting from {server_name}: {e}")