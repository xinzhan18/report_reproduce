# FARS 架构评估与优化计划

## Context

FARS 是一个自动化量化金融研究系统，使用 4 个 AI Agent 通过 LangGraph Pipeline 协作。项目已完成基本功能，但存在严重的架构腐化：全局单例泛滥、接口不统一、大量死代码、配置与代码脱节。核心目标是重构为**高效、工程化**的代码。

---

## 一、当前问题诊断（按严重度排序）

### P0 - 架构级缺陷

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | **全局单例泛滥** | `llm_config.py:85` `_llm_config`、`database.py:552` `_db`、`knowledge_graph.py:459` `get_knowledge_graph()` 每次创建新实例 | 无法并发、无法测试、无法为不同Agent用不同配置 |
| 2 | **LLM 调用接口分裂** | `knowledge_graph.py:293` 和 `iteration_memory.py` 直接调用 `llm.messages.create()`，绕过 `agents/llm.py` | 无重试、无 token 统计、硬编码模型名 |
| 3 | **配置与代码完全脱节** | `agent_config.py` 定义了 `deep_analysis_count: 5`、`max_retries: 2` 等参数，但 Agent 代码从不读取 | 配置形同虚设，改配置无效 |
| 4 | **ResearchState 类型断层** | `state.py` 定义了 7 个 dataclass（RankedPaper、StructuredInsights 等），但 ResearchState 未引用它们 | Agent 间数据传递靠隐式文件约定 |

### P1 - 死代码 / 过度设计

| # | 问题 | 位置 | 行数 |
|---|------|------|------|
| 5 | `multi_llm_config.py` **完全未使用** | `config/multi_llm_config.py` | 358 行 |
| 6 | `auth_config.py` OAuth 预留代码未使用 | `config/auth_config.py` 约 300 行 OAuth 流程 | ~300 行 |
| 7 | `llm_config_oauth.py` 未使用 | `config/llm_config_oauth.py` | 待确认 |
| 8 | `database.py` 的 `log_agent_execution()` 无人调用 | `database.py:520-544`，`agent_executions` 表存在但无写入 | - |
| 9 | `get_knowledge_graph()` 每次创建新实例 | `knowledge_graph.py:459-461` 没有缓存 | 每次都重新建表+populate |
| 10 | `get_llm()` 的 `model_type` 参数被忽略 | `llm_config.py:101-112` 接收 model_type 但返回相同 client | 函数签名误导 |

### P2 - 代码质量

| # | 问题 | 位置 |
|---|------|------|
| 11 | **Prompt 全硬编码** | 11 个 LLM 调用点全是 f-string，散在各方法内 |
| 12 | **`_build_kg_context()` 重复** | `ideation_agent.py` 和 `planning_agent.py` 几乎相同的实现 |
| 13 | **错误处理不一致** | IdeationAgent 有完善的降级，WritingAgent 零错误处理 |
| 14 | **Magic Numbers** | `pipeline.py:49` 硬编码 `iteration < 2`，应读 config |
| 15 | **`knowledge_graph.py:293`** 硬编码模型名 `claude-sonnet-4-5-20250929` | 应从 config 读取 |

---

## 二、优化方案（4 个阶段，每阶段独立可交付）

### 阶段 1：清理死代码 + 修复配置脱节

**目标**：删除无用代码，让现有配置真正生效

#### 1.1 删除死代码
- [ ] 删除 `config/multi_llm_config.py`（358 行，完全未使用）
- [ ] 删除 `config/llm_config_oauth.py`（如确认未使用）
- [ ] 精简 `config/auth_config.py`：删除 OAuth 预留代码，仅保留 API Key 认证
- [ ] 清理 `llm_config.py`：删除 `get_haiku_llm()`（无人调用），简化 `get_llm()` 签名

#### 1.2 让配置生效
- [ ] `pipeline.py:49`：`state["iteration"] < 2` → 读取 `PIPELINE_CONFIG["max_experiment_retries"]`（来自 `agent_config.py:64`）
- [ ] Agent 代码中读取 config 参数：
  - `ideation_agent.py`：使用 `self.config["deep_analysis_count"]`、`self.config["max_papers_per_scan"]`
  - `experiment_agent.py`：使用 `self.config["max_retries"]`、`self.config["validation_metrics"]`
  - `writing_agent.py`：使用 `self.config["citation_style"]`
  - `planning_agent.py`：使用 `self.config["max_iterations"]`

#### 1.3 修复 `get_knowledge_graph()`
- [ ] 改为真正的单例（加缓存），避免每次调用都重新创建实例+建表+populate

**关键文件**：
- 删除: `config/multi_llm_config.py`, `config/llm_config_oauth.py`
- 修改: `config/auth_config.py`, `config/llm_config.py`, `core/pipeline.py`, `core/knowledge_graph.py`
- 修改: `agents/ideation_agent.py`, `agents/planning_agent.py`, `agents/experiment_agent.py`, `agents/writing_agent.py`

---

### 阶段 2：统一 LLM 调用接口

**目标**：所有 LLM 调用走同一路径，消除绕过行为

#### 2.1 统一所有 LLM 调用到 `agents/llm.py`
- [ ] `knowledge_graph.py:293-298`：将直接 `llm.messages.create()` 替换为 `call_llm_json()` from `agents.llm`
  - 去掉硬编码模型名 `claude-sonnet-4-5-20250929`
  - 利用 `agents/llm.py` 已有的重试机制
- [ ] `iteration_memory.py`：同上，所有直接 API 调用改为走 `agents.llm`
- [ ] `knowledge_graph.py` 的 `update_knowledge_from_research()` 内置的 JSON 解析逻辑替换为 `extract_json()`

#### 2.2 简化 BaseAgent 的 LLM 接口
- [ ] 拆分 `BaseAgent.call_llm()` 的双重人格：
  - `call_llm(prompt, **kwargs) -> str`：纯文本
  - `call_llm_json(prompt, **kwargs) -> dict`：JSON 解析
  - 删除 `response_format` 参数，消除接口歧义

#### 2.3 添加 token 统计（轻量级）
- [ ] 在 `agents/llm.py` 的 `call_llm()` 中，记录 `response.usage.input_tokens` / `output_tokens` 到 logger
- [ ] 利用已有的 `database.log_agent_execution()` 方法（当前无人调用），在 `BaseAgent._save_log()` 中调用它

**关键文件**：
- 修改: `agents/llm.py`, `agents/base_agent.py`
- 修改: `core/knowledge_graph.py`, `core/iteration_memory.py`

---

### 阶段 3：依赖注入重构

**目标**：消除全局单例，建立清晰的依赖树

#### 3.1 创建 Dependencies 容器
- [ ] 新建 `core/dependencies.py`：

```python
@dataclass
class Dependencies:
    llm_client: Anthropic
    database: ResearchDatabase
    knowledge_graph: QuantFinanceKnowledgeGraph
    file_manager: FileManager
    paper_fetcher: PaperFetcher
    data_fetcher: FinancialDataFetcher
    backtest_engine: BacktestEngine
    pdf_reader: PDFReader

    @classmethod
    def create(cls, **overrides) -> "Dependencies":
        """工厂方法，测试时可传入 mock"""
        ...
```

#### 3.2 重构 Pipeline 入口
- [ ] `create_research_pipeline(deps: Dependencies)` 接受注入
- [ ] `run_research_pipeline()` 创建 Dependencies 后传入
- [ ] 删除 `pipeline.py` 内部的工具实例化逻辑

#### 3.3 重构 BaseAgent 构造函数
- [ ] `BaseAgent.__init__()` 显式接收 `knowledge_graph` 参数（不再内部调用 `get_knowledge_graph()`）
- [ ] `BaseAgent.__init__()` 显式接收 `memory: AgentMemory` 参数（不再内部创建）

#### 3.4 移除全局单例
- [ ] 删除 `llm_config.py` 的 `_llm_config` 全局变量和 `get_llm_config()`
- [ ] 删除 `database.py` 的 `_db` 全局变量
- [ ] 保留 `get_database()` 和 `get_knowledge_graph()` 作为便捷函数（内部改为每次返回新实例或接受参数），但 Pipeline 路径不再使用它们

**关键文件**：
- 新建: `core/dependencies.py`
- 修改: `core/pipeline.py`, `agents/base_agent.py`
- 修改: `config/llm_config.py`, `core/database.py`, `core/knowledge_graph.py`

---

### 阶段 4：消除代码重复 + 提升一致性

**目标**：DRY 原则，统一模式

#### 4.1 提取 `_build_kg_context()` 到 BaseAgent
- [ ] 将 `ideation_agent.py` 和 `planning_agent.py` 中重复的 `_build_kg_context()` 提取到 `BaseAgent`
- [ ] 统一接口：`BaseAgent.build_kg_context(query: str, node_type: str = None) -> str`

#### 4.2 Prompt 外置到独立文件
- [ ] 新建 `prompts/` 目录
- [ ] 将 11 个 LLM 调用的 prompt 提取为 `.txt` 文件（使用简单的 `{variable}` 占位符，`str.format()` 渲染）
- [ ] 命名规则：`prompts/{agent_name}/{method_name}.txt`
- [ ] 在 BaseAgent 添加 `load_prompt(name: str, **vars) -> str` 方法

#### 4.3 统一错误处理
- [ ] 为 WritingAgent 添加与其他 Agent 一致的 try-except + 降级逻辑
- [ ] 统一 `knowledge_graph.py:339` 的 `print()` 为 `logger.error()`

#### 4.4 更新三级文档
- [ ] 更新所有修改文件的文件头注释
- [ ] 更新 `agents/CLAUDE.md`, `core/CLAUDE.md`, `config/CLAUDE.md`
- [ ] 更新根 `CLAUDE.md`

**关键文件**：
- 新建: `prompts/` 目录（~11 个 prompt 文件）
- 修改: `agents/base_agent.py`, `agents/ideation_agent.py`, `agents/planning_agent.py`
- 修改: `agents/writing_agent.py`, `core/knowledge_graph.py`

---

## 三、验证方案

每个阶段完成后执行：

1. **语法检查**：`python -m py_compile <modified_files>` 确保无语法错误
2. **导入检查**：`python -c "from core.pipeline import create_research_pipeline"` 确保无循环导入
3. **单元测试**：运行 `pytest tests/` 确保现有测试不破坏
4. **手动验证**：`python -c "from core.pipeline import create_research_pipeline; p = create_research_pipeline(); print('OK')"` 确保 Pipeline 可创建

---

## 四、Checklist

- [ ] 阶段 1：清理死代码 + 修复配置脱节
- [ ] 阶段 2：统一 LLM 调用接口
- [ ] 阶段 3：依赖注入重构
- [ ] 阶段 4：消除代码重复 + 提升一致性
