"""Function Compute integration for Alibaba Cloud FC deployment."""

import asyncio
import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import aiohttp
try:
    import uvicorn
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logger.warning("FastAPI not available, FC API endpoints will not be functional")

try:
    from ...core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class FCConfig:
    """Function Compute configuration."""
    account_id: str
    access_key_id: str
    access_key_secret: str
    region: str = "cn-hangzhou"
    service_name: str = "mao-orchestration"
    function_name: str = "workflow-executor"


@dataclass
class FCFunction:
    """Function Compute function metadata."""
    name: str
    runtime: str = "python3.11"
    handler: str = "index.handler"
    memory_size: int = 512
    timeout: int = 300
    environment_variables: Dict[str, str] = None

    def __post_init__(self):
        if self.environment_variables is None:
            self.environment_variables = {}


# API Models
if FASTAPI_AVAILABLE:
    class WorkflowDeployRequest(BaseModel):
        """Request model for workflow deployment."""
        workflow_config: Dict[str, Any]
        function_name: Optional[str] = None

    class WorkflowExecuteRequest(BaseModel):
        """Request model for workflow execution."""
        workflow_name: str
        inputs: Dict[str, Any]

    class FunctionCreateRequest(BaseModel):
        """Request model for function creation."""
        function_config: Dict[str, Any]

    class ServiceCreateRequest(BaseModel):
        """Request model for service creation."""
        service_name: str
        description: Optional[str] = None


class FunctionComputeIntegration:
    """Alibaba Cloud Function Compute integration."""

    def __init__(self, config: Optional[FCConfig] = None):
        """Initialize FC integration.

        Args:
            config: FC configuration. If None, loads from environment.
        """
        self.config = config or self._load_config()
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = f"https://{self.config.account_id}.{self.config.region}.fc.aliyuncs.com"

        # Initialize FastAPI app if available
        if FASTAPI_AVAILABLE:
            self.app = self._create_fastapi_app()
        else:
            self.app = None

    def _create_fastapi_app(self) -> FastAPI:
        """Create FastAPI application with FC endpoints."""
        app = FastAPI(
            title="MAO Function Compute API",
            description="Multi-Agent Orchestration Function Compute API",
            version="1.0.0"
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Health check endpoint
        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            healthy = await self.health_check()
            if not healthy:
                raise HTTPException(status_code=503, detail="FC service unhealthy")
            return {"status": "healthy", "service": "function-compute"}

        # Service management endpoints
        @app.post("/services")
        async def create_service(request: ServiceCreateRequest):
            """Create FC service."""
            try:
                result = await self.create_service(request.service_name)
                return {"status": "success", "service": result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/services/{service_name}/functions")
        async def list_functions(service_name: str):
            """List functions in service."""
            try:
                functions = await self.list_functions(service_name)
                return {"functions": functions}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Function management endpoints
        @app.post("/services/{service_name}/functions")
        async def create_function(service_name: str, request: FunctionCreateRequest):
            """Create FC function."""
            try:
                # Convert dict to FCFunction
                config_dict = request.function_config
                function_config = FCFunction(**config_dict)
                result = await self.create_function(function_config)
                return {"status": "success", "function": result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.delete("/services/{service_name}/functions/{function_name}")
        async def delete_function(service_name: str, function_name: str):
            """Delete FC function."""
            try:
                await self.delete_function(function_name)
                return {"status": "success"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/services/{service_name}/functions/{function_name}/invocations")
        async def invoke_function(service_name: str, function_name: str, payload: Dict[str, Any]):
            """Invoke FC function."""
            try:
                result = await self.invoke_function(function_name, payload)
                return {"result": result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Workflow management endpoints
        @app.post("/workflows/deploy")
        async def deploy_workflow_endpoint(request: WorkflowDeployRequest, background_tasks: BackgroundTasks):
            """Deploy workflow as FC function."""
            try:
                function_name = await self.deploy_workflow(request.workflow_config)
                return {"status": "success", "function_name": function_name}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/workflows/execute")
        async def execute_workflow_endpoint(request: WorkflowExecuteRequest, background_tasks: BackgroundTasks):
            """Execute deployed workflow."""
            try:
                result = await self.execute_workflow(request.workflow_name, request.inputs)
                return {"result": result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/workflows/{workflow_name}/logs/{request_id}")
        async def get_workflow_logs(workflow_name: str, request_id: str):
            """Get workflow execution logs."""
            try:
                logs = await self.get_function_logs(f"workflow-{workflow_name}", request_id)
                return {"logs": logs}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        return app

    def start_api_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the FastAPI server.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        if not FASTAPI_AVAILABLE or not self.app:
            logger.error("FastAPI not available, cannot start API server")
            return

        logger.info(f"Starting FC API server on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)

    def _load_config(self) -> FCConfig:
        """Load FC configuration from environment variables."""
        return FCConfig(
            account_id=os.getenv("ALICLOUD_ACCOUNT_ID", ""),
            access_key_id=os.getenv("ALICLOUD_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("ALICLOUD_ACCESS_KEY_SECRET", ""),
            region=os.getenv("ALICLOUD_REGION", "cn-hangzhou"),
            service_name=os.getenv("FC_SERVICE_NAME", "mao-orchestration"),
            function_name=os.getenv("FC_FUNCTION_NAME", "workflow-executor")
        )

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to FC API."""
        if not self.session:
            raise RuntimeError("Integration not initialized. Use async context manager.")

        url = f"{self.base_url}/2023-03-30{endpoint}"
        headers = {
            "Authorization": f"FC {self.config.access_key_id}:{self._calculate_signature(method, endpoint, data)}",
            "Content-Type": "application/json"
        }

        async with self.session.request(method, url, headers=headers, json=data) as response:
            if response.status >= 400:
                error_text = await response.text()
                raise RuntimeError(f"FC API error {response.status}: {error_text}")

            return await response.json()

    def _calculate_signature(self, method: str, endpoint: str, data: Optional[Dict]) -> str:
        """Calculate FC API signature. (Simplified for demo)"""
        # In real implementation, this would use proper HMAC-SHA256 signing
        return "signature-placeholder"

    async def create_service(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Create FC service."""
        service_name = service_name or self.config.service_name

        data = {
            "serviceName": service_name,
            "description": "Multi-Agent Orchestration Platform",
            "role": f"acs:ram::{self.config.account_id}:role/aliyunfcdefaultrole"
        }

        return await self._make_request("POST", "/services", data)

    async def create_function(self, function_config: FCFunction) -> Dict[str, Any]:
        """Create FC function."""
        data = {
            "functionName": function_config.name,
            "runtime": function_config.runtime,
            "handler": function_config.handler,
            "memorySize": function_config.memory_size,
            "timeout": function_config.timeout,
            "environmentVariables": function_config.environment_variables,
            "code": {
                "ossBucketName": f"mao-{self.config.account_id}",
                "ossObjectName": "function-code.zip"
            }
        }

        endpoint = f"/services/{self.config.service_name}/functions"
        return await self._make_request("POST", endpoint, data)

    async def invoke_function(self, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke FC function."""
        endpoint = f"/services/{self.config.service_name}/functions/{function_name}/invocations"

        async with self.session.post(
            f"{self.base_url}/2023-03-30{endpoint}",
            headers={
                "Authorization": f"FC {self.config.access_key_id}:signature",
                "Content-Type": "application/json"
            },
            json=payload
        ) as response:
            if response.status >= 400:
                error_text = await response.text()
                raise RuntimeError(f"Function invocation failed: {error_text}")

            return await response.json()

    async def list_functions(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List functions in service."""
        service_name = service_name or self.config.service_name
        endpoint = f"/services/{service_name}/functions"

        response = await self._make_request("GET", endpoint)
        return response.get("functions", [])

    async def delete_function(self, function_name: str) -> None:
        """Delete FC function."""
        endpoint = f"/services/{self.config.service_name}/functions/{function_name}"
        await self._make_request("DELETE", endpoint)

    async def deploy_workflow(self, workflow_config: Dict[str, Any]) -> str:
        """Deploy workflow as FC function."""
        function_name = f"workflow-{workflow_config['name']}"

        # Create function configuration
        function_config = FCFunction(
            name=function_name,
            environment_variables={
                "WORKFLOW_CONFIG": json.dumps(workflow_config),
                "MAO_ENV": "fc"
            }
        )

        # Create the function
        await self.create_function(function_config)

        logger.info(f"Deployed workflow {workflow_config['name']} as FC function {function_name}")
        return function_name

    async def execute_workflow(self, workflow_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute deployed workflow."""
        function_name = f"workflow-{workflow_name}"

        payload = {
            "workflow_name": workflow_name,
            "inputs": inputs,
            "execution_mode": "fc"
        }

        return await self.invoke_function(function_name, payload)

    async def get_function_logs(self, function_name: str, request_id: str) -> List[str]:
        """Get function execution logs."""
        # In real implementation, this would query FC logs API
        # For demo, return placeholder logs
        return [
            f"[INFO] Function {function_name} started",
            f"[INFO] Processing request {request_id}",
            "[INFO] Workflow execution completed"
        ]

    async def health_check(self) -> bool:
        """Check FC service health."""
        try:
            await self._make_request("GET", "/services")
            return True
        except Exception as e:
            logger.error(f"FC health check failed: {e}")
            return False

    def create_deployment_script(self, workflow_config: Dict[str, Any], output_path: str) -> str:
        """Create deployment script for FC function.

        Args:
            workflow_config: Workflow configuration
            output_path: Path to save deployment script

        Returns:
            Path to created script
        """
        script_content = f"""#!/bin/bash
# MAO Function Compute Deployment Script
# Generated for workflow: {workflow_config['name']}

set -e

echo "🚀 Starting MAO FC deployment for {workflow_config['name']}"

# Set environment variables
export ALICLOUD_ACCOUNT_ID="{self.config.account_id}"
export ALICLOUD_ACCESS_KEY_ID="{self.config.access_key_id}"
export ALICLOUD_ACCESS_KEY_SECRET="{self.config.access_key_secret}"
export ALICLOUD_REGION="{self.config.region}"
export FC_SERVICE_NAME="{self.config.service_name}"

# Create service if it doesn't exist
echo "📦 Creating FC service..."
python -c "
import asyncio
from src.integrations.function_compute import FunctionComputeIntegration, FCConfig

async def create_service():
    config = FCConfig(
        account_id='$ALICLOUD_ACCOUNT_ID',
        access_key_id='$ALICLOUD_ACCESS_KEY_ID',
        access_key_secret='$ALICLOUD_ACCESS_KEY_SECRET',
        region='$ALICLOUD_REGION',
        service_name='$FC_SERVICE_NAME'
    )
    async with FunctionComputeIntegration(config) as fc:
        try:
            await fc.create_service()
            print('Service created successfully')
        except Exception as e:
            print(f'Service may already exist: {{e}}')

asyncio.run(create_service())
"

# Deploy workflow
echo "⚙️ Deploying workflow as FC function..."
python -c "
import asyncio
import json
from src.integrations.function_compute import FunctionComputeIntegration, FCConfig

async def deploy():
    config = FCConfig(
        account_id='$ALICLOUD_ACCOUNT_ID',
        access_key_id='$ALICLOUD_ACCESS_KEY_ID',
        access_key_secret='$ALICLOUD_ACCESS_KEY_SECRET',
        region='$ALICLOUD_REGION',
        service_name='$FC_SERVICE_NAME'
    )
    
    workflow_config = {json.dumps(workflow_config)}
    
    async with FunctionComputeIntegration(config) as fc:
        function_name = await fc.deploy_workflow(workflow_config)
        print(f'Workflow deployed as function: {{function_name}}')

asyncio.run(deploy())
"

echo "✅ Deployment completed successfully!"
echo "🌐 API endpoints available at: http://localhost:8000"
echo "📊 Health check: http://localhost:8000/health"
"""

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Write script
        with open(output_path, 'w') as f:
            f.write(script_content)

        # Make executable
        os.chmod(output_path, 0o755)

        logger.info(f"Created deployment script: {output_path}")
        return output_path

    def create_dockerfile(self, workflow_config: Dict[str, Any], output_path: str) -> str:
        """Create Dockerfile for FC function deployment.

        Args:
            workflow_config: Workflow configuration
            output_path: Path to save Dockerfile

        Returns:
            Path to created Dockerfile
        """
        dockerfile_content = f"""# MAO Function Compute Dockerfile
# Generated for workflow: {workflow_config['name']}

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY pyproject.toml .

# Install the application
RUN pip install -e .

# Set environment variables
ENV MAO_ENV=fc
ENV WORKFLOW_CONFIG='{json.dumps(workflow_config)}'

# Expose port (for local development)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["python", "-m", "src.integrations.function_compute"]
"""

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Write Dockerfile
        with open(output_path, 'w') as f:
            f.write(dockerfile_content)

        logger.info(f"Created Dockerfile: {output_path}")
        return output_path


async def main():
    """Main function for running FC integration."""
    import argparse

    parser = argparse.ArgumentParser(description="MAO Function Compute Integration")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--create-deployment", help="Create deployment script for workflow")
    parser.add_argument("--workflow-config", help="Path to workflow config JSON file")

    args = parser.parse_args()

    # Create FC integration
    fc = FunctionComputeIntegration()

    if args.create_deployment and args.workflow_config:
        # Load workflow config
        with open(args.workflow_config, 'r') as f:
            workflow_config = json.load(f)

        # Create deployment script
        script_path = fc.create_deployment_script(workflow_config, args.create_deployment)
        print(f"Deployment script created: {script_path}")

        # Create Dockerfile
        dockerfile_path = fc.create_dockerfile(workflow_config, "Dockerfile.fc")
        print(f"Dockerfile created: {dockerfile_path}")

    else:
        # Start API server
        if FASTAPI_AVAILABLE:
            fc.start_api_server(host=args.host, port=args.port)
        else:
            logger.error("FastAPI not available, cannot start server")


if __name__ == "__main__":
    asyncio.run(main())