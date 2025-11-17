# Quickstart: Agent MCP Integration

**Feature**: Agent MCP Integration
**Date**: 2025-11-12

## Overview

This quickstart guide demonstrates how to configure and use agents with MCP (Model Context Protocol) integration. The feature enables seamless tool access across LLM, CLI, and Docker agents while maintaining backward compatibility.

## Prerequisites

- Python 3.11+
- Docker (for Docker agents)
- MCP-compatible services running

## Installation

1. **Install the platform**:
   ```bash
   pip install -e .
   ```

2. **Start MCP services** (example):
   ```bash
   # Start a file system MCP service
   docker run -p 3001:3001 mcp/filesystem-server

   # Start a git MCP service
   docker run -p 3002:3002 mcp/git-server
   ```

## Basic Usage

### 1. Configure an LLM Agent with MCP Tools

```python
from src.core.config import PlatformConfig
from src.agents.claude import ClaudeAgent

# Create platform configuration
config = PlatformConfig(
    agents=[
        {
            "name": "claude-with-tools",
            "type": "LLM",
            "provider": "anthropic",
            "model": "claude-3-sonnet-20240229",
            "api_key": "your-api-key-here",
            "mcp_address": "http://localhost:3001",
            "enable_mcp_tools": True
        }
    ]
)

# Initialize agent
agent = ClaudeAgent(config.agents[0])

# Execute with MCP tools
result = await agent.execute("List all files in the current directory")
print(result)
```

### 2. Configure a CLI Agent with MCP Integration

```python
from src.core.config import PlatformConfig
from src.agents.cli import CLIExecutionAgent

# CLI agent configuration
cli_config = {
    "name": "cli-with-mcp",
    "type": "CLI",
    "command": "python",
    "working_directory": "/app",
    "mcp_address": "http://localhost:3002",
    "enable_mcp_tools": True,
    "mcp_timeout": 30
}

agent = CLIExecutionAgent(cli_config)
result = await agent.execute("Run git status and show available tools")
```

### 3. Configure a Docker Agent with MCP Services

```python
from src.core.config import PlatformConfig
from src.agents.docker import DockerExecutionAgent

# Docker agent configuration
docker_config = {
    "name": "docker-with-mcp",
    "type": "DOCKER",
    "docker_image": "python:3.11-slim",
    "docker_command": "python -c 'import sys; print(sys.version)'",
    "mcp_address": "http://host.docker.internal:3001",
    "enable_mcp_tools": True,
    "docker_volumes": ["/app:/app"]
}

agent = DockerExecutionAgent(docker_config)
result = await agent.execute("Execute Python code with file system access")
```

## Advanced Configuration

### MCP Service Management

```python
from src.integrations.mcp.service_manager import MCPServiceManager

# Initialize service manager
service_manager = MCPServiceManager()

# Register MCP services
await service_manager.register_service(
    address="http://localhost:3001",
    service_id="filesystem-tools"
)

await service_manager.register_service(
    address="http://localhost:3002",
    service_id="git-tools"
)

# Check service health
health = await service_manager.check_health("filesystem-tools")
print(f"Service healthy: {health.healthy}")
```

### Workflow Integration

```python
from src.core.workflow import WorkflowEngine
from src.workflows.langgraph.workflow import LangGraphWorkflow

# Create workflow with MCP-enabled agents
workflow_config = {
    "name": "mcp-integrated-workflow",
    "agents": ["claude-with-tools", "cli-with-mcp"],
    "steps": [
        {
            "agent": "claude-with-tools",
            "task": "Analyze the codebase structure"
        },
        {
            "agent": "cli-with-mcp",
            "task": "Run tests and generate reports"
        }
    ]
}

workflow = LangGraphWorkflow(workflow_config)
result = await workflow.execute()
```

## API Usage

### REST API Examples

```bash
# Create an agent with MCP integration
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "api-agent",
    "type": "LLM",
    "provider": "anthropic",
    "model": "claude-3-sonnet-20240229",
    "mcp_address": "http://localhost:3001",
    "enable_mcp_tools": true
  }'

# Execute agent with MCP tools
curl -X POST http://localhost:8000/api/v1/agents/api-agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task": "List all Python files and analyze their structure",
    "mcp_tools": ["filesystem.read", "filesystem.list"]
  }'

# Register MCP service
curl -X POST http://localhost:8000/api/v1/mcp/services \
  -H "Content-Type: application/json" \
  -d '{
    "address": "http://localhost:3001",
    "service_id": "filesystem-service"
  }'

# Check MCP service health
curl http://localhost:8000/api/v1/mcp/services/filesystem-service/health
```

## CLI Usage

```bash
# Create agent with MCP integration
bug_fix agent create --config agent-config.yaml

# List available MCP services
bug_fix mcp services list

# Execute workflow with MCP tools
bug_fix workflow run --config workflow-config.yaml --enable-mcp

# Check MCP service status
bug_fix mcp services health filesystem-service
```

## Configuration Examples

### agent-config.yaml
```yaml
name: claude-mcp-agent
type: LLM
provider: anthropic
model: claude-3-sonnet-20240229
api_key: ${ANTHROPIC_API_KEY}
max_tokens: 4096
temperature: 0.7
timeout_seconds: 60
max_retries: 3
retry_delay: 1.0
mcp_address: http://localhost:3001
mcp_timeout: 30
mcp_retry_attempts: 3
enable_mcp_tools: true
```

### workflow-config.yaml
```yaml
name: code-analysis-workflow
agents:
  - claude-mcp-agent
  - cli-mcp-agent
steps:
  - agent: claude-mcp-agent
    task: Analyze the codebase and identify improvement opportunities
    mcp_tools: [filesystem.read, filesystem.search]
  - agent: cli-mcp-agent
    task: Run linting and format the code
    mcp_tools: [git.status, filesystem.write]
```

## Troubleshooting

### Common Issues

1. **MCP Service Connection Failed**
   ```python
   # Check service health
   health = await service_manager.check_health("service-id")
   if not health.healthy:
       print(f"Service error: {health.error_message}")
   ```

2. **Tool Not Available**
   ```python
   # List available tools
   tools = await agent.list_available_tools()
   print(f"Available tools: {tools}")
   ```

3. **Timeout Issues**
   ```python
   # Increase timeout settings
   agent_config = {
       "mcp_timeout": 60,
       "timeout_seconds": 120,
       "max_retries": 5
   }
   ```

### Debug Mode

Enable debug logging to troubleshoot MCP integration:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable MCP debug logs
import os
os.environ["MCP_DEBUG"] = "true"
```

## Migration from Legacy Agents

Existing agents continue to work without changes. To enable MCP integration:

1. Add `mcp_address` to agent configuration
2. Set `enable_mcp_tools: true` (default)
3. Optionally configure `mcp_timeout` and `mcp_retry_attempts`

Legacy agents without MCP configuration will work as before.

## Performance Optimization

- **Connection Pooling**: MCP connections are automatically pooled for reuse
- **Circuit Breaker**: Failed services are temporarily disabled to prevent cascading failures
- **Health Checks**: Services are monitored continuously with automatic recovery
- **Caching**: Tool metadata is cached to reduce discovery overhead

## Next Steps

- Explore [API Documentation](contracts/api.yaml) for complete API reference
- Review [Data Model](data-model.md) for detailed entity relationships
- Check [Research Findings](research.md) for implementation details
- Run the test suite: `pytest tests/integration/test_mcp_integration.py`