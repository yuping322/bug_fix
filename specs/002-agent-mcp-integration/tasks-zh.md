# 实施任务：代理MCP集成

**功能**：代理MCP集成
**日期**：2025-11-13
**规范**：[spec.md](spec.md)
**计划**：[plan.md](plan.md)

## 概述

本文档包含代理MCP集成功能的详细实施任务。任务按用户故事组织，以实现独立实施和测试。每个用户故事代表一个完整、独立可测试的增量。

## 依赖关系与并行执行

### 用户故事依赖关系
- **US1** (LLM代理直接参数传递)：独立 - 参数系统的基础
- **US2** (CLI代理MCP服务集成)：依赖US1 - 在参数系统基础上构建
- **US3** (Docker代理MCP服务集成)：依赖US2 - 扩展MCP服务管理
- **US4** (CLI代理MCP地址配置)：依赖US2 - 增强CLI代理配置

### 并行机会
标记为`[P]`的任务可以与其他同阶段的`[P]`任务并行执行。并行任务处理不同文件，且不依赖于未完成的任务。

## 第1阶段：设置

项目初始化和基础架构设置。

- [ ] T001 在src/agents/mcp_service.py中创建MCP服务管理器基类
- [ ] T002 在src/core/config.py中创建MCP连接和服务配置模型
- [ ] T003 在src/agents/base.py中为AgentConfig添加MCP相关字段
- [ ] T004 在src/core/config.py中创建MCP服务状态枚举
- [ ] T005 [P] 在pyproject.toml中更新项目依赖以支持MCP协议
- [ ] T006 [P] 在src/utils/mcp.py中创建MCP工具模块

## 第2阶段：基础

在用户故事实施之前必须完成的阻塞性先决条件。

- [ ] T007 在src/core/config.py中实现MCPServiceConfig验证
- [ ] T008 在src/agents/mcp_service.py中创建MCP连接池管理
- [ ] T009 在src/agents/mcp_service.py中实现MCP服务健康检查
- [ ] T010 在src/agents/mcp_service.py中添加MCP服务生命周期管理
- [ ] T011 在src/utils/mcp.py中创建MCP服务发现工具
- [ ] T012 在src/agents/mcp_service.py中实现MCP连接的异步上下文管理器

## 第3阶段：用户故事1 (P1) - LLM代理直接参数传递

**目标**：使LLM代理能够直接接收参数而无需MCP服务依赖
**独立测试**：创建LLM代理实例，直接传递参数，验证在不涉及MCP服务的情况下执行

- [ ] T013 [US1] 从src/agents/claude.py中的ClaudeAgent移除tools参数
- [ ] T014 [US1] 从src/agents/codex.py中的CodexAgent移除tools参数
- [ ] T015 [US1] 从src/agents/copilot.py中的CopilotAgent移除tools参数
- [ ] T016 [US1] 在src/agents/base.py中更新LLM代理执行逻辑以接受直接参数
- [ ] T017 [US1] 在src/agents/base.py中为LLM代理添加参数验证
- [ ] T018 [US1] 在src/core/config.py中更新代理配置验证以拒绝LLM代理的MCP字段

## 第4阶段：用户故事2 (P1) - CLI代理MCP服务集成

**目标**：使CLI代理能够自动启动MCP服务并动态访问工具
**独立测试**：创建CLI代理，验证MCP服务自动启动，确认通过MCP协议访问工具

- [ ] T019 [US2] 在src/agents/cli_agent.py中为CLI代理实现MCP服务自动启动
- [ ] T020 [US2] 在src/agents/cli_agent.py中为CLI代理执行添加MCP连接注入逻辑
- [ ] T021 [US2] 在tests/unit/test_cli_agent.py中创建CLI代理MCP服务集成测试
- [ ] T022 [US2] 在src/agents/cli_agent.py中实现CLI代理执行前的MCP服务验证
- [ ] T023 [US2] 在src/agents/cli_agent.py中为CLI代理添加MCP连接清理
- [ ] T024 [US2] 在src/agents/cli_agent.py中更新CLI代理配置以支持MCP集成

## 第5阶段：用户故事3 (P2) - Docker代理MCP服务集成

**目标**：使Docker代理能够自动处理MCP服务启动和注入
**独立测试**：在容器中创建Docker代理，验证MCP服务启动，确认通过MCP协议访问工具

- [ ] T025 [US3] 在src/agents/docker_agent.py中为Docker代理实现MCP服务管理
- [ ] T026 [US3] 在src/agents/docker_agent.py中为MCP服务添加容器网络配置
- [ ] T027 [US3] 在tests/unit/test_docker_agent.py中创建Docker代理MCP集成测试
- [ ] T028 [US3] 在src/agents/docker_agent.py中为Docker容器实现MCP服务健康检查
- [ ] T029 [US3] 在src/agents/docker_agent.py中为Docker代理执行添加MCP连接注入
- [ ] T030 [US3] 在src/agents/docker_agent.py中更新Docker代理配置以支持MCP

## 第6阶段：用户故事4 (P2) - CLI代理MCP地址配置

**目标**：使CLI代理能够接受MCP服务地址参数以实现灵活的服务连接
**独立测试**：使用MCP地址参数配置CLI代理，验证连接到正确的MCP服务

- [ ] T031 [US4] 在src/agents/cli_agent.py中为CLI代理配置添加MCP地址参数验证
- [ ] T032 [US4] 在src/agents/cli_agent.py中实现MCP地址解析逻辑
- [ ] T033 [US4] 在tests/unit/test_cli_agent.py中创建CLI代理MCP地址配置测试
- [ ] T034 [US4] 在src/agents/cli_agent.py中添加MCP地址优先级处理（配置 > 环境 > 自动发现）
- [ ] T035 [US4] 在src/agents/cli_agent.py中更新CLI代理文档以说明MCP地址配置
- [ ] T036 [US4] 在src/agents/cli_agent.py中实现具有用户友好错误消息的MCP地址验证

## 第7阶段：API集成

代理和MCP服务管理API端点的实现。

- [ ] T037 在src/api/routes/agent.py中实现带有MCP验证的代理创建端点
- [ ] T038 在src/api/routes/agent.py中实现带有MCP配置的代理更新端点
- [ ] T039 在src/api/routes/execution.py中实现带有MCP集成的代理执行端点
- [ ] T040 在src/api/routes/mcp.py中实现MCP服务注册端点
- [ ] T041 在src/api/routes/mcp.py中实现MCP服务列表端点
- [ ] T042 在src/api/routes/mcp.py中实现MCP服务健康检查端点

## 第8阶段：集成测试

完整用户工作流的端到端测试。

- [ ] T043 在tests/integration/test_agent_mcp_integration.py中创建LLM代理直接参数传递的集成测试
- [ ] T044 在tests/integration/test_agent_mcp_integration.py中创建CLI代理MCP服务集成的集成测试
- [ ] T045 在tests/integration/test_agent_mcp_integration.py中创建Docker代理MCP服务集成的集成测试
- [ ] T046 在tests/integration/test_agent_mcp_integration.py中创建CLI代理MCP地址配置的集成测试
- [ ] T047 在tests/contract/test_agent_contracts.py中创建代理管理端点的API合约测试
- [ ] T048 在tests/contract/test_mcp_contracts.py中创建MCP服务端点的API合约测试

## 第9阶段：完善与跨领域关注点

最终完善、文档和跨领域关注点。

- [ ] T049 在src/agents/mcp_service.py中为MCP连接失败添加全面错误处理
- [ ] T050 在src/agents/mcp_service.py中实现MCP服务失败的断路器模式
- [ ] T051 在src/core/observability.py中为MCP服务操作添加性能监控
- [ ] T052 在src/cli/commands/agent.py中更新CLI命令以支持MCP服务管理
- [ ] T053 在docs/migration.md中创建移除tools参数的迁移文档
- [ ] T054 在docs/quickstart.md中为快速入门文档添加MCP集成示例
- [ ] T055 在src/agents/mcp_service.py中实现MCP服务的优雅关闭处理
- [ ] T056 在src/core/logging.py中为MCP操作添加全面日志记录
- [ ] T057 在tests/performance/中创建MCP服务操作的性能基准测试
- [ ] T058 在docs/api.md中更新带有MCP集成详细信息的API文档
- [ ] T059 在docs/troubleshooting.md中添加MCP连接问题的故障排除指南
- [ ] T060 在所有修改文件中进行最终代码审查和清理

## 实施策略

### MVP范围（用户故事1）
首先完成US1以建立参数系统基础。这提供了即时价值，并在投资MCP服务管理复杂性之前验证核心方法。

### 增量交付
每个用户故事交付完整、可测试的功能：
- **US1**：参数系统基础
- **US2**：CLI代理MCP集成
- **US3**：Docker代理MCP集成
- **US4**：增强的CLI配置

### 风险缓解
- 并行任务减少实施时间线
- 每个用户故事的独立测试实现早期问题检测
- API合约确保接口兼容性
- 全面错误处理防止运行时失败

## 成功标准验证

- [ ] 所有任务完成并通过测试
- [ ] 100% LLM代理使用直接参数执行（US1）
- [ ] 100% CLI代理在30秒内建立MCP连接（US2）
- [ ] 100% Docker代理在30秒内建立MCP连接（US3）
- [ ] 所有CLI代理支持MCP地址配置（US4）
- [ ] 由于MCP集成，代理执行时间增加≤10%
- [ ] 在正常条件下，99%的MCP服务连接成功率</content>
<parameter name="filePath">/Users/fengzhi/Downloads/git/bug_fix/specs/002-agent-mcp-integration/tasks-zh.md