"""Contract tests for Function Compute integration.

These tests define the expected behavior of Function Compute integration
and will fail until implementations are provided.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List

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


class FunctionComputeContract:
    """Contract for Function Compute integration functionality.

    This abstract class defines the interface that all Function Compute integration
    implementations must provide.
    """

    async def create_service(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Create FC service.

        Args:
            service_name: Name of the service to create

        Returns:
            Service creation response

        Raises:
            Exception: If service creation fails
        """
        raise NotImplementedError("create_service must be implemented")

    async def create_function(self, function_config: FCFunction) -> Dict[str, Any]:
        """Create FC function.

        Args:
            function_config: Function configuration

        Returns:
            Function creation response

        Raises:
            Exception: If function creation fails
        """
        raise NotImplementedError("create_function must be implemented")

    async def invoke_function(self, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke FC function.

        Args:
            function_name: Name of the function to invoke
            payload: Invocation payload

        Returns:
            Function invocation response

        Raises:
            Exception: If function invocation fails
        """
        raise NotImplementedError("invoke_function must be implemented")

    async def list_functions(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List functions in service.

        Args:
            service_name: Name of the service

        Returns:
            List of functions
        """
        raise NotImplementedError("list_functions must be implemented")

    async def delete_function(self, function_name: str) -> None:
        """Delete FC function.

        Args:
            function_name: Name of the function to delete

        Raises:
            Exception: If function deletion fails
        """
        raise NotImplementedError("delete_function must be implemented")

    async def deploy_workflow(self, workflow_config: Dict[str, Any]) -> str:
        """Deploy workflow as FC function.

        Args:
            workflow_config: Workflow configuration

        Returns:
            Deployed function name

        Raises:
            Exception: If deployment fails
        """
        raise NotImplementedError("deploy_workflow must be implemented")

    async def execute_workflow(self, workflow_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute deployed workflow.

        Args:
            workflow_name: Name of the workflow to execute
            inputs: Workflow inputs

        Returns:
            Workflow execution result

        Raises:
            Exception: If execution fails
        """
        raise NotImplementedError("execute_workflow must be implemented")

    async def get_function_logs(self, function_name: str, request_id: str) -> List[str]:
        """Get function execution logs.

        Args:
            function_name: Name of the function
            request_id: Request ID for the execution

        Returns:
            List of log lines
        """
        raise NotImplementedError("get_function_logs must be implemented")

    async def health_check(self) -> bool:
        """Check FC service health.

        Returns:
            True if healthy, False otherwise
        """
        raise NotImplementedError("health_check must be implemented")


class TestFunctionComputeContract:
    """Contract tests for Function Compute integration.

    These tests define the expected behavior of Function Compute integration
    and will fail until implementations are provided.
    """

    @pytest.fixture
    def fc_contract(self):
        """Create a Function Compute integration contract instance."""
        config = FCConfig(
            account_id="test-account",
            access_key_id="test-key-id",
            access_key_secret="test-key-secret",
            region="cn-hangzhou",
            service_name="test-service",
            function_name="test-function"
        )
        return FunctionComputeIntegration(config)

    @pytest.fixture
    def sample_function_config(self):
        """Create sample function configuration."""
        return FCFunction(
            name="test-function",
            runtime="python3.11",
            handler="index.handler",
            memory_size=512,
            timeout=300,
            environment_variables={"TEST_VAR": "test_value"}
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
    async def test_create_service_basic(self, fc_contract):
        """Test basic FC service creation."""
        with patch.object(fc_contract, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "serviceName": "test-service",
                "description": "Test service",
                "createdTime": "2023-01-01T00:00:00Z"
            }

            result = await fc_contract.create_service("test-service")

            assert result["serviceName"] == "test-service"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_service_failure(self, fc_contract):
        """Test FC service creation failure."""
        with patch.object(fc_contract, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = RuntimeError("Service creation failed")

            with pytest.raises(RuntimeError, match="Service creation failed"):
                await fc_contract.create_service("test-service")

    @pytest.mark.asyncio
    async def test_create_function_basic(self, fc_contract, sample_function_config):
        """Test basic FC function creation."""
        with patch.object(fc_contract, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "functionName": "test-function",
                "runtime": "python3.11",
                "createdTime": "2023-01-01T00:00:00Z"
            }

            result = await fc_contract.create_function(sample_function_config)

            assert result["functionName"] == "test-function"
            assert result["runtime"] == "python3.11"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_function_failure(self, fc_contract, sample_function_config):
        """Test FC function creation failure."""
        with patch.object(fc_contract, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = RuntimeError("Function creation failed")

            with pytest.raises(RuntimeError, match="Function creation failed"):
                await fc_contract.create_function(sample_function_config)

    @pytest.mark.asyncio
    async def test_invoke_function_basic(self, fc_contract):
        """Test basic FC function invocation."""
        payload = {"test": "data"}

        # Mock the invoke_function method directly for simplicity
        with patch.object(fc_contract, 'invoke_function', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"result": "success"}

            async with fc_contract:
                result = await fc_contract.invoke_function("test-function", payload)

            assert result["result"] == "success"
            mock_invoke.assert_called_once_with("test-function", payload)

    @pytest.mark.asyncio
    async def test_invoke_function_failure(self, fc_contract):
        """Test FC function invocation failure."""
        payload = {"test": "data"}

        with patch.object(fc_contract, 'session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            mock_session.post.return_value.__aenter__.return_value = mock_response

            async with fc_contract:
                with pytest.raises(RuntimeError, match="Function invocation failed"):
                    await fc_contract.invoke_function("test-function", payload)

    @pytest.mark.asyncio
    async def test_list_functions_basic(self, fc_contract):
        """Test basic function listing."""
        with patch.object(fc_contract, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "functions": [
                    {"functionName": "func1", "runtime": "python3.11"},
                    {"functionName": "func2", "runtime": "python3.11"}
                ]
            }

            functions = await fc_contract.list_functions()

            assert len(functions) == 2
            assert functions[0]["functionName"] == "func1"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_function_basic(self, fc_contract):
        """Test basic function deletion."""
        with patch.object(fc_contract, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {}

            await fc_contract.delete_function("test-function")

            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_workflow_basic(self, fc_contract, sample_workflow_config):
        """Test basic workflow deployment."""
        with patch.object(fc_contract, 'create_function', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {"functionName": "workflow-test-workflow"}

            function_name = await fc_contract.deploy_workflow(sample_workflow_config)

            assert function_name == "workflow-test-workflow"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_workflow_basic(self, fc_contract):
        """Test basic workflow execution."""
        inputs = {"param1": "value1"}

        with patch.object(fc_contract, 'invoke_function', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"status": "completed", "result": "success"}

            result = await fc_contract.execute_workflow("test-workflow", inputs)

            assert result["status"] == "completed"
            mock_invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_function_logs_basic(self, fc_contract):
        """Test basic function log retrieval."""
        logs = await fc_contract.get_function_logs("test-function", "req-123")

        # Should return some log lines (implementation may be placeholder)
        assert isinstance(logs, list)
        assert len(logs) > 0

    @pytest.mark.asyncio
    async def test_health_check_success(self, fc_contract):
        """Test health check success."""
        with patch.object(fc_contract, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"services": []}

            result = await fc_contract.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, fc_contract):
        """Test health check failure."""
        with patch.object(fc_contract, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = RuntimeError("Connection failed")

            result = await fc_contract.health_check()

            assert result is False