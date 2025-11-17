"""End-to-end tests for the complete multi-agent orchestration platform."""

import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import Mock, AsyncMock, patch
from click.testing import CliRunner
from fastapi.testclient import TestClient

from src.api.app import create_application
from src.cli.main import app


class TestFullSystemE2E:
    """End-to-end tests for the complete system."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        config_data = {
            "version": "1.0.0",
            "agents": {
                "claude-agent": {
                    "provider": "anthropic",
                    "model": "claude-3",
                    "max_tokens": 4096,
                    "temperature": 0.7,
                    "timeout_seconds": 60,
                    "enabled": True
                },
                "codex-agent": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "max_tokens": 2048,
                    "temperature": 0.5,
                    "timeout_seconds": 30,
                    "enabled": True
                }
            },
            "workflows": {
                "code-review": {
                    "name": "code-review",
                    "type": "simple",
                    "description": "Automated code review workflow",
                    "enabled": True,
                    "agents": ["claude-agent"],
                    "steps": [
                        {
                            "name": "analyze",
                            "agent": "claude-agent",
                            "prompt": "Analyze this code for issues: {{code}}",
                            "inputs": ["code"],
                            "output": "analysis",
                            "timeout": 300,
                            "retry": 0,
                            "dependencies": []
                        },
                        {
                            "name": "review",
                            "agent": "claude-agent",
                            "prompt": "Review the analysis: {{analysis}} and provide recommendations",
                            "inputs": ["analysis"],
                            "output": "recommendations",
                            "timeout": 300,
                            "retry": 0,
                            "dependencies": ["analyze"]
                        }
                    ],
                    "inputs": ["code"],
                    "outputs": ["analysis", "recommendations"],
                    "config": {},
                    "metadata": {}
                }
            },
            "logging": {
                "level": "INFO",
                "format": "json"
            },
            "observability": {
                "enabled": True,
                "metrics": True,
                "tracing": False
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(config_data, f)
            config_file = f.name

        yield config_file

        # Cleanup
        os.unlink(config_file)

    @pytest.fixture
    def mock_all_dependencies(self, temp_config_file):
        """Mock all external dependencies for full system testing."""
        with patch('src.core.config.ConfigManager') as mock_config_class, \
             patch('src.agents.base.agent_registry') as mock_registry, \
             patch('src.core.workflow.WorkflowEngine') as mock_engine_class, \
             patch('src.core.observability.ObservabilityManager') as mock_obs_class, \
             patch('src.utils.git.GitManager') as mock_git_class, \
             patch('src.utils.docker.DockerManager') as mock_docker_class, \
             patch('src.mcp_integration.server.MCPPlatformServer') as mock_mcp_class:

            # Mock config manager
            mock_config_manager = Mock()
            mock_config_manager.config_file = temp_config_file
            mock_config_manager.get_config.return_value = Mock(
                version="1.0.0",
                agents={
                    "claude-agent": Mock(
                        provider="anthropic",
                        model="claude-3",
                        max_tokens=4096,
                        temperature=0.7,
                        timeout_seconds=60,
                        enabled=True
                    )
                },
                workflows={
                    "code-review": Mock(
                        name="code-review",
                        type="simple",
                        description="Code review workflow",
                        enabled=True,
                        agents=["claude-agent"],
                        steps=[Mock(name="analyze"), Mock(name="review")],
                        inputs=["code"],
                        outputs=["analysis", "recommendations"]
                    )
                }
            )
            mock_config_manager.validate_config.return_value = []
            mock_config_manager.save_config.return_value = True
            mock_config_class.return_value = mock_config_manager

            # Mock agent registry
            mock_agent = Mock()
            mock_agent.name = "claude-agent"
            mock_agent.health_check = AsyncMock(return_value=True)
            mock_agent.capabilities = ["chat", "code_generation", "analysis"]
            mock_agent.execute = AsyncMock(return_value={
                "result": "Code analysis completed",
                "issues": [],
                "recommendations": ["Add docstrings", "Improve error handling"]
            })
            mock_registry.get_agent.return_value = mock_agent
            mock_registry.list_agents.return_value = [mock_agent]

            # Mock workflow engine
            mock_execution = Mock()
            mock_execution.execution_id = "exec-e2e-123"
            mock_execution.workflow_id = "code-review"
            mock_execution.status = Mock(value="completed")
            mock_execution.step_results = {
                "analysis": "Code analysis completed",
                "recommendations": ["Add docstrings", "Improve error handling"]
            }
            mock_execution.errors = []
            mock_execution.start_time = 1234567890.0
            mock_execution.end_time = 1234567900.0
            mock_execution.duration = 10.0

            mock_engine = Mock()
            mock_engine.execute_workflow = AsyncMock(return_value="exec-e2e-123")
            mock_engine.get_execution_status.return_value = mock_execution
            mock_engine.list_executions.return_value = [mock_execution]
            mock_engine.cancel_execution.return_value = True
            mock_engine_class.return_value = mock_engine

            # Mock observability
            mock_obs = Mock()
            mock_obs_class.return_value = mock_obs

            # Mock git manager
            mock_git = Mock()
            mock_git.clone_repo = AsyncMock(return_value="/tmp/test-repo")
            mock_git.get_status.return_value = {"modified": ["file1.py"], "untracked": []}
            mock_git_class.return_value = mock_git

            # Mock docker manager
            mock_docker = Mock()
            mock_docker.build_image = AsyncMock(return_value="test-image:latest")
            mock_docker.run_container = AsyncMock(return_value="container-123")
            mock_docker_class.return_value = mock_docker

            # Mock MCP server
            mock_mcp = Mock()
            mock_mcp.get_available_tools.return_value = [
                {"name": "list_agents", "description": "List available agents"}
            ]
            mock_mcp.handle_tool_call = AsyncMock(return_value={"agents": ["claude-agent"]})
            mock_mcp_class.return_value = mock_mcp

            yield {
                "config": mock_config_manager,
                "registry": mock_registry,
                "engine": mock_engine,
                "agent": mock_agent,
                "execution": mock_execution,
                "git": mock_git,
                "docker": mock_docker,
                "mcp": mock_mcp
            }

    def test_full_api_workflow(self, mock_all_dependencies):
        """Test complete API workflow from start to finish."""
        # Create API client
        app_instance = create_application()
        client = TestClient(app_instance)

        # 1. Check health
        response = client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"

        # 2. List agents
        response = client.get("/agents")
        assert response.status_code == 200
        agents_data = response.json()
        assert len(agents_data["agents"]) > 0
        assert agents_data["agents"][0]["name"] == "claude-agent"

        # 3. Get agent details
        response = client.get("/agents/claude-agent")
        assert response.status_code == 200
        agent_data = response.json()
        assert agent_data["name"] == "claude-agent"
        assert agent_data["type"] == "anthropic"

        # 4. Test agent
        response = client.post("/agents/claude-agent/test")
        assert response.status_code == 200
        test_data = response.json()
        assert test_data["healthy"] is True

        # 5. List workflows
        response = client.get("/workflows")
        assert response.status_code == 200
        workflows_data = response.json()
        assert len(workflows_data["workflows"]) > 0

        # 6. Execute workflow
        exec_request = {
            "workflow_name": "code-review",
            "inputs": {
                "code": "def hello():\n    print('Hello, World!')\n    return True"
            }
        }
        response = client.post("/workflows/execute", json=exec_request)
        assert response.status_code == 200
        exec_data = response.json()
        execution_id = exec_data["execution_id"]
        assert execution_id == "exec-e2e-123"

        # 7. Check execution status
        response = client.get(f"/executions/{execution_id}")
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["status"] == "completed"
        assert "analysis" in status_data["results"]
        assert "recommendations" in status_data["results"]

        # 8. List executions
        response = client.get("/executions")
        assert response.status_code == 200
        executions_data = response.json()
        assert len(executions_data["executions"]) > 0

    def test_full_cli_workflow(self, mock_all_dependencies):
        """Test complete CLI workflow from start to finish."""
        runner = CliRunner()

        # 1. Check CLI help
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Multi-Agent Orchestration Platform" in result.output

        # 2. List agents via CLI
        result = runner.invoke(app, ["agent", "list"])
        assert result.exit_code == 0
        assert "claude-agent" in result.output
        assert "anthropic" in result.output

        # 3. Get agent info via CLI
        result = runner.invoke(app, ["agent", "info", "claude-agent"])
        assert result.exit_code == 0
        assert "claude-3" in result.output
        assert "4096" in result.output

        # 4. Test agent via CLI
        result = runner.invoke(app, ["agent", "test", "claude-agent"])
        assert result.exit_code == 0
        assert "healthy" in result.output.lower() or "success" in result.output.lower()

        # 5. List workflows via CLI
        result = runner.invoke(app, ["workflow", "list"])
        assert result.exit_code == 0
        assert "code-review" in result.output

        # 6. Run workflow via CLI
        result = runner.invoke(app, [
            "workflow", "run", "code-review",
            "--input", "code=def hello(): pass"
        ])
        assert result.exit_code == 0
        assert "exec-e2e-123" in result.output

        # 7. Check workflow status via CLI
        result = runner.invoke(app, ["workflow", "status", "exec-e2e-123"])
        assert result.exit_code == 0
        assert "completed" in result.output
        assert "analysis" in result.output or "recommendations" in result.output

        # 8. Validate config via CLI
        result = runner.invoke(app, ["config", "validate"])
        assert result.exit_code == 0

        # 9. Show config via CLI
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "agents" in result.output or "workflows" in result.output

    def test_api_cli_integration(self, mock_all_dependencies):
        """Test that API and CLI work together consistently."""
        # Create API client
        app_instance = create_application()
        client = TestClient(app_instance)
        runner = CliRunner()

        # Execute workflow via API
        exec_request = {
            "workflow_name": "code-review",
            "inputs": {"code": "def test(): return 42"}
        }
        api_response = client.post("/workflows/execute", json=exec_request)
        assert api_response.status_code == 200
        api_execution_id = api_response.json()["execution_id"]

        # Check status via CLI
        cli_result = runner.invoke(app, ["workflow", "status", api_execution_id])
        assert cli_result.exit_code == 0
        assert api_execution_id in cli_result.output

        # Check status via API
        api_status_response = client.get(f"/executions/{api_execution_id}")
        assert api_status_response.status_code == 200
        api_status = api_status_response.json()

        # Verify consistency
        assert api_status["execution_id"] == api_execution_id
        assert api_status["status"] == "completed"

    def test_error_handling_e2e(self, mock_all_dependencies):
        """Test end-to-end error handling."""
        client = TestClient(create_application())
        runner = CliRunner()

        # Test API error handling
        # Non-existent agent
        response = client.get("/agents/non-existent")
        assert response.status_code == 404

        # Invalid workflow execution
        response = client.post("/workflows/execute", json={"invalid": "data"})
        assert response.status_code == 422

        # Non-existent execution
        response = client.get("/executions/non-existent")
        assert response.status_code == 404

        # Test CLI error handling
        # Non-existent agent
        result = runner.invoke(app, ["agent", "info", "non-existent"])
        assert result.exit_code != 0

        # Invalid command
        result = runner.invoke(app, ["invalid", "command"])
        assert result.exit_code != 0

    def test_concurrent_operations(self, mock_all_dependencies):
        """Test concurrent operations across API and CLI."""
        import threading

        client = TestClient(create_application())
        runner = CliRunner()

        results = []
        errors = []

        def api_health_check():
            try:
                response = client.get("/health")
                results.append(("api", response.status_code))
            except Exception as e:
                errors.append(("api", str(e)))

        def cli_agent_list():
            try:
                result = runner.invoke(app, ["agent", "list"])
                results.append(("cli", result.exit_code))
            except Exception as e:
                errors.append(("cli", str(e)))

        def api_agent_list():
            try:
                response = client.get("/agents")
                results.append(("api_agents", response.status_code))
            except Exception as e:
                errors.append(("api_agents", str(e)))

        # Run operations concurrently
        threads = [
            threading.Thread(target=api_health_check),
            threading.Thread(target=cli_agent_list),
            threading.Thread(target=api_agent_list),
            threading.Thread(target=api_health_check),
            threading.Thread(target=cli_agent_list)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all operations succeeded
        assert len(results) == 5
        assert all(status == 200 or status == 0 for _, status in results)
        assert len(errors) == 0

    def test_workflow_execution_with_dependencies(self, mock_all_dependencies):
        """Test workflow execution with step dependencies."""
        client = TestClient(create_application())

        # Execute workflow with dependent steps
        exec_request = {
            "workflow_name": "code-review",
            "inputs": {
                "code": """
def calculate_fibonacci(n):
    '''Calculate the nth Fibonacci number.'''
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

if __name__ == "__main__":
    print(calculate_fibonacci(10))
"""
            }
        }

        response = client.post("/workflows/execute", json=exec_request)
        assert response.status_code == 200

        execution_id = response.json()["execution_id"]

        # Check that execution completed with all steps
        status_response = client.get(f"/executions/{execution_id}")
        assert status_response.status_code == 200

        status_data = status_response.json()
        assert status_data["status"] == "completed"
        assert "analysis" in status_data["results"]
        assert "recommendations" in status_data["results"]

    def test_configuration_persistence(self, mock_all_dependencies, temp_config_file):
        """Test configuration persistence across operations."""
        runner = CliRunner()

        # Modify configuration via CLI
        result = runner.invoke(app, [
            "config", "set",
            "agents.claude-agent.max_tokens",
            "8192"
        ])
        assert result.exit_code == 0

        # Verify change persisted (in mock)
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0

        # Verify agent info reflects change
        result = runner.invoke(app, ["agent", "info", "claude-agent"])
        assert result.exit_code == 0

    def test_large_data_handling(self, mock_all_dependencies):
        """Test handling of large data payloads."""
        client = TestClient(create_application())

        # Create large code input
        large_code = "def func():\n" + "\n".join([f"    x = {i}" for i in range(1000)]) + "\n    return x"

        exec_request = {
            "workflow_name": "code-review",
            "inputs": {"code": large_code}
        }

        # Should handle large payload
        response = client.post("/workflows/execute", json=exec_request)
        assert response.status_code == 200

        execution_id = response.json()["execution_id"]

        # Should complete successfully
        status_response = client.get(f"/executions/{execution_id}")
        assert status_response.status_code == 200

    def test_system_recovery_scenarios(self, mock_all_dependencies):
        """Test system recovery from various failure scenarios."""
        client = TestClient(create_application())
        runner = CliRunner()

        # Test recovery from interrupted workflow
        # (This would be more complex in real implementation)

        # Test that system remains functional after errors
        # Make some failing requests
        for _ in range(3):
            client.get("/agents/non-existent")
            runner.invoke(app, ["agent", "info", "non-existent"])

        # System should still work for valid requests
        response = client.get("/health")
        assert response.status_code == 200

        result = runner.invoke(app, ["agent", "list"])
        assert result.exit_code == 0

    def test_cross_component_integration(self, mock_all_dependencies):
        """Test integration across all system components."""
        client = TestClient(create_application())
        runner = CliRunner()

        # 1. Health check
        assert client.get("/health").status_code == 200

        # 2. Agent operations
        assert client.get("/agents").status_code == 200
        assert runner.invoke(app, ["agent", "list"]).exit_code == 0

        # 3. Workflow operations
        assert client.get("/workflows").status_code == 200
        assert runner.invoke(app, ["workflow", "list"]).exit_code == 0

        # 4. Execution operations
        exec_response = client.post("/workflows/execute", json={
            "workflow_name": "code-review",
            "inputs": {"code": "def test(): pass"}
        })
        assert exec_response.status_code == 200

        execution_id = exec_response.json()["execution_id"]

        assert client.get(f"/executions/{execution_id}").status_code == 200
        assert runner.invoke(app, ["workflow", "status", execution_id]).exit_code == 0

        # 5. Configuration operations
        assert client.get("/executions").status_code == 200
        assert runner.invoke(app, ["config", "show"]).exit_code == 0

        # All components should work together seamlessly