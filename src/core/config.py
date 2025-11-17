"""Configuration management system for the multi-agent orchestration platform.

This module provides hierarchical configuration management with support for
YAML/JSON files, environment variable overrides, and validation.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
import yaml

from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError

# Import agent types to avoid circular imports
from src.agents.base import AgentConfig, AgentType, AgentProvider


class GlobalConfig(BaseModel):
    """Global platform configuration."""

    workspace_dir: str = Field(..., description="Default workspace directory")
    log_level: str = Field("INFO", description="Logging level")
    max_concurrent_workflows: int = Field(10, ge=1, le=100, description="Maximum concurrent workflows")
    timeout_seconds: int = Field(300, ge=10, le=3600, description="Default timeout for operations")
    enable_metrics: bool = Field(True, description="Enable metrics collection")
    enable_tracing: bool = Field(True, description="Enable distributed tracing")


class AgentConfigEntry(BaseModel):
    """Configuration for a single agent."""

    name: str = Field(..., description="Agent name")
    provider: str = Field(..., description="AI provider (anthropic, openai, github)")
    model: str = Field(..., description="Model identifier")
    api_key: Optional[str] = Field(None, description="API key (can be env var)")
    max_tokens: int = Field(4096, ge=1, description="Maximum tokens per request")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Creativity parameter")
    timeout_seconds: int = Field(60, ge=10, le=300, description="Request timeout")
    enabled: bool = Field(True, description="Whether agent is enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def to_agent_config(self) -> AgentConfig:
        """Convert the config entry to an AgentConfig instance.

        Returns:
            AgentConfig: Agent configuration instance
        """
        return AgentConfig(
            name=self.name,
            type=AgentType.LLM,  # All entries are currently LLM agents
            provider=AgentProvider(self.provider) if self.provider else None,
            model=self.model,
            api_key=self.api_key,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            timeout_seconds=self.timeout_seconds,
        )


class WorkflowConfigEntry(BaseModel):
    """Configuration for a single workflow."""

    name: str = Field(..., description="Workflow name")
    type: str = Field(..., description="Workflow type (simple, langgraph)")
    description: str = Field("", description="Workflow description")
    agents: List[str] = Field(default_factory=list, description="Required agents")
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="Workflow steps configuration")
    config: Dict[str, Any] = Field(default_factory=dict, description="Workflow-specific config")
    enabled: bool = Field(True, description="Whether workflow is enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    log_level: str = Field("INFO", description="Logging level")
    log_format: str = Field("json", description="Log format (json, text)")
    log_file: Optional[str] = Field(None, description="Log file path")
    metrics_enabled: bool = Field(True, description="Enable metrics")
    metrics_port: int = Field(9090, ge=1024, le=65535, description="Metrics server port")
    tracing_enabled: bool = Field(True, description="Enable tracing")
    tracing_exporter: str = Field("console", description="Tracing exporter (console, jaeger, zipkin)")


class DeploymentConfig(BaseModel):
    """Deployment-specific configuration."""

    environment: str = Field("development", description="Deployment environment")
    docker_enabled: bool = Field(False, description="Enable Docker isolation")
    function_compute_enabled: bool = Field(False, description="Enable Function Compute")
    github_actions_enabled: bool = Field(False, description="Enable GitHub Actions integration")
    max_memory_mb: int = Field(1024, ge=128, description="Maximum memory usage in MB")
    max_cpu_percent: int = Field(80, ge=1, le=100, description="Maximum CPU usage percentage")


class PlatformConfig(BaseModel):
    """Complete platform configuration."""

    version: str = Field("1.0", description="Configuration version")
    global_: GlobalConfig = Field(..., alias="global", description="Global configuration")
    agents: Dict[str, AgentConfigEntry] = Field(default_factory=dict, description="Agent configurations")
    workflows: Dict[str, WorkflowConfigEntry] = Field(default_factory=dict, description="Workflow configurations")
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig, description="Observability settings")
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig, description="Deployment settings")

    model_config = ConfigDict(
        validate_by_name=True,
    )

    @field_validator("version")
    @classmethod
    def validate_version(cls, v):
        """Validate version format."""
        if not v.replace(".", "").replace("-", "").replace("_", "").isalnum():
            raise ValueError("Version must be a valid semantic version")
        return v


class ConfigManager:
    """Configuration manager for loading, validating, and managing platform config."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize the configuration manager.

        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file or self._find_config_file()
        self._config: Optional[PlatformConfig] = None
        self._last_load_time: Optional[float] = None

    def _find_config_file(self) -> str:
        """Find configuration file in standard locations.

        Returns:
            str: Path to configuration file

        Raises:
            FileNotFoundError: If no config file is found
        """
        search_paths = [
            Path.cwd() / "config.yaml",
            Path.cwd() / "config.yml",
            Path.cwd() / "config.json",
            Path.home() / ".agent-orchestration" / "config.yaml",
            Path.home() / ".agent-orchestration" / "config.yml",
            Path.home() / ".agent-orchestration" / "config.json",
        ]

        for path in search_paths:
            if path.exists():
                return str(path)

        raise FileNotFoundError("No configuration file found in standard locations")

    def load_config(self, force_reload: bool = False) -> PlatformConfig:
        """Load configuration from file.

        Args:
            force_reload: Force reload even if already loaded

        Returns:
            PlatformConfig: Loaded and validated configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValidationError: If config is invalid
            ValueError: If config format is unsupported
        """
        if self._config is not None and not force_reload:
            return self._config

        if not Path(self.config_file).exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")

        # Load file based on extension
        file_path = Path(self.config_file)
        if file_path.suffix.lower() in [".yaml", ".yml"]:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        elif file_path.suffix.lower() == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")

        # Apply environment variable overrides
        data = self._apply_env_overrides(data)

        # Validate and create config object
        try:
            self._config = PlatformConfig(**data)
            self._last_load_time = file_path.stat().st_mtime
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e}") from e

        return self._config

    def _apply_env_overrides(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration.

        Args:
            data: Raw configuration data

        Returns:
            Dict: Configuration with environment overrides applied
        """
        # Override agent API keys from environment
        if "agents" in data:
            for agent_name, agent_config in data["agents"].items():
                if "api_key" in agent_config:
                    api_key = agent_config["api_key"]
                    if isinstance(api_key, str) and api_key.startswith("${") and api_key.endswith("}"):
                        env_var = api_key[2:-1]  # Remove ${}
                        env_value = os.getenv(env_var)
                        if env_value:
                            agent_config["api_key"] = env_value

        # Override global settings from environment
        env_mappings = {
            "AGENT_ORCHESTRATION_WORKSPACE_DIR": ("global", "workspace_dir"),
            "AGENT_ORCHESTRATION_LOG_LEVEL": ("global", "log_level"),
            "AGENT_ORCHESTRATION_MAX_CONCURRENT": ("global", "max_concurrent_workflows"),
            "AGENT_ORCHESTRATION_TIMEOUT": ("global", "timeout_seconds"),
            "AGENT_ORCHESTRATION_METRICS_ENABLED": ("observability", "metrics_enabled"),
            "AGENT_ORCHESTRATION_TRACING_ENABLED": ("observability", "tracing_enabled"),
        }

        for env_var, (section, key) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                if section not in data:
                    data[section] = {}
                # Convert string values to appropriate types
                if key in ["max_concurrent_workflows", "timeout_seconds", "metrics_port"]:
                    data[section][key] = int(env_value)
                elif key in ["metrics_enabled", "tracing_enabled"]:
                    data[section][key] = env_value.lower() in ("true", "1", "yes")
                else:
                    data[section][key] = env_value

        return data

    def save_config(self, config: PlatformConfig, file_path: Optional[str] = None) -> None:
        """Save configuration to file.

        Args:
            config: Configuration to save
            file_path: Optional file path (uses current config_file if not provided)
        """
        save_path = file_path or self.config_file
        file_path = Path(save_path)

        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and save
        data = config.dict(by_alias=True)

        if file_path.suffix.lower() in [".yaml", ".yml"]:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        elif file_path.suffix.lower() == ".json":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")

        self._config = config
        self._last_load_time = file_path.stat().st_mtime

    def get_config(self) -> PlatformConfig:
        """Get current configuration, loading if necessary.

        Returns:
            PlatformConfig: Current configuration
        """
        return self.load_config()

    def is_config_changed(self) -> bool:
        """Check if configuration file has been modified since last load.

        Returns:
            bool: True if config file has changed
        """
        if not self.config_file or not Path(self.config_file).exists():
            return False

        current_mtime = Path(self.config_file).stat().st_mtime
        return self._last_load_time is None or current_mtime > self._last_load_time

    def validate_config(self, config: PlatformConfig) -> List[str]:
        """Validate configuration for consistency and completeness.

        Args:
            config: Configuration to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check that all workflow agents exist
        agent_names = set(config.agents.keys())
        for workflow_name, workflow_config in config.workflows.items():
            missing_agents = set(workflow_config.agents) - agent_names
            if missing_agents:
                errors.append(f"Workflow '{workflow_name}' references unknown agents: {missing_agents}")

        # Check workspace directory exists or can be created
        workspace_path = Path(config.global_.workspace_dir)
        if not workspace_path.exists():
            try:
                workspace_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create workspace directory '{workspace_path}': {e}")

        # Check log file directory if specified
        if config.observability.log_file:
            log_path = Path(config.observability.log_file)
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create log directory '{log_path.parent}': {e}")

        return errors

    def create_default_config(self, workspace_dir: str = ".") -> PlatformConfig:
        """Create a default configuration.

        Args:
            workspace_dir: Workspace directory path

        Returns:
            PlatformConfig: Default configuration
        """
        return PlatformConfig(
            version="1.0",
            global_=GlobalConfig(
                workspace_dir=workspace_dir,
                log_level="INFO",
                max_concurrent_workflows=5,
                timeout_seconds=300,
            ),
            agents={},
            workflows={},
            observability=ObservabilityConfig(),
            deployment=DeploymentConfig(),
        )


# Global configuration manager instance
config_manager = ConfigManager()