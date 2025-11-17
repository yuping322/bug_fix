"""
Configuration schema and validation for the agent orchestration platform.

This module defines the configuration structure using Pydantic models
for type safety and validation.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class AgentConfig(BaseModel):
    """Configuration for a single AI agent."""

    name: str = Field(..., description="Agent name/identifier")
    type: str = Field("llm", description="Agent type (llm, cli, docker)")
    provider: Optional[str] = Field(None, description="AI provider (anthropic, openai, etc.) - for LLM agents")
    model: Optional[str] = Field(None, description="Model name/version - for LLM agents")
    api_key: Optional[str] = Field(None, description="API key (can be set via env var) - for LLM agents")
    base_url: Optional[str] = Field(None, description="Custom API base URL - for LLM agents")
    max_tokens: int = Field(4096, description="Maximum tokens per request - for LLM agents")
    temperature: float = Field(0.7, description="Sampling temperature - for LLM agents")
    timeout: int = Field(60, description="Request timeout in seconds")
    retry_attempts: int = Field(3, description="Number of retry attempts")
    retry_delay: float = Field(1.0, description="Delay between retries in seconds")

    # CLI agent specific configuration
    command: Optional[str] = Field(None, description="CLI command to execute - for CLI agents")
    working_directory: Optional[str] = Field(None, description="Working directory for CLI execution - for CLI agents")
    environment_variables: Optional[Dict[str, str]] = Field(None, description="Environment variables for CLI execution - for CLI agents")

    # Docker agent specific configuration
    docker_image: Optional[str] = Field(None, description="Docker image to use - for Docker agents")
    docker_command: Optional[str] = Field(None, description="Command to run in Docker container - for Docker agents")
    docker_environment: Optional[Dict[str, str]] = Field(None, description="Environment variables for Docker execution - for Docker agents")
    docker_volumes: Optional[Dict[str, str]] = Field(None, description="Volume mounts for Docker execution - for Docker agents")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        """Validate agent type is supported."""
        supported_types = {"llm", "cli", "docker"}
        if v not in supported_types:
            raise ValueError(
                f"Agent type {v} not supported. Must be one of "
                f"{supported_types}"
            )
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v):
        """Validate provider is supported for LLM agents."""
        if v is None:
            return v  # Allow None for non-LLM agents
        supported_providers = {"anthropic", "openai", "azure", "copilot", "github"}
        if v not in supported_providers:
            raise ValueError(
                f"Provider {v} not supported. Must be one of "
                f"{supported_providers}"
            )
        return v


class WorkflowConfig(BaseModel):
    """Configuration for a workflow."""

    name: str = Field(..., description="Workflow name")
    description: str = Field("", description="Workflow description")
    type: str = Field(..., description="Workflow type (simple, langgraph)")
    agent: str = Field(..., description="Default agent to use")
    steps: List[Dict[str, Any]] = Field(
        default_factory=list, description="Workflow steps"
    )
    timeout: int = Field(3600, description="Workflow timeout in seconds")
    max_retries: int = Field(3, description="Maximum workflow retries")
    parallel_execution: bool = Field(
        False, description="Enable parallel step execution"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field("INFO", description="Log level")
    format: str = Field("json", description="Log format (json, console)")
    file: Optional[str] = Field(None, description="Log file path")
    max_file_size: str = Field("10 MB", description="Maximum log file size")
    backup_count: int = Field(5, description="Number of backup log files")


class SecurityConfig(BaseModel):
    """Security configuration."""

    encryption_key: Optional[str] = Field(
        None, description="Encryption key for sensitive data"
    )
    credential_store: str = Field("local", description="Credential storage method")
    token_expiry: int = Field(3600, description="Token expiry in seconds")


class APIConfig(BaseModel):
    """API server configuration."""

    host: str = Field("0.0.0.0", description="API server host")
    port: int = Field(8000, description="API server port")
    workers: int = Field(4, description="Number of API workers")
    reload: bool = Field(False, description="Enable auto-reload in development")


class MCPConfig(BaseModel):
    """Model Context Protocol configuration."""

    enabled: bool = Field(False, description="Enable MCP integration")
    server_url: Optional[str] = Field(None, description="MCP server URL")
    tools: List[str] = Field(default_factory=list, description="Enabled MCP tools")


class Config(BaseModel):
    """Main configuration schema."""

    version: str = Field("1.0", description="Configuration version")

    agents: Dict[str, AgentConfig] = Field(
        default_factory=dict, description="Agent configurations"
    )
    workflows: Dict[str, WorkflowConfig] = Field(
        default_factory=dict, description="Workflow configurations"
    )

    logging: LoggingConfig = Field(
        default_factory=lambda: LoggingConfig(),
        description="Logging configuration"
    )
    security: SecurityConfig = Field(
        default_factory=lambda: SecurityConfig(),
        description="Security configuration"
    )
    api: APIConfig = Field(
        default_factory=lambda: APIConfig(),
        description="API configuration"
    )
    mcp: MCPConfig = Field(
        default_factory=lambda: MCPConfig(),
        description="MCP configuration"
    )

    # Environment-specific overrides
    environment: str = Field(
        "development", description="Environment (development, staging, production)"
    )

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        json_encoders = {
            Path: str,
        }


# Default configuration
DEFAULT_CONFIG = Config(
    version="1.0",
    environment="development",
    agents={
        "claude": AgentConfig(
            name="claude",
            type="llm",
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            max_tokens=4096,
            temperature=0.7,
            api_key=None,
            base_url=None,
            timeout=60,
            retry_attempts=3,
            retry_delay=1.0,
        ),
        "gpt4": AgentConfig(
            name="gpt4",
            type="llm",
            provider="openai",
            model="gpt-4",
            max_tokens=4096,
            temperature=0.7,
            api_key=None,
            base_url=None,
            timeout=60,
            retry_attempts=3,
            retry_delay=1.0,
        ),
        "claude_cli": AgentConfig(
            name="claude_cli",
            type="cli",
            command="claude code",
            working_directory="/tmp/workspace",
            timeout=300,
            retry_attempts=1,
            retry_delay=1.0,
        ),
        "docker_agent": AgentConfig(
            name="docker_agent",
            type="docker",
            docker_image="anthropic/claude-code:latest",
            docker_command="python /app/agent.py",
            timeout=300,
            retry_attempts=1,
            retry_delay=1.0,
        ),
    },
    workflows={
        "code-review": WorkflowConfig(
            name="code-review",
            description="Automated code review workflow",
            type="simple",
            agent="claude",
            steps=[
                {"name": "analyze", "action": "analyze_codebase"},
                {"name": "review", "action": "review_changes"},
                {"name": "suggest", "action": "suggest_improvements"},
            ],
            timeout=3600,
            max_retries=3,
            parallel_execution=False,
        ),
    },
)
