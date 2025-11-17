# Data Model: Agent MCP Integration

**Feature**: Agent MCP Integration
**Date**: 2025-11-12

## Overview

This document defines the data models and entities required for the Agent MCP Integration feature. The models extend existing agent configuration and execution structures to support MCP service management while maintaining backward compatibility.

## Core Entities

### AgentConfig (Extended)

**Purpose**: Configuration for all agent types with MCP integration support

**Fields**:
- `name: str` - Agent identifier (required)
- `type: AgentType` - Agent execution type: LLM, CLI, or DOCKER (required)
- `provider: Optional[str]` - AI provider for LLM agents (anthropic, openai, github)
- `model: Optional[str]` - Model identifier for LLM agents
- `api_key: Optional[str]` - API key (can be env var reference)
- `max_tokens: int` - Maximum tokens per request (default: 4096)
- `temperature: float` - Creativity parameter (default: 0.7, range: 0.0-2.0)
- `timeout_seconds: int` - Request timeout (default: 60, range: 10-300)
- `max_retries: int` - Maximum retry attempts (default: 3)
- `retry_delay: float` - Delay between retries in seconds (default: 1.0)
- `command: Optional[str]` - Command for CLI agents
- `working_directory: Optional[str]` - Working directory for CLI agents
- `environment_variables: Optional[Dict[str, str]]` - Environment variables for CLI agents
- `docker_image: Optional[str]` - Docker image for Docker agents
- `docker_command: Optional[str]` - Command to run in Docker container
- `docker_environment: Optional[Dict[str, str]]` - Environment variables for Docker containers
- `docker_volumes: Optional[List[str]]` - Volume mounts for Docker containers
- `mcp_address: Optional[str]` - MCP service address (URL format)
- `mcp_timeout: int` - MCP connection timeout in seconds (default: 30)
- `mcp_retry_attempts: int` - MCP connection retry attempts (default: 3)
- `enable_mcp_tools: bool` - Enable MCP tool integration (default: True)

**Validation Rules**:
- `name` must be unique across all agents
- `type` must be valid AgentType enum value
- `mcp_address` must be valid URL format if provided
- `temperature` must be between 0.0 and 2.0
- `timeout_seconds` must be between 10 and 300
- `max_retries` must be non-negative

**State Transitions**: Configuration is immutable during agent execution

### MCPService

**Purpose**: Represents an MCP service instance with connection management

**Fields**:
- `service_id: str` - Unique service identifier (required)
- `address: str` - Service endpoint URL (required)
- `status: MCPServiceStatus` - Current service status (required)
- `connection_pool: List[MCPConnection]` - Active connections (internal)
- `created_at: datetime` - Service creation timestamp (required)
- `last_health_check: datetime` - Last health check timestamp
- `health_status: bool` - Current health status
- `config: MCPServiceConfig` - Service configuration (required)

**Validation Rules**:
- `service_id` must be unique
- `address` must be valid URL
- `status` must be valid MCPServiceStatus enum

**State Transitions**:
- CREATED → STARTING → RUNNING → STOPPING → STOPPED
- Any state → ERROR on failures
- ERROR → RECOVERING → RUNNING on successful recovery

### MCPConnection

**Purpose**: Individual connection to an MCP service

**Fields**:
- `connection_id: str` - Unique connection identifier (required)
- `service_id: str` - Parent service identifier (required)
- `status: ConnectionStatus` - Connection status (required)
- `created_at: datetime` - Connection creation timestamp (required)
- `last_used: datetime` - Last usage timestamp
- `tool_count: int` - Number of available tools (default: 0)

**Validation Rules**:
- `connection_id` must be unique
- `service_id` must reference existing MCPService

### MCPServiceConfig

**Purpose**: Configuration for MCP service behavior

**Fields**:
- `max_connections: int` - Maximum connection pool size (default: 10)
- `connection_timeout: int` - Connection timeout in seconds (default: 30)
- `health_check_interval: int` - Health check interval in seconds (default: 60)
- `retry_attempts: int` - Connection retry attempts (default: 3)
- `retry_delay: float` - Delay between retries (default: 1.0)
- `enable_circuit_breaker: bool` - Enable circuit breaker pattern (default: True)
- `circuit_breaker_threshold: int` - Failure threshold for circuit breaker (default: 5)

**Validation Rules**:
- `max_connections` must be positive
- `connection_timeout` must be positive
- `health_check_interval` must be positive

## Entity Relationships

### AgentConfig → MCPService
- One-to-many: Agent can connect to multiple MCP services
- Navigation: AgentConfig.mcp_address → MCPService.address
- Lifecycle: Agent configuration drives MCP service discovery/creation

### MCPService → MCPConnection
- One-to-many: Service manages multiple connections
- Navigation: MCPService.connection_pool → List[MCPConnection]
- Lifecycle: Service creates/destroys connections as needed

### Agent Execution Context → MCPService
- Many-to-one: Multiple agent executions can share MCP services
- Navigation: ExecutionContext.mcp_services → Set[MCPService]
- Lifecycle: Execution context references but doesn't own MCP services

## Data Flow

1. **Configuration Phase**: AgentConfig loaded with MCP settings
2. **Discovery Phase**: MCPServiceManager discovers or creates MCP services
3. **Connection Phase**: MCPConnection established to services
4. **Execution Phase**: Agent uses MCP connections for tool access
5. **Cleanup Phase**: Connections returned to pool, services cleaned up

## Validation Rules Summary

### Business Rules
- LLM agents cannot have MCP address (direct parameter passing only)
- CLI agents must have either mcp_address or enable auto-discovery
- Docker agents use container networking for MCP discovery
- MCP services must be healthy before agent execution
- Connection pools cannot exceed configured limits

### Data Integrity
- All foreign key references must be valid
- Timestamps must be in chronological order
- Status transitions must follow defined state machine
- Configuration values must be within allowed ranges

## Migration Notes

### From Existing System
- `tools` parameter removed from all agent configurations
- MCP-related fields added as optional
- Existing agents continue to work with `enable_mcp_tools: false`
- Gradual migration path with feature flags

### Backward Compatibility
- Existing AgentConfig instances remain valid
- New fields have sensible defaults
- API contracts maintain compatibility
- Error handling provides clear migration guidance