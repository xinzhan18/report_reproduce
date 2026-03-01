# FARS 架构评估与优化计划

## Context

FARS 已完成 Agentic Tool-Use 架构升级（2026-03-01），4 个 Agent 均为子包模式，Prompt 已提取到 prompts.py，通用工具已提取到 common_tools.py，token 追踪已在 _agentic_loop 中实现。大量死代码已清除。

但仍存在若干结构性问题影响代码的**工程化质量**。本计划聚焦于剩余的架构缺陷。

---

## 一、剩余问题诊断

### P0 - 必须修复

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | **`get_knowledge_graph()` 每次调用创建新实例** | `knowledge_graph.py:459-461` → `base_agent.py:48` | 每个 Agent 实例化时都重新建表+populate，4 个 Agent = 4 次 |
| 2 | **knowledge_graph 直接调用 LLM API** | `knowledge_graph.py:293-298` 直接 `llm.messages.create(model="claude-sonnet-4-5-20250929")` | 绕过 agents/llm.py 的重试机制，硬编码模型名，自建 JSON 解析 |
| 3 | **pipeline 硬编码重试次数** | `pipeline.py:49` `state["iteration"] < 2` | 应读取 `PIPELINE_CONFIG` 或 `agent_config["experiment"]["max_retries"]` |

### P1 - 代码质量

| # | 问题 | 位置 |
|---|------|------|
| 4 | **`_build_kg_context()` 在两个 Agent 中重复** | `ideation/agent.py:197-209` 和 `planning/agent.py:179-207`（逻辑不同但模式相同） |
| 5 | **`BaseAgent.call_llm()` 双重人格** | `base_agent.py:299-321` 的 `response_format` 参数导致返回类型 `Union[str, dict]` |
| 6 | **bare except** | `knowledge_graph.py:214` |
| 7 | **print 代替 logger** | `knowledge_graph.py:340`, `pipeline.py:89-93,152-156` 等多处 |
| 8 | **`get_llm()` 签名误导** | `llm_config.py:101-112` 接收 `model_type` 参数但完全忽略 |

### P2 - 全局单例

| # | 问题 | 位置 |
|---|------|------|
| 9 | `_llm_config` 全局变量 | `llm_config.py:85` |
| 10 | `_db` 全局变量 | `database.py:552` |

> 注：全局单例在当前单项目同步执行模式下不影响功能，但阻碍未来并发和测试。列为 P2 最后处理。

---

## 二、4 阶段优化方案

### 阶段 1：修复 KnowledgeGraph（P0-1, P0-2, P1-6, P1-7）

**目标**：消除 KnowledgeGraph 的所有结构性问题

#### 1.1 `get_knowledge_graph()` 改为真正的单例
- [ ] `knowledge_graph.py:459-461`：添加 `_kg` 全局缓存，避免重复实例化

```python
_kg: Optional[QuantFinanceKnowledgeGraph] = None

def get_knowledge_graph() -> QuantFinanceKnowledgeGraph:
    global _kg
    if _kg is None:
        _kg = QuantFinanceKnowledgeGraph()
    return _kg
```

#### 1.2 `update_knowledge_from_research()` 改用 agents/llm.py
- [ ] `knowledge_graph.py:293-298`：替换 `llm.messages.create()` 为 `call_llm_json()` from `agents.llm`
- [ ] 删除硬编码模型名 `claude-sonnet-4-5-20250929`，改用 `model` 参数（默认 "sonnet"）
- [ ] 删除自建 JSON 解析逻辑 (`knowledge_graph.py:300-306`)，复用 `extract_json()`
- [ ] 方法签名从 `llm: Anthropic` 改为 `llm_client, model: str = "sonnet"`

#### 1.3 修复代码质量
- [ ] `knowledge_graph.py:214`：bare `except:` → `except Exception:`
- [ ] `knowledge_graph.py:340`：`print(...)` → `logger.error(...)`
- [ ] 文件顶部添加 `logger = logging.getLogger("core.knowledge_graph")`

**修改文件**：
- `core/knowledge_graph.py`

---

### 阶段 2：修复 Pipeline 配置 + 简化 LLM 接口（P0-3, P1-5, P1-8）

**目标**：消除硬编码，清理接口歧义

#### 2.1 Pipeline 读取配置
- [ ] `pipeline.py:49`：`state["iteration"] < 2` → `state["iteration"] < AGENT_CONFIG["experiment"]["max_retries"]`
- [ ] 顶部添加 `from config.agent_config import AGENT_CONFIG`

#### 2.2 简化 `get_llm()` 签名
- [ ] `llm_config.py:101-112`：删除无用的 `model_type` 参数，签名改为 `get_llm() -> Anthropic`
- [ ] 删除 `get_haiku_llm()`（如仍存在且无人调用）
- [ ] 更新 `pipeline.py:65` 的调用处：`get_llm("sonnet")` → `get_llm()`

#### 2.3 清理 BaseAgent.call_llm 双重人格
- [ ] `base_agent.py:299-321`：删除 `response_format` 参数
- [ ] 只保留两个清晰的方法：
  - `call_llm(prompt, **kwargs) -> str`（纯文本）
  - `call_llm_json(prompt, **kwargs) -> dict`（JSON 解析）
- [ ] 搜索所有调用 `self.call_llm(..., response_format="json")` 的地方改为 `self.call_llm_json(...)`

#### 2.4 Pipeline 中的 print → logger
- [ ] `pipeline.py` 多处 `print()` 改为 `logger.info()`
- [ ] 添加 `logger = logging.getLogger("core.pipeline")`

**修改文件**：
- `core/pipeline.py`
- `config/llm_config.py`
- `agents/base_agent.py`
- 搜索并修改所有 `call_llm(..., response_format=...)` 调用处

---

### 阶段 3：消除 `_build_kg_context` 重复 + 依赖注入（P1-4, P2-9, P2-10）

**目标**：DRY 原则 + 消除全局单例

#### 3.1 提取 `_build_kg_context()` 到 BaseAgent
- [ ] 在 `base_agent.py` 中添加通用方法：

```python
def build_kg_context(self, query: str, node_type: str = None, max_items: int = 5) -> str:
    """查询知识图谱并格式化为 prompt 可注入的上下文。"""
    results = self.knowledge_graph.search_knowledge(query=query, node_type=node_type)
    if not results:
        return ""
    lines = ["## Prior Knowledge (from knowledge graph):"]
    for k in results[:max_items]:
        lines.append(f"- **{k['name']}**: {k['description'][:150]}")
    return "\n".join(lines) + "\n"
```

- [ ] `ideation/agent.py`：删除 `_build_kg_context()`，改调 `self.build_kg_context(direction)`
- [ ] `planning/agent.py`：删除 `_build_kg_context()`，改调组合查询：

```python
strategies_ctx = self.build_kg_context(hypothesis[:100], node_type="strategy")
metrics_ctx = self.build_kg_context("performance metrics", node_type="metric")
kg_context = strategies_ctx + metrics_ctx
```

#### 3.2 Dependencies 容器（轻量版）
- [ ] 新建 `core/dependencies.py`：

```python
@dataclass
class Dependencies:
    llm_client: Anthropic
    database: ResearchDatabase
    knowledge_graph: QuantFinanceKnowledgeGraph
    file_manager: FileManager
    paper_fetcher: PaperFetcher
    data_fetcher: DataFetcher
    pdf_reader: PDFReader

    @classmethod
    def create(cls, **overrides) -> "Dependencies":
        """工厂方法。测试时可传入 mock。"""
        from config.llm_config import get_llm
        from core.database import get_database
        from core.knowledge_graph import get_knowledge_graph
        # ... 默认创建所有依赖，overrides 覆盖
```

- [ ] `pipeline.py` 的 `create_research_pipeline()` 改为接受 `deps: Dependencies = None`
  - None 时调用 `Dependencies.create()` 保持向后兼容
  - 有值时使用注入的依赖
- [ ] `BaseAgent.__init__()` 的 `knowledge_graph` 改为构造函数参数（而非内部调用 `get_knowledge_graph()`）

#### 3.3 移除 llm_config 全局变量
- [ ] `llm_config.py`：删除 `_llm_config` 全局变量
- [ ] `get_llm()` 每次创建 LLMConfig（Anthropic client 本身是轻量的）
  - 或改为 Dependencies 内管理

**修改/新建文件**：
- 新建: `core/dependencies.py`
- 修改: `agents/base_agent.py`, `agents/ideation/agent.py`, `agents/planning/agent.py`
- 修改: `core/pipeline.py`, `config/llm_config.py`

---

### 阶段 4：文档更新

**目标**：三级文档一致性

- [ ] 更新修改文件的文件头注释
- [ ] 更新 `agents/CLAUDE.md`
- [ ] 更新 `core/CLAUDE.md`（新增 dependencies.py）
- [ ] 更新 `config/CLAUDE.md`
- [ ] 更新根 `CLAUDE.md`（如架构图有变）

---

## 三、验证方案

每个阶段完成后执行：

```bash
# 语法检查
python -m py_compile core/knowledge_graph.py
python -m py_compile core/pipeline.py
python -m py_compile agents/base_agent.py

# 导入链检查（无循环导入）
python -c "from core.pipeline import create_research_pipeline; print('Pipeline OK')"

# 现有测试
pytest tests/ -v

# Pipeline 可创建
python -c "from core.pipeline import create_research_pipeline; p = create_research_pipeline(); print('Created OK')"
```

---

## 四、Checklist

- [ ] 阶段 1：修复 KnowledgeGraph（单例 + LLM 接口 + 代码质量）
- [ ] 阶段 2：修复 Pipeline 配置 + 简化 LLM 接口
- [ ] 阶段 3：消除重复 + Dependencies 容器
- [ ] 阶段 4：文档更新

## 五、不在范围内

以下问题已在之前的重构中解决，无需重复：
- ~~死代码清理~~（multi_llm_config, auth_config 等已删除）
- ~~Prompt 外置~~（已在各 Agent 的 prompts.py 中）
- ~~Token 追踪~~（已在 _agentic_loop 中实现）
- ~~通用工具提取~~（已在 common_tools.py 中）
