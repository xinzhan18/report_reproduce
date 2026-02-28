# Agent 架构重构计划

## Context

当前 Agent 层存在严重的架构问题，需要彻底重构：

1. **Services 层是无意义的间接层**: `LLMService`(270行)、`IntelligenceContext`(291行)、`OutputManager`(277行) 三个类都是薄 wrapper，增加了 ~840 行代码但没有实质收益
2. **Memory 系统 key 不匹配 bug**: `AgentMemoryManager.load_all_memories()` 返回 `{"memory", "daily_recent"}`，但 `IntelligenceContext._build_system_prompt()` 期望 `{"long_term", "daily_logs"}`，导致长期记忆和每日日志永远无法加载到 system prompt
3. **Memory 系统三重重叠**: `AgentMemoryManager`(Markdown)、`AgentPersona`(SQLite)、`SelfReflection`(SQLite) 功能严重重复（mistakes 记录了3次，persona 存了2处），且后两者从未被 Agent 实际调用——是死代码
4. **目录结构混乱**: 记忆文件同时存在于 `data/agents/ideation/`、`agents/ideation/`，Agent 代码在子目录里 (`agents/ideation/ideation_agent.py`) 但 `__init__.py` 用扁平路径 import (`from .ideation_agent import`)

**目标**: 消除间接层、修复 bug、删除死代码、统一目录结构。预计减少 ~2500 行代码。

---

## 重构方案

### 1. 新目录结构

```
agents/
  ├── __init__.py              # 导出 4 个 Agent
  ├── base_agent.py            # ~200 行 (从 339 行精简)
  ├── llm.py                   # ~80 行 (新文件: call_llm + call_llm_json + extract_json)
  ├── ideation_agent.py        # 扁平化,从 agents/ideation/ 移出
  ├── planning_agent.py        # 扁平化
  ├── experiment_agent.py      # 扁平化
  ├── writing_agent.py         # 扁平化
  └── CLAUDE.md

core/
  ├── memory.py                # ~150 行 (新文件: 替代 AgentMemoryManager)
  ├── state.py                 # 不变
  ├── pipeline.py              # 更新 import
  ├── database.py              # 不变
  ├── knowledge_graph.py       # 不变
  ├── persistence.py           # 不变
  ├── document_memory_manager.py  # 不变
  ├── document_tracker.py      # 不变
  ├── database_extensions.py   # 不变
  ├── logging_config.py        # 不变
  └── CLAUDE.md

data/
  ├── ideation/                # Agent 记忆数据 (与代码分离)
  │   ├── persona.md
  │   ├── memory.md
  │   ├── mistakes.md
  │   └── daily/
  ├── planning/
  ├── experiment/
  └── writing/
```

### 2. 删除的文件 (共 ~2500 行)

| 文件 | 行数 | 原因 |
|------|------|------|
| `agents/services/llm_service.py` | 270 | 合并到 `agents/llm.py` (~80行) |
| `agents/services/intelligence_context.py` | 291 | 功能内联到 BaseAgent + core/memory.py |
| `agents/services/output_manager.py` | 277 | 功能内联到 BaseAgent.save_artifact() |
| `agents/services/__init__.py` | ~20 | 整个 services 子包删除 |
| `agents/services/CLAUDE.md` | - | 一并删除 |
| `agents/utils/json_parser.py` | 147 | 合并到 `agents/llm.py` |
| `agents/utils/prompt_builder.py` | 252 | **未被任何 Agent import**，死代码 |
| `agents/utils/__init__.py` | ~20 | 整个 utils 子包删除 |
| `agents/utils/CLAUDE.md` | - | 一并删除 |
| `agents/ideation/__init__.py` | ~1 | 扁平化后删除子目录 |
| `agents/planning/__init__.py` | ~1 | 同上 |
| `agents/experiment/__init__.py` | ~1 | 同上 |
| `agents/writing/__init__.py` | ~1 | 同上 |
| `core/agent_memory_manager.py` | 531 | 替换为 `core/memory.py` (~150行) |
| `core/agent_persona.py` | 520 | **从未被 Agent 调用**，死代码 |
| `core/self_reflection.py` | 546 | **从未被 Agent 调用**，死代码 |

### 3. 新建的文件

#### `agents/llm.py` (~80 行)

无状态的模块级函数，替代 `LLMService` 类 + `json_parser.py`:

```python
# 3 个函数:
def call_llm(client, prompt, system_prompt="", model="sonnet", max_tokens=4000,
             temperature=0.7, max_retries=3) -> str
def call_llm_json(client, prompt, ...) -> dict    # call_llm + extract_json
def extract_json(text: str) -> dict                # 3 策略: code block → raw {} → 直接 parse
```

删除的功能: token 统计 (无实际用途)、batch_call (未使用)、类实例化开销。

#### `core/memory.py` (~150 行)

统一的 Markdown 记忆管理器，替代 `AgentMemoryManager`:

```python
class AgentMemory:
    def __init__(self, agent_name: str, base_path: str = "data"):
        # 路径: data/{agent_name}/persona.md, memory.md, mistakes.md, daily/

    def build_system_prompt(self) -> str:
        # 直接读文件构建 prompt，不经过 dict 中转，彻底修复 key 不匹配 bug

    def save_daily_log(self, project_id: str, log: str):
    def add_learning(self, insight: str, category: str):
    def record_mistake(self, description, severity, root_cause, prevention, project_id):
```

删除的功能: backward compatibility 路径检测、migrate_to_new_path()、_create_default_persona() 中的大段模板。

### 4. BaseAgent 重构

**关键变化**:
- 构造函数: `(llm, file_manager, agent_name, **tools)` — 子类工具通过 kwargs 传入
- 消除 3 个 service 依赖: LLM 用 `agents.llm.call_llm()`; 文件保存内联; 记忆用 `core.memory.AgentMemory`
- 知识图谱直接暴露: `self.knowledge_graph`
- 简化生命周期: `__call__` 中只做 setup(构建 system_prompt) → execute → save_log
- `_finalize()` 中的 `update_knowledge()` 逻辑移到各 Agent 的 `_execute()` 中（它们已经在做了，BaseAgent 的是重复调用）

```python
class BaseAgent(ABC):
    def __init__(self, llm, file_manager, agent_name: str, **tools):
        self.llm = llm
        self.file_manager = file_manager
        self.agent_name = agent_name
        self.config = get_agent_config(agent_name)
        self.memory = AgentMemory(agent_name)           # 直接用，不经过 IntelligenceContext
        self.knowledge_graph = get_knowledge_graph()     # 直接暴露
        for k, v in tools.items():
            setattr(self, k, v)                          # paper_fetcher, data_fetcher 等

    def __call__(self, state):
        self._system_prompt = self.memory.build_system_prompt()  # 一次构建
        state["status"] = self.agent_name
        state = self._execute(state)
        self._save_log(state)
        return state

    def call_llm(self, prompt, **kwargs) -> str:        # 直接调用 agents.llm.call_llm
    def call_llm_json(self, prompt, **kwargs) -> dict:  # 直接调用 agents.llm.call_llm_json
    def save_artifact(self, content, project_id, filename, subdir):  # 直接调用 file_manager
```

### 5. Agent 子类改动

每个子类需要修改的点（业务逻辑完全不变）:

| 改动项 | 旧代码 | 新代码 |
|--------|--------|--------|
| 构造函数 | `super().__init__(llm, file_manager, "ideation")` | `super().__init__(llm, file_manager, "ideation", paper_fetcher=paper_fetcher)` |
| 知识图谱 | `self.intelligence.knowledge_graph.xxx()` | `self.knowledge_graph.xxx()` |
| JSON 调用 | `self.call_llm(prompt, response_format="json")` | `self.call_llm_json(prompt)` |
| 记录错误 | `self.intelligence.memory_manager.record_mistake()` | `self.memory.record_mistake()` |
| 文件保存 | `self.save_artifact(content, ..., format="auto")` | `self.save_artifact(content, ...)` (去掉 format 参数) |

### 6. Pipeline 改动

`core/pipeline.py` — 当前 import 路径已是 `from agents.ideation_agent import IdeationAgent`，扁平化后路径一致，import 代码不需要改。但需要检查 Agent 实例化代码是否传参正确。

### 7. 记忆文件迁移

当前记忆文件分散在两处:
- `data/agents/ideation/` (旧路径，只有 ideation 的数据)
- `agents/ideation/persona.md` 等 (混在代码目录里)

重构后统一到 `data/{agent_name}/`:
- 将 `agents/ideation/persona.md` 等复制到 `data/ideation/`
- 将 `agents/ideation/memory.md` 等复制到 `data/ideation/`
- 删除 `agents/*/persona.md` 等数据文件

---

## 实施步骤

### 阶段 1: 基础设施（无依赖）
1. 创建 `agents/llm.py` — 合并 LLMService + json_parser 的核心逻辑
2. 创建 `core/memory.py` — 从 AgentMemoryManager 提取核心功能，修复 key 不匹配 bug
3. 迁移记忆文件: `agents/*/persona.md` → `data/{agent_name}/persona.md`

### 阶段 2: BaseAgent 重写（依赖阶段 1）
4. 重写 `agents/base_agent.py` — 使用新的 `AgentMemory` 和 `call_llm`

### 阶段 3: Agent 子类迁移（依赖阶段 2）
5. 迁移 `agents/ideation/ideation_agent.py` → `agents/ideation_agent.py`，更新内部引用
6. 迁移 `agents/planning/planning_agent.py` → `agents/planning_agent.py`
7. 迁移 `agents/experiment/experiment_agent.py` → `agents/experiment_agent.py`
8. 迁移 `agents/writing/writing_agent.py` → `agents/writing_agent.py`
9. 更新 `agents/__init__.py`

### 阶段 4: 清理（依赖阶段 3）
10. 删除 `agents/services/` 整个目录
11. 删除 `agents/utils/` 整个目录
12. 删除 `agents/ideation/`、`agents/planning/`、`agents/experiment/`、`agents/writing/` 子目录
13. 删除 `core/agent_memory_manager.py`、`core/agent_persona.py`、`core/self_reflection.py`

### 阶段 5: 集成验证（依赖阶段 4）
14. 更新 `core/pipeline.py` import（如果需要）
15. 检查其他文件对已删除模块的引用并修复

### 阶段 6: 文档更新
16. 更新 `agents/CLAUDE.md`
17. 更新 `core/CLAUDE.md`
18. 更新根 `CLAUDE.md`

---

## 验证方式

1. **Import 测试**: `python -c "from agents import IdeationAgent, PlanningAgent, ExperimentAgent, WritingAgent"`
2. **Memory 测试**: `python -c "from core.memory import AgentMemory; m = AgentMemory('ideation'); print(m.build_system_prompt()[:100])"`
3. **LLM 模块测试**: `python -c "from agents.llm import extract_json; print(extract_json('{\"a\": 1}'))"`
4. **Pipeline 测试**: `python -c "from core.pipeline import create_research_pipeline"` (验证 import 链路完整)
5. **全链路**: 如果有 API key，执行一次完整 pipeline 运行

---

## Checklist

- [x] 创建 `agents/llm.py`
- [x] 创建 `core/memory.py`
- [x] 迁移记忆文件到 `data/{agent_name}/`
- [x] 重写 `agents/base_agent.py`
- [x] 迁移 ideation_agent.py 到扁平结构
- [x] 迁移 planning_agent.py 到扁平结构
- [x] 迁移 experiment_agent.py 到扁平结构
- [x] 迁移 writing_agent.py 到扁平结构
- [x] 更新 `agents/__init__.py`
- [x] 删除 `agents/services/` 目录
- [x] 删除 `agents/utils/` 目录
- [x] 删除 Agent 子目录
- [x] 删除 `core/agent_memory_manager.py`
- [x] 删除 `core/agent_persona.py`
- [x] 删除 `core/self_reflection.py`
- [x] 更新 `core/pipeline.py` (无需修改,import路径已正确)
- [x] 修复其他引用 (test_base_agent.py, test_agent_memory_manager.py, initialize_agent_memories.py, core/__init__.py循环依赖)
- [x] 更新 `agents/CLAUDE.md`
- [x] 更新 `core/CLAUDE.md`
- [x] 更新根 `CLAUDE.md`
- [x] 验证测试通过 (import链路、extract_json、AgentMemory.build_system_prompt)
