"""Codex agent implementation for OpenAI's GPT models.

This module provides an implementation of the BaseAgent interface for
OpenAI's GPT models, supporting both chat completions and legacy completion endpoints.
"""

import asyncio
import time
from typing import Dict, Any, Optional
import httpx

from .base import LLMAgent, AgentConfig, AgentResponse, AgentCapabilities, AgentExecutionError


class CodexAgent(LLMAgent):
    """Codex agent implementation using OpenAI's API.

    Supports GPT models with configurable parameters and error handling.
    """

    def __init__(self, config: AgentConfig):
        """Initialize the Codex agent.

        Args:
            config: Agent configuration with OpenAI settings

        Raises:
            ValueError: If configuration is invalid for OpenAI
        """
        super().__init__(config)

        if config.provider != "openai":
            raise ValueError(f"CodexAgent requires provider='openai', got '{config.provider}'")

        if not config.api_key:
            raise ValueError("Codex agent requires an API key")

        # Initialize HTTP client for OpenAI API
        self._client = httpx.AsyncClient(
            base_url="https://api.openai.com",
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=config.timeout_seconds,
        )

        # Validate model is a GPT model
        valid_models = [
            "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview", "gpt-4-0125-preview",
            "gpt-4-1106-preview", "gpt-4-vision-preview", "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k", "gpt-3.5-turbo-instruct"
        ]

        if config.model not in valid_models and not config.model.startswith("gpt-"):
            raise ValueError(f"Invalid OpenAI model: {config.model}")

    def get_capabilities(self) -> AgentCapabilities:
        """Return Codex's capabilities.

        Returns:
            AgentCapabilities: Codex's supported operations
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
        """Validate OpenAI-specific configuration.

        Returns:
            bool: True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.config.api_key:
            raise ValueError("OpenAI API key is required")

        # Validate model-specific limits
        model_limits = {
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4-turbo-preview": 128000,
            "gpt-4-0125-preview": 128000,
            "gpt-4-1106-preview": 128000,
            "gpt-4-vision-preview": 128000,
            "gpt-3.5-turbo": 16385,
            "gpt-3.5-turbo-16k": 16385,
            "gpt-3.5-turbo-instruct": 4096,
        }

        max_tokens = model_limits.get(self.config.model, 4096)
        if self.config.max_tokens > max_tokens:
            raise ValueError(f"max_tokens ({self.config.max_tokens}) exceeds model limit ({max_tokens})")

        return True

    async def execute(self, prompt: str, **kwargs) -> AgentResponse:
        """Execute a prompt using OpenAI's API.

        Args:
            prompt: The prompt to execute
            **kwargs: Additional parameters (system_prompt, conversation_history, etc.)

        Returns:
            AgentResponse: Structured response from OpenAI

        Raises:
            AgentExecutionError: If execution fails
        """
        start_time = time.time()

        try:
            # Prepare the request payload
            system_prompt = kwargs.get("system_prompt", "")
            conversation_history = kwargs.get("conversation_history", [])

            messages = []

            # Add system message if provided
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

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
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }

            # Add any additional OpenAI-specific parameters
            if "top_p" in kwargs:
                payload["top_p"] = kwargs["top_p"]
            if "frequency_penalty" in kwargs:
                payload["frequency_penalty"] = kwargs["frequency_penalty"]
            if "presence_penalty" in kwargs:
                payload["presence_penalty"] = kwargs["presence_penalty"]

            # Make the API request with retry logic
            response = await self._execute_with_retry(payload)

            execution_time = time.time() - start_time

            choice = response["choices"][0]
            message = choice["message"]

            return AgentResponse(
                content=message["content"],
                tokens_used=response["usage"]["total_tokens"],
                finish_reason=choice["finish_reason"],
                metadata={
                    "model": response["model"],
                    "prompt_tokens": response["usage"]["prompt_tokens"],
                    "completion_tokens": response["usage"]["completion_tokens"],
                    "total_tokens": response["usage"]["total_tokens"],
                },
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            raise AgentExecutionError(
                f"OpenAI execution failed: {str(e)}",
                agent_name=self.config.name,
                provider="openai",
                details={"execution_time": execution_time, "error": str(e)}
            )

    async def _execute_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API request with retry logic.

        Args:
            payload: Request payload for OpenAI API

        Returns:
            Dict: API response

        Raises:
            AgentExecutionError: If all retries fail
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self._client.post("/v1/chat/completions", json=payload)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limit
                    if attempt < self.config.max_retries:
                        await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                        continue
                elif response.status_code >= 400:
                    error_data = response.json()
                    raise AgentExecutionError(
                        f"OpenAI API error: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        agent_name=self.config.name,
                        provider="openai",
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
            f"OpenAI API request failed after {self.config.max_retries + 1} attempts: {str(last_exception)}",
            agent_name=self.config.name,
            provider="openai",
            details={"last_exception": str(last_exception)}
        )

    async def test_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to OpenAI API.

        Returns:
            Dict containing connectivity test results
        """
        start_time = time.time()
        try:
            # Simple connectivity test with a minimal prompt
            payload = {
                "model": self.config.model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }

            response = await self._client.post("/v1/chat/completions", json=payload)
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