# 快速入门指南：多智能体代码开发编排平台

**版本**：1.0.0
**日期**：2025-11-12

## 概述

本指南将在 10 分钟内让您开始使用多智能体代码开发编排平台。该平台允许您为自动化代码开发工作流编排多个 AI 智能体（Claude、Codex、Copilot）。

## 先决条件

- **Python 3.11+** 已安装
- **Git** 已安装
- **Docker**（可选，用于隔离执行）
- **API 密钥** 用于您想要使用的 AI 提供商：
  - Anthropic API 密钥（用于 Claude）
  - OpenAI API 密钥（用于 Codex）
  - GitHub 个人访问令牌（用于 Copilot）

## 安装

### 选项 1：从源码（开发）

```bash
# 克隆仓库
git clone <repository-url>
cd agent-orchestration-platform

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows 上：venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 以开发模式安装包
pip install -e .
```

### 选项 2：使用 Docker

```bash
# 构建 Docker 镜像
docker build -t agent-orchestration .

# 运行容器
docker run -it --rm \
  -v $(pwd):/workspace \
  -e ANTHROPIC_API_KEY=your_key_here \
  agent-orchestration
```

## 配置

### 1. 创建配置文件

在您的工作区中创建一个 `config.yaml` 文件：

```yaml
# 全局配置
global:
  workspace_dir: "/path/to/your/code"
  log_level: "INFO"
  max_concurrent_workflows: 5
  timeout_seconds: 300

# 智能体配置
agents:
  claude:
    api_key: "${ANTHROPIC_API_KEY}"
    model: "claude-3-sonnet-20240229"
    max_tokens: 4096
    temperature: 0.7

  codex:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
    max_tokens: 4096
    temperature: 0.3

  copilot:
    token: "${GITHUB_TOKEN}"
    model: "gpt-4"
    max_tokens: 4096

# 工作流模板
workflows:
  code_review:
    description: "自动化代码审查工作流"
    agents: ["claude", "copilot"]
    steps:
      - name: "analyze_code"
        agent: "claude"
        prompt_template: "分析此代码是否存在质量问题：{{code}}"
        output_key: "analysis"
      - name: "suggest_improvements"
        agent: "copilot"
        prompt_template: "基于此分析：{{analysis}}，建议具体改进"
        output_key: "suggestions"

# 可观测性设置
observability:
  log_format: "json"
  metrics_enabled: true
  trace_enabled: true
  exporters:
    - type: "console"
```

### 2. 设置环境变量

```bash
# 设置您的 API 密钥
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
export GITHUB_TOKEN="your-github-token"
```

## 基本用法

### CLI 模式

#### 1. 验证配置

```bash
# 验证您的配置文件
agent-orchestration config validate --config config.yaml
```

#### 2. 注册智能体

```bash
# 注册 Claude 智能体
agent-orchestration agent register claude --config config.yaml

# 注册所有配置的智能体
agent-orchestration agent register-all --config config.yaml
```

#### 3. 执行工作流

```bash
# 执行代码审查工作流
agent-orchestration workflow run code_review \
  --config config.yaml \
  --param code="def hello():\n    print('Hello, World!')" \
  --workspace /path/to/code
```

#### 4. 检查执行状态

```bash
# 列出正在运行的执行
agent-orchestration workflow list

# 获取特定执行的详细状态
agent-orchestration workflow status <execution-id>
```

### API 模式

#### 1. 启动 API 服务器

```bash
# 启动 FastAPI 服务器
agent-orchestration api start --config config.yaml --host 0.0.0.0 --port 8000
```

#### 2. 健康检查

```bash
curl http://localhost:8000/api/v1/health
```

#### 3. 通过 API 执行工作流

```bash
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "workflowId": "code_review",
    "parameters": {
      "code": "def hello():\n    print(\"Hello, World!\")"
    },
    "workspaceDir": "/path/to/code"
  }'
```

#### 4. 检查执行状态

```bash
# 获取执行状态
curl http://localhost:8000/api/v1/workflows/code_review/executions/{execution-id}

# 获取执行日志
curl http://localhost:8000/api/v1/workflows/code_review/executions/{execution-id}/logs
```

## 示例工作流

### 代码审查工作流

```yaml
# 在您的 config.yaml 中
workflows:
  code_review:
    description: "全面代码审查"
    agents: ["claude", "copilot"]
    steps:
      - name: "security_check"
        agent: "claude"
        prompt_template: "检查是否存在安全漏洞：{{code}}"
        output_key: "security_issues"
      - name: "quality_analysis"
        agent: "claude"
        prompt_template: "分析代码质量：{{code}}"
        output_key: "quality_score"
      - name: "improvement_suggestions"
        agent: "copilot"
        prompt_template: "为：{{code}} 基于质量：{{quality_score}} 建议改进"
        output_key: "suggestions"
```

执行它：

```bash
agent-orchestration workflow run code_review \
  --param code="$(cat your_file.py)" \
  --workspace .
```

### GitHub 任务开发

```yaml
workflows:
  github_task:
    description: "为 GitHub 问题开发代码"
    agents: ["claude", "codex"]
    steps:
      - name: "analyze_issue"
        agent: "claude"
        prompt_template: "分析此 GitHub 问题并计划实施：{{issue_description}}"
        output_key: "analysis"
      - name: "generate_code"
        agent: "codex"
        prompt_template: "为：{{analysis}} 在 {{language}} 中生成代码"
        output_key: "code"
      - name: "create_pr"
        agent: "copilot"
        prompt_template: "为此生成的代码创建拉取请求：{{code}}"
        output_key: "pr_url"
```

## GitHub Actions 集成

### 1. 创建 GitHub Action 工作流

创建 `.github/workflows/agent-orchestration.yml`：

```yaml
name: Agent Orchestration
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  code-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Agent Orchestration
        uses: your-org/agent-orchestration-action@v1
        with:
          workflow: code_review
          config: config.yaml
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

### 2. 设置仓库密钥

在您的 GitHub 仓库设置中，添加这些密钥：
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GITHUB_TOKEN`（自动可用）

## 函数计算部署

### 1. 部署到阿里云 FC

```bash
# 构建并部署
agent-orchestration deploy fc \
  --config config.yaml \
  --region cn-hangzhou \
  --service-name agent-orchestration
```

### 2. 通过 API 调用

```bash
curl -X POST https://your-fc-endpoint.com/workflows \
  -H "Content-Type: application/json" \
  -d '{"workflowId": "code_review", "parameters": {...}}'
```

## 故障排除

### 常见问题

#### 智能体注册失败
```bash
# 检查 API 密钥有效性
agent-orchestration agent test claude --config config.yaml

# 验证网络连接
curl -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
  https://api.anthropic.com/v1/messages
```

#### 工作流执行超时
```bash
# 在配置中增加超时
global:
  timeout_seconds: 600  # 10 分钟

# 检查智能体响应时间
agent-orchestration agent benchmark --config config.yaml
```

#### Docker 隔离问题
```bash
# 运行时不使用 Docker（仅开发）
export AGENT_ORCHESTRATION_ISOLATION= subprocess

# 检查 Docker 守护进程
docker ps
docker system info
```

### 调试模式

启用详细日志记录：

```bash
export AGENT_ORCHESTRATION_LOG_LEVEL=DEBUG
agent-orchestration workflow run code_review --verbose
```

### 获取帮助

```bash
# 显示所有命令
agent-orchestration --help

# 显示命令特定帮助
agent-orchestration workflow --help
agent-orchestration agent --help
```

## 后续步骤

1. **自定义工作流**：修改现有工作流或为您的特定需求创建新工作流
2. **添加新智能体**：使用其他 AI 提供商扩展平台
3. **与 CI/CD 集成**：为您的开发管道设置自动化工作流
4. **监控性能**：使用可观测性功能跟踪使用情况并优化工作流

有关高级使用和 API 参考，请参阅完整文档。