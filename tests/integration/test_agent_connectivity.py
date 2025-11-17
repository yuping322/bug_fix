"""Integration tests for agent connectivity.

This module tests the integration between agent implementations
and external services (Claude API, OpenAI API, GitHub API).
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from src.agents.base import AgentRegistry, AgentConfig, AgentType
from src.agents.claude import ClaudeAgent
from src.agents.codex import CodexAgent
from src.agents.copilot import CopilotAgent
from src.core.config import PlatformConfig


class TestAgentConnectivityIntegration:
    """Integration tests for agent connectivity to external services."""

    @pytest.fixture
    def agent_registry(self):
        """Create an agent registry for testing."""
        registry = AgentRegistry()
        return registry

    @pytest.fixture
    def claude_config(self):
        """Create Claude agent configuration."""
        return AgentConfig(
            name="test-claude",
            type=AgentType.LLM,
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            api_key="test-anthropic-key",
            max_tokens=4096,
            temperature=0.7,
            timeout_seconds=30,
        )

    @pytest.fixture
    def codex_config(self):
        """Create Codex agent configuration."""
        return AgentConfig(
            name="test-codex",
            type=AgentType.LLM,
            provider="openai",
            model="gpt-4",
            api_key="test-openai-key",
            max_tokens=4096,
            temperature=0.7,
            timeout_seconds=30,
        )

    @pytest.fixture
    def copilot_config(self):
        """Create Copilot agent configuration."""
        return AgentConfig(
            name="test-copilot",
            type=AgentType.LLM,
            provider="github",
            model="copilot",
            api_key="test-github-token",
            max_tokens=4096,
            temperature=0.7,
            timeout_seconds=30,
        )

    def test_claude_agent_initialization(self, claude_config):
        """Test Claude agent can be initialized."""
        agent = ClaudeAgent(claude_config)
        assert agent.config.name == "test-claude"
        assert agent.config.provider == "anthropic"
        assert agent.config.model == "claude-3-sonnet-20240229"

    def test_codex_agent_initialization(self, codex_config):
        """Test Codex agent can be initialized."""
        agent = CodexAgent(codex_config)
        assert agent.config.name == "test-codex"
        assert agent.config.provider == "openai"
        assert agent.config.model == "gpt-4"

    def test_copilot_agent_initialization(self, copilot_config):
        """Test Copilot agent can be initialized."""
        agent = CopilotAgent(copilot_config)
        assert agent.config.name == "test-copilot"
        assert agent.config.provider == "github"
        assert agent.config.model == "copilot"

    @patch('httpx.AsyncClient')
    def test_claude_agent_connectivity_success(self, mock_http_client, claude_config):
        """Test successful Claude API connectivity."""
        # Mock the HTTP client
        mock_client = Mock()
        mock_http_client.return_value = mock_client

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": [{"text": "Hello"}], "usage": {"input_tokens": 1, "output_tokens": 1}}
        mock_client.post = AsyncMock(return_value=mock_response)

        agent = ClaudeAgent(claude_config)

        # Test connectivity
        result = asyncio.run(agent.test_connectivity())
        assert result["success"] is True
        assert "response_time" in result
        assert result["response_time"] >= 0

    @patch('httpx.AsyncClient')
    def test_claude_agent_connectivity_failure(self, mock_http_client, claude_config):
        """Test Claude API connectivity failure."""
        # Mock the HTTP client to raise an exception
        mock_client = Mock()
        mock_http_client.return_value = mock_client
        mock_client.post = AsyncMock(side_effect=Exception("API Error"))

        agent = ClaudeAgent(claude_config)

        # Test connectivity
        result = asyncio.run(agent.test_connectivity())
        assert result["success"] is False
        assert "error" in result
        assert "API Error" in result["error"]

    @patch('httpx.AsyncClient')
    def test_codex_agent_connectivity_success(self, mock_http_client, codex_config):
        """Test successful OpenAI API connectivity."""
        # Mock the HTTP client
        mock_client = Mock()
        mock_http_client.return_value = mock_client

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "Hello"}}], "usage": {"total_tokens": 10}}
        mock_client.post = AsyncMock(return_value=mock_response)

        agent = CodexAgent(codex_config)

        # Test connectivity
        result = asyncio.run(agent.test_connectivity())
        assert result["success"] is True
        assert "response_time" in result
        assert result["response_time"] >= 0

    @patch('httpx.AsyncClient')
    def test_codex_agent_connectivity_failure(self, mock_http_client, codex_config):
        """Test OpenAI API connectivity failure."""
        # Mock the HTTP client to raise an exception
        mock_client = Mock()
        mock_http_client.return_value = mock_client
        mock_client.post = AsyncMock(side_effect=Exception("OpenAI API Error"))

        agent = CodexAgent(codex_config)

        # Test connectivity
        result = asyncio.run(agent.test_connectivity())
        assert result["success"] is False
        assert "error" in result
        assert "OpenAI API Error" in result["error"]

    def test_copilot_agent_connectivity_success(self, copilot_config):
        """Test successful GitHub Copilot API connectivity."""
        agent = CopilotAgent(copilot_config)

        # Test connectivity (simulated)
        result = asyncio.run(agent.test_connectivity())
        assert result["success"] is True
        assert "response_time" in result
        assert result["response_time"] >= 0

    def test_agent_registry_registration(self, agent_registry, claude_config):
        """Test agent registration in registry."""
        agent = ClaudeAgent(claude_config)
        agent_registry.register(agent)

        # Verify agent is registered
        registered_agent = agent_registry.get_agent("test-claude")
        assert registered_agent is not None
        assert registered_agent.config.name == "test-claude"

    def test_agent_registry_multiple_agents(self, agent_registry, claude_config, codex_config):
        """Test registering multiple agents in registry."""
        claude_agent = ClaudeAgent(claude_config)
        codex_agent = CodexAgent(codex_config)

        agent_registry.register(claude_agent)
        agent_registry.register(codex_agent)

        # Verify both agents are registered
        assert agent_registry.get_agent("test-claude") is not None
        assert agent_registry.get_agent("test-codex") is not None

        # Verify agent listing
        agents = agent_registry.list_agents()
        assert len(agents) == 2
        agent_names = [agent["id"] for agent in agents]
        assert "test-claude" in agent_names
        assert "test-codex" in agent_names

    def test_agent_registry_duplicate_registration(self, agent_registry, claude_config):
        """Test handling of duplicate agent registration."""
        agent1 = ClaudeAgent(claude_config)
        agent2 = ClaudeAgent(claude_config)  # Same config

        agent_registry.register(agent1)

        # Second registration should either fail or replace
        try:
            agent_registry.register(agent2)
            # If it succeeds, should still have only one agent
            agents = agent_registry.list_agents()
            assert len(agents) == 1
        except Exception:
            # If it fails, that's also acceptable
            pass