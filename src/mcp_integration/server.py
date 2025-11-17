"""MCP (Model Context Protocol) server implementation.

This module provides an MCP server that exposes the multi-agent orchestration
platform capabilities through the Model Context Protocol.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
import logging

from mcp import Tool, types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from ..core.config import ConfigManager
from ..core.workflow import WorkflowEngine, ExecutionStatus
from ..agents.base import agent_registry
from ..workflows.templates import get_template
from ..utils.validation import validate_config


logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """MCP tool definition."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable


class MCPPlatformServer:
    """MCP server for the multi-agent orchestration platform."""

    def __init__(self):
        """Initialize the MCP server."""
        self.server = Server("multi-agent-orchestration")
        self.config_manager = ConfigManager()
        self.workflow_engine = None
        self.tools = {}

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register all available MCP tools."""
        self.tools = {
            "list_agents": MCPTool(
                name="list_agents",
                description="List all configured agents and their status",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                handler=self._handle_list_agents
            ),
            "get_agent_info": MCPTool(
                name="get_agent_info",
                description="Get detailed information about a specific agent",
                input_schema={
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Name of the agent to get info for"
                        }
                    },
                    "required": ["agent_name"]
                },
                handler=self._handle_get_agent_info
            ),
            "list_workflows": MCPTool(
                name="list_workflows",
                description="List all available workflows",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                handler=self._handle_list_workflows
            ),
            "get_workflow_info": MCPTool(
                name="get_workflow_info",
                description="Get detailed information about a specific workflow",
                input_schema={
                    "type": "object",
                    "properties": {
                        "workflow_name": {
                            "type": "string",
                            "description": "Name of the workflow to get info for"
                        }
                    },
                    "required": ["workflow_name"]
                },
                handler=self._handle_get_workflow_info
            ),
            "execute_workflow": MCPTool(
                name="execute_workflow",
                description="Execute a workflow with given parameters",
                input_schema={
                    "type": "object",
                    "properties": {
                        "workflow_name": {
                            "type": "string",
                            "description": "Name of the workflow to execute"
                        },
                        "inputs": {
                            "type": "object",
                            "description": "Input parameters for the workflow"
                        },
                        "async_execution": {
                            "type": "boolean",
                            "description": "Whether to execute asynchronously",
                            "default": True
                        }
                    },
                    "required": ["workflow_name"]
                },
                handler=self._handle_execute_workflow
            ),
            "get_execution_status": MCPTool(
                name="get_execution_status",
                description="Get the status of a workflow execution",
                input_schema={
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "ID of the execution to check"
                        }
                    },
                    "required": ["execution_id"]
                },
                handler=self._handle_get_execution_status
            ),
            "list_executions": MCPTool(
                name="list_executions",
                description="List workflow executions with optional filtering",
                input_schema={
                    "type": "object",
                    "properties": {
                        "workflow_name": {
                            "type": "string",
                            "description": "Filter by workflow name"
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter by execution status",
                            "enum": ["pending", "running", "completed", "failed", "cancelled"]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of executions to return",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 100
                        }
                    },
                    "required": []
                },
                handler=self._handle_list_executions
            ),
            "cancel_execution": MCPTool(
                name="cancel_execution",
                description="Cancel a running workflow execution",
                input_schema={
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "ID of the execution to cancel"
                        }
                    },
                    "required": ["execution_id"]
                },
                handler=self._handle_cancel_execution
            ),
            "validate_config": MCPTool(
                name="validate_config",
                description="Validate platform configuration",
                input_schema={
                    "type": "object",
                    "properties": {
                        "config": {
                            "type": "object",
                            "description": "Configuration object to validate"
                        }
                    },
                    "required": ["config"]
                },
                handler=self._handle_validate_config
            ),
            "get_platform_status": MCPTool(
                name="get_platform_status",
                description="Get overall platform status and health",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                handler=self._handle_get_platform_status
            )
        }

    async def _handle_list_agents(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_agents tool call."""
        try:
            config = self.config_manager.get_config()
            agents = []

            for agent_name, agent_config in config.agents.items():
                agent_info = {
                    "name": agent_name,
                    "type": agent_config.provider,
                    "model": agent_config.model,
                    "enabled": agent_config.enabled,
                    "healthy": False,  # Would check actual health
                    "description": f"{agent_config.provider} agent using {agent_config.model}"
                }

                # Try to get actual agent health
                try:
                    agent = agent_registry.get_agent(agent_name)
                    if agent:
                        agent_info["healthy"] = await agent.health_check()
                except Exception:
                    pass

                agents.append(agent_info)

            return {
                "agents": agents,
                "total": len(agents)
            }

        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            return {"error": str(e)}

    async def _handle_get_agent_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_agent_info tool call."""
        try:
            agent_name = arguments["agent_name"]
            config = self.config_manager.get_config()

            if agent_name not in config.agents:
                return {"error": f"Agent '{agent_name}' not found"}

            agent_config = config.agents[agent_name]

            agent_info = {
                "name": agent_name,
                "type": agent_config.provider,
                "model": agent_config.model,
                "max_tokens": agent_config.max_tokens,
                "temperature": agent_config.temperature,
                "timeout_seconds": agent_config.timeout_seconds,
                "enabled": agent_config.enabled,
                "healthy": False,
                "capabilities": []  # Would be populated based on agent type
            }

            # Try to get actual agent health and capabilities
            try:
                agent = agent_registry.get_agent(agent_name)
                if agent:
                    agent_info["healthy"] = await agent.health_check()
                    agent_info["capabilities"] = agent.capabilities
            except Exception:
                pass

            return agent_info

        except Exception as e:
            logger.error(f"Error getting agent info: {e}")
            return {"error": str(e)}

    async def _handle_list_workflows(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_workflows tool call."""
        try:
            config = self.config_manager.get_config()
            workflows = []

            for workflow_name, workflow_config in config.workflows.items():
                workflow_info = {
                    "name": workflow_name,
                    "type": workflow_config.type,
                    "description": workflow_config.description,
                    "enabled": workflow_config.enabled,
                    "agents": workflow_config.agents,
                    "step_count": len(workflow_config.steps)
                }
                workflows.append(workflow_info)

            return {
                "workflows": workflows,
                "total": len(workflows)
            }

        except Exception as e:
            logger.error(f"Error listing workflows: {e}")
            return {"error": str(e)}

    async def _handle_get_workflow_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_workflow_info tool call."""
        try:
            workflow_name = arguments["workflow_name"]
            config = self.config_manager.get_config()

            if workflow_name not in config.workflows:
                return {"error": f"Workflow '{workflow_name}' not found"}

            workflow_config = config.workflows[workflow_name]

            workflow_info = {
                "name": workflow_name,
                "type": workflow_config.type,
                "description": workflow_config.description,
                "enabled": workflow_config.enabled,
                "agents": workflow_config.agents,
                "steps": workflow_config.steps,
                "config": workflow_config.config,
                "metadata": workflow_config.metadata
            }

            return workflow_info

        except Exception as e:
            logger.error(f"Error getting workflow info: {e}")
            return {"error": str(e)}

    async def _handle_execute_workflow(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle execute_workflow tool call."""
        try:
            workflow_name = arguments["workflow_name"]
            inputs = arguments.get("inputs", {})
            async_execution = arguments.get("async_execution", True)

            config = self.config_manager.get_config()

            if workflow_name not in config.workflows:
                return {"error": f"Workflow '{workflow_name}' not found"}

            workflow_config = config.workflows[workflow_name]

            # Initialize workflow engine if needed
            if self.workflow_engine is None:
                self.workflow_engine = WorkflowEngine(config, agent_registry)

            # Create workflow definition
            from ..core.workflow import WorkflowDefinition, WorkflowStep

            steps = []
            for i, step_config in enumerate(workflow_config.steps):
                steps.append(WorkflowStep(
                    id=f"step_{i}",
                    name=step_config.get("name", f"Step {i}"),
                    agent_id=step_config.get("agent", ""),
                    prompt_template=step_config.get("prompt", ""),
                    input_mappings=step_config.get("inputs", {}),
                    output_key=step_config.get("output", f"output_{i}"),
                    timeout_seconds=step_config.get("timeout", 300),
                    retry_count=step_config.get("retry", 0),
                    dependencies=step_config.get("dependencies", [])
                ))

            workflow_def = WorkflowDefinition(
                id=workflow_name,
                name=workflow_config.name,
                description=workflow_config.description,
                type=workflow_config.type,
                steps=steps,
                config=workflow_config.config,
                metadata=workflow_config.metadata
            )

            # Execute workflow
            execution_id = await self.workflow_engine.execute_workflow(
                workflow=workflow_def,
                parameters=inputs
            )

            return {
                "execution_id": execution_id,
                "status": "running" if async_execution else "completed",
                "workflow_name": workflow_name
            }

        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            return {"error": str(e)}

    async def _handle_get_execution_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_execution_status tool call."""
        try:
            execution_id = arguments["execution_id"]

            if self.workflow_engine is None:
                config = self.config_manager.get_config()
                self.workflow_engine = WorkflowEngine(config, agent_registry)

            execution_context = self.workflow_engine.get_execution_status(execution_id)

            if execution_context is None:
                return {"error": f"Execution '{execution_id}' not found"}

            return {
                "execution_id": execution_context.execution_id,
                "workflow_id": execution_context.workflow_id,
                "status": execution_context.status.value,
                "start_time": execution_context.start_time,
                "end_time": execution_context.end_time,
                "duration": execution_context.duration,
                "results": execution_context.step_results,
                "errors": execution_context.errors
            }

        except Exception as e:
            logger.error(f"Error getting execution status: {e}")
            return {"error": str(e)}

    async def _handle_list_executions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_executions tool call."""
        try:
            workflow_name = arguments.get("workflow_name")
            status_filter = arguments.get("status")
            limit = arguments.get("limit", 50)

            if self.workflow_engine is None:
                config = self.config_manager.get_config()
                self.workflow_engine = WorkflowEngine(config, agent_registry)

            executions = self.workflow_engine.list_executions()

            # Apply filters
            if workflow_name:
                executions = [e for e in executions if e.workflow_id == workflow_name]

            if status_filter:
                executions = [e for e in executions if e.status.value == status_filter]

            # Apply limit
            executions = executions[:limit]

            execution_list = []
            for execution in executions:
                execution_list.append({
                    "execution_id": execution.execution_id,
                    "workflow_id": execution.workflow_id,
                    "status": execution.status.value,
                    "start_time": execution.start_time,
                    "end_time": execution.end_time,
                    "duration": execution.duration
                })

            return {
                "executions": execution_list,
                "total": len(execution_list)
            }

        except Exception as e:
            logger.error(f"Error listing executions: {e}")
            return {"error": str(e)}

    async def _handle_cancel_execution(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cancel_execution tool call."""
        try:
            execution_id = arguments["execution_id"]

            if self.workflow_engine is None:
                config = self.config_manager.get_config()
                self.workflow_engine = WorkflowEngine(config, agent_registry)

            cancelled = self.workflow_engine.cancel_execution(execution_id)

            return {
                "cancelled": cancelled,
                "execution_id": execution_id
            }

        except Exception as e:
            logger.error(f"Error cancelling execution: {e}")
            return {"error": str(e)}

    async def _handle_validate_config(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle validate_config tool call."""
        try:
            config_data = arguments["config"]

            # Validate the configuration
            errors = validate_config(config_data)

            return {
                "valid": len(errors) == 0,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error validating config: {e}")
            return {"error": str(e)}

    async def _handle_get_platform_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_platform_status tool call."""
        try:
            config = self.config_manager.get_config()

            # Get basic platform info
            status = {
                "name": "Multi-Agent Orchestration Platform",
                "version": config.version,
                "agent_count": len(config.agents),
                "workflow_count": len(config.workflows),
                "status": "healthy"  # Would check actual health
            }

            # Get active executions if workflow engine is available
            if self.workflow_engine:
                active_executions = self.workflow_engine.get_active_execution_count()
                status["active_executions"] = active_executions

            return status

        except Exception as e:
            logger.error(f"Error getting platform status: {e}")
            return {"error": str(e)}

    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a tool call from the MCP client."""
        if name not in self.tools:
            return {"error": f"Unknown tool: {name}"}

        tool = self.tools[name]
        return await tool.handler(arguments)

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools for MCP discovery."""
        tools = []
        for tool in self.tools.values():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            })
        return tools


async def main():
    """Main entry point for the MCP server."""
    server = MCPPlatformServer()

    # Set up MCP protocol handlers
    @server.server.list_tools()
    async def handle_list_tools():
        """Handle tool listing request."""
        tools = []
        for tool in server.tools.values():
            tools.append(types.Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.input_schema
            ))
        return tools

    @server.server.call_tool()
    async def handle_call_tool(name: str, arguments: Dict[str, Any]):
        """Handle tool call request."""
        result = await server.handle_tool_call(name, arguments)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())