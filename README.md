# Agent Orchestration Platform

[![CI](https://github.com/your-org/agent-orchestration/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/agent-orchestration/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agent-orchestration)](https://pypi.org/project/agent-orchestration/)
[![Docker](https://img.shields.io/docker/v/agent-orchestration/latest)](https://hub.docker.com/r/agent-orchestration)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A multi-agent code development orchestration platform that supports CLI execution, GitHub Actions integration, and Function Computing deployment. Enables developers to create and execute complex development workflows using multiple AI agents (Claude, Codex, Copilot) with comprehensive observability and MCP tool integration.

## Features

- **Multi-Agent Support**: Integrate Claude, Codex, Copilot, and custom agents
- **Workflow Orchestration**: Simple workflows and LangGraph-based complex workflows
- **Multiple Deployment Modes**:
  - CLI for local development
  - GitHub Actions for CI/CD integration
  - Function Computing for serverless execution
- **Model Context Protocol (MCP)**: Extend agent capabilities with custom tools
- **Comprehensive Observability**: Structured logging, metrics, and monitoring
- **Security**: Encrypted credential storage and secure API key management
- **Docker Support**: Containerized deployment and development environment

## Quick Start

### Installation

```bash
# Install from PyPI
pip install agent-orchestration

# Or install from source
git clone https://github.com/your-org/agent-orchestration.git
cd agent-orchestration
pip install -e .
```

### Basic Usage

1. **Configure your agents**:
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml with your API keys
   ```

2. **Run a workflow**:
   ```bash
   agent-orchestration workflow run code-review --repo https://github.com/your-org/your-repo
   ```

## Configuration

Create a `config.yaml` file based on `config.example.yaml`:

```yaml
version: "1.0"
environment: "development"

agents:
  claude:
    name: "claude"
    provider: "anthropic"
    model: "claude-3-sonnet-20240229"
    api_key: "${ANTHROPIC_API_KEY}"

workflows:
  code-review:
    name: "code-review"
    type: "simple"
    agent: "claude"
    steps:
      - name: "analyze"
        action: "analyze_codebase"
      - name: "review"
        action: "review_changes"
```

## Development

### Prerequisites

- Python 3.11+
- Git
- Docker (optional)

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/your-org/agent-orchestration.git
cd agent-orchestration

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .[dev,test]

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linting
pre-commit run --all-files
```

### Docker Development

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build manually
docker build -t agent-orchestration .
docker run agent-orchestration --help
```

## CLI Commands

```bash
agent-orchestration --help

# Workflow management
agent-orchestration workflow list
agent-orchestration workflow run <name> [options]
agent-orchestration workflow create <name> [options]

# Agent management
agent-orchestration agent list
agent-orchestration agent test <name>
agent-orchestration agent configure <name>

# MCP tools
agent-orchestration mcp list
agent-orchestration mcp enable <tool>
agent-orchestration mcp server start
```

## GitHub Actions Integration

Add to your repository's `.github/workflows/`:

```yaml
name: Code Review
on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Agent Code Review
        uses: agent-orchestration/action@v1
        with:
          workflow: code-review
          config: .github/agent-config.yaml
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Function Computing Deployment

Deploy to Alibaba Cloud FC:

```bash
# Build and deploy
agent-orchestration fc deploy --config config.yaml

# Invoke workflow
curl -X POST https://your-fc-endpoint.com/workflow \
  -H "Content-Type: application/json" \
  -d '{"workflow": "code-review", "parameters": {...}}'
```

## Architecture

```
src/
├── cli/              # Command-line interface
├── core/             # Core abstractions and infrastructure
│   ├── config.py     # Configuration management
│   ├── workflow.py   # Workflow orchestration
│   ├── execution.py  # Execution context and isolation
│   ├── observability.py # Logging and metrics
│   └── logging.py    # Structured logging
├── agents/           # AI agent implementations
├── workflows/        # Workflow definitions and templates
├── api/              # FastAPI application and routes
├── mcp/              # Model Context Protocol integration
└── integrations/     # External service integrations
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- 📖 [Documentation](https://agent-orchestration.readthedocs.io/)
- 🐛 [Issue Tracker](https://github.com/your-org/agent-orchestration/issues)
- 💬 [Discussions](https://github.com/your-org/agent-orchestration/discussions)