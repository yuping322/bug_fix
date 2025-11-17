"""Unit tests for MCP tools."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

from src.mcp_integration.tools.chat_integration import ChatIntegrationTool
from src.mcp_integration.tools.custom_workflows import CustomWorkflowsTool
from src.mcp_integration.tools.external_services import ExternalServicesTool


class TestChatIntegrationTool:
    """Test chat integration tool."""

    @pytest.fixture
    def config_manager(self):
        """Create mock config manager."""
        return Mock()

    @pytest.fixture
    def tool(self, config_manager):
        """Create test chat integration tool."""
        return ChatIntegrationTool(config_manager)

    def test_initialization(self, tool):
        """Test tool initialization."""
        assert tool.platforms == {}
        assert tool.active_sessions == {}

    def test_register_platform(self, tool):
        """Test registering chat platform."""
        config = {
            "name": "slack",
            "api_token": "xoxb-token",
            "webhook_url": "https://hooks.slack.com/...",
            "channels": ["#general", "#dev"]
        }

        tool.register_platform("slack", config)

        assert "slack" in tool.platforms
        assert tool.platforms["slack"] == config

    def test_unregister_platform(self, tool):
        """Test unregistering chat platform."""
        # Register first
        tool.register_platform("slack", {"api_token": "token"})

        # Unregister
        tool.unregister_platform("slack")

        assert "slack" not in tool.platforms

    def test_create_session(self, tool):
        """Test creating chat session."""
        session_config = {
            "platform": "slack",
            "channel": "#general",
            "workflow_id": "workflow-123",
            "auto_respond": True
        }

        session_id = tool.create_session(session_config)

        assert session_id in tool.active_sessions
        assert tool.active_sessions[session_id]["platform"] == "slack"
        assert tool.active_sessions[session_id]["channel"] == "#general"

    def test_end_session(self, tool):
        """Test ending chat session."""
        # Create session first
        session_id = tool.create_session({
            "platform": "slack",
            "channel": "#general"
        })

        # End session
        result = tool.end_session(session_id)

        assert result is True
        assert session_id not in tool.active_sessions

    def test_end_session_not_found(self, tool):
        """Test ending non-existent session."""
        result = tool.end_session("non-existent")

        assert result is False

    @patch('aiohttp.ClientSession')
    def test_send_message_slack(self, mock_session_class, tool):
        """Test sending message to Slack."""
        # Register Slack platform
        tool.register_platform("slack", {
            "api_token": "xoxb-token",
            "webhook_url": "https://hooks.slack.com/..."
        })

        # Mock aiohttp session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status = 200
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session_class.return_value.__aenter__.return_value = mock_session

        # Test sending message
        result = asyncio.run(tool.send_message(
            "slack",
            "#general",
            "Hello from MCP!"
        ))

        assert result is True
        mock_session.post.assert_called_once()

    @patch('aiohttp.ClientSession')
    def test_send_message_discord(self, mock_session_class, tool):
        """Test sending message to Discord."""
        # Register Discord platform
        tool.register_platform("discord", {
            "webhook_url": "https://discord.com/api/webhooks/..."
        })

        # Mock aiohttp session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status = 204
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session_class.return_value.__aenter__.return_value = mock_session

        # Test sending message
        result = asyncio.run(tool.send_message(
            "discord",
            "#general",
            "Hello from MCP!"
        ))

        assert result is True
        mock_session.post.assert_called_once()

    @patch('aiohttp.ClientSession')
    def test_send_message_unsupported_platform(self, mock_session_class, tool):
        """Test sending message to unsupported platform."""
        result = asyncio.run(tool.send_message(
            "unsupported",
            "#general",
            "Hello!"
        ))

        assert result is False

    def test_list_platforms(self, tool):
        """Test listing registered platforms."""
        # Register platforms
        tool.register_platform("slack", {"api_token": "token"})
        tool.register_platform("discord", {"webhook_url": "url"})

        platforms = tool.list_platforms()

        assert len(platforms) == 2
        platform_names = [p["name"] for p in platforms]
        assert "slack" in platform_names
        assert "discord" in platform_names

    def test_list_active_sessions(self, tool):
        """Test listing active sessions."""
        # Create sessions
        session1 = tool.create_session({"platform": "slack", "channel": "#dev"})
        session2 = tool.create_session({"platform": "discord", "channel": "#general"})

        sessions = tool.list_active_sessions()

        assert len(sessions) == 2
        session_ids = [s["session_id"] for s in sessions]
        assert session1 in session_ids
        assert session2 in session_ids

    def test_get_session_info(self, tool):
        """Test getting session information."""
        session_id = tool.create_session({
            "platform": "slack",
            "channel": "#general",
            "workflow_id": "workflow-123"
        })

        info = tool.get_session_info(session_id)

        assert info is not None
        assert info["platform"] == "slack"
        assert info["channel"] == "#general"
        assert info["workflow_id"] == "workflow-123"

    def test_get_session_info_not_found(self, tool):
        """Test getting info for non-existent session."""
        info = tool.get_session_info("non-existent")

        assert info is None


class TestCustomWorkflowsTool:
    """Test custom workflows tool."""

    @pytest.fixture
    def config_manager(self):
        """Create mock config manager."""
        return Mock()

    @pytest.fixture
    def tool(self, config_manager):
        """Create test custom workflows tool."""
        return CustomWorkflowsTool(config_manager)

    def test_initialization(self, tool):
        """Test tool initialization."""
        assert tool.templates == {}
        assert tool.custom_workflows == {}

    def test_register_template(self, tool):
        """Test registering workflow template."""
        template = {
            "name": "code-review",
            "description": "Automated code review workflow",
            "steps": [
                {
                    "name": "analyze",
                    "agent": "claude-agent",
                    "prompt": "Analyze this code",
                    "inputs": ["code"],
                    "output": "analysis"
                }
            ],
            "inputs": ["code", "language"],
            "outputs": ["analysis", "recommendations"]
        }

        tool.register_template("code-review", template)

        assert "code-review" in tool.templates
        assert tool.templates["code-review"] == template

    def test_unregister_template(self, tool):
        """Test unregistering workflow template."""
        # Register first
        tool.register_template("test-template", {"name": "test"})

        # Unregister
        tool.unregister_template("test-template")

        assert "test-template" not in tool.templates

    def test_list_templates(self, tool):
        """Test listing workflow templates."""
        # Register templates
        tool.register_template("template1", {"name": "Template 1"})
        tool.register_template("template2", {"name": "Template 2"})

        templates = tool.list_templates()

        assert len(templates) == 2
        template_names = [t["name"] for t in templates]
        assert "template1" in template_names
        assert "template2" in template_names

    def test_create_workflow_from_template(self, tool):
        """Test creating workflow from template."""
        # Register template
        template = {
            "name": "test-workflow",
            "description": "Test workflow",
            "steps": [
                {
                    "name": "step1",
                    "agent": "test-agent",
                    "prompt": "Test prompt",
                    "inputs": ["input1"],
                    "output": "output1"
                }
            ],
            "inputs": ["input1"],
            "outputs": ["output1"]
        }
        tool.register_template("test-template", template)

        # Create workflow
        workflow_config = tool.create_workflow_from_template(
            "test-template",
            "my-workflow",
            {"input1": "custom_value"}
        )

        assert workflow_config is not None
        assert workflow_config["name"] == "my-workflow"
        assert len(workflow_config["steps"]) == 1
        assert workflow_config["steps"][0]["inputs"]["input1"] == "custom_value"

    def test_create_workflow_from_template_not_found(self, tool):
        """Test creating workflow from non-existent template."""
        workflow_config = tool.create_workflow_from_template(
            "non-existent",
            "my-workflow",
            {}
        )

        assert workflow_config is None

    def test_validate_workflow_config(self, tool):
        """Test validating workflow configuration."""
        valid_config = {
            "name": "test-workflow",
            "description": "Test workflow",
            "steps": [
                {
                    "name": "step1",
                    "agent": "test-agent",
                    "prompt": "Test prompt",
                    "inputs": {},
                    "output": "result"
                }
            ],
            "inputs": [],
            "outputs": ["result"]
        }

        is_valid, errors = tool.validate_workflow_config(valid_config)

        assert is_valid is True
        assert errors == []

    def test_validate_workflow_config_invalid(self, tool):
        """Test validating invalid workflow configuration."""
        invalid_config = {
            "name": "",  # Invalid: empty name
            "steps": []  # Invalid: no steps
        }

        is_valid, errors = tool.validate_workflow_config(invalid_config)

        assert is_valid is False
        assert len(errors) > 0

    def test_save_custom_workflow(self, tool):
        """Test saving custom workflow."""
        workflow_config = {
            "name": "custom-workflow",
            "description": "Custom workflow",
            "steps": [
                {
                    "name": "step1",
                    "agent": "test-agent",
                    "prompt": "Test",
                    "inputs": {},
                    "output": "result"
                }
            ],
            "inputs": [],
            "outputs": ["result"]
        }

        workflow_id = tool.save_custom_workflow(workflow_config)

        assert workflow_id is not None
        assert workflow_id in tool.custom_workflows
        assert tool.custom_workflows[workflow_id] == workflow_config

    def test_save_custom_workflow_invalid(self, tool):
        """Test saving invalid custom workflow."""
        invalid_config = {"name": ""}

        workflow_id = tool.save_custom_workflow(invalid_config)

        assert workflow_id is None

    def test_load_custom_workflow(self, tool):
        """Test loading custom workflow."""
        # Save workflow first
        config = {"name": "test", "steps": []}
        workflow_id = tool.save_custom_workflow(config)

        # Load workflow
        loaded_config = tool.load_custom_workflow(workflow_id)

        assert loaded_config == config

    def test_load_custom_workflow_not_found(self, tool):
        """Test loading non-existent custom workflow."""
        loaded_config = tool.load_custom_workflow("non-existent")

        assert loaded_config is None

    def test_list_custom_workflows(self, tool):
        """Test listing custom workflows."""
        # Save workflows
        config1 = {"name": "workflow1", "steps": []}
        config2 = {"name": "workflow2", "steps": []}
        tool.save_custom_workflow(config1)
        tool.save_custom_workflow(config2)

        workflows = tool.list_custom_workflows()

        assert len(workflows) == 2

    def test_delete_custom_workflow(self, tool):
        """Test deleting custom workflow."""
        # Save workflow first
        config = {"name": "test", "steps": []}
        workflow_id = tool.save_custom_workflow(config)

        # Delete workflow
        result = tool.delete_custom_workflow(workflow_id)

        assert result is True
        assert workflow_id not in tool.custom_workflows

    def test_delete_custom_workflow_not_found(self, tool):
        """Test deleting non-existent custom workflow."""
        result = tool.delete_custom_workflow("non-existent")

        assert result is False


class TestExternalServicesTool:
    """Test external services tool."""

    @pytest.fixture
    def config_manager(self):
        """Create mock config manager."""
        return Mock()

    @pytest.fixture
    def tool(self, config_manager):
        """Create test external services tool."""
        return ExternalServicesTool(config_manager)

    def test_initialization(self, tool):
        """Test tool initialization."""
        assert tool.services == {}
        assert tool.call_history == []

    def test_register_service(self, tool):
        """Test registering external service."""
        service_config = {
            "name": "github-api",
            "base_url": "https://api.github.com",
            "auth_type": "token",
            "auth_config": {"token": "ghp_token"},
            "headers": {"Accept": "application/vnd.github.v3+json"},
            "timeout": 30
        }

        tool.register_service("github-api", service_config)

        assert "github-api" in tool.services
        assert tool.services["github-api"] == service_config

    def test_unregister_service(self, tool):
        """Test unregistering external service."""
        # Register first
        tool.register_service("test-service", {"base_url": "http://test.com"})

        # Unregister
        tool.unregister_service("test-service")

        assert "test-service" not in tool.services

    @patch('aiohttp.ClientSession')
    def test_call_service_get(self, mock_session_class, tool):
        """Test calling external service with GET request."""
        # Register service
        tool.register_service("test-api", {
            "base_url": "http://api.test.com",
            "auth_type": "none"
        })

        # Mock aiohttp session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"result": "success"})
        mock_response.text = AsyncMock(return_value='{"result": "success"}')
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session_class.return_value.__aenter__.return_value = mock_session

        # Test service call
        result = asyncio.run(tool.call_service(
            "test-api",
            "GET",
            "/users",
            None,
            {"param": "value"}
        ))

        assert result["status"] == 200
        assert result["data"] == {"result": "success"}
        assert len(tool.call_history) == 1

    @patch('aiohttp.ClientSession')
    def test_call_service_post(self, mock_session_class, tool):
        """Test calling external service with POST request."""
        # Register service
        tool.register_service("test-api", {
            "base_url": "http://api.test.com",
            "auth_type": "none"
        })

        # Mock aiohttp session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value={"id": 123})
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session_class.return_value.__aenter__.return_value = mock_session

        # Test service call
        result = asyncio.run(tool.call_service(
            "test-api",
            "POST",
            "/users",
            {"name": "test"},
            None
        ))

        assert result["status"] == 201
        assert result["data"] == {"id": 123}
        mock_session.post.assert_called_once()

    @patch('aiohttp.ClientSession')
    def test_call_service_with_auth_token(self, mock_session_class, tool):
        """Test calling service with token authentication."""
        # Register service with token auth
        tool.register_service("github-api", {
            "base_url": "https://api.github.com",
            "auth_type": "token",
            "auth_config": {"token": "ghp_token"}
        })

        # Mock aiohttp session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"user": "test"})
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session_class.return_value.__aenter__.return_value = mock_session

        # Test service call
        result = asyncio.run(tool.call_service(
            "github-api",
            "GET",
            "/user"
        ))

        assert result["status"] == 200
        # Check that Authorization header was added
        call_args = mock_session.get.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "token ghp_token"

    def test_call_service_not_found(self, tool):
        """Test calling non-existent service."""
        result = asyncio.run(tool.call_service(
            "non-existent",
            "GET",
            "/test"
        ))

        assert result is None

    def test_list_services(self, tool):
        """Test listing registered services."""
        # Register services
        tool.register_service("service1", {"base_url": "http://test1.com"})
        tool.register_service("service2", {"base_url": "http://test2.com"})

        services = tool.list_services()

        assert len(services) == 2
        service_names = [s["name"] for s in services]
        assert "service1" in service_names
        assert "service2" in service_names

    def test_get_call_history(self, tool):
        """Test getting call history."""
        # Add some history entries
        tool.call_history = [
            {
                "service": "api1",
                "method": "GET",
                "endpoint": "/test",
                "status": 200,
                "timestamp": 1234567890
            },
            {
                "service": "api2",
                "method": "POST",
                "endpoint": "/create",
                "status": 201,
                "timestamp": 1234567891
            }
        ]

        history = tool.get_call_history()

        assert len(history) == 2
        assert history[0]["service"] == "api1"
        assert history[1]["service"] == "api2"

    def test_get_call_history_filtered(self, tool):
        """Test getting filtered call history."""
        # Add history entries
        tool.call_history = [
            {"service": "api1", "method": "GET", "status": 200},
            {"service": "api2", "method": "POST", "status": 201},
            {"service": "api1", "method": "PUT", "status": 204}
        ]

        # Filter by service
        history = tool.get_call_history(service="api1")

        assert len(history) == 2
        assert all(h["service"] == "api1" for h in history)

    def test_clear_call_history(self, tool):
        """Test clearing call history."""
        # Add history
        tool.call_history = [{"service": "test"}]

        # Clear history
        tool.clear_call_history()

        assert tool.call_history == []

    @patch('aiohttp.ClientSession')
    def test_health_check_service(self, mock_session_class, tool):
        """Test health check for service."""
        # Register service
        tool.register_service("test-api", {
            "base_url": "http://api.test.com",
            "health_endpoint": "/health",
            "auth_type": "none"
        })

        # Mock aiohttp session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status = 200
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session_class.return_value.__aenter__.return_value = mock_session

        # Test health check
        is_healthy = asyncio.run(tool.health_check_service("test-api"))

        assert is_healthy is True
        mock_session.get.assert_called_once_with("http://api.test.com/health")

    @patch('aiohttp.ClientSession')
    def test_health_check_service_failure(self, mock_session_class, tool):
        """Test health check failure."""
        # Register service
        tool.register_service("test-api", {
            "base_url": "http://api.test.com",
            "auth_type": "none"
        })

        # Mock aiohttp session with failure
        mock_session = Mock()
        mock_session.get = AsyncMock(side_effect=Exception("Connection failed"))
        mock_session_class.return_value.__aenter__.return_value = mock_session

        # Test health check
        is_healthy = asyncio.run(tool.health_check_service("test-api"))

        assert is_healthy is False

    def test_health_check_service_not_found(self, tool):
        """Test health check for non-existent service."""
        is_healthy = asyncio.run(tool.health_check_service("non-existent"))

        assert is_healthy is False