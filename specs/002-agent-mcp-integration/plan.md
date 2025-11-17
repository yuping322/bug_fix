# Implementation Plan: Agent MCP Integration

**Branch**: `002-agent-mcp-integration` | **Date**: 2025-11-12 | **Spec**: [link to spec.md](spec.md)
**Input**: Feature specification from `/specs/002-agent-mcp-integration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement agent parameter handling system that removes the `tools` parameter and provides seamless MCP service integration for CLI/Docker agents while maintaining direct parameter passing for LLM agents. The implementation will encapsulate complexity to provide a unified, user-transparent interface.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Pydantic, MCP protocol, asyncio  
**Storage**: N/A (configuration-based, in-memory execution state)  
**Testing**: pytest with async support  
**Target Platform**: Linux/macOS server environments  
**Project Type**: Backend API service with agent orchestration  
**Performance Goals**: API response time <500ms p95, MCP service startup <30 seconds  
**Constraints**: Memory usage <80% of allocated resources, CPU usage <70% during normal operations, MCP connection timeouts handled gracefully  
**Scale/Scope**: Support for LLM, CLI, and Docker agent types with dynamic MCP service management

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Code Quality Standards
- ✅ Code will follow existing Python conventions and patterns
- ✅ Complex MCP integration logic will be well-documented
- ✅ Automated linting (ruff) and formatting will be maintained
- ✅ No exceptions to quality standards

### II. Test-First Development
- ✅ All acceptance criteria will have corresponding test cases
- ✅ Implementation will focus on making tests pass
- ✅ Code coverage will exceed 80% for new functionality
- ✅ Tests will be independently executable

### III. User Experience Consistency
- ✅ Agent interface will remain consistent across all agent types
- ✅ Error messages will be user-friendly and actionable
- ✅ MCP service management will be transparent to users
- ✅ No breaking changes to existing agent APIs

### IV. Performance Requirements
- ✅ MCP service startup will be optimized (<30 seconds)
- ✅ API response times will remain <500ms p95
- ✅ Memory and CPU usage will stay within limits
- ✅ Connection pooling and cleanup will be implemented

**GATE STATUS**: ✅ ALL GATES PASS - No violations detected. Feature aligns with all constitutional principles.

## Phase Status

### Phase 0: Research ✅ COMPLETED
- Comprehensive research on MCP service management architecture
- CLI agent parameter handling strategies documented
- Docker agent lifecycle management approaches identified
- Error handling and performance optimization strategies defined
- Backward compatibility approaches established

### Phase 1: Design ✅ COMPLETED
- Data model entities and relationships defined
- API contracts specified (English and Chinese)
- Quickstart guides created (English and Chinese)
- Agent context updated with new MCP technologies
- Constitution re-check passed - all gates remain open

### Phase 2: Tasks ✅ COMPLETED
- Generate implementation tasks breakdown
- Create detailed task specifications
- Establish implementation milestones
- Generate Chinese translation (tasks-zh.md)

### Phase 3: Implementation (Next)
- Execute implementation tasks from tasks.md
- Follow user story dependencies and parallel execution opportunities
- Complete MVP scope (User Story 1) first

## Project Structure

### Documentation (this feature)

```text
specs/002-agent-mcp-integration/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command) ✅ COMPLETED
├── data-model.md        # Phase 1 output (/speckit.plan command) ✅ COMPLETED
├── quickstart.md        # Phase 1 output (/speckit.plan command) ✅ COMPLETED
├── contracts/           # Phase 1 output (/speckit.plan command) ✅ COMPLETED
│   ├── api.yaml         # OpenAPI specification (English)
│   └── api-zh.yaml      # OpenAPI specification (Chinese)
├── tasks.md             # Phase 2 output (/speckit.tasks command) ✅ COMPLETED
└── tasks-zh.md          # Phase 2 output (/speckit.tasks command - Chinese translation) ✅ COMPLETED
```

### Source Code (repository root)

```text
src/
├── agents/
│   ├── base.py              # AgentConfig, BaseAgent classes (MODIFIED)
│   ├── claude.py            # ClaudeAgent (MODIFIED - remove tools param)
│   ├── codex.py             # CodexAgent (MODIFIED - remove tools param)
│   ├── copilot.py           # CopilotAgent (MODIFIED - remove tools param)
│   ├── cli_agent.py         # CLIExecutionAgent (MODIFIED - add MCP integration)
│   ├── docker_agent.py      # DockerExecutionAgent (MODIFIED - add MCP integration)
│   └── mcp_service.py       # NEW - MCP service manager
├── core/
│   ├── config.py            # PlatformConfig (MODIFIED - update agent config)
│   ├── execution.py         # Execution context (MODIFIED - MCP integration)
│   └── workflow.py          # WorkflowEngine (MODIFIED - agent parameter handling)
├── api/
│   └── routes/
│       └── execution.py     # Execution routes (MODIFIED - parameter validation)
└── utils/
    └── mcp.py               # MCP utilities (MODIFIED - service management)

tests/
├── unit/
│   ├── test_agents.py       # Agent tests (MODIFIED - parameter handling)
│   ├── test_mcp_service.py  # NEW - MCP service tests
│   └── test_execution_api.py # Execution API tests (MODIFIED)
├── integration/
│   └── test_agent_mcp_integration.py # NEW - MCP integration tests
└── contract/
    └── test_agent_contracts.py # Agent contract tests (MODIFIED)
```

**Structure Decision**: Following existing project structure with modifications to existing files and addition of new MCP service management components. Changes are encapsulated to maintain backward compatibility while adding new functionality.

## Agent Context

**Active Technologies** (Updated):
- Python 3.11 + anthropic (Claude SDK), GitPython, langgraph, langchain, fastapi, typer, docker, pyyaml, structlog, rich
- **NEW**: MCP protocol integration, asyncio-based service management, connection pooling

**Commands** (Updated):
- cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .
- **NEW**: MCP service management commands (to be implemented in CLI)

**Code Style** (Updated):
- Python 3.11: Follow standard conventions
- **NEW**: Async/await patterns for MCP service operations, connection lifecycle management

**Recent Changes** (Updated):
- 001-agent-orchestration: Added Python 3.11 + anthropic (Claude SDK), GitPython, langgraph, langchain, fastapi, typer, docker, pyyaml, structlog, rich
- **NEW**: 002-agent-mcp-integration: MCP protocol integration, unified agent parameter handling, service management architecture

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
