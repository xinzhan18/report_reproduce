# Agent 记忆自动更新机制

## Context

当前 AgentMemory 系统是一个半成品骨架：
- `save_daily_log()` — 被所有 Agent 调用，但写入的内容来自 `_generate_execution_summary()` 这个硬编码返回空列表的方法
- `add_learning()` — **从未被任何 Agent 调用**
- `record_mistake()` — 仅被 ExperimentAgent 在失败时调用

结果：`memory.md` 和 `mistakes.md` 始终为空，Agent 无法从历史执行中积累经验。

**目标**：在 `_save_log()` 之后添加一个 LLM 反思步骤，自动从执行日志中提取 learnings 和 mistakes，写入持久化记忆文件。

---

## 方案：BaseAgent 添加 LLM 反思步骤

### 核心思路

在 `__call__()` 生命周期的 `_save_log()` 之后，新增 `_reflect_and_update_memory()` 方法：
1. 截取执行日志（head 500 + tail 3000 字符，避免超长）
2. 用 **haiku** 模型（最低成本）做一次 JSON 格式 LLM 调用，提取 learnings 和 mistakes
3. 调用现有的 `self.memory.add_learning()` 和 `self.memory.record_mistake()` 写入文件
4. 全程 try/except 包裹，失败不影响主流程

### 数据流

```
_agentic_loop() → execution_log (str)
                      ↓
               self._last_execution_log = execution_log  (存在实例属性上)
                      ↓
__call__() → _save_log() → _reflect_and_update_memory()
                                    ↓
                            call_llm_json(haiku, 截取的日志)
                                    ↓
                            {"learnings": [...], "mistakes": [...]}
                                    ↓
                    memory.add_learning() / memory.record_mistake()
```

---

## 修改文件清单

### 1. `agents/base_agent.py` — 主要修改

**a) `_agentic_loop()` 末尾存储执行日志**（L261 `execution_log = "\n".join(log_lines)` 之后）

```python
self._last_execution_log = execution_log
```

**b) `__call__()` 中 `_save_log()` 后添加反思调用**（L81 后）

```python
self._save_log(state)
self._reflect_and_update_memory(state)  # 新增
```

**c) 新增 `_reflect_and_update_memory()` 方法**

在 `_save_log()` 方法之后添加：

```python
def _reflect_and_update_memory(self, state: ResearchState):
    """用 LLM 分析执行日志，自动提取 learnings/mistakes 写入记忆。"""
    config = REFLECTION_CONFIG.get(self.agent_name, REFLECTION_CONFIG["_default"])
    if not config.get("enabled", True):
        return

    execution_log = getattr(self, "_last_execution_log", "")
    if not execution_log or len(execution_log) < 100:
        return

    try:
        max_len = config.get("max_log_chars", 3500)
        if len(execution_log) > max_len:
            head = execution_log[:500]
            tail = execution_log[-(max_len - 500):]
            truncated_log = head + "\n...[truncated]...\n" + tail
        else:
            truncated_log = execution_log

        prompt = f"""Analyze this {self.agent_name} agent execution log and extract insights.

## Execution Log
{truncated_log}

## Instructions
Return a JSON object with:
- "learnings": list of 0-3 concise, actionable insights worth remembering for future runs
- "mistakes": list of 0-2 objects with keys "description", "severity" (1-5), "root_cause", "prevention"

Only include genuinely useful insights. If routine with nothing notable, return empty lists.
Return ONLY the JSON object."""

        result = call_llm_json(
            self.llm, prompt,
            model=config.get("model", "haiku"),
            max_tokens=config.get("max_tokens", 1024),
            temperature=0.1,
        )

        project_id = state.get("project_id", "unknown")
        for learning in result.get("learnings", []):
            if isinstance(learning, str) and learning.strip():
                self.memory.add_learning(learning.strip(), category=self.agent_name.title())
                self.logger.info(f"Memory: added learning: {learning[:80]}")

        for mistake in result.get("mistakes", []):
            if isinstance(mistake, dict) and mistake.get("description"):
                self.memory.record_mistake(
                    description=mistake["description"],
                    severity=mistake.get("severity", 3),
                    root_cause=mistake.get("root_cause", "Unknown"),
                    prevention=mistake.get("prevention", "TBD"),
                    project_id=project_id,
                )
                self.logger.info(f"Memory: recorded mistake: {mistake['description'][:80]}")

    except Exception as e:
        self.logger.warning(f"Reflection failed (non-fatal): {e}")
```

**d) 修改 import**（L29）

```python
# 原来
from config.agent_config import get_agent_config
# 改为
from config.agent_config import get_agent_config, REFLECTION_CONFIG
```

### 2. `config/agent_config.py` — 添加反思配置

在文件末尾添加：

```python
REFLECTION_CONFIG: Dict[str, Dict[str, Any]] = {
    "_default": {
        "enabled": True,
        "model": "haiku",
        "max_tokens": 1024,
        "max_log_chars": 3500,
    },
    "ideation": {"enabled": True},
    "planning": {"enabled": True},
    "experiment": {"enabled": True},
    "writing": {"enabled": True},
}


def get_reflection_config(agent_name: str) -> Dict[str, Any]:
    """获取 Agent 反思配置，合并默认值。"""
    default = REFLECTION_CONFIG.get("_default", {})
    override = REFLECTION_CONFIG.get(agent_name, {})
    return {**default, **override}
```

### 3. 文档更新

| 文件 | 更新内容 |
|------|---------|
| `agents/base_agent.py` 文件头 | INPUT 添加 `REFLECTION_CONFIG`；POSITION 添加反思说明 |
| `agents/CLAUDE.md` | base_agent.py 功能描述添加 `_reflect_and_update_memory()` |
| `config/CLAUDE.md` | agent_config.py 功能描述添加 REFLECTION_CONFIG |
| `config/agent_config.py` 文件头 | OUTPUT 添加 REFLECTION_CONFIG, get_reflection_config |

---

## 关键设计决策

1. **haiku 模型** — 反思是辅助功能，用最便宜的模型，每次 ~500 input + 200 output tokens
2. **实例属性 `self._last_execution_log`** — 不修改 ResearchState，避免序列化问题
3. **日志截取 head 500 + tail 3000** — 覆盖任务描述（头部）和最终结果（尾部）
4. **try/except 全包裹** — 反思失败不影响主流程
5. **可配置开关** — `REFLECTION_CONFIG` 中 `enabled: False` 即可关闭

---

## 验证

1. **AST 语法检查**: `python -c "import ast; ast.parse(open('agents/base_agent.py', encoding='utf-8').read()); ast.parse(open('config/agent_config.py', encoding='utf-8').read())"`
2. **导入检查**: `python -c "from config.agent_config import REFLECTION_CONFIG, get_reflection_config; print(REFLECTION_CONFIG)"`
3. **功能验证**: 运行任意 Agent，检查日志中出现 `Memory: added learning:` 或 `Reflection failed (non-fatal):` 行
4. **文件验证**: `data/{agent_name}/memory.md` 有新内容追加
5. **关闭测试**: 将 `REFLECTION_CONFIG._default.enabled` 改为 `False`，确认无反思调用
