"""Chat integration tools for MCP.

This module provides tools for integrating chat functionality with external
chat platforms and services through the MCP protocol.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
import logging
from datetime import datetime

from ...core.config import ConfigManager
from ...agents.base import agent_registry


logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Represents a chat message."""

    id: str
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatSession:
    """Represents a chat session."""

    id: str
    platform: str  # "slack", "discord", "teams", etc.
    channel: str
    user: str
    messages: List[ChatMessage] = field(default_factory=list)
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)


class ChatIntegrationManager:
    """Manager for chat integrations with external platforms."""

    def __init__(self, config_manager: ConfigManager):
        """Initialize the chat integration manager.

        Args:
            config_manager: Configuration manager
        """
        self.config_manager = config_manager
        self.active_sessions: Dict[str, ChatSession] = {}
        self.platform_integrations: Dict[str, Any] = {}

        # Add aliases for backward compatibility with tests
        self.platforms = self.platform_integrations

    async def initialize_integrations(self):
        """Initialize configured chat platform integrations."""
        config = self.config_manager.get_config()

        # Get chat integration configurations
        chat_configs = config.deployment.get("chat_integrations", {})

        for platform, platform_config in chat_configs.items():
            if platform_config.get("enabled", False):
                await self._initialize_platform_integration(platform, platform_config)

    async def _initialize_platform_integration(self, platform: str, config: Dict[str, Any]):
        """Initialize integration for a specific chat platform.

        Args:
            platform: Platform name
            config: Platform configuration
        """
        try:
            if platform == "slack":
                integration = SlackIntegration(config)
            elif platform == "discord":
                integration = DiscordIntegration(config)
            elif platform == "teams":
                integration = TeamsIntegration(config)
            else:
                logger.warning(f"Unsupported chat platform: {platform}")
                return

            # Initialize the integration
            success = await integration.initialize()
            if success:
                self.platform_integrations[platform] = integration
                logger.info(f"Initialized {platform} chat integration")
            else:
                logger.error(f"Failed to initialize {platform} chat integration")

        except Exception as e:
            logger.error(f"Error initializing {platform} integration: {e}")

    async def handle_incoming_message(self, platform: str, message_data: Dict[str, Any]) -> Optional[str]:
        """Handle an incoming message from a chat platform.

        Args:
            platform: Platform name
            message_data: Message data from the platform

        Returns:
            Response message or None
        """
        try:
            integration = self.platform_integrations.get(platform)
            if not integration:
                logger.warning(f"No integration configured for platform: {platform}")
                return None

            # Parse the message
            session_id = message_data.get("session_id")
            user_message = message_data.get("text", "")
            user_id = message_data.get("user_id", "unknown")
            channel_id = message_data.get("channel_id", "unknown")

            # Get or create session
            session = self._get_or_create_session(platform, channel_id, user_id, session_id)

            # Add user message to session
            user_msg = ChatMessage(
                id=str(uuid.uuid4()),
                role="user",
                content=user_message,
                metadata={"platform": platform, "user_id": user_id}
            )
            session.messages.append(user_msg)
            session.last_activity = datetime.utcnow()

            # Process the message
            response = await self._process_chat_message(session, user_message)

            # Add assistant response to session
            if response:
                assistant_msg = ChatMessage(
                    id=str(uuid.uuid4()),
                    role="assistant",
                    content=response,
                    metadata={"platform": platform}
                )
                session.messages.append(assistant_msg)

            return response

        except Exception as e:
            logger.error(f"Error handling incoming message: {e}")
            return "Sorry, I encountered an error processing your message."

    def _get_or_create_session(self, platform: str, channel: str, user: str, session_id: Optional[str] = None) -> ChatSession:
        """Get or create a chat session.

        Args:
            platform: Platform name
            channel: Channel ID
            user: User ID
            session_id: Optional existing session ID

        Returns:
            Chat session
        """
        if session_id and session_id in self.active_sessions:
            return self.active_sessions[session_id]

        # Create new session
        session = ChatSession(
            id=session_id or str(uuid.uuid4()),
            platform=platform,
            channel=channel,
            user=user
        )

        self.active_sessions[session.id] = session
        return session

    async def _process_chat_message(self, session: ChatSession, message: str) -> Optional[str]:
        """Process a chat message and generate a response.

        Args:
            session: Chat session
            message: User message

        Returns:
            Response message
        """
        try:
            # Check if this is a command for the platform
            if message.startswith("/"):
                return await self._handle_chat_command(session, message)

            # Check if this is a request to execute a workflow
            if "workflow" in message.lower() or "execute" in message.lower():
                return await self._handle_workflow_request(session, message)

            # Default: route to an agent for general chat
            agent = agent_registry.get_agent("claude-agent")  # Default to Claude
            if agent:
                # Prepare context from session history
                context = self._build_context_from_session(session)

                prompt = f"{context}\n\nUser: {message}\n\nAssistant:"

                response = await agent.execute(prompt)
                return response.content

            return "I'm sorry, I don't have an available agent to respond to your message."

        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return "Sorry, I encountered an error processing your message."

    async def _handle_chat_command(self, session: ChatSession, command: str) -> Optional[str]:
        """Handle a chat command.

        Args:
            session: Chat session
            command: Command string

        Returns:
            Command response
        """
        try:
            parts = command[1:].split()  # Remove leading slash
            cmd = parts[0].lower() if parts else ""

            if cmd == "help":
                return self._get_help_text()
            elif cmd == "status":
                return await self._get_status_info()
            elif cmd == "workflows":
                return await self._list_available_workflows()
            elif cmd == "sessions":
                return self._get_session_info(session)
            elif cmd == "clear":
                session.messages.clear()
                return "Chat history cleared."
            else:
                return f"Unknown command: {cmd}. Type /help for available commands."

        except Exception as e:
            logger.error(f"Error handling chat command: {e}")
            return "Error processing command."

    async def _handle_workflow_request(self, session: ChatSession, message: str) -> Optional[str]:
        """Handle a workflow execution request.

        Args:
            session: Chat session
            message: User message containing workflow request

        Returns:
            Workflow execution response
        """
        try:
            # Simple workflow detection and execution
            # This is a basic implementation - could be enhanced with NLP

            config = self.config_manager.get_config()
            workflows = list(config.workflows.keys())

            # Try to match workflow name in message
            requested_workflow = None
            for workflow_name in workflows:
                if workflow_name.lower() in message.lower():
                    requested_workflow = workflow_name
                    break

            if not requested_workflow:
                return f"I couldn't identify which workflow to run. Available workflows: {', '.join(workflows)}"

            # Execute the workflow
            from ...core.workflow import WorkflowEngine

            workflow_engine = WorkflowEngine(config, agent_registry)

            # Create workflow definition (simplified)
            workflow_config = config.workflows[requested_workflow]
            # ... (workflow creation logic would go here)

            execution_id = await workflow_engine.execute_workflow(
                workflow=None,  # Would need proper workflow definition
                parameters={"source": "chat", "message": message}
            )

            return f"Started workflow '{requested_workflow}' with execution ID: {execution_id}"

        except Exception as e:
            logger.error(f"Error handling workflow request: {e}")
            return "Sorry, I couldn't execute the requested workflow."

    def _build_context_from_session(self, session: ChatSession, max_messages: int = 10) -> str:
        """Build context string from session message history.

        Args:
            session: Chat session
            max_messages: Maximum number of messages to include

        Returns:
            Context string
        """
        recent_messages = session.messages[-max_messages:]
        context_parts = []

        for msg in recent_messages:
            role = "User" if msg.role == "user" else "Assistant"
            context_parts.append(f"{role}: {msg.content}")

        return "\n".join(context_parts)

    def _get_help_text(self) -> str:
        """Get help text for available commands."""
        return """
Available commands:
/help - Show this help message
/status - Show system status
/workflows - List available workflows
/sessions - Show session information
/clear - Clear chat history

You can also ask me questions or request workflow executions naturally.
        """.strip()

    async def _get_status_info(self) -> str:
        """Get system status information."""
        try:
            config = self.config_manager.get_config()

            status = f"""
System Status:
- Platform: Multi-Agent Orchestration Platform v{config.version}
- Agents: {len(config.agents)}
- Workflows: {len(config.workflows)}
- Active Sessions: {len(self.active_sessions)}
- Integrations: {len(self.platform_integrations)}
            """.strip()

            return status

        except Exception as e:
            return "Error retrieving status information."

    async def _list_available_workflows(self) -> str:
        """List available workflows."""
        try:
            config = self.config_manager.get_config()
            workflows = list(config.workflows.keys())

            if not workflows:
                return "No workflows are currently configured."

            workflow_list = "\n".join(f"- {name}" for name in workflows)
            return f"Available workflows:\n{workflow_list}"

        except Exception as e:
            return "Error retrieving workflow list."

    def _get_session_info(self, session: ChatSession) -> str:
        """Get information about the current session."""
        message_count = len(session.messages)
        created = session.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        return f"""
Session Information:
- Session ID: {session.id}
- Platform: {session.platform}
- Channel: {session.channel}
- User: {session.user}
- Messages: {message_count}
- Created: {created}
- Active: {session.active}
        """.strip()

    async def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """Clean up inactive chat sessions.

        Args:
            max_age_hours: Maximum age of sessions to keep
        """
        try:
            current_time = datetime.utcnow()
            to_remove = []

            for session_id, session in self.active_sessions.items():
                age_hours = (current_time - session.last_activity).total_seconds() / 3600
                if age_hours > max_age_hours:
                    to_remove.append(session_id)

            for session_id in to_remove:
                logger.info(f"Removing inactive session: {session_id}")
                del self.active_sessions[session_id]

        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")

    def register_platform(self, platform: str, config: Dict[str, Any]):
        """Register a chat platform."""
        self.platform_integrations[platform] = config

    def unregister_platform(self, platform: str):
        """Unregister a chat platform."""
        if platform in self.platform_integrations:
            del self.platform_integrations[platform]

    def create_session(self, session_config: Dict[str, Any]) -> str:
        """Create a chat session."""
        import uuid
        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = session_config
        return session_id

    def end_session(self, session_id: str) -> bool:
        """End a chat session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False

    def list_platforms(self) -> List[Dict[str, Any]]:
        """List registered platforms."""
        return [{"name": name, **config} for name, config in self.platform_integrations.items()]

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List active sessions."""
        return [{"session_id": sid, **config} for sid, config in self.active_sessions.items()]

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        return self.active_sessions.get(session_id)

    async def send_message(self, platform: str, channel: str, text: str) -> bool:
        """Send a message to a chat platform."""
        try:
            if platform not in self.platform_integrations:
                return False

            config = self.platform_integrations[platform]

            if platform == "slack":
                return await self._send_slack_message(config, channel, text)
            elif platform == "discord":
                return await self._send_discord_message(config, channel, text)
            else:
                # Unsupported platform
                return False

        except Exception as e:
            logger.error(f"Error sending message to {platform}: {e}")
            return False

    async def _send_slack_message(self, config: Dict[str, Any], channel: str, text: str) -> bool:
        """Send message to Slack."""
        import aiohttp

        webhook_url = config.get("webhook_url")
        if not webhook_url:
            return False

        payload = {
            "channel": channel,
            "text": text
        }

        async with aiohttp.ClientSession() as session:
            response = await session.post(webhook_url, json=payload)
            return response.status == 200

    async def _send_discord_message(self, config: Dict[str, Any], channel: str, text: str) -> bool:
        """Send message to Discord."""
        import aiohttp

        webhook_url = config.get("webhook_url")
        if not webhook_url:
            return False

        payload = {
            "content": text
        }

        async with aiohttp.ClientSession() as session:
            response = await session.post(webhook_url, json=payload)
            return response.status == 204


# Platform-specific integration classes
class SlackIntegration:
    """Slack chat integration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.token = config.get("token")
        self.signing_secret = config.get("signing_secret")

    async def initialize(self) -> bool:
        """Initialize Slack integration."""
        # Implementation would set up Slack API client
        # This is a placeholder
        return bool(self.token)

    async def send_message(self, channel: str, text: str) -> bool:
        """Send a message to a Slack channel."""
        # Implementation would use Slack API
        logger.info(f"Would send Slack message to {channel}: {text}")
        return True


class DiscordIntegration:
    """Discord chat integration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.token = config.get("token")
        self.application_id = config.get("application_id")

    async def initialize(self) -> bool:
        """Initialize Discord integration."""
        # Implementation would set up Discord API client
        return bool(self.token)

    async def send_message(self, channel: str, text: str) -> bool:
        """Send a message to a Discord channel."""
        logger.info(f"Would send Discord message to {channel}: {text}")
        return True


class TeamsIntegration:
    """Microsoft Teams chat integration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.tenant_id = config.get("tenant_id")

    async def initialize(self) -> bool:
        """Initialize Teams integration."""
        # Implementation would set up Microsoft Graph API client
        return bool(self.client_id and self.client_secret)

    async def send_message(self, channel: str, text: str) -> bool:
        """Send a message to a Teams channel."""
        logger.info(f"Would send Teams message to {channel}: {text}")
        return True


# Global chat integration manager
chat_manager = ChatIntegrationManager(ConfigManager())

# Alias for backward compatibility
ChatIntegrationTool = ChatIntegrationManager