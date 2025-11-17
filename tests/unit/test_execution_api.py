"""Unit tests for execution API routes."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.routes.execution import router
from src.core.workflow import ExecutionStatus


@pytest.fixture
def test_app():
    """Create test FastAPI application."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


class TestExecutionRoutes:
    """Test execution API routes."""

    @patch('src.api.routes.execution.CopilotAgent')
    @patch('src.api.routes.execution.CodexAgent')
    @patch('src.api.routes.execution.ClaudeAgent')
    @patch('src.api.routes.execution.ConfigManager')
    @patch('src.api.routes.execution.WorkflowEngine')
    @patch('src.api.routes.execution.agent_registry')
    def test_create_execution_success(self, mock_registry, mock_engine_class, mock_config_class, mock_claude, mock_codex, mock_copilot, client):
        """Test successful execution creation."""
        # Mock config
        mock_config = Mock()
        mock_config.agents = {}
        
        # Create a proper mock workflow config that returns actual strings
        mock_workflow = Mock()
        mock_workflow.name = 'test-workflow'
        mock_workflow.description = 'Test workflow'
        mock_workflow.type = 'simple'
        mock_workflow.steps = [
            {
                'name': 'step1',
                'agent': 'test-agent',
                'prompt': 'Test prompt',
                'inputs': {},
                'output': 'result',
                'timeout': 300,
                'retry': 0,
                'dependencies': []
            }
        ]
        mock_workflow.config = {}
        mock_workflow.metadata = {}
        
        mock_config.workflows = {
            'test-workflow': mock_workflow
        }
        mock_config_class.return_value.get_config.return_value = mock_config

        # Mock agent registry
        mock_registry.list_agents.return_value = ['test-agent']
        mock_registry.get_agent.return_value = Mock()

        # Mock workflow engine
        mock_engine = Mock()
        mock_engine.execute_workflow = AsyncMock(return_value='exec-123')
        mock_engine_class.return_value = mock_engine

        response = client.post(
            "/api/v1/executions",
            json={
                "workflow_name": "test-workflow",
                "inputs": {"param1": "value1"},
                "async_execution": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["execution_id"] == "exec-123"
        assert data["data"]["status"] == "running"

    def test_create_execution_workflow_not_found(self, client):
        """Test execution creation with non-existent workflow."""
        with patch('src.api.routes.execution.ConfigManager') as mock_config_class:
            mock_config = Mock()
            mock_config.workflows = {}
            mock_config_class.return_value.get_config.return_value = mock_config

            response = client.post(
                "/api/v1/executions",
                json={
                    "workflow_name": "non-existent-workflow",
                    "async_execution": True
                }
            )

            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Workflow 'non-existent-workflow' not found"

    @patch('src.api.routes.execution.ConfigManager')
    @patch('src.api.routes.execution.WorkflowEngine')
    @patch('src.api.routes.execution.agent_registry')
    def test_get_execution_success(self, mock_registry, mock_engine_class, mock_config_class, client):
        """Test successful execution retrieval."""
        # Mock execution context
        mock_execution = Mock()
        mock_execution.execution_id = "exec-123"
        mock_execution.status = ExecutionStatus.RUNNING
        mock_execution.step_results = {}
        mock_execution.errors = []
        mock_execution.start_time = 1234567890.0
        mock_execution.end_time = None
        mock_execution.duration = None

        # Mock workflow engine
        mock_engine = Mock()
        mock_engine.get_execution_status.return_value = mock_execution
        mock_engine_class.return_value = mock_engine

        response = client.get("/api/v1/executions/exec-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["execution_id"] == "exec-123"
        assert data["data"]["status"] == "running"

    def test_get_execution_not_found(self, client):
        """Test execution retrieval for non-existent execution."""
        with patch('src.api.routes.execution.ConfigManager'), \
             patch('src.api.routes.execution.WorkflowEngine') as mock_engine_class, \
             patch('src.api.routes.execution.agent_registry'):

            mock_engine = Mock()
            mock_engine.get_execution_status.return_value = None
            mock_engine_class.return_value = mock_engine

            response = client.get("/api/v1/executions/non-existent")

            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Execution 'non-existent' not found"

    @patch('src.api.routes.execution.ConfigManager')
    @patch('src.api.routes.execution.WorkflowEngine')
    @patch('src.api.routes.execution.agent_registry')
    def test_list_executions(self, mock_registry, mock_engine_class, mock_config_class, client):
        """Test execution listing."""
        # Mock executions
        mock_executions = [
            Mock(
                execution_id="exec-1",
                status=ExecutionStatus.COMPLETED,
                step_results={"result": "success"},
                errors=[],
                start_time=1234567890.0,
                end_time=1234567900.0,
                duration=10.0
            ),
            Mock(
                execution_id="exec-2",
                status=ExecutionStatus.RUNNING,
                step_results={},
                errors=[],
                start_time=1234567890.0,
                end_time=None,
                duration=None
            )
        ]

        # Mock workflow engine
        mock_engine = Mock()
        mock_engine.list_executions.return_value = mock_executions
        mock_engine_class.return_value = mock_engine

        response = client.get("/api/v1/executions")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["data"][0]["execution_id"] == "exec-1"
        assert data["data"][1]["execution_id"] == "exec-2"

    @patch('src.api.routes.execution.ConfigManager')
    @patch('src.api.routes.execution.WorkflowEngine')
    @patch('src.api.routes.execution.agent_registry')
    def test_cancel_execution_success(self, mock_registry, mock_engine_class, mock_config_class, client):
        """Test successful execution cancellation."""
        # Mock workflow engine
        mock_engine = Mock()
        mock_engine.cancel_execution.return_value = True
        mock_engine_class.return_value = mock_engine

        response = client.delete("/api/v1/executions/exec-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cancelled successfully" in data["message"]

    @patch('src.api.routes.execution.ConfigManager')
    @patch('src.api.routes.execution.WorkflowEngine')
    @patch('src.api.routes.execution.agent_registry')
    def test_cancel_execution_not_found(self, mock_registry, mock_engine_class, mock_config_class, client):
        """Test cancellation of non-existent execution."""
        # Mock workflow engine
        mock_engine = Mock()
        mock_engine.cancel_execution.return_value = False
        mock_engine_class.return_value = mock_engine

        response = client.delete("/api/v1/executions/non-existent")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Execution 'non-existent' not found or not running"

    @patch('src.api.routes.execution.ConfigManager')
    @patch('src.api.routes.execution.WorkflowEngine')
    @patch('src.api.routes.execution.agent_registry')
    def test_get_active_executions(self, mock_registry, mock_engine_class, mock_config_class, client):
        """Test getting active executions count."""
        # Mock config
        mock_config = Mock()
        mock_config_class.return_value.get_config.return_value = mock_config
        
        # Mock workflow engine
        mock_engine = Mock()
        mock_engine.get_active_execution_count.return_value = 3
        mock_engine_class.return_value = mock_engine

        response = client.get("/api/v1/executions/active")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["active_executions"] == 3

    @patch('src.api.routes.execution.ConfigManager')
    @patch('src.api.routes.execution.WorkflowEngine')
    @patch('src.api.routes.execution.agent_registry')
    def test_get_execution_stats(self, mock_registry, mock_engine_class, mock_config_class, client):
        """Test getting execution statistics."""
        # Mock config
        mock_config = Mock()
        mock_config_class.return_value.get_config.return_value = mock_config
        
        # Mock executions
        mock_executions = [
            Mock(
                execution_id="exec-1",
                workflow_id="workflow-1",
                status=ExecutionStatus.COMPLETED,
                duration=10.0
            ),
            Mock(
                execution_id="exec-2",
                workflow_id="workflow-1",
                status=ExecutionStatus.FAILED,
                duration=None
            ),
            Mock(
                execution_id="exec-3",
                workflow_id="workflow-2",
                status=ExecutionStatus.RUNNING,
                duration=None
            )
        ]

        # Mock workflow engine
        mock_engine = Mock()
        mock_engine.list_executions.return_value = mock_executions
        mock_engine_class.return_value = mock_engine

        response = client.get("/api/v1/executions/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_executions"] == 3
        assert data["data"]["successful_executions"] == 1
        assert data["data"]["failed_executions"] == 1
        assert data["data"]["running_executions"] == 1