# Quick Start Guide: Multi-Agent Code Development Orchestration Platform

**Version**: 1.0.0
**Date**: 2025-11-12

## Overview

This guide will get you up and running with the Multi-Agent Code Development Orchestration Platform in under 10 minutes. The platform allows you to orchestrate multiple AI agents (Claude, Codex, Copilot) for automated code development workflows.

## Prerequisites

- **Python 3.11+** installed
- **Git** installed
- **Docker** (optional, for isolated execution)
- **API Keys** for AI providers you want to use:
  - Anthropic API key (for Claude)
  - OpenAI API key (for Codex)
  - GitHub Personal Access Token (for Copilot)

## Installation

### Option 1: From Source (Development)

```bash
# Clone the repository
git clone <repository-url>
cd agent-orchestration-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

### Option 2: Using Docker

```bash
# Build the Docker image
docker build -t agent-orchestration .

# Run the container
docker run -it --rm \
  -v $(pwd):/workspace \
  -e ANTHROPIC_API_KEY=your_key_here \
  agent-orchestration
```

## Configuration

### 1. Create Configuration File

Create a `config.yaml` file in your workspace:

```yaml
# Global configuration
global:
  workspace_dir: "/path/to/your/code"
  log_level: "INFO"
  max_concurrent_workflows: 5
  timeout_seconds: 300

# Agent configurations
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

# Workflow templates
workflows:
  code_review:
    description: "Automated code review workflow"
    agents: ["claude", "copilot"]
    steps:
      - name: "analyze_code"
        agent: "claude"
        prompt_template: "Analyze this code for quality issues: {{code}}"
        output_key: "analysis"
      - name: "suggest_improvements"
        agent: "copilot"
        prompt_template: "Based on this analysis: {{analysis}}, suggest specific improvements"
        output_key: "suggestions"

# Observability settings
observability:
  log_format: "json"
  metrics_enabled: true
  trace_enabled: true
  exporters:
    - type: "console"
```

### 2. Set Environment Variables

```bash
# Set your API keys
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
export GITHUB_TOKEN="your-github-token"
```

## Basic Usage

### CLI Mode

#### 1. Validate Configuration

```bash
# Validate your configuration file
agent-orchestration config validate --config config.yaml
```

#### 2. Register Agents

```bash
# Register Claude agent
agent-orchestration agent register claude --config config.yaml

# Register all configured agents
agent-orchestration agent register-all --config config.yaml
```

#### 3. Execute a Workflow

```bash
# Execute code review workflow
agent-orchestration workflow run code_review \
  --config config.yaml \
  --param code="def hello():\n    print('Hello, World!')" \
  --workspace /path/to/code
```

#### 4. Check Execution Status

```bash
# List running executions
agent-orchestration workflow list

# Get detailed status of specific execution
agent-orchestration workflow status <execution-id>
```

### API Mode

#### 1. Start the API Server

```bash
# Start FastAPI server
agent-orchestration api start --config config.yaml --host 0.0.0.0 --port 8000
```

#### 2. Health Check

```bash
curl http://localhost:8000/api/v1/health
```

#### 3. Execute Workflow via API

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

#### 4. Check Execution Status

```bash
# Get execution status
curl http://localhost:8000/api/v1/workflows/code_review/executions/{execution-id}

# Get execution logs
curl http://localhost:8000/api/v1/workflows/code_review/executions/{execution-id}/logs
```

## Example Workflows

### Code Review Workflow

```yaml
# In your config.yaml
workflows:
  code_review:
    description: "Comprehensive code review"
    agents: ["claude", "copilot"]
    steps:
      - name: "security_check"
        agent: "claude"
        prompt_template: "Check for security vulnerabilities: {{code}}"
        output_key: "security_issues"
      - name: "quality_analysis"
        agent: "claude"
        prompt_template: "Analyze code quality: {{code}}"
        output_key: "quality_score"
      - name: "improvement_suggestions"
        agent: "copilot"
        prompt_template: "Suggest improvements for: {{code}} based on quality: {{quality_score}}"
        output_key: "suggestions"
```

Execute it:

```bash
agent-orchestration workflow run code_review \
  --param code="$(cat your_file.py)" \
  --workspace .
```

### GitHub Task Development

```yaml
workflows:
  github_task:
    description: "Develop code for GitHub issue"
    agents: ["claude", "codex"]
    steps:
      - name: "analyze_issue"
        agent: "claude"
        prompt_template: "Analyze this GitHub issue and plan implementation: {{issue_description}}"
        output_key: "analysis"
      - name: "generate_code"
        agent: "codex"
        prompt_template: "Generate code for: {{analysis}} in {{language}}"
        output_key: "code"
      - name: "create_pr"
        agent: "copilot"
        prompt_template: "Create a pull request for the generated code: {{code}}"
        output_key: "pr_url"
```

## GitHub Actions Integration

### 1. Create GitHub Action Workflow

Create `.github/workflows/agent-orchestration.yml`:

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

### 2. Set Repository Secrets

In your GitHub repository settings, add these secrets:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GITHUB_TOKEN` (automatically available)

## Function Compute Deployment

### 1. Deploy to Alibaba Cloud FC

```bash
# Build and deploy
agent-orchestration deploy fc \
  --config config.yaml \
  --region cn-hangzhou \
  --service-name agent-orchestration
```

### 2. Invoke via API

```bash
curl -X POST https://your-fc-endpoint.com/workflows \
  -H "Content-Type: application/json" \
  -d '{"workflowId": "code_review", "parameters": {...}}'
```

## Troubleshooting

### Common Issues

#### Agent Registration Fails
```bash
# Check API key validity
agent-orchestration agent test claude --config config.yaml

# Verify network connectivity
curl -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
  https://api.anthropic.com/v1/messages
```

#### Workflow Execution Times Out
```bash
# Increase timeout in config
global:
  timeout_seconds: 600  # 10 minutes

# Check agent response times
agent-orchestration agent benchmark --config config.yaml
```

#### Docker Isolation Issues
```bash
# Run without Docker (development only)
export AGENT_ORCHESTRATION_ISOLATION= subprocess

# Check Docker daemon
docker ps
docker system info
```

### Debug Mode

Enable detailed logging:

```bash
export AGENT_ORCHESTRATION_LOG_LEVEL=DEBUG
agent-orchestration workflow run code_review --verbose
```

### Getting Help

```bash
# Show all commands
agent-orchestration --help

# Show command-specific help
agent-orchestration workflow --help
agent-orchestration agent --help
```

## Next Steps

1. **Customize Workflows**: Modify existing workflows or create new ones for your specific needs
2. **Add New Agents**: Extend the platform with additional AI providers
3. **Integrate with CI/CD**: Set up automated workflows for your development pipeline
4. **Monitor Performance**: Use the observability features to track usage and optimize workflows

For advanced usage and API reference, see the full documentation.