"""Integration tests for Function Compute integration."""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from integrations import FunctionComputeIntegration

# Import FCConfig and FCFunction from the function_compute module
import importlib.util
fc_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'integrations', 'function_compute.py')
spec = importlib.util.spec_from_file_location('function_compute_integration', fc_path)
fc_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc_module)
FCConfig = fc_module.FCConfig
FCFunction = fc_module.FCFunction


class TestFunctionComputeIntegration:
    """Integration tests for Function Compute functionality."""

    @pytest.fixture
    def fc_config(self):
        """Create FC configuration for testing."""
        return FCConfig(
            account_id="test-account",
            access_key_id="test-key-id",
            access_key_secret="test-key-secret",
            region="cn-hangzhou",
            service_name="test-service",
            function_name="test-function"
        )

    @pytest.fixture
    def sample_workflow_config(self):
        """Create sample workflow configuration."""
        return {
            "name": "test-workflow",
            "description": "Test workflow for FC deployment",
            "type": "simple",
            "steps": [
                {
                    "id": "step1",
                    "name": "Test Step",
                    "agent": "test-agent",
                    "prompt": "Test prompt",
                    "output_key": "result"
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_full_deployment_workflow(self, fc_config, sample_workflow_config):
        """Test complete workflow deployment and execution."""
        with patch.object(FunctionComputeIntegration, '_make_request', new_callable=AsyncMock) as mock_request, \
             patch.object(FunctionComputeIntegration, 'invoke_function', new_callable=AsyncMock) as mock_invoke:

            # Mock service creation
            mock_request.return_value = {"serviceName": "test-service"}

            async with FunctionComputeIntegration(fc_config) as fc:
                # Test service creation
                service_result = await fc.create_service()
                assert service_result["serviceName"] == "test-service"

                # Test workflow deployment
                function_name = await fc.deploy_workflow(sample_workflow_config)
                assert function_name == "workflow-test-workflow"

                # Test workflow execution
                mock_invoke.return_value = {"status": "completed", "result": "success"}
                result = await fc.execute_workflow("test-workflow", {"input": "test"})
                assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_function_lifecycle(self, fc_config):
        """Test complete function lifecycle."""
        with patch.object(FunctionComputeIntegration, '_make_request', new_callable=AsyncMock) as mock_request:

            async with FunctionComputeIntegration(fc_config) as fc:
                # Mock function creation
                mock_request.return_value = {"functionName": "test-function"}

                # Create function
                function_config = FCFunction(name="test-function")
                result = await fc.create_function(function_config)
                assert result["functionName"] == "test-function"

                # Mock function listing
                mock_request.return_value = {
                    "functions": [
                        {"functionName": "test-function", "runtime": "python3.11"}
                    ]
                }

                # List functions
                functions = await fc.list_functions()
                assert len(functions) == 1
                assert functions[0]["functionName"] == "test-function"

                # Mock function deletion
                mock_request.return_value = {}

                # Delete function
                await fc.delete_function("test-function")

    @pytest.mark.asyncio
    async def test_deployment_script_creation(self, fc_config, sample_workflow_config):
        """Test deployment script creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, "deploy.sh")

            fc = FunctionComputeIntegration(fc_config)
            result_path = fc.create_deployment_script(sample_workflow_config, script_path)

            assert result_path == script_path
            assert os.path.exists(result_path)

            # Verify script content
            with open(result_path, 'r') as f:
                content = f.read()
                assert "MAO FC deployment" in content
                assert sample_workflow_config["name"] in content
                assert fc_config.account_id in content

    @pytest.mark.asyncio
    async def test_dockerfile_creation(self, fc_config, sample_workflow_config):
        """Test Dockerfile creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dockerfile_path = os.path.join(temp_dir, "Dockerfile")

            fc = FunctionComputeIntegration(fc_config)
            result_path = fc.create_dockerfile(sample_workflow_config, dockerfile_path)

            assert result_path == dockerfile_path
            assert os.path.exists(result_path)

            # Verify Dockerfile content
            with open(result_path, 'r') as f:
                content = f.read()
                assert "MAO Function Compute Dockerfile" in content
                assert sample_workflow_config["name"] in content
                assert "python:3.11-slim" in content

    @pytest.mark.asyncio
    async def test_health_check_integration(self, fc_config):
        """Test health check with real FC API simulation."""
        with patch.object(FunctionComputeIntegration, '_make_request', new_callable=AsyncMock) as mock_request:

            async with FunctionComputeIntegration(fc_config) as fc:
                # Test successful health check
                mock_request.return_value = {"services": []}
                healthy = await fc.health_check()
                assert healthy is True

                # Test failed health check
                mock_request.side_effect = RuntimeError("Connection failed")
                healthy = await fc.health_check()
                assert healthy is False

    @pytest.mark.asyncio
    async def test_workflow_execution_with_inputs(self, fc_config, sample_workflow_config):
        """Test workflow execution with various inputs."""
        test_inputs = [
            {"param1": "value1", "param2": "value2"},
            {"data": [1, 2, 3]},
            {"config": {"nested": "value"}}
        ]

        with patch.object(FunctionComputeIntegration, 'invoke_function', new_callable=AsyncMock) as mock_invoke:

            async with FunctionComputeIntegration(fc_config) as fc:
                for inputs in test_inputs:
                    mock_invoke.return_value = {"status": "completed", "inputs": inputs}

                    result = await fc.execute_workflow("test-workflow", inputs)
                    assert result["status"] == "completed"
                    assert result["inputs"] == inputs

    @pytest.mark.asyncio
    async def test_error_handling(self, fc_config):
        """Test error handling in various scenarios."""
        with patch.object(FunctionComputeIntegration, '_make_request', new_callable=AsyncMock) as mock_request:

            async with FunctionComputeIntegration(fc_config) as fc:
                # Test service creation failure
                mock_request.side_effect = RuntimeError("API Error")
                with pytest.raises(RuntimeError):
                    await fc.create_service()

                # Test function creation failure
                with pytest.raises(RuntimeError):
                    function_config = FCFunction(name="test-function")
                    await fc.create_function(function_config)

    @pytest.mark.asyncio
    async def test_function_logs_retrieval(self, fc_config):
        """Test function logs retrieval."""
        async with FunctionComputeIntegration(fc_config) as fc:
            logs = await fc.get_function_logs("test-function", "req-123")

            # Should return some logs (placeholder implementation)
            assert isinstance(logs, list)
            assert len(logs) > 0
            assert "started" in logs[0].lower()

    def test_fastapi_app_creation(self, fc_config):
        """Test FastAPI app creation if available."""
        fc = FunctionComputeIntegration(fc_config)

        # Check if FastAPI is available
        try:
            import fastapi
            assert fc.app is not None
            assert hasattr(fc.app, 'routes')
        except ImportError:
            assert fc.app is None

    def test_config_loading_from_env(self):
        """Test configuration loading from environment variables."""
        env_vars = {
            "ALICLOUD_ACCOUNT_ID": "env-account",
            "ALICLOUD_ACCESS_KEY_ID": "env-key-id",
            "ALICLOUD_ACCESS_KEY_SECRET": "env-key-secret",
            "ALICLOUD_REGION": "us-west-1",
            "FC_SERVICE_NAME": "env-service",
            "FC_FUNCTION_NAME": "env-function"
        }

        with patch.dict(os.environ, env_vars):
            fc = FunctionComputeIntegration()
            config = fc.config

            assert config.account_id == "env-account"
            assert config.access_key_id == "env-key-id"
            assert config.region == "us-west-1"
            assert config.service_name == "env-service"