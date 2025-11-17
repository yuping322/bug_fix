import pytest
from unittest.mock import Mock
from typing import Dict, Any

from src.agents.base import AgentConfig, AgentType
from src.core.config import PlatformConfig, AgentConfigEntry
from pydantic import ValidationError


class TestAgentConfig:
    """Unit tests for agent configuration."""

    def test_agent_config_creation_valid(self):
        """Test creating a valid agent configuration."""
        config = AgentConfig(
            name="test-agent",
            type=AgentType.LLM,
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            api_key="test-key-123",
            max_tokens=4096,
            temperature=0.7,
            timeout_seconds=60,
        )

        assert config.name == "test-agent"
        assert config.type == AgentType.LLM
        assert config.provider == "anthropic"
        assert config.model == "claude-3-sonnet-20240229"
        assert config.api_key == "test-key-123"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.timeout_seconds == 60

    def test_agent_config_creation_minimal(self):
        """Test creating a minimal agent configuration."""
        config = AgentConfig(
            name="minimal-agent",
            type=AgentType.LLM,
            provider="anthropic",
            model="claude-3-haiku-20240307",
            api_key="test-key",
        )

        assert config.name == "minimal-agent"
        assert config.max_tokens == 4096  # Default value
        assert config.temperature == 0.7  # Default value
        assert config.timeout_seconds == 60  # Default value

    def test_agent_config_invalid_temperature(self):
        """Test agent configuration with invalid temperature."""
        with pytest.raises(ValidationError):
            AgentConfig(
                name="test-agent",
                type=AgentType.LLM,
                provider="anthropic",
                model="claude-3-sonnet-20240229",
                api_key="test-key",
                temperature=2.5,  # Invalid: > 2.0
            )

        with pytest.raises(ValidationError):
            AgentConfig(
                name="test-agent",
                type=AgentType.LLM,
                provider="anthropic",
                model="claude-3-sonnet-20240229",
                api_key="test-key",
                temperature=-0.1,  # Invalid: < 0.0
            )

    def test_agent_config_invalid_max_tokens(self):
        """Test agent configuration with invalid max_tokens."""
        with pytest.raises(ValueError):
            AgentConfig(
                name="test-agent",
                type=AgentType.LLM,
                provider="anthropic",
                model="claude-3-sonnet-20240229",
                api_key="test-key",
                max_tokens=0,  # Invalid: <= 0
            )

        with pytest.raises(ValueError):
            AgentConfig(
                name="test-agent",
                type=AgentType.LLM,
                provider="anthropic",
                model="claude-3-sonnet-20240229",
                api_key="test-key",
                max_tokens=100000,  # Invalid: > 32768
            )

    def test_agent_config_invalid_timeout(self):
        """Test agent configuration with invalid timeout."""
        with pytest.raises(ValueError):
            AgentConfig(
                name="test-agent",
                type=AgentType.LLM,
                provider="anthropic",
                model="claude-3-sonnet-20240229",
                api_key="test-key",
                timeout_seconds=0,  # Invalid: <= 0
            )

        with pytest.raises(ValueError):
            AgentConfig(
                name="test-agent",
                type=AgentType.LLM,
                provider="anthropic",
                model="claude-3-sonnet-20240229",
                api_key="test-key",
                timeout_seconds=3601,  # Invalid: > 3600
            )

    def test_agent_config_invalid_provider(self):
        """Test agent configuration with invalid provider."""
        with pytest.raises(ValueError):
            AgentConfig(
                name="test-agent",
                type=AgentType.LLM,
                provider="invalid-provider",  # Invalid provider
                model="some-model",
                api_key="test-key",
            )

    def test_agent_config_to_dict(self):
        """Test converting agent config to dictionary."""
        config = AgentConfig(
            name="test-agent",
            type=AgentType.LLM,
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            api_key="test-key-123",
            max_tokens=4096,
            temperature=0.7,
            timeout_seconds=60,
        )

        config_dict = config.to_dict()

        assert config_dict["name"] == "test-agent"
        assert config_dict["type"] == "llm"
        assert config_dict["provider"] == "anthropic"
        assert config_dict["model"] == "claude-3-sonnet-20240229"
        assert config_dict["api_key"] == "test-key-123"
        assert config_dict["max_tokens"] == 4096
        assert config_dict["temperature"] == 0.7
        assert config_dict["timeout_seconds"] == 60

    def test_agent_config_from_dict(self):
        """Test creating agent config from dictionary."""
        config_dict = {
            "name": "test-agent",
            "type": "llm",
            "provider": "anthropic",
            "model": "claude-3-sonnet-20240229",
            "api_key": "test-key-123",
            "max_tokens": 4096,
            "temperature": 0.7,
            "timeout_seconds": 60,
        }

        config = AgentConfig.from_dict(config_dict)

        assert config.name == "test-agent"
        assert config.type == AgentType.LLM
        assert config.provider == "anthropic"
        assert config.model == "claude-3-sonnet-20240229"
        assert config.api_key == "test-key-123"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.timeout_seconds == 60

    def test_agent_config_from_dict_invalid(self):
        """Test creating agent config from invalid dictionary."""
        invalid_config_dict = {
            "name": "",  # Invalid
            "type": "LLM",
            "provider": "anthropic",
            "model": "claude-3-sonnet-20240229",
            "api_key": "test-key",
        }

        with pytest.raises(ValueError):
            AgentConfig.from_dict(invalid_config_dict)


class TestAgentConfigEntry:
    """Unit tests for agent config entry."""

    def test_agent_config_entry_creation(self):
        """Test creating a valid agent config entry."""
        entry = AgentConfigEntry(
            name="test-agent",
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            api_key="test-key-123",
            max_tokens=4096,
            temperature=0.7,
            timeout_seconds=60,
            enabled=True,
        )

        assert entry.name == "test-agent"
        assert entry.provider == "anthropic"
        assert entry.model == "claude-3-sonnet-20240229"
        assert entry.api_key == "test-key-123"
        assert entry.max_tokens == 4096
        assert entry.temperature == 0.7
        assert entry.timeout_seconds == 60
        assert entry.enabled is True

    def test_agent_config_entry_to_agent_config(self):
        """Test converting config entry to agent config."""
        entry = AgentConfigEntry(
            name="test-agent",
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            api_key="test-key-123",
            max_tokens=4096,
            temperature=0.7,
            timeout_seconds=60,
            enabled=True,
        )

        agent_config = entry.to_agent_config()

        assert agent_config.name == "test-agent"
        assert agent_config.type == AgentType.LLM
        assert agent_config.provider == "anthropic"
        assert agent_config.model == "claude-3-sonnet-20240229"
        assert agent_config.api_key == "test-key-123"
        assert agent_config.max_tokens == 4096
        assert agent_config.temperature == 0.7
        assert agent_config.timeout_seconds == 60

    def test_agent_config_entry_disabled(self):
        """Test disabled agent config entry."""
        entry = AgentConfigEntry(
            name="disabled-agent",
            provider="anthropic",
            model="claude-3-haiku-20240307",
            api_key="test-key",
            enabled=False,
        )

        agent_config = entry.to_agent_config()

        assert agent_config.name == "disabled-agent"
        assert agent_config.provider == "anthropic"
        # Note: AgentConfig doesn't have an 'enabled' field - that's only on AgentConfigEntry


class TestPlatformConfigAgentIntegration:
    """Unit tests for platform config agent integration."""

    def test_platform_config_agent_conversion(self):
        """Test converting platform config agents to agent configs."""
        # Create mock platform config with agents
        config = Mock(spec=PlatformConfig)

        agent_entry = Mock(spec=AgentConfigEntry)
        agent_entry.name = "test-agent"
        agent_entry.provider = "anthropic"
        agent_entry.model = "claude-3-sonnet-20240229"
        agent_entry.api_key = "test-key"
        agent_entry.max_tokens = 4096
        agent_entry.temperature = 0.7
        agent_entry.timeout_seconds = 60
        agent_entry.enabled = True
        agent_entry.to_agent_config.return_value = AgentConfig(
            name="test-agent",
            type=AgentType.LLM,
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            api_key="test-key",
            max_tokens=4096,
            temperature=0.7,
            timeout_seconds=60,
        )

        config.agents = {"test-agent": agent_entry}

        # Test conversion
        agent_configs = {}
        for agent_name, agent_entry in config.agents.items():
            if agent_entry.enabled:
                agent_configs[agent_name] = agent_entry.to_agent_config()

        assert "test-agent" in agent_configs
        agent_config = agent_configs["test-agent"]
        assert agent_config.name == "test-agent"
        assert agent_config.provider == "anthropic"

    def test_platform_config_disabled_agents_filtered(self):
        """Test that disabled agents are filtered out."""
        config = Mock(spec=PlatformConfig)

        enabled_entry = Mock(spec=AgentConfigEntry)
        enabled_entry.name = "enabled-agent"
        enabled_entry.enabled = True
        enabled_entry.to_agent_config.return_value = AgentConfig(
            name="enabled-agent",
            type=AgentType.LLM,
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            api_key="test-key",
        )

        disabled_entry = Mock(spec=AgentConfigEntry)
        disabled_entry.name = "disabled-agent"
        disabled_entry.enabled = False

        config.agents = {
            "enabled-agent": enabled_entry,
            "disabled-agent": disabled_entry,
        }

        # Test filtering
        agent_configs = {}
        for agent_name, agent_entry in config.agents.items():
            if agent_entry.enabled:
                agent_configs[agent_name] = agent_entry.to_agent_config()

        assert "enabled-agent" in agent_configs
        assert "disabled-agent" not in agent_configs
        assert len(agent_configs) == 1