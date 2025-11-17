"""Unit tests for MCP server implementation."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

from src.mcp_integration.server import MCPPlatformServer


class TestMCPPlatformServer:
    """Test MCP platform server."""

    @pytest.fixture
    def server(self):
        """Create test MCP server."""
        return MCPPlatformServer()

    def test_initialization(self, server):
        """Test server initialization."""
        assert server.server is not None
        assert len(server.tools) > 0
        assert "list_agents" in server.tools
        assert "execute_workflow" in server.tools

    @patch('src.mcp_integration.server.ConfigManager')
    @patch('src.mcp_integration.server.agent_registry')
    def test_list_agents_tool(self, mock_registry, mock_config_class, server):
        """Test list_agents tool."""
        # Mock config
        mock_config = Mock()
        mock_config.agents = {
            "claude-agent": Mock(provider="anthropic", model="claude-3", enabled=True),
            "codex-agent": Mock(provider="openai", model="gpt-4", enabled=False)
        }
        mock_config_class.return_value.get_config.return_value = mock_config

        # Mock agent registry
        mock_agent = Mock()
        mock_agent.health_check = AsyncMock(return_value=True)
        mock_registry.get_agent.return_value = mock_agent

        # Test the tool
        result = asyncio.run(server._handle_list_agents({}))

        assert "agents" in result
        assert len(result["agents"]) == 2
        assert result["agents"][0]["name"] == "claude-agent"
        assert result["agents"][0]["type"] == "anthropic"
        assert result["agents"][1]["name"] == "codex-agent"
        assert result["agents"][1]["enabled"] is False

    @patch('src.mcp_integration.server.ConfigManager')
    def test_get_agent_info_tool(self, mock_config_class, server):
        """Test get_agent_info tool."""
        # Mock config
        mock_config = Mock()
        mock_config.agents = {
            "claude-agent": Mock(
                provider="anthropic",
                model="claude-3",
                max_tokens=4096,
                temperature=0.7,
                timeout_seconds=60,
                enabled=True
            )
        }
        mock_config_class.return_value.get_config.return_value = mock_config

        with patch('src.mcp_integration.server.agent_registry') as mock_registry:
            mock_agent = Mock()
            mock_agent.health_check = AsyncMock(return_value=True)
            mock_agent.capabilities = ["chat", "code_generation"]
            mock_registry.get_agent.return_value = mock_agent

            # Test the tool
            result = asyncio.run(server._handle_get_agent_info({"agent_name": "claude-agent"}))

            assert result["name"] == "claude-agent"
            assert result["type"] == "anthropic"
            assert result["model"] == "claude-3"
            assert result["healthy"] is True
            assert "chat" in result["capabilities"]

    @patch('src.mcp_integration.server.ConfigManager')
    def test_list_workflows_tool(self, mock_config_class, server):
        """Test list_workflows tool."""
        # Mock config
        mock_config = Mock()
        mock_config.workflows = {
            "code-review": Mock(
                name="code-review",
                type="simple",
                description="Code review workflow",
                enabled=True,
                agents=["claude-agent"],
                steps=[{"name": "analyze"}, {"name": "review"}]
            )
        }
        mock_config_class.return_value.get_config.return_value = mock_config

        # Test the tool
        result = asyncio.run(server._handle_list_workflows({}))

        assert "workflows" in result
        assert len(result["workflows"]) == 1
        assert result["workflows"][0]["name"] == "code-review"
        assert result["workflows"][0]["step_count"] == 2

    @patch('src.mcp_integration.server.ConfigManager')
    @patch('src.mcp_integration.server.WorkflowEngine')
    @patch('src.mcp_integration.server.agent_registry')
    def test_execute_workflow_tool(self, mock_registry, mock_engine_class, mock_config_class, server):
        """Test execute_workflow tool."""
        # Mock config
        mock_config = Mock()
        mock_config.workflows = {
            "test-workflow": Mock(
                name="test-workflow",
                description="Test workflow",
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
        mock_engine.execute_workflow = AsyncMock(return_value="exec-123")
        mock_engine_class.return_value = mock_engine

        # Test the tool
        result = asyncio.run(server._handle_execute_workflow({
            "workflow_name": "test-workflow",
            "inputs": {"param": "value"}
        }))

        assert result["execution_id"] == "exec-123"
        assert result["workflow_name"] == "test-workflow"
        mock_engine.execute_workflow.assert_called_once()

    @patch('src.mcp_integration.server.ConfigManager')
    @patch('src.mcp_integration.server.WorkflowEngine')
    @patch('src.mcp_integration.server.agent_registry')
    def test_get_execution_status_tool(self, mock_registry, mock_engine_class, mock_config_class, server):
        """Test get_execution_status tool."""
        # Mock execution context
        mock_execution = Mock()
        mock_execution.execution_id = "exec-123"
        mock_execution.workflow_id = "workflow-1"
        mock_execution.status.value = "completed"
        mock_execution.step_results = {"result": "success"}
        mock_execution.errors = []
        mock_execution.start_time = 1234567890.0
        mock_execution.end_time = 1234567900.0
        mock_execution.duration = 10.0

        # Mock workflow engine
        mock_engine = Mock()
        mock_engine.get_execution_status.return_value = mock_execution
        mock_engine_class.return_value = mock_engine

        # Test the tool
        result = asyncio.run(server._handle_get_execution_status({"execution_id": "exec-123"}))

        assert result["execution_id"] == "exec-123"
        assert result["status"] == "completed"
        assert result["results"]["result"] == "success"
        assert result["duration"] == 10.0

    def test_get_execution_status_not_found(self, server):
        """Test get_execution_status for non-existent execution."""
        with patch('src.mcp_integration.server.ConfigManager'), \
             patch('src.mcp_integration.server.WorkflowEngine') as mock_engine_class, \
             patch('src.mcp_integration.server.agent_registry'):

            mock_engine = Mock()
            mock_engine.get_execution_status.return_value = None
            mock_engine_class.return_value = mock_engine

            result = asyncio.run(server._handle_get_execution_status({"execution_id": "non-existent"}))

            assert "error" in result
            assert "not found" in result["error"]

    @patch('src.mcp_integration.server.ConfigManager')
    @patch('src.mcp_integration.server.WorkflowEngine')
    @patch('src.mcp_integration.server.agent_registry')
    def test_list_executions_tool(self, mock_registry, mock_engine_class, mock_config_class, server):
        """Test list_executions tool."""
        # Mock executions
        mock_executions = [
            Mock(
                execution_id="exec-1",
                workflow_id="workflow-1",
                status=Mock(value="completed"),
                start_time=1234567890.0,
                end_time=1234567900.0,
                duration=10.0
            ),
            Mock(
                execution_id="exec-2",
                workflow_id="workflow-2",
                status=Mock(value="running"),
                start_time=1234567890.0,
                end_time=None,
                duration=None
            )
        ]

        # Mock workflow engine
        mock_engine = Mock()
        mock_engine.list_executions.return_value = mock_executions
        mock_engine_class.return_value = mock_engine

        # Test the tool
        result = asyncio.run(server._handle_list_executions({}))

        assert "executions" in result
        assert len(result["executions"]) == 2
        assert result["executions"][0]["execution_id"] == "exec-1"
        assert result["executions"][0]["status"] == "completed"
        assert result["executions"][1]["execution_id"] == "exec-2"
        assert result["executions"][1]["status"] == "running"

    @patch('src.mcp_integration.server.ConfigManager')
    @patch('src.mcp_integration.server.WorkflowEngine')
    @patch('src.mcp_integration.server.agent_registry')
    def test_cancel_execution_tool(self, mock_registry, mock_engine_class, mock_config_class, server):
        """Test cancel_execution tool."""
        # Mock workflow engine
        mock_engine = Mock()
        mock_engine.cancel_execution.return_value = True
        mock_engine_class.return_value = mock_engine

        # Test the tool
        result = asyncio.run(server._handle_cancel_execution({"execution_id": "exec-123"}))

        assert result["cancelled"] is True
        assert result["execution_id"] == "exec-123"
        mock_engine.cancel_execution.assert_called_once_with("exec-123")

    @patch('src.mcp_integration.server.ConfigManager')
    def test_validate_config_tool(self, mock_config_class, server):
        """Test validate_config tool."""
        # Mock config manager with validation
        mock_config_manager = Mock()
        mock_config_manager.validate_config.return_value = ["Invalid agent config"]
        mock_config_class.return_value = mock_config_manager

        # Test the tool
        result = asyncio.run(server._handle_validate_config({
            "config": {"agents": {"invalid": "config"}}
        }))

        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "Invalid agent config" in result["errors"][0]

    @patch('src.mcp_integration.server.ConfigManager')
    def test_get_platform_status_tool(self, mock_config_class, server):
        """Test get_platform_status tool."""
        # Mock config
        mock_config = Mock()
        mock_config.version = "1.0.0"
        mock_config.agents = {"agent1": Mock(), "agent2": Mock()}
        mock_config.workflows = {"workflow1": Mock()}
        mock_config_class.return_value.get_config.return_value = mock_config

        # Test the tool
        result = asyncio.run(server._handle_get_platform_status({}))

        assert result["name"] == "Multi-Agent Orchestration Platform"
        assert result["version"] == "1.0.0"
        assert result["agent_count"] == 2
        assert result["workflow_count"] == 1

    def test_get_available_tools(self, server):
        """Test get_available_tools method."""
        tools = server.get_available_tools()

        assert len(tools) > 0
        tool_names = [tool["name"] for tool in tools]
        assert "list_agents" in tool_names
        assert "execute_workflow" in tool_names
        assert "get_platform_status" in tool_names

        # Check tool structure
        list_agents_tool = next(tool for tool in tools if tool["name"] == "list_agents")
        assert "description" in list_agents_tool
        assert "inputSchema" in list_agents_tool

    def test_handle_tool_call_unknown_tool(self, server):
        """Test handling call to unknown tool."""
        result = asyncio.run(server.handle_tool_call("unknown_tool", {}))

        assert "error" in result
        assert "Unknown tool" in result["error"]

    def test_handle_tool_call_valid_tool(self, server):
        """Test handling call to valid tool."""
        with patch.object(server, '_handle_list_agents', new_callable=AsyncMock) as mock_handler:
            mock_handler.return_value = {"agents": []}

            result = asyncio.run(server.handle_tool_call("list_agents", {}))

            assert result == {"agents": []}
            mock_handler.assert_called_once_with({})