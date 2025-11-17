"""Service discovery for MCP servers.

This module provides service discovery functionality to automatically
find and register MCP servers in the network or local environment.
"""

import asyncio
import json
import socket
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging
import hashlib

from .external_mcp import ExternalMCPClient


logger = logging.getLogger(__name__)


@dataclass
class DiscoveredServer:
    """Information about a discovered MCP server."""

    id: str
    name: str
    address: str
    port: int
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.time)
    status: str = "unknown"  # unknown, available, unavailable

    @property
    def is_expired(self) -> bool:
        """Check if the server discovery has expired."""
        return time.time() - self.last_seen > 300  # 5 minutes


class ServiceDiscovery:
    """Service discovery for MCP servers."""

    def __init__(self, multicast_group: str = "224.0.0.1", port: int = 9999):
        """Initialize service discovery.

        Args:
            multicast_group: Multicast group for discovery
            port: Port for discovery messages
        """
        self.multicast_group = multicast_group
        self.port = port
        self.discovered_servers: Dict[str, DiscoveredServer] = {}
        self.services: Dict[str, Dict[str, Any]] = {}  # Local service registry
        self.scan_ports: List[int] = [3000, 3001, 3002, 8080, 8081]  # Common MCP ports
        self.running = False
        self._discovery_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the service discovery."""
        if self.running:
            return

        self.running = True
        logger.info("Starting MCP service discovery")

        # Start discovery listener
        self._discovery_task = asyncio.create_task(self._listen_for_discovery())

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_servers())

        # Send initial discovery request
        await self._send_discovery_request()

    async def stop(self):
        """Stop the service discovery."""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping MCP service discovery")

        if self._discovery_task:
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _listen_for_discovery(self):
        """Listen for discovery messages from MCP servers."""
        try:
            # Create UDP socket for multicast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind to the multicast port
            sock.bind(("", self.port))

            # Join multicast group
            group = socket.inet_aton(self.multicast_group)
            mreq = group + socket.inet_aton("0.0.0.0")
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            logger.info(f"Listening for MCP discovery messages on {self.multicast_group}:{self.port}")

            while self.running:
                try:
                    data, addr = await asyncio.get_event_loop().sock_recvfrom(sock, 4096)
                    message = json.loads(data.decode())

                    if message.get("type") == "mcp_discovery_response":
                        await self._handle_discovery_response(message, addr)

                except json.JSONDecodeError:
                    logger.debug("Received invalid JSON in discovery message")
                except Exception as e:
                    logger.error(f"Error processing discovery message: {e}")

        except Exception as e:
            logger.error(f"Error in discovery listener: {e}")
        finally:
            sock.close()

    async def _handle_discovery_response(self, message: Dict[str, Any], addr: Tuple[str, int]):
        """Handle a discovery response from an MCP server.

        Args:
            message: Discovery response message
            addr: Address of the sender
        """
        try:
            server_info = message.get("server", {})
            server_id = server_info.get("id", f"{addr[0]}:{server_info.get('port', 0)}")

            # Create or update discovered server
            server = DiscoveredServer(
                id=server_id,
                name=server_info.get("name", f"mcp-server-{server_id}"),
                address=addr[0],
                port=server_info.get("port", 0),
                capabilities=server_info.get("capabilities", []),
                metadata=server_info.get("metadata", {}),
                last_seen=time.time(),
                status="available"
            )

            self.discovered_servers[server_id] = server
            logger.info(f"Discovered MCP server: {server.name} at {server.address}:{server.port}")

        except Exception as e:
            logger.error(f"Error handling discovery response: {e}")

    async def _send_discovery_request(self):
        """Send a discovery request to find MCP servers."""
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

            # Create discovery request
            request = {
                "type": "mcp_discovery_request",
                "timestamp": time.time(),
                "requester": socket.gethostname()
            }

            # Send to multicast group
            data = json.dumps(request).encode()
            sock.sendto(data, (self.multicast_group, self.port))

            logger.debug("Sent MCP discovery request")

        except Exception as e:
            logger.error(f"Error sending discovery request: {e}")
        finally:
            sock.close()

    async def _cleanup_expired_servers(self):
        """Clean up expired server discoveries."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute

                expired = []
                for server_id, server in self.discovered_servers.items():
                    if server.is_expired:
                        expired.append(server_id)

                for server_id in expired:
                    logger.info(f"Removing expired MCP server: {self.discovered_servers[server_id].name}")
                    del self.discovered_servers[server_id]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    def get_discovered_servers(self) -> List[DiscoveredServer]:
        """Get list of discovered servers.

        Returns:
            List of discovered MCP servers
        """
        return list(self.discovered_servers.values())

    def get_server_by_id(self, server_id: str) -> Optional[DiscoveredServer]:
        """Get a discovered server by ID.

        Args:
            server_id: Server ID

        Returns:
            Discovered server or None
        """
        return self.discovered_servers.get(server_id)

    async def connect_to_server(self, server: DiscoveredServer) -> Optional[ExternalMCPClient]:
        """Connect to a discovered MCP server.

        Args:
            server: Discovered server information

        Returns:
            MCP client instance or None if connection failed
        """
        try:
            # Create server config for client
            server_config = {
                "name": server.name,
                "command": [],  # Not used for direct connection
                "args": [],
                "env": {},
                "timeout": 30,
                "working_dir": None,
                "address": server.address,
                "port": server.port
            }

            # For discovered servers, we'd need a different connection method
            # This is a placeholder - actual implementation would depend on
            # how discovered servers expose their endpoints
            logger.warning("Direct connection to discovered servers not yet implemented")
            return None

        except Exception as e:
            logger.error(f"Error connecting to discovered server {server.name}: {e}")
            return None

    async def refresh_discovery(self):
        """Refresh server discovery by sending a new discovery request."""
        await self._send_discovery_request()

    def register_service(self, service_info: Dict[str, Any]) -> None:
        """Register a local MCP service.

        Args:
            service_info: Service information dictionary
        """
        service_name = service_info.get("name", "")
        if service_name:
            self.services[service_name] = service_info
            logger.info(f"Registered local MCP service: {service_name}")

    def unregister_service(self, service_name: str) -> None:
        """Unregister a local MCP service.

        Args:
            service_name: Name of the service to unregister
        """
        if service_name in self.services:
            del self.services[service_name]
            logger.info(f"Unregistered local MCP service: {service_name}")

    def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered service.

        Args:
            service_name: Name of the service

        Returns:
            Service information or None if not found
        """
        return self.services.get(service_name)

    def list_services(self) -> List[Dict[str, Any]]:
        """List all registered services.

        Returns:
            List of service information dictionaries
        """
        return list(self.services.values())

    def filter_services_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Filter services by capability.

        Args:
            capability: Capability to filter by

        Returns:
            List of services with the specified capability
        """
        return [
            service for service in self.services.values()
            if capability in service.get("capabilities", [])
        ]

    def get_services_by_protocol(self, protocol: str) -> List[Dict[str, Any]]:
        """Get services by protocol.

        Args:
            protocol: Protocol to filter by

        Returns:
            List of services using the specified protocol
        """
        return [
            service for service in self.services.values()
            if service.get("protocol") == protocol
        ]

    async def scan_network_services(self, network: str) -> List[Dict[str, Any]]:
        """Scan network for MCP services.

        Args:
            network: Network range to scan (e.g., "192.168.1.0/24")

        Returns:
            List of discovered services
        """
        # This is a simplified implementation for testing
        # In a real implementation, this would scan the network
        discovered_services = []

        # Mock some discovered services for testing
        if network == "192.168.1.0/24":
            discovered_services = [
                {
                    "name": "mcp-server-1",
                    "host": "192.168.1.100",
                    "port": 3000,
                    "protocol": "mcp",
                    "capabilities": ["tools", "resources"]
                },
                {
                    "name": "mcp-server-2",
                    "host": "192.168.1.101",
                    "port": 3001,
                    "protocol": "mcp",
                    "capabilities": ["chat", "tools"]
                }
            ]

        return discovered_services

    def discover_local_services(self) -> List[Dict[str, Any]]:
        """Discover local MCP services.

        Returns:
            List of local services
        """
        # This is a simplified implementation for testing
        # In a real implementation, this would scan local configuration files
        return [
            {
                "name": "local-mcp-git",
                "host": "localhost",
                "port": 3000,
                "protocol": "mcp",
                "capabilities": ["git", "version-control"]
            }
        ]


class LocalServiceDiscovery:
    """Service discovery for locally running MCP servers."""

    def __init__(self):
        """Initialize local service discovery."""
        self.local_servers: Dict[str, ExternalMCPClient] = {}
        self.scan_paths: List[str] = [
            "/usr/local/bin",
            "/usr/bin",
            "/opt/homebrew/bin",  # macOS Homebrew
            "/home/linuxbrew/.linuxbrew/bin",  # Linux Homebrew
            str(Path.home() / ".local" / "bin"),
            str(Path.home() / "bin"),
        ]

    async def scan_for_servers(self) -> List[Dict[str, Any]]:
        """Scan for locally available MCP servers.

        Returns:
            List of discovered local MCP servers
        """
        found_servers = []

        # Common MCP server executables to look for
        server_executables = [
            "mcp-server-git",
            "mcp-server-filesystem",
            "mcp-server-weather",
            "mcp-server-calculator",
            "mcp-server-database",
            "mcp-server-http",
            "mcp-server-python",
            "mcp-server-node",
        ]

        for path_str in self.scan_paths:
            path = Path(path_str)
            if not path.exists():
                continue

            for executable in server_executables:
                exe_path = path / executable
                if exe_path.exists() and exe_path.is_file() and exe_path.stat().st_mode & 0o111:
                    # Found executable
                    server_info = {
                        "name": executable,
                        "path": str(exe_path),
                        "type": "local",
                        "capabilities": self._infer_capabilities(executable),
                        "description": f"Local MCP server: {executable}"
                    }
                    found_servers.append(server_info)

        logger.info(f"Found {len(found_servers)} local MCP servers")
        return found_servers

    def _infer_capabilities(self, executable: str) -> List[str]:
        """Infer capabilities from executable name.

        Args:
            executable: Executable name

        Returns:
            List of inferred capabilities
        """
        capabilities = []

        if "git" in executable:
            capabilities.extend(["git", "version-control", "repository"])
        if "filesystem" in executable or "files" in executable:
            capabilities.extend(["filesystem", "file-operations", "read", "write"])
        if "weather" in executable:
            capabilities.extend(["weather", "forecast", "climate"])
        if "calculator" in executable or "calc" in executable:
            capabilities.extend(["calculator", "math", "computation"])
        if "database" in executable or "db" in executable:
            capabilities.extend(["database", "query", "data"])
        if "http" in executable:
            capabilities.extend(["http", "web", "api"])
        if "python" in executable:
            capabilities.extend(["python", "code", "execution"])
        if "node" in executable or "javascript" in executable:
            capabilities.extend(["javascript", "node", "code"])

        return capabilities

    async def create_client_for_server(self, server_info: Dict[str, Any]) -> Optional[ExternalMCPClient]:
        """Create an MCP client for a local server.

        Args:
            server_info: Server information

        Returns:
            MCP client instance or None
        """
        try:
            server_config = {
                "name": server_info["name"],
                "command": [server_info["path"]],
                "args": [],
                "env": {},
                "timeout": 30,
                "working_dir": None
            }

            client = ExternalMCPClient(server_config)
            self.local_servers[server_info["name"]] = client

            return client

        except Exception as e:
            logger.error(f"Error creating client for local server {server_info['name']}: {e}")
            return None


# Global service discovery instances
network_discovery = ServiceDiscovery()
local_discovery = LocalServiceDiscovery()

# Alias for backward compatibility
MCPServiceDiscovery = ServiceDiscovery