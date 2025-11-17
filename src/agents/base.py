"""Agent abstraction layer for the multi-agent orchestration platform.

This module defines the base interfaces and abstractions for AI agents
used in the orchestration platform. It provides a consistent interface
across different AI providers (Claude, Codex, Copilot) while allowing
for provider-specific optimizations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
import time


class AgentStatus(str, Enum):
    """Enumeration of possible agent statuses."""
    UNREGISTERED = "unregistered"
    REGISTERING = "registering"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class AgentProvider(str, Enum):
    """Enumeration of supported AI providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GITHUB = "github"


class AgentType(str, Enum):
    """Enumeration of supported agent execution types."""
    LLM = "llm"  # Direct API calls to language models
    CLI = "cli"  # Subprocess execution of CLI tools
    DOCKER = "docker"  # Containerized execution in Docker


class AgentConfig(BaseModel):
    """Configuration for an AI agent.

    Contains provider-specific settings and operational parameters.
    """
    name: str = Field(..., description="Human-readable name for the agent")
    type: AgentType = Field(..., description="Type of agent execution")
    provider: Optional[AgentProvider] = Field(None, description="AI provider name (for LLM agents)")
    model: Optional[str] = Field(None, description="Model identifier for the provider (for LLM agents)")
    api_key: Optional[str] = Field(None, description="API key for authentication (for LLM agents)")
    max_tokens: int = Field(4096, ge=1, le=32768, description="Maximum tokens per request (for LLM agents)")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Creativity/randomness parameter (for LLM agents)")
    timeout_seconds: int = Field(60, ge=10, le=300, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay: float = Field(1.0, ge=0.1, le=60.0, description="Delay between retries in seconds")

    # CLI agent specific configuration
    command: Optional[str] = Field(None, description="CLI command to execute (for CLI agents)")
    working_directory: Optional[str] = Field(None, description="Working directory for CLI execution (for CLI agents)")
    environment_variables: Optional[Dict[str, str]] = Field(None, description="Environment variables for CLI execution (for CLI agents)")

    # Docker agent specific configuration
    docker_image: Optional[str] = Field(None, description="Docker image to use (for Docker agents)")
    docker_command: Optional[str] = Field(None, description="Command to run in Docker container (for Docker agents)")
    docker_environment: Optional[Dict[str, str]] = Field(None, description="Environment variables for Docker execution (for Docker agents)")
    docker_volumes: Optional[Dict[str, str]] = Field(None, description="Volume mounts for Docker execution (for Docker agents)")

    model_config = ConfigDict(
        use_enum_values=True,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the agent config to a dictionary.

        Returns:
            Dict: Dictionary representation of the config
        """
        data = self.model_dump()
        # Enum values are already strings due to use_enum_values=True
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        """Create an agent config from a dictionary.

        Args:
            data: Dictionary containing config data

        Returns:
            AgentConfig: New agent config instance

        Raises:
            ValueError: If the dictionary contains invalid data
        """
        # Convert string values back to enums
        if 'type' in data:
            data['type'] = AgentType(data['type'])
        if 'provider' in data and data['provider'] is not None:
            data['provider'] = AgentProvider(data['provider'])

        return cls(**data)


class AgentResponse(BaseModel):
    """Response from an AI agent execution.

    Contains the generated content and metadata about the execution.
    """
    content: str = Field(..., description="Generated content from the agent")
    tokens_used: int = Field(..., ge=0, description="Number of tokens consumed")
    finish_reason: str = Field(..., description="Reason the generation finished")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional response metadata")
    execution_time: float = Field(..., description="Time taken for execution in seconds")
    timestamp: float = Field(default_factory=time.time, description="Response timestamp")


class AgentCapabilities(BaseModel):
    """Capabilities supported by an agent.

    Defines what operations the agent can perform.
    """
    code_review: bool = Field(False, description="Can perform code review")
    code_generation: bool = Field(False, description="Can generate code")
    task_planning: bool = Field(False, description="Can plan development tasks")
    documentation: bool = Field(False, description="Can generate documentation")
    testing: bool = Field(False, description="Can generate tests")
    debugging: bool = Field(False, description="Can help with debugging")
    refactoring: bool = Field(False, description="Can suggest refactoring")
    analysis: bool = Field(False, description="Can analyze code/complexity")


class BaseAgent(ABC):
    """Abstract base class for AI agents.

    Defines the interface that all agent implementations must follow.
    Provides common functionality and error handling.
    """

    def __init__(self, config: AgentConfig):
        """Initialize the agent with configuration.

        Args:
            config: Agent configuration containing execution settings

        Raises:
            ValueError: If configuration is invalid
        """
        self.config = config
        self._validate_config()

    @abstractmethod
    def get_capabilities(self) -> AgentCapabilities:
        """Return the capabilities supported by this agent.

        Returns:
            AgentCapabilities: Object describing agent capabilities
        """
        pass

    @abstractmethod
    async def execute(self, prompt: str, **kwargs) -> AgentResponse:
        """Execute a prompt and return a structured response.

        Args:
            prompt: The prompt to execute
            **kwargs: Additional execution parameters

        Returns:
            AgentResponse: Structured response from the agent

        Raises:
            AgentExecutionError: If execution fails
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate the agent configuration.

        Returns:
            bool: True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        pass

    def _validate_config(self) -> None:
        """Internal configuration validation.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.config.name:
            raise ValueError("Agent name cannot be empty")

        # Validate based on agent type
        if self.config.type == AgentType.LLM:
            self._validate_llm_config()
        elif self.config.type == AgentType.CLI:
            self._validate_cli_config()
        elif self.config.type == AgentType.DOCKER:
            self._validate_docker_config()
        else:
            raise ValueError(f"Invalid agent type: {self.config.type}")

        # Common validations
        if not (10 <= self.config.timeout_seconds <= 300):
            raise ValueError("timeout_seconds must be between 10 and 300")

    def _validate_llm_config(self) -> None:
        """Validate LLM agent configuration."""
        if not self.config.provider:
            raise ValueError("LLM agents require a provider")

        # Check provider is valid (handle both enum and string values)
        valid_providers = [p.value if hasattr(p, 'value') else str(p) for p in AgentProvider]
        if self.config.provider not in valid_providers:
            raise ValueError(f"Invalid provider: {self.config.provider}")

        if not self.config.model:
            raise ValueError("LLM agents require a model")

        if not self.config.api_key:
            raise ValueError("LLM agents require an API key")

        if self.config.max_tokens < 1:
            raise ValueError("max_tokens must be positive")

        if not (0.0 <= self.config.temperature <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")

    def _validate_cli_config(self) -> None:
        """Validate CLI agent configuration."""
        if not self.config.command:
            raise ValueError("CLI agents require a command")

    def _validate_docker_config(self) -> None:
        """Validate Docker agent configuration."""
        if not self.config.docker_image:
            raise ValueError("Docker agents require a docker_image")

        if not self.config.docker_command:
            raise ValueError("Docker agents require a docker_command")

    async def health_check(self) -> AgentStatus:
        """Perform a health check on the agent.

        Returns:
            AgentStatus: Current health status of the agent
        """
        try:
            # Simple health check by attempting a minimal prompt
            test_prompt = "Hello"
            start_time = time.time()
            response = await self.execute(test_prompt)
            execution_time = time.time() - start_time

            # Check if response is reasonable
            if response.content and len(response.content.strip()) > 0:
                return AgentStatus.ACTIVE
            else:
                return AgentStatus.ERROR

        except Exception:
            return AgentStatus.ERROR

    async def test_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to the agent's external service.

        Returns:
            Dict containing connectivity test results with keys:
            - success: bool indicating if test passed
            - response_time: float response time in seconds (if applicable)
            - error: error message if test failed (if applicable)
        """
        start_time = time.time()
        try:
            # Default implementation - assume connectivity is OK
            # Subclasses should override with actual connectivity tests
            response_time = time.time() - start_time
            return {
                "success": True,
                "response_time": response_time,
            }
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "success": False,
                "response_time": response_time,
                "error": str(e),
            }

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the agent provider.

        Returns:
            Dict containing provider metadata
        """
        info = {
            "type": self.config.type,
            "name": self.config.name,
            "capabilities": self.get_capabilities().dict(),
            "config": {
                "timeout_seconds": self.config.timeout_seconds,
                "max_retries": self.config.max_retries,
                "retry_delay": self.config.retry_delay,
            }
        }

        # Add type-specific information
        if self.config.type == AgentType.LLM:
            info.update({
                "provider": self.config.provider,
                "model": self.config.model,
                "config": {
                    **info["config"],
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                }
            })
        elif self.config.type == AgentType.CLI:
            info.update({
                "command": self.config.command,
                "working_directory": self.config.working_directory,
            })
        elif self.config.type == AgentType.DOCKER:
            info.update({
                "docker_image": self.config.docker_image,
                "docker_command": self.config.docker_command,
            })

        return info


class LLMAgent(BaseAgent):
    """Base class for LLM-based agents that make direct API calls."""

    def __init__(self, config: AgentConfig):
        """Initialize the LLM agent with configuration.

        Args:
            config: Agent configuration with LLM settings

        Raises:
            ValueError: If configuration is invalid for LLM agent
        """
        if config.type != AgentType.LLM:
            raise ValueError(f"LLMAgent requires type='{AgentType.LLM}', got '{config.type}'")
        super().__init__(config)


class CLIAgent(BaseAgent):
    """Base class for CLI-based agents that execute subprocess commands."""

    def __init__(self, config: AgentConfig):
        """Initialize the CLI agent with configuration.

        Args:
            config: Agent configuration with CLI settings

        Raises:
            ValueError: If configuration is invalid for CLI agent
        """
        if config.type != AgentType.CLI:
            raise ValueError(f"CLIAgent requires type='{AgentType.CLI}', got '{config.type}'")
        super().__init__(config)


class DockerAgent(BaseAgent):
    """Base class for Docker-based agents that execute in containers."""

    def __init__(self, config: AgentConfig):
        """Initialize the Docker agent with configuration.

        Args:
            config: Agent configuration with Docker settings

        Raises:
            ValueError: If configuration is invalid for Docker agent
        """
        if config.type != AgentType.DOCKER:
            raise ValueError(f"DockerAgent requires type='{AgentType.DOCKER}', got '{config.type}'")
        super().__init__(config)


class AgentExecutionError(Exception):
    """Exception raised when agent execution fails."""
    pass


class AgentRegistrationError(Exception):
    """Exception raised when agent registration fails."""
    pass


class AgentNotFoundError(Exception):
    """Exception raised when an agent is not found."""
    pass


class AgentConfigError(Exception):
    """Exception raised when agent configuration is invalid."""
    pass


class AgentRegistry:
    """Registry for managing agent instances.

    Provides centralized management of agent registration, lookup, and lifecycle.
    Implements the AgentManagementContract interface.
    """

    def __init__(self):
        """Initialize the agent registry."""
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_configs: Dict[str, AgentConfig] = {}
        self._agent_health: Dict[str, Dict[str, Any]] = {}

    def register_agent(self, agent_config: AgentConfig) -> str:
        """Register a new agent with the system.

        Args:
            agent_config: Configuration for the agent to register

        Returns:
            str: Unique identifier for the registered agent

        Raises:
            AgentRegistrationError: If agent registration fails
        """
        try:
            # Validate configuration
            self.validate_agent_config(agent_config)

            # Check if agent already exists
            if agent_config.name in self._agents:
                raise AgentRegistrationError(f"Agent '{agent_config.name}' is already registered")

            # Create agent instance based on type and provider
            agent = self._create_agent_from_config(agent_config)

            # Register the agent
            self._agents[agent_config.name] = agent
            self._agent_configs[agent_config.name] = agent_config

            # Initialize health tracking
            self._agent_health[agent_config.name] = {
                "status": "unknown",
                "last_check": None,
                "response_time": None,
                "error_rate": 0.0,
                "details": {}
            }

            return agent_config.name

        except Exception as e:
            raise AgentRegistrationError(f"Failed to register agent: {str(e)}")

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the system.

        Args:
            agent_id: Unique identifier of the agent to unregister

        Returns:
            bool: True if agent was successfully unregistered

        Raises:
            AgentNotFoundError: If agent is not found
        """
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent '{agent_id}' not found")

        del self._agents[agent_id]
        del self._agent_configs[agent_id]
        if agent_id in self._agent_health:
            del self._agent_health[agent_id]

        return True

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by its identifier.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            BaseAgent instance or None if not found
        """
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents.

        Returns:
            List of agent information dictionaries with keys:
            - id: Agent unique identifier
            - name: Agent display name
            - type: Agent type (LLM, etc.)
            - provider: Service provider (anthropic, openai, github)
            - status: Agent status (active, inactive, error)
            - capabilities: List of agent capabilities
        """
        agents = []
        for name, agent in self._agents.items():
            health = self._agent_health.get(name, {})
            agents.append({
                "id": name,
                "name": agent.config.name,
                "type": agent.config.type,
                "provider": agent.config.provider,
                "status": health.get("status", "unknown"),
                "capabilities": self._get_agent_capabilities(agent)
            })
        return agents

    def validate_agent_config(self, agent_config: AgentConfig) -> bool:
        """Validate agent configuration.

        Args:
            agent_config: Configuration to validate

        Returns:
            bool: True if configuration is valid

        Raises:
            AgentConfigError: If configuration is invalid
        """
        if not agent_config.name or not agent_config.name.strip():
            raise AgentConfigError("Agent name cannot be empty")

        if agent_config.type == AgentType.LLM:
            if not agent_config.provider:
                raise AgentConfigError("LLM agents must specify a provider")
            if not agent_config.model:
                raise AgentConfigError("LLM agents must specify a model")
            if not agent_config.api_key:
                raise AgentConfigError("LLM agents must specify an API key")

        # Validate temperature range
        if not (0.0 <= agent_config.temperature <= 2.0):
            raise AgentConfigError("Temperature must be between 0.0 and 2.0")

        # Validate max_tokens range
        if not (1 <= agent_config.max_tokens <= 32768):
            raise AgentConfigError("max_tokens must be between 1 and 32768")

        # Validate timeout
        if not (10 <= agent_config.timeout_seconds <= 300):
            raise AgentConfigError("timeout_seconds must be between 10 and 300")

        return True

    def test_agent_connectivity(self, agent_id: str) -> Dict[str, Any]:
        """Test connectivity to an agent service.

        Args:
            agent_id: Unique identifier of the agent to test

        Returns:
            Dict containing connectivity test results with keys:
            - success: bool indicating if test passed
            - response_time: float response time in seconds
            - error: error message if test failed
            - details: additional test details

        Raises:
            AgentNotFoundError: If agent is not found
        """
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent '{agent_id}' not found")

        agent = self._agents[agent_id]
        import asyncio
        import time

        start_time = time.time()
        try:
            result = asyncio.run(agent.test_connectivity())
            response_time = time.time() - start_time

            # Update health tracking
            self._agent_health[agent_id].update({
                "status": "healthy" if result["success"] else "unhealthy",
                "last_check": time.time(),
                "response_time": response_time,
                "details": result
            })

            return {
                "success": result["success"],
                "response_time": response_time,
                "error": result.get("error"),
                "details": result
            }

        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)

            # Update health tracking
            self._agent_health[agent_id].update({
                "status": "error",
                "last_check": time.time(),
                "response_time": response_time,
                "details": {"error": error_msg}
            })

            return {
                "success": False,
                "response_time": response_time,
                "error": error_msg,
                "details": {}
            }

    def get_agent_health(self, agent_id: str) -> Dict[str, Any]:
        """Get health status of an agent.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            Dict containing health information with keys:
            - status: Health status (healthy, degraded, unhealthy)
            - last_check: Timestamp of last health check
            - response_time: Average response time
            - error_rate: Error rate percentage
            - details: Additional health details

        Raises:
            AgentNotFoundError: If agent is not found
        """
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent '{agent_id}' not found")

        health = self._agent_health.get(agent_id, {
            "status": "unknown",
            "last_check": None,
            "response_time": None,
            "error_rate": 0.0,
            "details": {}
        })

        return {
            "status": health["status"],
            "last_check": health["last_check"],
            "response_time": health["response_time"],
            "error_rate": health["error_rate"],
            "details": health["details"]
        }

    def update_agent_config(self, agent_id: str, updates: Dict[str, Any]) -> bool:
        """Update configuration of an existing agent.

        Args:
            agent_id: Unique identifier of the agent
            updates: Configuration updates to apply

        Returns:
            bool: True if update was successful

        Raises:
            AgentNotFoundError: If agent is not found
            AgentConfigError: If updates are invalid
        """
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent '{agent_id}' not found")

        current_config = self._agent_configs[agent_id]

        # Create updated config
        try:
            updated_config_data = current_config.model_dump()
            updated_config_data.update(updates)
            updated_config = AgentConfig(**updated_config_data)

            # Validate the updated configuration
            self.validate_agent_config(updated_config)

            # Update the configuration
            self._agent_configs[agent_id] = updated_config

            # Recreate the agent with new config
            new_agent = self._create_agent_from_config(updated_config)
            self._agents[agent_id] = new_agent

            return True

        except Exception as e:
            raise AgentConfigError(f"Invalid configuration update: {str(e)}")

    def _create_agent_from_config(self, config: AgentConfig) -> BaseAgent:
        """Create an agent instance from configuration.

        Args:
            config: Agent configuration

        Returns:
            BaseAgent instance

        Raises:
            AgentConfigError: If agent creation fails
        """
        if config.type == AgentType.LLM:
            if config.provider == AgentProvider.ANTHROPIC:
                from .claude import ClaudeAgent
                return ClaudeAgent(config)
            elif config.provider == AgentProvider.OPENAI:
                from .codex import CodexAgent
                return CodexAgent(config)
            elif config.provider == AgentProvider.GITHUB:
                from .copilot import CopilotAgent
                return CopilotAgent(config)
            else:
                raise AgentConfigError(f"Unsupported LLM provider: {config.provider}")
        else:
            raise AgentConfigError(f"Unsupported agent type: {config.type}")

    def _get_agent_capabilities(self, agent: BaseAgent) -> List[str]:
        """Get capabilities of an agent.

        Args:
            agent: Agent instance

        Returns:
            List of capability strings
        """
        capabilities = []
        if hasattr(agent, 'execute'):
            capabilities.append("execute")
        if hasattr(agent, 'test_connectivity'):
            capabilities.append("connectivity_test")
        return capabilities

    # Legacy methods for backward compatibility
    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance (legacy method)."""
        if agent.config.name in self._agents:
            raise ValueError(f"Agent '{agent.config.name}' is already registered")
        self._agents[agent.config.name] = agent
        self._agent_configs[agent.config.name] = agent.config

    def unregister(self, name: str) -> None:
        """Unregister an agent (legacy method)."""
        self.unregister_agent(name)

    def get_agent_status(self, name: str) -> AgentStatus:
        """Get the status of a registered agent (legacy method)."""
        health = self.get_agent_health(name)
        return AgentStatus(health["status"])

    async def health_check_all(self) -> Dict[str, AgentStatus]:
        """Perform health check on all registered agents (legacy method)."""
        results = {}
        for name in self._agents.keys():
            health = self.get_agent_health(name)
            results[name] = AgentStatus(health["status"])
        return results

    def clear(self) -> None:
        """Clear all registered agents."""
        self._agents.clear()
        self._agent_configs.clear()
        self._agent_health.clear()


# Global agent registry instance
agent_registry = AgentRegistry()