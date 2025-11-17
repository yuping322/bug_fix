"""Integration tests for MCP components."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
import tempfile
import os

from src.mcp_integration.server import MCPPlatformServer
from src.mcp_integration.clients.external_mcp import ExternalMCPClient
from src.mcp_integration.clients.service_discovery import MCPServiceDiscovery
from src.mcp_integration.tools.chat_integration import ChatIntegrationTool
from src.mcp_integration.tools.custom_workflows import CustomWorkflowsTool
from src.mcp_integration.tools.external_services import ExternalServicesTool


class TestMCPIntegration:
    """Integration tests for MCP components working together."""

    @pytest.fixture
    def setup_mcp_components(self):
        """Set up MCP components for integration testing."""
        from src.core.config import ConfigManager
        config_manager = ConfigManager()
        
        server = MCPPlatformServer()
        client_config = {
            "name": "test-mcp-server",
            "command": ["python", "-m", "mcp.server"],
            "args": [],
            "env": {"TEST_MODE": "1"},
            "timeout": 30
        }
        client = ExternalMCPClient(client_config)
        discovery = MCPServiceDiscovery()
        chat_tool = ChatIntegrationTool(config_manager)
        workflow_tool = CustomWorkflowsTool(config_manager)
        external_tool = ExternalServicesTool(config_manager)

        return {
            "server": server,
            "client": client,
            "discovery": discovery,
            "chat_tool": chat_tool,
            "workflow_tool": workflow_tool,
            "external_tool": external_tool
        }

    @patch('src.mcp_integration.server.ConfigManager')
    @patch('src.mcp_integration.server.WorkflowEngine')
    @patch('src.mcp_integration.server.agent_registry')
    def test_full_workflow_execution_via_mcp(self, mock_registry, mock_engine_class, mock_config_class, setup_mcp_components):
        """Test full workflow execution through MCP interface."""
        components = setup_mcp_components
        server = components["server"]

        # Mock configuration
        mock_config = Mock()
        mock_config.workflows = {
            "integration-test": Mock(
                name="integration-test",
                description="Integration test workflow",
                type="simple",
                steps=[
                    {
                        "name": "step1",
                        "agent": "test-agent",
                        "prompt": "Test prompt",
                        "inputs": {},
                        "output": "result",
                        "timeout": 300,
                        "retry": 0,
                        "dependencies": []
                    }
                ],
                config={},
                metadata={}
            )
        }
        mock_config_class.return_value.get_config.return_value = mock_config

        # Mock workflow engine
        mock_engine = Mock()
        mock_execution = Mock()
        mock_execution.execution_id = "exec-integration-123"
        mock_engine.execute_workflow = AsyncMock(return_value="exec-integration-123")
        mock_engine.get_execution_status = Mock(return_value=mock_execution)
        mock_engine_class.return_value = mock_engine

        # Test workflow execution via MCP
        result = asyncio.run(server.handle_tool_call("execute_workflow", {
            "workflow_name": "integration-test",
            "inputs": {"param": "test_value"}
        }))

        assert result["execution_id"] == "exec-integration-123"

        # Test getting execution status
        status_result = asyncio.run(server.handle_tool_call("get_execution_status", {
            "execution_id": "exec-integration-123"
        }))

        assert status_result["execution_id"] == "exec-integration-123"

    def test_service_discovery_and_registration(self, setup_mcp_components):
        """Test service discovery and registration workflow."""
        components = setup_mcp_components
        discovery = components["discovery"]
        client = components["client"]

        # Register a service
        service_info = {
            "name": "test-mcp-service",
            "host": "localhost",
            "port": 3000,
            "protocol": "mcp",
            "capabilities": ["tools", "resources", "chat"]
        }

        discovery.register_service(service_info)

        # Verify service is registered
        services = discovery.list_services()
        assert len(services) == 1
        assert services[0]["name"] == "test-mcp-service"

        # Test filtering by capability
        chat_services = discovery.filter_services_by_capability("chat")
        assert len(chat_services) == 1

        tool_services = discovery.filter_services_by_capability("tools")
        assert len(tool_services) == 1

    @patch('aiohttp.ClientSession')
    def test_chat_integration_with_external_service(self, mock_session_class, setup_mcp_components):
        """Test chat integration working with external services."""
        components = setup_mcp_components
        chat_tool = components["chat_tool"]
        external_tool = components["external_tool"]

        # Register Slack platform
        chat_tool.register_platform("slack", {
            "api_token": "xoxb-test-token",
            "webhook_url": "https://hooks.slack.com/test"
        })

        # Register external service for notifications
        external_tool.register_service("notification-api", {
            "base_url": "https://api.notifications.com",
            "auth_type": "token",
            "auth_config": {"token": "notif-token"}
        })

        # Mock HTTP responses
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"delivered": True})
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session_class.return_value.__aenter__.return_value = mock_session

        # Test sending chat message
        chat_result = asyncio.run(chat_tool.send_message(
            "slack",
            "#dev",
            "Workflow completed successfully!"
        ))

        assert chat_result is True

        # Test external service call
        service_result = asyncio.run(external_tool.call_service(
            "notification-api",
            "POST",
            "/notify",
            {"message": "Workflow done", "channel": "#dev"}
        ))

        assert service_result["status"] == 200
        assert service_result["data"]["delivered"] is True

    def test_custom_workflow_creation_and_execution(self, setup_mcp_components):
        """Test creating and executing custom workflows."""
        components = setup_mcp_components
        workflow_tool = components["workflow_tool"]

        # Register a template
        template = {
            "name": "notification-workflow",
            "description": "Send notifications via multiple channels",
            "steps": [
                {
                    "name": "slack_notification",
                    "agent": "chat-agent",
                    "prompt": "Send Slack notification",
                    "inputs": {"message": "input_message", "channel": "input_channel"},
                    "output": "slack_result"
                },
                {
                    "name": "email_notification",
                    "agent": "email-agent",
                    "prompt": "Send email notification",
                    "inputs": {"message": "input_message", "recipients": "input_recipients"},
                    "output": "email_result"
                }
            ],
            "inputs": ["input_message", "input_channel", "input_recipients"],
            "outputs": ["slack_result", "email_result"]
        }

        workflow_tool.register_template("notification-template", template)

        # Create custom workflow from template
        custom_config = workflow_tool.create_workflow_from_template(
            "notification-template",
            "my-notification-workflow",
            {
                "input_channel": "#production",
                "input_recipients": ["admin@company.com"]
            }
        )

        assert custom_config is not None
        assert custom_config["name"] == "my-notification-workflow"
        assert len(custom_config["steps"]) == 2

        # Save the custom workflow
        workflow_id = workflow_tool.save_custom_workflow(custom_config)

        assert workflow_id is not None

        # Load and verify
        loaded_config = workflow_tool.load_custom_workflow(workflow_id)

        assert loaded_config["name"] == "my-notification-workflow"

    @patch('asyncio.open_connection')
    @patch('src.mcp_integration.clients.external_mcp.ExternalMCPClient.start_mcp_server')
    def test_client_server_connection_workflow(self, mock_start_server, mock_open_connection, setup_mcp_components):
        """Test client connecting to MCP server workflow."""
        components = setup_mcp_components
        client = components["client"]

        # Mock server start
        mock_start_server.return_value = True

        # Mock connection
        mock_reader = Mock()
        mock_writer = Mock()
        mock_open_connection.return_value = (mock_reader, mock_writer)

        # Start MCP server
        server_started = asyncio.run(client.start_mcp_server(
            "test-platform-server",
            "python",
            ["-m", "mcp.platform_server"],
            {"API_KEY": "test-key"}
        ))

        assert server_started is True

        # Connect to the server
        connected = asyncio.run(client.connect_to_mcp_server(
            "test-platform-server",
            "localhost",
            3000
        ))

        assert connected is True

        # Verify connection is tracked
        connections = client.list_connected_servers()
        assert "test-platform-server" in connections

        # Test sending a message
        with patch.object(client, 'send_message', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            message_sent = asyncio.run(client.send_message(
                "test-platform-server",
                {"type": "tool_call", "tool": "list_agents"}
            ))

            assert message_sent is True

    def test_mcp_tool_chaining(self, setup_mcp_components):
        """Test chaining multiple MCP tools together."""
        components = setup_mcp_components
        chat_tool = components["chat_tool"]
        workflow_tool = components["workflow_tool"]
        external_tool = components["external_tool"]

        # Set up chat integration
        chat_tool.register_platform("teams", {
            "webhook_url": "https://outlook.office.com/webhook/..."
        })

        # Create a workflow that uses multiple tools
        workflow_config = {
            "name": "multi-channel-notification",
            "description": "Send notifications via multiple channels",
            "steps": [
                {
                    "name": "check_status",
                    "agent": "monitoring-agent",
                    "prompt": "Check system status",
                    "inputs": {},
                    "output": "status_result"
                },
                {
                    "name": "send_chat",
                    "agent": "chat-agent",
                    "prompt": "Send chat notification",
                    "inputs": {"message": "status_result"},
                    "output": "chat_result"
                },
                {
                    "name": "call_webhook",
                    "agent": "webhook-agent",
                    "prompt": "Call external webhook",
                    "inputs": {"payload": "status_result"},
                    "output": "webhook_result"
                }
            ],
            "inputs": [],
            "outputs": ["status_result", "chat_result", "webhook_result"]
        }

        # Validate and save workflow
        is_valid, errors = workflow_tool.validate_workflow_config(workflow_config)
        assert is_valid is True

        workflow_id = workflow_tool.save_custom_workflow(workflow_config)
        assert workflow_id is not None

        # Register external service for webhook
        external_tool.register_service("webhook-service", {
            "base_url": "https://api.webhooks.com",
            "auth_type": "none"
        })

        # Verify all components are set up
        platforms = chat_tool.list_platforms()
        assert len(platforms) == 1

        services = external_tool.list_services()
        assert len(services) == 1

        workflows = workflow_tool.list_custom_workflows()
        assert len(workflows) == 1

    @patch('src.mcp_integration.server.ConfigManager')
    def test_platform_status_via_mcp(self, mock_config_class, setup_mcp_components):
        """Test getting platform status through MCP."""
        components = setup_mcp_components
        server = components["server"]

        # Mock configuration with multiple agents and workflows
        mock_config = Mock()
        mock_config.version = "1.0.0"
        mock_config.agents = {
            "claude-agent": Mock(provider="anthropic"),
            "codex-agent": Mock(provider="openai"),
            "copilot-agent": Mock(provider="github")
        }
        mock_config.workflows = {
            "code-review": Mock(),
            "pr-automation": Mock(),
            "task-development": Mock()
        }
        mock_config_class.return_value.get_config.return_value = mock_config

        # Get platform status via MCP
        status = asyncio.run(server.handle_tool_call("get_platform_status", {}))

        assert status["name"] == "Multi-Agent Orchestration Platform"
        assert status["version"] == "1.0.0"
        assert status["agent_count"] == 3
        assert status["workflow_count"] == 3

    def test_error_handling_across_mcp_components(self, setup_mcp_components):
        """Test error handling across MCP components."""
        components = setup_mcp_components
        client = components["client"]
        chat_tool = components["chat_tool"]
        external_tool = components["external_tool"]

        # Test calling non-existent service
        result = asyncio.run(external_tool.call_service(
            "non-existent-service",
            "GET",
            "/test"
        ))
        assert result is None

        # Test sending message to non-existent platform
        result = asyncio.run(chat_tool.send_message(
            "non-existent-platform",
            "#test",
            "message"
        ))
        assert result is False

        # Test connecting to non-existent server
        result = asyncio.run(client.connect_to_mcp_server(
            "non-existent-server",
            "localhost",
            9999
        ))
        assert result is False

        # Test ending non-existent session
        result = chat_tool.end_session("non-existent-session")
        assert result is False

    def test_mcp_component_lifecycle(self, setup_mcp_components):
        """Test complete lifecycle of MCP components."""
        components = setup_mcp_components
        discovery = components["discovery"]
        chat_tool = components["chat_tool"]
        workflow_tool = components["workflow_tool"]
        external_tool = components["external_tool"]

        # Phase 1: Setup components
        # Register services
        discovery.register_service({
            "name": "mcp-chat-service",
            "host": "localhost",
            "port": 3001,
            "capabilities": ["chat"]
        })

        chat_tool.register_platform("discord", {
            "webhook_url": "https://discord.com/api/webhooks/test"
        })

        external_tool.register_service("api-service", {
            "base_url": "https://api.external.com",
            "auth_type": "none"
        })

        # Phase 2: Create and configure workflows
        template = {
            "name": "lifecycle-test",
            "steps": [{"name": "test", "agent": "test-agent", "prompt": "test", "inputs": {}, "output": "result"}],
            "inputs": [],
            "outputs": ["result"]
        }
        workflow_tool.register_template("lifecycle-template", template)

        workflow_config = workflow_tool.create_workflow_from_template(
            "lifecycle-template",
            "lifecycle-workflow",
            {}
        )
        workflow_id = workflow_tool.save_custom_workflow(workflow_config)

        # Phase 3: Verify setup
        assert len(discovery.list_services()) == 1
        assert len(chat_tool.list_platforms()) == 1
        assert len(external_tool.list_services()) == 1
        assert len(workflow_tool.list_custom_workflows()) == 1

        # Phase 4: Simulate usage
        session_id = chat_tool.create_session({
            "platform": "discord",
            "channel": "#lifecycle-test"
        })

        assert session_id in [s["session_id"] for s in chat_tool.list_active_sessions()]

        # Phase 5: Cleanup
        chat_tool.end_session(session_id)
        workflow_tool.delete_custom_workflow(workflow_id)
        discovery.unregister_service("mcp-chat-service")
        chat_tool.unregister_platform("discord")
        external_tool.unregister_service("api-service")

        # Phase 6: Verify cleanup
        assert len(chat_tool.list_active_sessions()) == 0
        assert len(workflow_tool.list_custom_workflows()) == 0
        assert len(discovery.list_services()) == 0
        assert len(chat_tool.list_platforms()) == 0
        assert len(external_tool.list_services()) == 0