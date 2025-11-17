# 快速入门：代理MCP集成

**功能**：代理MCP集成
**日期**：2025-11-12

## 概述

本快速入门指南演示了如何配置和使用支持MCP（模型上下文协议）集成的代理。该功能实现了LLM、CLI和Docker代理之间的无缝工具访问，同时保持向后兼容性。

## 先决条件

- Python 3.11+
- Docker（用于Docker代理）
- 运行中的MCP兼容服务

## 安装

1. **安装平台**：
   ```bash
   pip install -e .
   ```

2. **启动MCP服务**（示例）：
   ```bash
   # 启动文件系统MCP服务
   docker run -p 3001:3001 mcp/filesystem-server

   # 启动Git MCP服务
   docker run -p 3002:3002 mcp/git-server
   ```

## 基本用法

### 1. 配置带有MCP工具的LLM代理

```python
from src.core.config import PlatformConfig
from src.agents.claude import ClaudeAgent

# 创建平台配置
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

# 初始化代理
agent = ClaudeAgent(config.agents[0])

# 使用MCP工具执行
result = await agent.execute("List all files in the current directory")
print(result)
```

### 2. 配置带有MCP集成的CLI代理

```python
from src.core.config import PlatformConfig
from src.agents.cli import CLIExecutionAgent

# CLI代理配置
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

### 3. 配置带有MCP服务的Docker代理

```python
from src.core.config import PlatformConfig
from src.agents.docker import DockerExecutionAgent

# Docker代理配置
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

## 高级配置

### MCP服务管理

```python
from src.integrations.mcp.service_manager import MCPServiceManager

# 初始化服务管理器
service_manager = MCPServiceManager()

# 注册MCP服务
await service_manager.register_service(
    address="http://localhost:3001",
    service_id="filesystem-tools"
)

await service_manager.register_service(
    address="http://localhost:3002",
    service_id="git-tools"
)

# 检查服务健康状态
health = await service_manager.check_health("filesystem-tools")
print(f"Service healthy: {health.healthy}")
```

### 工作流集成

```python
from src.core.workflow import WorkflowEngine
from src.workflows.langgraph.workflow import LangGraphWorkflow

# 创建带有MCP启用代理的工作流
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

## API使用

### REST API示例

```bash
# 创建带有MCP集成的代理
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

# 使用MCP工具执行代理
curl -X POST http://localhost:8000/api/v1/agents/api-agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task": "List all Python files and analyze their structure",
    "mcp_tools": ["filesystem.read", "filesystem.list"]
  }'

# 注册MCP服务
curl -X POST http://localhost:8000/api/v1/mcp/services \
  -H "Content-Type: application/json" \
  -d '{
    "address": "http://localhost:3001",
    "service_id": "filesystem-service"
  }'

# 检查MCP服务健康状态
curl http://localhost:8000/api/v1/mcp/services/filesystem-service/health
```

## CLI使用

```bash
# 创建带有MCP集成的代理
bug_fix agent create --config agent-config.yaml

# 列出可用的MCP服务
bug_fix mcp services list

# 使用MCP工具执行工作流
bug_fix workflow run --config workflow-config.yaml --enable-mcp

# 检查MCP服务状态
bug_fix mcp services health filesystem-service
```

## 配置示例

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

## 故障排除

### 常见问题

1. **MCP服务连接失败**
   ```python
   # 检查服务健康状态
   health = await service_manager.check_health("service-id")
   if not health.healthy:
       print(f"Service error: {health.error_message}")
   ```

2. **工具不可用**
   ```python
   # 列出可用工具
   tools = await agent.list_available_tools()
   print(f"Available tools: {tools}")
   ```

3. **超时问题**
   ```python
   # 增加超时设置
   agent_config = {
       "mcp_timeout": 60,
       "timeout_seconds": 120,
       "max_retries": 5
   }
   ```

### 调试模式

启用调试日志来排除MCP集成故障：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 启用MCP调试日志
import os
os.environ["MCP_DEBUG"] = "true"
```

## 从遗留代理迁移

现有代理无需更改即可继续工作。要启用MCP集成：

1. 在代理配置中添加 `mcp_address`
2. 设置 `enable_mcp_tools: true`（默认值）
3. 可选配置 `mcp_timeout` 和 `mcp_retry_attempts`

没有MCP配置的遗留代理将按以前的方式工作。

## 性能优化

- **连接池化**：MCP连接自动池化以供重用
- **断路器**：失败的服务被临时禁用以防止级联故障
- **健康检查**：服务持续监控并自动恢复
- **缓存**：工具元数据被缓存以减少发现开销

## 后续步骤

- 探索[API文档](contracts/api.yaml)以获取完整的API参考
- 查看[数据模型](data-model.md)以了解详细的实体关系
- 检查[研究发现](research.md)以获取实现细节
- 运行测试套件：`pytest tests/integration/test_mcp_integration.py`