"""Integration tests for API endpoints."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json

from src.api.app import create_application
from src.api.models import (
    AgentListResponse, WorkflowResponse,
    WorkflowListResponse, ExecutionResponse, ExecutionListResponse,
    HealthResponse, ErrorResponse
)
from src.agents.base import AgentResponse


class TestAPIIntegration:
    """Integration tests for API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client for API."""
        app = create_application()
        return TestClient(app)

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies for testing."""
        with patch('src.api.routes.agent.ConfigManager') as mock_config_class, \
             patch('src.api.routes.agent.agent_registry') as mock_registry, \
             patch('src.api.routes.workflow.ConfigManager') as mock_config_workflow, \
             patch('src.api.routes.workflow.WorkflowEngine') as mock_engine_class, \
             patch('src.api.routes.execution.ConfigManager') as mock_config_exec, \
             patch('src.api.routes.execution.WorkflowEngine') as mock_engine_exec, \
             patch('src.api.routes.health.ConfigManager') as mock_config_health:

            # Mock config for agents
            mock_config = Mock()
            mock_config.agents = {
                "claude-agent": Mock(
                    provider="anthropic",
                    model="claude-3",
                    max_tokens=4096,
                    temperature=0.7,
                    timeout_seconds=60,
                    enabled=True
                ),
                "codex-agent": Mock(
                    provider="openai",
                    model="gpt-4",
                    max_tokens=2048,
                    temperature=0.5,
                    timeout_seconds=30,
                    enabled=False
                )
            }
            mock_config_class.return_value.get_config.return_value = mock_config

            # Mock agent registry
            mock_agent = Mock()
            mock_agent.health_check = AsyncMock(return_value=True)
            mock_agent.capabilities = ["chat", "code_generation"]
            mock_registry.get_agent.return_value = mock_agent

            # Mock config for workflows
            mock_config_workflow.return_value.get_config.return_value = mock_config

            # Mock workflow engine
            mock_engine = Mock()
            mock_execution = Mock()
            mock_execution.execution_id = "exec-123"
            mock_execution.workflow_id = "workflow-1"
            mock_execution.status = Mock(value="completed")
            mock_execution.step_results = {"result": "success"}
            mock_execution.errors = []
            mock_execution.start_time = 1234567890.0
            mock_execution.end_time = 1234567900.0
            mock_execution.duration = 10.0

            mock_engine.execute_workflow = AsyncMock(return_value="exec-123")
            mock_engine.get_execution_status.return_value = mock_execution
            mock_engine.list_executions.return_value = [mock_execution]
            mock_engine_class.return_value = mock_engine
            mock_engine_exec.return_value = mock_engine

            # Mock config for health
            mock_config_health.return_value.get_config.return_value = mock_config

            yield {
                "config": mock_config,
                "registry": mock_registry,
                "engine": mock_engine
            }

    def test_health_endpoint(self, client, mock_dependencies):
        """Test health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data

    def test_list_agents_endpoint(self, client, mock_dependencies):
        """Test list agents endpoint."""
        response = client.get("/agents")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 2
        assert data["agents"][0]["name"] == "claude-agent"
        assert data["agents"][0]["type"] == "anthropic"
        assert data["agents"][1]["name"] == "codex-agent"
        assert data["agents"][1]["enabled"] is False

    def test_get_agent_endpoint(self, client, mock_dependencies):
        """Test get agent endpoint."""
        response = client.get("/agents/claude-agent")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "claude-agent"
        assert data["type"] == "anthropic"
        assert data["model"] == "claude-3"
        assert data["healthy"] is True
        assert "chat" in data["capabilities"]

    def test_get_agent_not_found(self, client, mock_dependencies):
        """Test get agent endpoint for non-existent agent."""
        response = client.get("/agents/non-existent")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_test_agent_endpoint(self, client, mock_dependencies):
        """Test test agent endpoint."""
        response = client.post("/agents/claude-agent/test")

        assert response.status_code == 200
        data = response.json()
        assert "healthy" in data
        assert data["healthy"] is True

    def test_list_workflows_endpoint(self, client, mock_dependencies):
        """Test list workflows endpoint."""
        # Add workflows to mock config
        mock_dependencies["config"].workflows = {
            "code-review": Mock(
                name="code-review",
                type="simple",
                description="Code review workflow",
                enabled=True,
                agents=["claude-agent"],
                steps=[{"name": "analyze"}, {"name": "review"}]
            )
        }

        response = client.get("/workflows")

        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert len(data["workflows"]) == 1
        assert data["workflows"][0]["name"] == "code-review"
        assert data["workflows"][0]["step_count"] == 2

    def test_execute_workflow_endpoint(self, client, mock_dependencies):
        """Test execute workflow endpoint."""
        # Add workflow to config
        mock_dependencies["config"].workflows = {
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

        request_data = {
            "workflow_name": "test-workflow",
            "inputs": {"param": "value"}
        }

        response = client.post("/workflows/execute", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "execution_id" in data
        assert data["execution_id"] == "exec-123"

    def test_get_execution_endpoint(self, client, mock_dependencies):
        """Test get execution endpoint."""
        response = client.get("/executions/exec-123")

        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == "exec-123"
        assert data["status"] == "completed"
        assert data["results"]["result"] == "success"
        assert data["duration"] == 10.0

    def test_get_execution_not_found(self, client, mock_dependencies):
        """Test get execution endpoint for non-existent execution."""
        # Mock engine to return None
        mock_dependencies["engine"].get_execution_status.return_value = None

        response = client.get("/executions/non-existent")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_list_executions_endpoint(self, client, mock_dependencies):
        """Test list executions endpoint."""
        response = client.get("/executions")

        assert response.status_code == 200
        data = response.json()
        assert "executions" in data
        assert len(data["executions"]) == 1
        assert data["executions"][0]["execution_id"] == "exec-123"
        assert data["executions"][0]["status"] == "completed"

    def test_cancel_execution_endpoint(self, client, mock_dependencies):
        """Test cancel execution endpoint."""
        # Mock successful cancellation
        mock_dependencies["engine"].cancel_execution.return_value = True

        response = client.post("/executions/exec-123/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["cancelled"] is True
        assert data["execution_id"] == "exec-123"

    def test_cancel_execution_not_found(self, client, mock_dependencies):
        """Test cancel execution endpoint for non-existent execution."""
        # Mock failed cancellation
        mock_dependencies["engine"].cancel_execution.return_value = False

        response = client.post("/executions/non-existent/cancel")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_workflow_templates_endpoint(self, client, mock_dependencies):
        """Test workflow templates endpoint."""
        response = client.get("/workflows/templates")

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        # Should include built-in templates like CodeReview, PRAutomation, TaskDevelopment

    def test_create_workflow_from_template_endpoint(self, client, mock_dependencies):
        """Test create workflow from template endpoint."""
        request_data = {
            "template_name": "CodeReview",
            "workflow_name": "my-code-review",
            "customizations": {
                "language": "python",
                "max_issues": 10
            }
        }

        response = client.post("/workflows/templates/create", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "workflow" in data
        assert data["workflow"]["name"] == "my-code-review"

    def test_api_error_handling(self, client, mock_dependencies):
        """Test API error handling."""
        # Test invalid JSON
        response = client.post("/workflows/execute", data="invalid json")

        assert response.status_code == 422  # Validation error

        # Test missing required fields
        response = client.post("/workflows/execute", json={})

        assert response.status_code == 422

    def test_cors_headers(self, client, mock_dependencies):
        """Test CORS headers are present."""
        response = client.options("/health")

        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_api_versioning(self, client, mock_dependencies):
        """Test API versioning."""
        # Test that version is included in responses
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data

    @patch('src.api.app.logging')
    def test_request_logging(self, mock_logging, client, mock_dependencies):
        """Test that requests are logged."""
        response = client.get("/health")

        assert response.status_code == 200
        # Verify logging was called (this would need proper logging setup)

    def test_concurrent_requests(self, client, mock_dependencies):
        """Test handling concurrent requests."""
        import threading
        import time

        results = []
        errors = []

        def make_request():
            try:
                response = client.get("/health")
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads making requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all requests succeeded
        assert len(results) == 5
        assert all(status == 200 for status in results)
        assert len(errors) == 0

    def test_large_payload_handling(self, client, mock_dependencies):
        """Test handling of large request payloads."""
        # Create a large payload
        large_data = {
            "workflow_name": "test-workflow",
            "inputs": {
                "large_param": "x" * 10000,  # 10KB string
                "array_param": list(range(1000))  # Large array
            }
        }

        response = client.post("/workflows/execute", json=large_data)

        # Should handle large payloads gracefully
        assert response.status_code in [200, 413]  # 200 if processed, 413 if payload too large

    def test_malformed_request_handling(self, client, mock_dependencies):
        """Test handling of malformed requests."""
        # Test various malformed requests
        test_cases = [
            ("/agents", "GET", None),  # Valid
            ("/agents/invalid/agent", "GET", None),  # Invalid path
            ("/workflows/execute", "POST", {"invalid": "data"}),  # Invalid data
            ("/executions", "PUT", None),  # Invalid method
        ]

        for path, method, data in test_cases:
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                response = client.post(path, json=data if data else {})
            elif method == "PUT":
                response = client.put(path, json=data if data else {})

            # Should not crash the server
            assert response.status_code != 500

    def test_rate_limiting_simulation(self, client, mock_dependencies):
        """Test rate limiting behavior (simulated)."""
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = client.get("/health")
            responses.append(response.status_code)

        # All should succeed (no rate limiting implemented in test)
        assert all(status == 200 for status in responses)