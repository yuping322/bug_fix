"""Unit tests for MCP client implementations."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
import subprocess
import tempfile
import os

from src.mcp_integration.clients.external_mcp import ExternalMCPClient
from src.mcp_integration.clients.service_discovery import MCPServiceDiscovery


class TestExternalMCPClient:
    """Test external MCP client."""

    @pytest.fixture
    def client(self):
        """Create test MCP client."""
        return ExternalMCPClient()

    def test_initialization(self, client):
        """Test client initialization."""
        assert client.processes == {}
        assert client.connections == {}

    @patch('subprocess.Popen')
    @patch('asyncio.create_subprocess_exec')
    def test_start_mcp_server(self, mock_create_subprocess, mock_popen, client):
        """Test starting MCP server."""
        # Mock subprocess
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_process.poll.return_value = None
        mock_process.communicate = AsyncMock(return_value=(b"stdout", b"stderr"))
        mock_process.wait = AsyncMock(return_value=0)
        mock_create_subprocess.return_value = mock_process

        # Mock stdin/stdout
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        # Test starting server
        result = asyncio.run(client.start_mcp_server(
            "test-server",
            "python",
            ["-m", "mcp.server"],
            env={"TEST": "value"}
        ))

        assert result is True
        assert "test-server" in client.processes
        mock_create_subprocess.assert_called_once()

    @patch('asyncio.create_subprocess_exec')
    def test_start_mcp_server_failure(self, mock_create_subprocess, client):
        """Test starting MCP server failure."""
        mock_create_subprocess.side_effect = Exception("Process failed")

        result = asyncio.run(client.start_mcp_server(
            "test-server",
            "python",
            ["-m", "mcp.server"]
        ))

        assert result is False
        assert "test-server" not in client.processes

    def test_stop_mcp_server(self, client):
        """Test stopping MCP server."""
        # Mock process
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = AsyncMock(return_value=0)

        client.processes["test-server"] = mock_process

        # Test stopping server
        result = asyncio.run(client.stop_mcp_server("test-server"))

        assert result is True
        mock_process.terminate.assert_called_once()
        assert "test-server" not in client.processes

    def test_stop_mcp_server_not_found(self, client):
        """Test stopping non-existent MCP server."""
        result = asyncio.run(client.stop_mcp_server("non-existent"))

        assert result is False

    @patch('asyncio.open_connection')
    def test_connect_to_mcp_server(self, mock_open_connection, client):
        """Test connecting to MCP server."""
        # Mock connection
        mock_reader = Mock()
        mock_writer = Mock()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        # Test connection
        result = asyncio.run(client.connect_to_mcp_server(
            "test-server",
            "localhost",
            3000
        ))

        assert result is True
        assert "test-server" in client.connections
        mock_open_connection.assert_called_once_with("localhost", 3000)

    @patch('asyncio.open_connection')
    def test_connect_to_mcp_server_failure(self, mock_open_connection, client):
        """Test connecting to MCP server failure."""
        mock_open_connection.side_effect = Exception("Connection failed")

        result = asyncio.run(client.connect_to_mcp_server(
            "test-server",
            "localhost",
            3000
        ))

        assert result is False
        assert "test-server" not in client.connections

    def test_disconnect_from_mcp_server(self, client):
        """Test disconnecting from MCP server."""
        # Mock writer
        mock_writer = Mock()
        mock_writer.close = Mock()
        mock_writer.wait_closed = AsyncMock()

        client.connections["test-server"] = (Mock(), mock_writer)

        # Test disconnecting
        result = asyncio.run(client.disconnect_from_mcp_server("test-server"))

        assert result is True
        mock_writer.close.assert_called_once()
        assert "test-server" not in client.connections

    def test_disconnect_from_mcp_server_not_found(self, client):
        """Test disconnecting from non-existent server."""
        result = asyncio.run(client.disconnect_from_mcp_server("non-existent"))

        assert result is False

    def test_list_running_servers(self, client):
        """Test listing running servers."""
        # Add mock processes
        client.processes["server1"] = Mock(pid=123, poll=Mock(return_value=None))
        client.processes["server2"] = Mock(pid=456, poll=Mock(return_value=0))

        servers = client.list_running_servers()

        assert len(servers) == 2
        assert servers[0]["name"] == "server1"
        assert servers[0]["pid"] == 123
        assert servers[0]["running"] is True
        assert servers[1]["name"] == "server2"
        assert servers[1]["running"] is False

    def test_list_connected_servers(self, client):
        """Test listing connected servers."""
        # Add mock connections
        client.connections["server1"] = (Mock(), Mock())
        client.connections["server2"] = (Mock(), Mock())

        servers = client.list_connected_servers()

        assert len(servers) == 2
        assert "server1" in servers
        assert "server2" in servers

    @patch('asyncio.StreamWriter.drain')
    @patch('asyncio.StreamWriter.write')
    @patch('json.dumps')
    def test_send_message(self, mock_dumps, mock_write, mock_drain, client):
        """Test sending message to MCP server."""
        # Mock writer
        mock_writer = Mock()
        client.connections["test-server"] = (Mock(), mock_writer)

        # Mock json.dumps
        mock_dumps.return_value = '{"test": "message"}'

        # Test sending message
        result = asyncio.run(client.send_message("test-server", {"test": "message"}))

        assert result is True
        mock_dumps.assert_called_once_with({"test": "message"})
        mock_write.assert_called_once()
        mock_drain.assert_called_once()

    def test_send_message_no_connection(self, client):
        """Test sending message without connection."""
        result = asyncio.run(client.send_message("non-existent", {"test": "message"}))

        assert result is False

    @patch('json.loads')
    @patch('asyncio.StreamReader.readuntil')
    def test_receive_message(self, mock_readuntil, mock_loads, client):
        """Test receiving message from MCP server."""
        # Mock reader
        mock_reader = Mock()
        client.connections["test-server"] = (mock_reader, Mock())

        # Mock readuntil and json.loads
        mock_readuntil.return_value = b'{"test": "response"}\n'
        mock_loads.return_value = {"test": "response"}

        # Test receiving message
        result = asyncio.run(client.receive_message("test-server"))

        assert result == {"test": "response"}
        mock_readuntil.assert_called_once_with(mock_reader, b'\n')
        mock_loads.assert_called_once_with('{"test": "response"}')

    def test_receive_message_no_connection(self, client):
        """Test receiving message without connection."""
        result = asyncio.run(client.receive_message("non-existent"))

        assert result is None

    @patch('asyncio.wait_for')
    @patch.object(ExternalMCPClient, 'send_message', new_callable=AsyncMock)
    @patch.object(ExternalMCPClient, 'receive_message', new_callable=AsyncMock)
    def test_call_tool(self, mock_receive, mock_send, mock_wait_for, client):
        """Test calling tool on MCP server."""
        # Setup mocks
        mock_send.return_value = True
        mock_receive.return_value = {"result": "success"}
        mock_wait_for.return_value = {"result": "success"}

        # Test tool call
        result = asyncio.run(client.call_tool(
            "test-server",
            "test_tool",
            {"param": "value"}
        ))

        assert result == {"result": "success"}
        mock_send.assert_called_once()
        mock_receive.assert_called_once()

    @patch.object(ExternalMCPClient, 'send_message', new_callable=AsyncMock)
    def test_call_tool_send_failure(self, mock_send, client):
        """Test tool call with send failure."""
        mock_send.return_value = False

        result = asyncio.run(client.call_tool(
            "test-server",
            "test_tool",
            {"param": "value"}
        ))

        assert result is None


class TestMCPServiceDiscovery:
    """Test MCP service discovery."""

    @pytest.fixture
    def discovery(self):
        """Create test service discovery."""
        return MCPServiceDiscovery()

    def test_initialization(self, discovery):
        """Test discovery initialization."""
        assert discovery.services == {}
        assert discovery.scan_ports == [3000, 3001, 3002, 8080, 8081]

    @patch('socket.socket')
    def test_scan_network_services(self, mock_socket_class, discovery):
        """Test scanning network for MCP services."""
        # Mock socket
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        # Mock successful connection
        mock_socket.connect_ex.return_value = 0
        mock_socket.recv.return_value = b'MCP-SERVER-READY\n'

        # Test scanning
        services = asyncio.run(discovery.scan_network_services("192.168.1.0/24"))

        # Should find services on scanned ports
        assert len(services) > 0
        mock_socket.connect_ex.assert_called()

    @patch('os.path.exists')
    @patch('builtins.open')
    def test_discover_local_services(self, mock_open, mock_exists, discovery):
        """Test discovering local MCP services."""
        # Mock file exists
        mock_exists.return_value = True

        # Mock config file content
        mock_file = Mock()
        mock_file.read.return_value = """
        servers:
          - name: local-mcp
            command: python -m mcp.server
            port: 3000
            env:
              API_KEY: test
        """
        mock_open.return_value.__enter__.return_value = mock_file

        # Test discovery
        services = discovery.discover_local_services()

        assert len(services) == 1
        assert services[0]["name"] == "local-mcp"
        assert services[0]["port"] == 3000

    @patch('os.path.exists')
    def test_discover_local_services_no_config(self, mock_exists, discovery):
        """Test discovering local services without config file."""
        mock_exists.return_value = False

        services = discovery.discover_local_services()

        assert services == []

    def test_register_service(self, discovery):
        """Test registering MCP service."""
        service_info = {
            "name": "test-service",
            "host": "localhost",
            "port": 3000,
            "protocol": "mcp",
            "capabilities": ["tools", "resources"]
        }

        discovery.register_service(service_info)

        assert "test-service" in discovery.services
        assert discovery.services["test-service"] == service_info

    def test_unregister_service(self, discovery):
        """Test unregistering MCP service."""
        # Register service first
        discovery.register_service({
            "name": "test-service",
            "host": "localhost",
            "port": 3000
        })

        # Unregister
        discovery.unregister_service("test-service")

        assert "test-service" not in discovery.services

    def test_get_service_info(self, discovery):
        """Test getting service information."""
        service_info = {
            "name": "test-service",
            "host": "localhost",
            "port": 3000
        }

        discovery.register_service(service_info)

        result = discovery.get_service_info("test-service")

        assert result == service_info

    def test_get_service_info_not_found(self, discovery):
        """Test getting info for non-existent service."""
        result = discovery.get_service_info("non-existent")

        assert result is None

    def test_list_services(self, discovery):
        """Test listing all services."""
        # Register multiple services
        discovery.register_service({
            "name": "service1",
            "host": "localhost",
            "port": 3000
        })
        discovery.register_service({
            "name": "service2",
            "host": "localhost",
            "port": 3001
        })

        services = discovery.list_services()

        assert len(services) == 2
        service_names = [s["name"] for s in services]
        assert "service1" in service_names
        assert "service2" in service_names

    def test_filter_services_by_capability(self, discovery):
        """Test filtering services by capability."""
        # Register services with different capabilities
        discovery.register_service({
            "name": "chat-service",
            "capabilities": ["chat", "tools"]
        })
        discovery.register_service({
            "name": "tool-service",
            "capabilities": ["tools", "resources"]
        })

        # Filter by capability
        chat_services = discovery.filter_services_by_capability("chat")

        assert len(chat_services) == 1
        assert chat_services[0]["name"] == "chat-service"

    def test_get_services_by_protocol(self, discovery):
        """Test getting services by protocol."""
        # Register services with different protocols
        discovery.register_service({
            "name": "mcp-service",
            "protocol": "mcp"
        })
        discovery.register_service({
            "name": "http-service",
            "protocol": "http"
        })

        mcp_services = discovery.get_services_by_protocol("mcp")

        assert len(mcp_services) == 1
        assert mcp_services[0]["name"] == "mcp-service"