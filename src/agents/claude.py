"""Claude agent implementation for Anthropic's Claude models.

This module provides an implementation of the BaseAgent interface for
Anthropic's Claude AI models, supporting both the Messages API and
legacy completion endpoints.
"""

import asyncio
import time
from typing import Dict, Any, Optional
import httpx

from .base import LLMAgent, AgentConfig, AgentResponse, AgentCapabilities, AgentExecutionError


class ClaudeAgent(LLMAgent):
    """Claude agent implementation using Anthropic's API.

    Supports Claude models with configurable parameters and error handling.
    """

    def __init__(self, config: AgentConfig):
        """Initialize the Claude agent.

        Args:
            config: Agent configuration with Anthropic settings

        Raises:
            ValueError: If configuration is invalid for Claude
        """
        super().__init__(config)

        # Claude-specific validations
        if config.provider != "anthropic":
            raise ValueError(f"ClaudeAgent requires provider='anthropic', got '{config.provider}'")

        if not config.api_key:
            raise ValueError("Claude agent requires an API key")

        # Validate model is a Claude model
        if not config.model or not config.model.startswith("claude"):
            raise ValueError(f"Invalid Claude model: {config.model}")

        # Initialize HTTP client for Anthropic API
        self._client = httpx.AsyncClient(
            base_url="https://api.anthropic.com",
            headers={
                "x-api-key": config.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=config.timeout_seconds,
        )

    def get_capabilities(self) -> AgentCapabilities:
        """Return Claude's capabilities.

        Returns:
            AgentCapabilities: Claude's supported operations
        """
        return AgentCapabilities(
            code_review=True,
            code_generation=True,
            task_planning=True,
            documentation=True,
            testing=True,
            debugging=True,
            refactoring=True,
            analysis=True,
        )

    def validate_config(self) -> bool:
        """Validate Claude-specific configuration.

        Returns:
            bool: True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.config.api_key:
            raise ValueError("Claude API key is required")

        if not self.config.model.startswith("claude"):
            raise ValueError(f"Model must be a Claude model, got: {self.config.model}")

        # Validate model-specific limits
        model_limits = {
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 200000,
            "claude-3-haiku-20240307": 200000,
            "claude-3-5-sonnet-20240620": 200000,
            "claude-2.1": 200000,
            "claude-2.0": 100000,
            "claude-instant-1.2": 100000,
        }

        max_tokens = model_limits.get(self.config.model, 100000)
        if self.config.max_tokens > max_tokens:
            raise ValueError(f"max_tokens ({self.config.max_tokens}) exceeds model limit ({max_tokens})")

        return True

    async def execute(self, prompt: str, **kwargs) -> AgentResponse:
        """Execute a prompt using Claude.

        Args:
            prompt: The prompt to execute
            **kwargs: Additional parameters (system_prompt, conversation_history, etc.)

        Returns:
            AgentResponse: Structured response from Claude

        Raises:
            AgentExecutionError: If execution fails
        """
        start_time = time.time()

        try:
            # Prepare the request payload
            system_prompt = kwargs.get("system_prompt", "")
            conversation_history = kwargs.get("conversation_history", [])

            messages = []

            # Add conversation history if provided
            for msg in conversation_history:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            # Add the current prompt
            messages.append({
                "role": "user",
                "content": prompt
            })

            payload = {
                "model": self.config.model,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "messages": messages,
            }

            # Add system prompt if provided
            if system_prompt:
                payload["system"] = system_prompt

            # Add any additional Claude-specific parameters
            if "top_p" in kwargs:
                payload["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                payload["top_k"] = kwargs["top_k"]

            # Make the API request with retry logic
            response = await self._execute_with_retry(payload)

            execution_time = time.time() - start_time

            return AgentResponse(
                content=response["content"][0]["text"],
                tokens_used=response["usage"]["input_tokens"] + response["usage"]["output_tokens"],
                finish_reason=response["stop_reason"],
                metadata={
                    "model": response["model"],
                    "stop_sequence": response.get("stop_sequence"),
                    "input_tokens": response["usage"]["input_tokens"],
                    "output_tokens": response["usage"]["output_tokens"],
                },
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            raise AgentExecutionError(
                f"Claude execution failed: {str(e)}",
                agent_name=self.config.name,
                provider="anthropic",
                details={"execution_time": execution_time, "error": str(e)}
            )

    async def _execute_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API request with retry logic.

        Args:
            payload: Request payload for Claude API

        Returns:
            Dict: API response

        Raises:
            AgentExecutionError: If all retries fail
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self._client.post("/v1/messages", json=payload)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limit
                    if attempt < self.config.max_retries:
                        await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                        continue
                elif response.status_code >= 400:
                    error_data = response.json()
                    raise AgentExecutionError(
                        f"Claude API error: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        agent_name=self.config.name,
                        provider="anthropic",
                        details=error_data
                    )

                # Other status codes
                response.raise_for_status()

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay)
                    continue
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay)
                    continue

        # All retries failed
        raise AgentExecutionError(
            f"Claude API request failed after {self.config.max_retries + 1} attempts: {str(last_exception)}",
            agent_name=self.config.name,
            provider="anthropic",
            details={"last_exception": str(last_exception)}
        )

    async def test_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to Claude API.

        Returns:
            Dict containing connectivity test results
        """
        start_time = time.time()
        try:
            # Simple connectivity test with a minimal prompt
            payload = {
                "model": self.config.model,
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hello"}]
            }

            response = await self._client.post("/v1/messages", json=payload)
            response_time = time.time() - start_time

            if response.status_code == 200:
                return {
                    "success": True,
                    "response_time": response_time,
                }
            else:
                return {
                    "success": False,
                    "response_time": response_time,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }

        except Exception as e:
            response_time = time.time() - start_time
            return {
                "success": False,
                "response_time": response_time,
                "error": str(e),
            }

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._client.aclose()