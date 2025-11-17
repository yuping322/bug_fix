# Implementation Tasks: Agent MCP Integration

**Feature**: Agent MCP Integration
**Date**: 2025-11-13
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

## Overview

This document contains the detailed implementation tasks for the Agent MCP Integration feature. Tasks are organized by user story to enable independent implementation and testing. Each user story represents a complete, independently testable increment.

## Dependencies & Parallel Execution

### User Story Dependencies
- **US1** (LLM Agent Direct Parameter Passing): Independent - Foundation for parameter system
- **US2** (CLI Agent MCP Service Integration): Depends on US1 - Builds on parameter system
- **US3** (Docker Agent MCP Service Integration): Depends on US2 - Extends MCP service management
- **US4** (CLI Agent MCP Address Configuration): Depends on US2 - Enhances CLI agent configuration

### Parallel Opportunities
Tasks marked `[P]` can be executed in parallel with other `[P]` tasks in the same phase. Parallel tasks work on different files and have no dependencies on incomplete tasks.

## Phase 1: Setup

Project initialization and foundational infrastructure setup.

- [ ] T001 Create MCP service manager base class in src/agents/mcp_service.py
- [ ] T002 Create MCP connection and service configuration models in src/core/config.py
- [ ] T003 Add MCP-related fields to AgentConfig in src/agents/base.py
- [ ] T004 Create MCP service status enums in src/core/config.py
- [ ] T005 [P] Update project dependencies for MCP protocol support in pyproject.toml
- [ ] T006 [P] Create MCP utilities module in src/utils/mcp.py

## Phase 2: Foundational

Blocking prerequisites that must complete before user story implementation.

- [ ] T007 Implement MCPServiceConfig validation in src/core/config.py
- [ ] T008 Create MCP connection pool management in src/agents/mcp_service.py
- [ ] T009 Implement MCP service health checking in src/agents/mcp_service.py
- [ ] T010 Add MCP service lifecycle management in src/agents/mcp_service.py
- [ ] T011 Create MCP service discovery utilities in src/utils/mcp.py
- [ ] T012 Implement async context managers for MCP connections in src/agents/mcp_service.py

## Phase 3: User Story 1 (P1) - LLM Agent Direct Parameter Passing

**Goal**: Enable LLM agents to receive parameters directly without MCP service dependency
**Independent Test**: Create LLM agent instance, pass parameters directly, verify execution without MCP service involvement

- [ ] T013 [US1] Remove tools parameter from ClaudeAgent in src/agents/claude.py
- [ ] T014 [US1] Remove tools parameter from CodexAgent in src/agents/codex.py
- [ ] T015 [US1] Remove tools parameter from CopilotAgent in src/agents/copilot.py
- [ ] T016 [US1] Update LLM agent execution logic to accept direct parameters in src/agents/base.py
- [ ] T017 [US1] Add parameter validation for LLM agents in src/agents/base.py
- [ ] T018 [US1] Update agent configuration validation to reject MCP fields for LLM agents in src/core/config.py

## Phase 4: User Story 2 (P1) - CLI Agent MCP Service Integration

**Goal**: Enable CLI agents to automatically start MCP services and access tools dynamically
**Independent Test**: Create CLI agent, verify MCP service auto-startup, confirm tool access through MCP protocol

- [ ] T019 [US2] Implement MCP service auto-startup for CLI agents in src/agents/cli_agent.py
- [ ] T020 [US2] Add MCP connection injection logic to CLI agent execution in src/agents/cli_agent.py
- [ ] T021 [US2] Create CLI agent MCP service integration tests in tests/unit/test_cli_agent.py
- [ ] T022 [US2] Implement MCP service validation before CLI agent execution in src/agents/cli_agent.py
- [ ] T023 [US2] Add MCP connection cleanup for CLI agents in src/agents/cli_agent.py
- [ ] T024 [US2] Update CLI agent configuration to support MCP integration in src/agents/cli_agent.py

## Phase 5: User Story 3 (P2) - Docker Agent MCP Service Integration

**Goal**: Enable Docker agents to handle MCP service startup and injection automatically
**Independent Test**: Create Docker agent in container, verify MCP service startup, confirm tool access through MCP protocol

- [ ] T025 [US3] Implement MCP service management for Docker agents in src/agents/docker_agent.py
- [ ] T026 [US3] Add container networking configuration for MCP services in src/agents/docker_agent.py
- [ ] T027 [US3] Create Docker agent MCP integration tests in tests/unit/test_docker_agent.py
- [ ] T028 [US3] Implement MCP service health checks for Docker containers in src/agents/docker_agent.py
- [ ] T029 [US3] Add MCP connection injection for Docker agent execution in src/agents/docker_agent.py
- [ ] T030 [US3] Update Docker agent configuration for MCP support in src/agents/docker_agent.py

## Phase 6: User Story 4 (P2) - CLI Agent MCP Address Configuration

**Goal**: Enable CLI agents to accept MCP service address parameters for flexible service connections
**Independent Test**: Configure CLI agent with MCP address parameters, verify connection to correct MCP service

- [ ] T031 [US4] Add MCP address parameter validation to CLI agent config in src/agents/cli_agent.py
- [ ] T032 [US4] Implement MCP address resolution logic in src/agents/cli_agent.py
- [ ] T033 [US4] Create CLI agent MCP address configuration tests in tests/unit/test_cli_agent.py
- [ ] T034 [US4] Add MCP address precedence handling (config > env > auto-discovery) in src/agents/cli_agent.py
- [ ] T035 [US4] Update CLI agent documentation for MCP address configuration in src/agents/cli_agent.py
- [ ] T036 [US4] Implement MCP address validation with user-friendly error messages in src/agents/cli_agent.py

## Phase 7: API Integration

Agent and MCP service management API endpoints implementation.

- [ ] T037 Implement agent creation endpoint with MCP validation in src/api/routes/agent.py
- [ ] T038 Implement agent update endpoint with MCP configuration in src/api/routes/agent.py
- [ ] T039 Implement agent execution endpoint with MCP integration in src/api/routes/execution.py
- [ ] T040 Implement MCP service registration endpoint in src/api/routes/mcp.py
- [ ] T041 Implement MCP service listing endpoint in src/api/routes/mcp.py
- [ ] T042 Implement MCP service health check endpoint in src/api/routes/mcp.py

## Phase 8: Integration Testing

End-to-end testing for complete user workflows.

- [ ] T043 Create integration tests for LLM agent direct parameter passing in tests/integration/test_agent_mcp_integration.py
- [ ] T044 Create integration tests for CLI agent MCP service integration in tests/integration/test_agent_mcp_integration.py
- [ ] T045 Create integration tests for Docker agent MCP service integration in tests/integration/test_agent_mcp_integration.py
- [ ] T046 Create integration tests for CLI agent MCP address configuration in tests/integration/test_agent_mcp_integration.py
- [ ] T047 Create API contract tests for agent management endpoints in tests/contract/test_agent_contracts.py
- [ ] T048 Create API contract tests for MCP service endpoints in tests/contract/test_mcp_contracts.py

## Phase 9: Polish & Cross-Cutting Concerns

Final polish, documentation, and cross-cutting concerns.

- [ ] T049 Add comprehensive error handling for MCP connection failures in src/agents/mcp_service.py
- [ ] T050 Implement circuit breaker pattern for MCP service failures in src/agents/mcp_service.py
- [ ] T051 Add performance monitoring for MCP service operations in src/core/observability.py
- [ ] T052 Update CLI commands to support MCP service management in src/cli/commands/agent.py
- [ ] T053 Create migration documentation for removing tools parameter in docs/migration.md
- [ ] T054 Add MCP integration examples to quickstart documentation in docs/quickstart.md
- [ ] T055 Implement graceful shutdown handling for MCP services in src/agents/mcp_service.py
- [ ] T056 Add comprehensive logging for MCP operations in src/core/logging.py
- [ ] T057 Create performance benchmarks for MCP service operations in tests/performance/
- [ ] T058 Update API documentation with MCP integration details in docs/api.md
- [ ] T059 Add troubleshooting guide for MCP connection issues in docs/troubleshooting.md
- [ ] T060 Final code review and cleanup across all modified files

## Implementation Strategy

### MVP Scope (User Story 1)
Complete US1 first to establish the parameter system foundation. This provides immediate value and validates the core approach before investing in MCP service management complexity.

### Incremental Delivery
Each user story delivers complete, testable functionality:
- **US1**: Parameter system foundation
- **US2**: CLI agent MCP integration
- **US3**: Docker agent MCP integration  
- **US4**: Enhanced CLI configuration

### Risk Mitigation
- Parallel tasks reduce implementation timeline
- Independent testing per user story enables early issue detection
- API contracts ensure interface compatibility
- Comprehensive error handling prevents runtime failures

## Success Criteria Validation

- [ ] All tasks completed with passing tests
- [ ] 100% LLM agents execute with direct parameters (US1)
- [ ] 100% CLI agents establish MCP connections within 30s (US2)
- [ ] 100% Docker agents establish MCP connections within 30s (US3)
- [ ] All CLI agents support MCP address configuration (US4)
- [ ] Agent execution time increase ≤10% due to MCP integration
- [ ] 99% MCP service connection success rate under normal conditions</content>
<parameter name="filePath">/Users/fengzhi/Downloads/git/bug_fix/specs/002-agent-mcp-integration/tasks.md