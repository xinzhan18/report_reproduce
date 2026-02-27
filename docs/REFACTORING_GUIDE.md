# Agent Refactoring Guide

本指南展示如何将现有agents重构为继承BaseAgent的版本。

## 重构模式

### Before (旧版本)

```python
class SomeAgent:
    def __init__(self, llm, tool1, tool2, file_manager):
        self.llm = llm
        self.tool1 = tool1
        self.tool2 = tool2
        self.file_manager = file_manager
        self.config = get_agent_config("some")
        self.model = get_model_name(self.config.get("model"))

        # 重复的infrastructure代码
        self.memory_manager = get_agent_memory_manager("some")
        self.knowledge_graph = get_knowledge_graph()

    def _build_system_prompt(self, memories):
        # 在所有agents中重复的代码
        return f"""...构建系统提示..."""

    def __call__(self, state: ResearchState) -> ResearchState:
        # 重复的setup代码
        print("Loading memories...")
        self.memories = self.memory_manager.load_all_memories()
        self.system_prompt = self._build_system_prompt(self.memories)

        # 业务逻辑
        result = self.do_work(state)

        # 重复的finalize代码
        self.memory_manager.save_daily_log(...)
        return state
```

### After (重构后)

```python
from agents.base_agent import BaseAgent

class SomeAgent(BaseAgent):
    def __init__(self, llm, tool1, tool2, file_manager):
        # 调用BaseAgent初始化（处理所有infrastructure）
        super().__init__(llm, file_manager, agent_name="some")

        # 只保留agent-specific工具
        self.tool1 = tool1
        self.tool2 = tool2

    def _execute(self, state: ResearchState) -> ResearchState:
        """只包含业务逻辑"""

        # 使用BaseAgent提供的方法
        result = self.do_work(state)

        # 使用便捷方法保存artifact
        self.save_artifact(
            content=result,
            project_id=state["project_id"],
            filename="result.json",
            subdir="outputs"
        )

        return state

    def _generate_execution_summary(self, state):
        """可选：提供agent-specific的执行总结"""
        return {
            "log": f"Agent completed with {len(state['results'])} items",
            "learnings": ["Learning 1", "Learning 2"],
            "mistakes": [],
            "reflection": "Execution went well"
        }
```

## 重构步骤

### 1. 更新import

```python
# Before
from anthropic import Anthropic
from config.agent_config import get_agent_config
from config.llm_config import get_model_name
from core.agent_memory_manager import get_agent_memory_manager
from core.knowledge_graph import get_knowledge_graph

# After
from agents.base_agent import BaseAgent
```

### 2. 修改类定义

```python
# Before
class PlanningAgent:

# After
class PlanningAgent(BaseAgent):
```

### 3. 简化 __init__

```python
# Before
def __init__(self, llm, file_manager):
    self.llm = llm
    self.file_manager = file_manager
    self.config = get_agent_config("planning")
    self.model = get_model_name(self.config.get("model"))
    self.memory_manager = get_agent_memory_manager("planning")
    self.knowledge_graph = get_knowledge_graph()

# After
def __init__(self, llm, file_manager):
    super().__init__(llm, file_manager, agent_name="planning")
    # 只保留agent-specific工具
```

### 4. 删除重复的方法

删除以下方法（BaseAgent已提供）：
- `_build_system_prompt()` - 由IntelligenceContext处理
- `__call__()` - 由BaseAgent的Template Method处理
- Daily log saving代码 - 由BaseAgent的_finalize处理

### 5. 将业务逻辑移到 _execute

```python
def _execute(self, state: ResearchState) -> ResearchState:
    """
    只包含planning agent的业务逻辑

    所有infrastructure（memory loading, logging, etc.）
    已被BaseAgent处理
    """
    # 原来__call__中的业务逻辑移到这里

    # 步骤1: 分析hypothesis
    analysis = self.analyze_hypothesis(state["hypothesis"])

    # 步骤2: 设计实验
    experiment_plan = self.design_experiment(analysis)

    # 步骤3: 保存结果
    self.save_artifact(
        content=experiment_plan,
        project_id=state["project_id"],
        filename="experiment_plan.json",
        subdir="planning"
    )

    state["experiment_plan"] = experiment_plan
    return state
```

### 6. 使用BaseAgent的便捷方法

```python
# LLM调用
# Before:
response = self.llm.messages.create(
    model=self.model,
    max_tokens=4000,
    temperature=0.7,
    system=self.system_prompt,
    messages=[{"role": "user", "content": prompt}]
)
text = response.content[0].text

# After:
text = self.call_llm(
    prompt=prompt,
    model="sonnet",  # or from config
    max_tokens=4000,
    temperature=0.7
)

# 保存文件
# Before:
self.file_manager.save_json(
    data=result,
    project_id=state["project_id"],
    filename="result.json",
    subdir="outputs"
)

# After:
self.save_artifact(
    content=result,
    project_id=state["project_id"],
    filename="result.json",
    subdir="outputs",
    format="json"
)
```

## 示例：PlanningAgent重构

### Before (410 lines)

```python
class PlanningAgent:
    def __init__(self, llm, file_manager):
        self.llm = llm
        self.file_manager = file_manager
        self.config = get_agent_config("planning")
        self.model = get_model_name(self.config.get("model"))
        self.memory_manager = get_agent_memory_manager("planning")
        self.knowledge_graph = get_knowledge_graph()

    def _build_system_prompt(self, memories):
        # 95行重复代码
        pass

    def __call__(self, state):
        # 150行 - 包含setup, 业务逻辑, finalize
        print("Loading memories...")
        self.memories = self.memory_manager.load_all_memories()
        self.system_prompt = self._build_system_prompt(self.memories)

        # ... 业务逻辑 ...

        self.memory_manager.save_daily_log(...)
        return state

    def analyze_hypothesis(self, hypothesis):
        # 业务逻辑
        pass

    def design_experiment(self, analysis):
        # 业务逻辑
        pass
```

### After (200 lines - 51% reduction)

```python
from agents.base_agent import BaseAgent

class PlanningAgent(BaseAgent):
    def __init__(self, llm, file_manager):
        super().__init__(llm, file_manager, agent_name="planning")

    def _execute(self, state: ResearchState) -> ResearchState:
        """Planning agent业务逻辑"""

        # 分析hypothesis
        analysis = self.analyze_hypothesis(state["hypothesis"])
        self.logger.info("✓ Analyzed hypothesis")

        # 设计实验
        experiment_plan = self.design_experiment(
            analysis,
            state["literature_summary"]
        )
        self.logger.info("✓ Designed experiment plan")

        # 保存
        self.save_artifact(
            content=experiment_plan,
            project_id=state["project_id"],
            filename="experiment_plan.json",
            subdir="planning"
        )

        state["experiment_plan"] = experiment_plan
        return state

    def _generate_execution_summary(self, state):
        """Planning-specific execution summary"""
        plan = state.get("experiment_plan", {})
        return {
            "log": f"Created experiment plan with {len(plan.get('implementation_steps', []))} steps",
            "learnings": [
                f"Designed {plan.get('methodology', 'unknown')} methodology"
            ],
            "mistakes": [],
            "reflection": "Plan is ready for experiment execution"
        }

    def analyze_hypothesis(self, hypothesis):
        """业务逻辑 - 使用BaseAgent的call_llm"""
        prompt = f"Analyze this hypothesis: {hypothesis}"
        return self.call_llm(prompt, model="sonnet")

    def design_experiment(self, analysis, literature):
        """业务逻辑"""
        prompt = f"Design experiment based on: {analysis}"
        result = self.call_llm(prompt, response_format="json")
        return result
```

## 重构检查清单

- [ ] 继承BaseAgent
- [ ] 调用super().__init__(llm, file_manager, agent_name)
- [ ] 删除_build_system_prompt方法
- [ ] 将__call__的业务逻辑移到_execute
- [ ] 删除手动的memory loading代码
- [ ] 删除手动的daily log saving代码
- [ ] 用self.call_llm替换直接的LLM调用
- [ ] 用self.save_artifact替换file_manager.save_*
- [ ] 用self.logger替换print语句
- [ ] 可选：实现_generate_execution_summary
- [ ] 可选：实现_extract_learnings

## 预期效果

### 代码减少

- IdeationAgent: 444 lines → 250 lines (44% reduction)
- PlanningAgent: 410 lines → 200 lines (51% reduction)
- ExperimentAgent: 520 lines → 280 lines (46% reduction)
- WritingAgent: 385 lines → 190 lines (51% reduction)

### 总体改进

- **代码重复率**: 95% → <15%
- **维护性**: 4个文件需要修改 → 1个文件（BaseAgent）
- **测试性**: 难以mock → 易于测试（依赖注入）
- **可扩展性**: 新agent需要复制大量代码 → 只需实现_execute

## 下一步

1. 重构PlanningAgent
2. 重构ExperimentAgent
3. 重构WritingAgent
4. 运行测试验证功能不变
5. 更新文档
