# 数据模型：多智能体代码开发编排平台

**日期**：2025-11-12
**功能**：多智能体代码开发编排平台

## 概述

数据模型定义了多智能体编排平台的核心实体及其关系。所有实体都设计有验证规则，这些规则源自功能需求，并包括状态转换（如果适用）。

## 核心实体

### 1. 智能体

**目的**：表示具有特定能力的 AI 服务提供商，具有配置和凭据

**字段**：
- `id: str` - 唯一标识符（例如："claude"、"codex"、"copilot"）
- `name: str` - 人类可读名称
- `provider: str` - 提供商名称（anthropic、openai、github）
- `model: str` - 模型标识符（claude-3-sonnet-20240229、gpt-4）
- `capabilities: List[str]` - 支持的能力（code_review、task_planning 等）
- `config: Dict[str, Any]` - 提供商特定配置
- `status: AgentStatus` - 当前运营状态
- `last_health_check: datetime` - 最后健康验证的时间戳
- `created_at: datetime` - 创建时间戳
- `updated_at: datetime` - 最后修改时间戳

**验证规则**：
- `id` 必须唯一且匹配模式 `^[a-z][a-z0-9_-]*$`
- `provider` 必须是支持的提供商之一
- `model` 必须对提供商有效
- `capabilities` 必须是非空列表
- `config` 必须包含提供商所需的凭据

**状态转换**：
```
UNREGISTERED → REGISTERING → ACTIVE ↔ INACTIVE
    ↓             ↓            ↓
  ERROR         ERROR        ERROR
```

### 2. 工作流

**目的**：定义具有执行逻辑的开发任务序列

**字段**：
- `id: str` - 唯一标识符
- `name: str` - 人类可读名称
- `description: str` - 详细描述
- `type: WorkflowType` - SIMPLE 或 LANGGRAPH
- `steps: List[WorkflowStep]` - 有序执行步骤列表
- `config: Dict[str, Any]` - 工作流特定配置
- `metadata: Dict[str, Any]` - 附加元数据（标签、版本等）
- `created_at: datetime` - 创建时间戳
- `updated_at: datetime` - 最后修改时间戳

**验证规则**：
- `id` 必须唯一且匹配模式 `^[a-z][a-z0-9_-]*$`
- `steps` 必须包含至少一个步骤
- 每个步骤必须引用有效智能体并具有必需字段
- `type` 必须是有效 WorkflowType 枚举

**关系**：
- 通过步骤引用多个 `Agent` 实体
- 可以实例化为 `WorkflowExecution`

### 3. 工作流步骤

**目的**：定义工作流中的单个工作单元

**字段**：
- `id: str` - 工作流中的步骤标识符
- `name: str` - 人类可读步骤名称
- `agent_id: str` - 执行智能体的引用
- `prompt_template: str` - 智能体提示的模板
- `input_mappings: Dict[str, str]` - 输入参数映射
- `output_key: str` - 存储步骤输出的键
- `condition: Optional[str]` - 条件执行表达式
- `timeout_seconds: int` - 最大执行时间
- `retry_policy: RetryPolicy` - 失败处理策略
- `dependencies: List[str]` - 必需的先前步骤输出

**验证规则**：
- `agent_id` 必须引用现有智能体
- `prompt_template` 必须是有效的 Jinja2 模板
- `timeout_seconds` 必须在 10-3600 之间
- `condition` 如果提供必须是有效的表达式

### 4. 执行上下文

**目的**：包含工作流执行的共享配置和运行时环境

**字段**：
- `id: str` - 唯一执行标识符
- `workflow_id: str` - 被执行工作流的引用
- `workspace_dir: str` - 工作目录路径
- `parameters: Dict[str, Any]` - 执行参数
- `environment: Dict[str, str]` - 环境变量
- `shared_config: Dict[str, Any]` - 全局配置覆盖
- `start_time: datetime` - 执行开始时间戳
- `end_time: Optional[datetime]` - 执行完成时间戳
- `status: ExecutionStatus` - 当前执行状态

**验证规则**：
- `workspace_dir` 必须是绝对路径且可写
- `parameters` 必须匹配工作流参数模式
- `shared_config` 必须是有效的配置结构

**状态转换**：
```
PENDING → RUNNING → COMPLETED
    ↓        ↓         ↓
  FAILED   FAILED    FAILED
```

### 5. 执行日志

**目的**：记录可观测性和调试的工作流执行细节

**字段**：
- `id: str` - 唯一日志条目标识符
- `execution_id: str` - 执行上下文的引用
- `step_id: str` - 生成日志的步骤
- `level: LogLevel` - 日志严重级别
- `message: str` - 日志消息
- `timestamp: datetime` - 日志时间戳
- `metadata: Dict[str, Any]` - 结构化日志数据
- `trace_id: str` - 分布式跟踪标识符

**验证规则**：
- `execution_id` 必须引用现有执行
- `level` 必须是有效的 LogLevel 枚举
- `timestamp` 必须是有效的日期时间

### 6. 配置

**目的**：平台的层次化配置管理

**字段**：
- `version: str` - 配置版本
- `global: GlobalConfig` - 全局设置
- `agents: Dict[str, AgentConfig]` - 智能体配置
- `workflows: Dict[str, WorkflowConfig]` - 工作流模板
- `observability: ObservabilityConfig` - 监控设置
- `deployment: DeploymentConfig` - 部署特定设置

**验证规则**：
- `version` 必须遵循语义版本控制
- 所有嵌套配置必须根据其模式有效
- 必需字段必须存在于活动组件

## 实体关系

```
Configuration (1) ────→ Agent (N)
Configuration (1) ────→ Workflow (N)
Workflow (1) ────→ WorkflowStep (N)
Workflow (1) ────→ Agent (N) [通过步骤]
ExecutionContext (1) ──→ Workflow (1)
ExecutionContext (1) ──→ ExecutionLog (N)
ExecutionContext (1) ──→ Agent (N) [通过工作流步骤]
```

## 数据流

1. **配置加载**：Configuration → Agent Registry → Workflow Registry
2. **工作流执行**：ExecutionContext → Workflow → Steps → Agents → Logs
3. **结果聚合**：ExecutionContext → ExecutionLogs → Structured Results

## 验证规则总结

### 业务规则
- 每个工作流必须有至少一个步骤
- 工作流执行前必须验证智能体
- 执行上下文必须有有效的 workspace 目录
- 配置更改需要验证后应用

### 数据完整性
- 所有外键引用必须有效
- 时间戳必须单调递增
- 状态转换必须遵循定义的状态机
- 配置版本必须在应用后不可变

### 性能约束
- 执行日志不应超过每个执行 10MB
- 配置文件的解析应在 100ms 内完成
- 相同提示的智能体响应应被缓存
- 并发执行不应超过配置限制

## 迁移考虑

### 版本 1.0 模式
- 具有所有核心实体的初始模式
- 灵活性的 JSON 基础存储
- 简单性的文件基础持久性

### 未来扩展
- 可扩展性的数据库迁移路径
- 向后兼容的模式版本控制
- 配置更改的审计跟踪
- 数据导出/导入能力