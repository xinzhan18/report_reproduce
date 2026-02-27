# Agent System Refactoring Plan

## Context

The current FARS (Research Automation Agent System) has an architectural inconsistency problem. While a well-designed `BaseAgent` class exists implementing the Template Method Pattern, only **1 out of 4 agents** (IdeationAgent) actually uses it. The other three agents (PlanningAgent, ExperimentAgent, WritingAgent) duplicate approximately **790 lines of infrastructure code** that BaseAgent already provides.

Additionally, agent memory files are stored in `data/agents/{agent_name}/` but should be moved to `data/{agent_name}/` for a flatter, cleaner structure.

**Problems to solve**:
1. **Code duplication**: 250-300 lines duplicated in each of 3 agents (~790 lines total)
2. **Inconsistent patterns**: Some agents use BaseAgent, others bypass it
3. **Memory path complexity**: Unnecessary `agents` middle layer in path
4. **Maintenance burden**: Changes to infrastructure must be made in 4 places

**Desired outcome**:
- All agents inherit from BaseAgent (consistent architecture)
- Memory files stored in `data/{agent_name}/` (simpler structure)
- ~790 lines of duplicated code eliminated
- Consistent use of services (LLMService, IntelligenceContext, OutputManager)

---

## Implementation Plan

### Phase 1: Memory Path Migration (Foundation)

**Goal**: Update memory system to use `data/{agent_name}/` path with backward compatibility.

**Critical Files**:

1. **`core/agent_memory_manager.py`** (Line 23):
   - Change `base_path` default from `"data/agents"` to `"data"`
   - Add backward compatibility logic to check both old and new paths
   - Add `migrate_to_new_path()` method for safe migration

2. **`agents/services/intelligence_context.py`** (Line 29):
   - Fix incorrect import: `core.memory.agent_memory_manager` → `core.agent_memory_manager`
   - (Note: There is no `core/memory/` directory, this is a bug)

**Changes**:

```python
# core/agent_memory_manager.py - Line 23
def __init__(self, agent_name: str, base_path: str = "data"):  # Changed from "data/agents"
    self.agent_name = agent_name
    self.base_path = Path(base_path)

    # Backward compatibility: check both paths
    old_path = Path("data/agents") / agent_name
    new_path = self.base_path / agent_name

    if old_path.exists() and not new_path.exists():
        self.agent_dir = old_path  # Use old path during migration
        self._migration_needed = True
    else:
        self.agent_dir = new_path  # Use new path
        self._migration_needed = False

    self.daily_dir = self.agent_dir / "daily"
    # ... rest of initialization
```

**Verification**:
- [ ] Memory files load from both `data/agents/ideation/` and `data/ideation/`
- [ ] All 4 agents still run without changes
- [ ] No import errors from intelligence_context.py

---

### Phase 2: Refactor PlanningAgent

**Goal**: Convert PlanningAgent to inherit from BaseAgent, eliminating ~260 lines of duplicated infrastructure.

**File**: `agents/planning_agent.py`

**Current State** (534 lines):
- Does NOT inherit from BaseAgent
- Has `_build_system_prompt()` method (35 lines, duplicated)
- Has `__call__()` method with mixed infrastructure + business logic (200 lines)
- Makes direct `self.llm.messages.create()` calls (50+ lines)
- Manually manages memory, knowledge graph, daily logs

**Target State** (~274 lines, 260 removed):
- Inherits from BaseAgent
- Deletes `_build_system_prompt()` (BaseAgent/IntelligenceContext provides this)
- Replaces `__call__()` with `_execute()` (business logic only)
- Uses `self.call_llm()` instead of direct API calls
- Uses `self.save_artifact()` instead of direct file_manager calls
- Overrides `_generate_execution_summary()` for agent-specific logging

**Refactoring Steps**:

1. Change class declaration:
   ```python
   from agents.base_agent import BaseAgent

   class PlanningAgent(BaseAgent):  # Add inheritance
   ```

2. Simplify `__init__`:
   ```python
   def __init__(self, llm, file_manager):
       super().__init__(llm, file_manager, agent_name="planning")
       # No agent-specific tools needed for PlanningAgent
   ```

3. Delete `_build_system_prompt()` method (lines 63-98)

4. Replace `__call__()` with `_execute()`:
   ```python
   def _execute(self, state: ResearchState) -> ResearchState:
       # Only business logic, no infrastructure

       # Query knowledge graph (via self.intelligence from BaseAgent)
       related_strategies = self.intelligence.knowledge_graph.search_knowledge(...)

       # Core business logic
       experiment_plan = self.design_experiment(
           hypothesis=state["hypothesis"],
           research_gaps=state.get("research_gaps", []),
           related_knowledge=related_strategies
       )
       state["experiment_plan"] = experiment_plan

       # Use BaseAgent's save_artifact instead of file_manager
       self.save_artifact(
           content=experiment_plan,
           project_id=state["project_id"],
           filename="experiment_plan_v1.json",
           subdir="experiments",
           format="json"
       )

       # More business logic...
       methodology = self.generate_methodology(experiment_plan, state["hypothesis"])
       state["methodology"] = methodology

       return state
   ```

5. Replace all direct LLM calls:
   ```python
   # FROM:
   response = self.llm.messages.create(
       model=self.model,
       max_tokens=3000,
       temperature=0.3,
       system=self.system_prompt,
       messages=[{"role": "user", "content": prompt}]
   )
   content = response.content[0].text

   # TO:
   content = self.call_llm(
       prompt=prompt,
       max_tokens=3000,
       temperature=0.3
   )
   ```

6. Add execution summary override:
   ```python
   def _generate_execution_summary(self, state: ResearchState) -> Dict:
       plan = state.get("experiment_plan", {})
       return {
           "log": f"Created {len(plan.get('implementation_steps', []))}-step experiment plan",
           "learnings": [
               f"Methodology: {plan.get('methodology', 'N/A')}",
               f"Resources required: {plan.get('resources', 'N/A')}"
           ],
           "mistakes": [],
           "reflection": "Experiment planning phase completed"
       }
   ```

**Verification**:
- [ ] PlanningAgent runs without errors
- [ ] Produces identical experiment_plan.json to baseline
- [ ] Memory system works correctly
- [ ] Daily logs saved properly
- [ ] Knowledge graph updated

---

### Phase 3: Refactor WritingAgent

**Goal**: Convert WritingAgent to inherit from BaseAgent, eliminating ~250 lines of duplicated infrastructure.

**File**: `agents/writing_agent.py`

**Same refactoring pattern as PlanningAgent**:

1. Inherit from BaseAgent
2. Simplify `__init__` to call `super().__init__(llm, file_manager, "writing")`
3. Delete `_build_system_prompt()` (lines 64-99)
4. Replace `__call__()` with `_execute()` (lines 101-235)
5. Replace all direct LLM calls with `self.call_llm()`
6. Replace file saving with `self.save_artifact()`
7. Override `_generate_execution_summary()`

**Agent-Specific Logic to Preserve**:
- `create_report_structure()` - Define sections
- `generate_section()` - LLM-generate each section
- `assemble_report()` - Combine sections
- `polish_report()` - Final refinement
- `convert_to_html_friendly()` - Add table of contents

**Verification**:
- [ ] WritingAgent runs without errors
- [ ] Produces identical research report to baseline
- [ ] All report sections generated correctly
- [ ] HTML formatting preserved

---

### Phase 4: Refactor ExperimentAgent

**Goal**: Convert ExperimentAgent to inherit from BaseAgent, eliminating ~280 lines of duplicated infrastructure.

**File**: `agents/experiment_agent.py`

**Additional Complexity**:
- Has agent-specific tools (data_fetcher, backtest_engine)
- Has `retry_on_failure()` method for error recovery
- More complex state management

**Refactoring Steps**:

1. Inherit from BaseAgent

2. Keep agent-specific tools in `__init__`:
   ```python
   def __init__(self, llm, file_manager, data_fetcher, backtest_engine):
       super().__init__(llm, file_manager, agent_name="experiment")
       # Agent-specific tools
       self.data_fetcher = data_fetcher
       self.backtest_engine = backtest_engine
   ```

3. Delete `_build_system_prompt()` (lines 75-110)

4. Replace `__call__()` with `_execute()` (lines 112-343)

5. Preserve `retry_on_failure()` method (agent-specific business logic)

6. Replace LLM calls and file operations

**Agent-Specific Logic to Preserve**:
- `generate_strategy_code()` - LLM generates Backtrader code
- `prepare_data()` - Fetch financial data
- `execute_backtest()` - Run backtest engine
- `validate_results()` - Check success criteria
- `retry_on_failure()` - Retry logic with modifications

**Verification**:
- [ ] ExperimentAgent runs without errors
- [ ] Generates identical strategy code to baseline
- [ ] Backtest results match baseline
- [ ] Retry logic still works
- [ ] All backtest metrics calculated correctly

---

### Phase 5: Documentation Updates

**Goal**: Update all three-level documentation per CLAUDE.md rules.

**Updates Required**:

1. **File header comments** (in each refactored agent file):
   - Update INPUT section (remove direct dependencies on memory_manager, knowledge_graph)
   - Update OUTPUT section (clarify that infrastructure is inherited)
   - Update POSITION section (mention BaseAgent inheritance)

2. **`agents/CLAUDE.md`**:
   - Update file descriptions for planning_agent.py, experiment_agent.py, writing_agent.py
   - Add note about BaseAgent inheritance pattern
   - Update line counts

3. **Root `CLAUDE.md`** (if needed):
   - Only if module architecture relationships changed
   - Update data flow diagram if memory path changed

**Example File Header Update**:
```python
# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - agents/base_agent (BaseAgent基类继承),
#                   core/state (ResearchState状态定义),
#                   typing (类型系统)
# OUTPUT: 对外提供 - PlanningAgent类,继承自BaseAgent,
#                   实现_execute()方法,输出实验计划
# POSITION: 系统地位 - Agent/Planning (智能体层-规划智能体)
#                     继承BaseAgent,消除基础设施重复代码,
#                     Pipeline第二阶段,将假设转化为可执行实验计划
#
# 注意：当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================
```

**Verification**:
- [ ] All three refactored files have updated headers
- [ ] agents/CLAUDE.md reflects new architecture
- [ ] Root CLAUDE.md updated if needed
- [ ] Documentation is consistent across all three levels

---

## Testing Strategy

### Pre-Refactoring Baseline

Before any changes:

1. Create baseline test for each agent:
   ```bash
   # Run each agent with test input, save outputs
   pytest tests/test_planning_agent.py --create-baseline
   pytest tests/test_writing_agent.py --create-baseline
   pytest tests/test_experiment_agent.py --create-baseline
   ```

2. Document current behavior:
   - LLM call counts
   - Files created
   - Memory interactions
   - Execution time

### Per-Agent Testing

After refactoring each agent:

1. **Unit tests**:
   - Test `_execute()` method with mock state
   - Verify business logic methods unchanged
   - Check `_generate_execution_summary()` output

2. **Integration tests**:
   - Run full pipeline with refactored agent
   - Compare outputs with baseline (should be identical)
   - Verify memory system still works
   - Check all files created correctly

3. **Regression checks**:
   - Same inputs → same outputs
   - Same LLM prompts → same responses
   - Same file structure

### Memory Migration Testing

1. Test backward compatibility:
   - Files in old path `data/agents/ideation/`
   - Agent still loads correctly
   - Migration flag set appropriately

2. Test new path:
   - Delete old path
   - Create new agent
   - Verify files created in `data/ideation/`

---

## Implementation Checklist

### Phase 1: Memory Path Migration
- [x] Fix `intelligence_context.py` import path (line 29)
- [x] Update `agent_memory_manager.py` base_path (line 23)
- [x] Add backward compatibility logic
- [x] Add `migrate_to_new_path()` method
- [ ] Test all agents still work
- [ ] Git commit: "refactor: migrate agent memory to data/{agent}/"

### Phase 2: PlanningAgent
- [x] Inherit from BaseAgent
- [x] Delete `_build_system_prompt()`
- [x] Replace `__call__()` with `_execute()`
- [x] Replace LLM calls with `call_llm()`
- [x] Replace file ops with `save_artifact()`
- [x] Add `_generate_execution_summary()`
- [x] Update file header comment
- [ ] Run tests, verify outputs match baseline
- [ ] Git commit: "refactor: PlanningAgent inherits from BaseAgent"

### Phase 3: WritingAgent
- [x] Inherit from BaseAgent
- [x] Delete `_build_system_prompt()`
- [x] Replace `__call__()` with `_execute()`
- [x] Replace LLM calls with `call_llm()`
- [x] Replace file ops with `save_artifact()`
- [x] Add `_generate_execution_summary()`
- [x] Update file header comment
- [ ] Run tests, verify outputs match baseline
- [ ] Git commit: "refactor: WritingAgent inherits from BaseAgent"

### Phase 4: ExperimentAgent
- [x] Inherit from BaseAgent
- [x] Keep agent-specific tools in __init__
- [x] Delete `_build_system_prompt()`
- [x] Replace `__call__()` with `_execute()`
- [x] Replace LLM calls with `call_llm()`
- [x] Preserve `retry_on_failure()` method
- [x] Update file header comment
- [ ] Run tests, verify outputs match baseline
- [ ] Git commit: "refactor: ExperimentAgent inherits from BaseAgent"

### Phase 5: Documentation
- [x] Update `agents/planning_agent.py` header
- [x] Update `agents/writing_agent.py` header
- [x] Update `agents/experiment_agent.py` header
- [x] Update `agents/CLAUDE.md`
- [x] Update `core/CLAUDE.md`
- [x] Update `agents/services/CLAUDE.md`
- [ ] Git commit: "docs: update CLAUDE.md for agent refactoring"

### Phase 6: Cleanup
- [ ] Run full pipeline integration test
- [ ] Verify all memory files in new location
- [ ] Delete old `data/agents/` directory (after backup)
- [ ] Update any remaining hardcoded paths
- [ ] Git commit: "chore: complete agent refactoring cleanup"

---

## Success Criteria

### Functional Requirements
- ✓ All 4 agents run without errors
- ✓ Full pipeline produces identical outputs to baseline
- ✓ Memory files load from `data/{agent}/` path
- ✓ All agent-specific business logic preserved
- ✓ LLM calls produce same results

### Code Quality Requirements
- ✓ ~790 lines of duplication removed
- ✓ All agents inherit from BaseAgent
- ✓ Consistent use of `call_llm()`, `save_artifact()`
- ✓ No `_build_system_prompt()` duplication
- ✓ No direct `self.llm.messages.create()` calls

### Documentation Requirements
- ✓ All file headers updated (INPUT/OUTPUT/POSITION)
- ✓ `agents/CLAUDE.md` updated
- ✓ Three-level documentation consistency achieved

---

## Risk Mitigation

### High Risk: Memory system breaks
- **Mitigation**: Backward compatibility in `__init__`
- **Rollback**: Keep old path logic, revert base_path change

### High Risk: Agent behavior changes
- **Mitigation**: Baseline testing before each refactor
- **Rollback**: Git commit after each agent, easy revert

### Medium Risk: Import path errors
- **Mitigation**: Fix `intelligence_context.py` first in Phase 1
- **Test**: Import all agents before any refactoring

### Medium Risk: LLM call signature differences
- **Mitigation**: Carefully review `call_llm()` implementation
- **Test**: Compare prompts and responses with baseline

### Low Risk: Logging format changes
- **Impact**: Minimal, logging is informational
- **Fix**: Adjust logger calls if needed

---

## Expected Benefits

1. **Code reduction**: ~790 lines of duplicated infrastructure eliminated
2. **Maintainability**: Infrastructure changes only in BaseAgent
3. **Consistency**: All agents follow same pattern
4. **Testability**: Easier to test business logic separately
5. **Clarity**: Clear separation of infrastructure vs. business logic
6. **Simpler paths**: `data/{agent}/` instead of `data/agents/{agent}/`

---

## Estimated Effort

- **Phase 1 (Memory)**: 1-2 hours
- **Phase 2 (Planning)**: 2-3 hours
- **Phase 3 (Writing)**: 2-3 hours
- **Phase 4 (Experiment)**: 3-4 hours
- **Phase 5 (Docs)**: 1 hour
- **Phase 6 (Cleanup)**: 1 hour

**Total**: 10-14 hours of focused work

---

## Critical Files Reference

**Files to modify**:
1. `F:\shuxu\report_reproduce\core\agent_memory_manager.py` (line 23)
2. `F:\shuxu\report_reproduce\agents\services\intelligence_context.py` (line 29)
3. `F:\shuxu\report_reproduce\agents\planning_agent.py` (major refactor)
4. `F:\shuxu\report_reproduce\agents\writing_agent.py` (major refactor)
5. `F:\shuxu\report_reproduce\agents\experiment_agent.py` (major refactor)
6. `F:\shuxu\report_reproduce\agents\CLAUDE.md` (documentation)

**Reference file** (working example):
- `F:\shuxu\report_reproduce\agents\ideation_agent.py` - Already follows BaseAgent pattern correctly
