"""Contract tests for agent management.

This module defines the contract for agent management functionality.
All implementations must satisfy these contracts to be considered complete.
"""

import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import Mock

from src.core.config import PlatformConfig, AgentConfigEntry
from src.agents.base import BaseAgent, AgentRegistry, AgentConfig, AgentType, AgentRegistrationError, AgentNotFoundError, AgentConfigError


class AgentManagementContract:
    """Contract for agent management functionality.

    This abstract class defines the interface that all agent management
    implementations must provide.
    """

    def register_agent(self, agent_config: AgentConfig) -> str:
        """Register a new agent with the system.

        Args:
            agent_config: Configuration for the agent to register

        Returns:
            str: Unique identifier for the registered agent

        Raises:
            AgentRegistrationError: If agent registration fails
        """
        raise NotImplementedError("register_agent must be implemented")

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the system.

        Args:
            agent_id: Unique identifier of the agent to unregister

        Returns:
            bool: True if agent was successfully unregistered

        Raises:
            AgentNotFoundError: If agent is not found
        """
        raise NotImplementedError("unregister_agent must be implemented")

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by its identifier.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            BaseAgent instance or None if not found
        """
        raise NotImplementedError("get_agent must be implemented")

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
        raise NotImplementedError("list_agents must be implemented")

    def validate_agent_config(self, agent_config: AgentConfig) -> bool:
        """Validate agent configuration.

        Args:
            agent_config: Configuration to validate

        Returns:
            bool: True if configuration is valid

        Raises:
            AgentConfigError: If configuration is invalid
        """
        raise NotImplementedError("validate_agent_config must be implemented")

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
        raise NotImplementedError("test_agent_connectivity must be implemented")

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
        raise NotImplementedError("get_agent_health must be implemented")

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
        raise NotImplementedError("update_agent_config must be implemented")


class TestAgentManagementContract:
    """Contract tests for agent management.

    These tests define the expected behavior of agent management
    and will fail until implementations are provided.
    """

    @pytest.fixture
    def agent_contract(self):
        """Create an agent management contract instance."""
        return AgentRegistry()

    @pytest.fixture
    def sample_agent_config(self):
        """Create a sample agent configuration."""
        return AgentConfig(
            name="test-claude",
            type=AgentType.LLM,
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            api_key="test-key-123",
            max_tokens=4096,
            temperature=0.7,
            timeout_seconds=60,
        )

    def test_register_agent_basic(self, agent_contract, sample_agent_config):
        """Test basic agent registration."""
        agent_id = agent_contract.register_agent(sample_agent_config)
        assert isinstance(agent_id, str)
        assert len(agent_id) > 0

    def test_register_agent_duplicate(self, agent_contract, sample_agent_config):
        """Test registering agent with duplicate name."""
        # First registration should succeed
        agent_contract.register_agent(sample_agent_config)

        # Second registration with same name should fail or handle gracefully
        with pytest.raises(AgentRegistrationError):
            agent_contract.register_agent(sample_agent_config)

    def test_unregister_agent_existing(self, agent_contract, sample_agent_config):
        """Test unregistering an existing agent."""
        agent_id = agent_contract.register_agent(sample_agent_config)
        result = agent_contract.unregister_agent(agent_id)
        assert result is True

    def test_unregister_agent_nonexistent(self, agent_contract):
        """Test unregistering a non-existent agent."""
        with pytest.raises(AgentNotFoundError):
            agent_contract.unregister_agent("nonexistent-agent")

    def test_get_agent_existing(self, agent_contract, sample_agent_config):
        """Test getting an existing agent."""
        agent_id = agent_contract.register_agent(sample_agent_config)
        agent = agent_contract.get_agent(agent_id)
        assert agent is not None
        assert hasattr(agent, 'execute')

    def test_get_agent_nonexistent(self, agent_contract):
        """Test getting a non-existent agent."""
        agent = agent_contract.get_agent("nonexistent-agent")
        assert agent is None

    def test_list_agents_empty(self, agent_contract):
        """Test listing agents when none are registered."""
        agents = agent_contract.list_agents()
        assert isinstance(agents, list)
        assert len(agents) == 0

    def test_list_agents_with_agents(self, agent_contract, sample_agent_config):
        """Test listing agents when some are registered."""
        agent_contract.register_agent(sample_agent_config)

        agents = agent_contract.list_agents()
        assert isinstance(agents, list)
        assert len(agents) >= 1

        # Check structure of first agent
        agent_info = agents[0]
        assert "id" in agent_info
        assert "name" in agent_info
        assert "type" in agent_info
        assert "provider" in agent_info
        assert "status" in agent_info

    def test_validate_agent_config_valid(self, agent_contract, sample_agent_config):
        """Test validating a valid agent configuration."""
        result = agent_contract.validate_agent_config(sample_agent_config)
        assert result is True

    def test_validate_agent_config_invalid(self, agent_contract):
        """Test validating an invalid agent configuration."""
        invalid_config = AgentConfig(
            name="",  # Invalid: empty name
            type=AgentType.LLM,
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            api_key="test-key",
            max_tokens=4096,
            temperature=0.7,
            timeout_seconds=60,
        )

        with pytest.raises(AgentConfigError):
            agent_contract.validate_agent_config(invalid_config)

    def test_test_agent_connectivity_existing(self, agent_contract, sample_agent_config):
        """Test connectivity testing for existing agent."""
        agent_id = agent_contract.register_agent(sample_agent_config)
        result = agent_contract.test_agent_connectivity(agent_id)

        assert isinstance(result, dict)
        assert "success" in result
        assert "response_time" in result
        assert isinstance(result["success"], bool)

    def test_test_agent_connectivity_nonexistent(self, agent_contract):
        """Test connectivity testing for non-existent agent."""
        with pytest.raises(AgentNotFoundError):
            agent_contract.test_agent_connectivity("nonexistent-agent")

    def test_get_agent_health_existing(self, agent_contract, sample_agent_config):
        """Test getting health status for existing agent."""
        agent_id = agent_contract.register_agent(sample_agent_config)
        health = agent_contract.get_agent_health(agent_id)

        assert isinstance(health, dict)
        assert "status" in health
        assert "last_check" in health

    def test_get_agent_health_nonexistent(self, agent_contract):
        """Test getting health status for non-existent agent."""
        with pytest.raises(AgentNotFoundError):
            agent_contract.get_agent_health("nonexistent-agent")

    def test_update_agent_config_existing(self, agent_contract, sample_agent_config):
        """Test updating configuration of existing agent."""
        agent_id = agent_contract.register_agent(sample_agent_config)

        updates = {"temperature": 0.8, "max_tokens": 8192}
        result = agent_contract.update_agent_config(agent_id, updates)
        assert result is True

    def test_update_agent_config_nonexistent(self, agent_contract):
        """Test updating configuration of non-existent agent."""
        updates = {"temperature": 0.8}
        with pytest.raises(AgentNotFoundError):
            agent_contract.update_agent_config("nonexistent-agent", updates)

    def test_update_agent_config_invalid(self, agent_contract, sample_agent_config):
        """Test updating agent with invalid configuration."""
        agent_id = agent_contract.register_agent(sample_agent_config)

        invalid_updates = {"temperature": 2.5}  # Invalid: temperature > 1.0
        with pytest.raises(AgentConfigError):
            agent_contract.update_agent_config(agent_id, invalid_updates)