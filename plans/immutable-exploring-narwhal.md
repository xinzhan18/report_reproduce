# Pipeline 架构升级：Markdown 驱动 + Checklist 反馈回路

## Context

当前 4 个 Agent 的数据交换是 ResearchState（内存） + 散落的 JSON/MD 文件双写。
用户期望的架构：**每个 Agent 维护一个核心 Markdown 文档**，下游 Agent 直接读取上游 Markdown 获取上下文。
PlanningAgent 输出的 plan.md 包含 **checklist**，ExperimentAgent 执行后**回写 plan.md 标记完成/失败状态**。
如果有未完成的 step，pipeline 路由回 PlanningAgent 读取标记后的 plan.md 修正方案。

---

## 核心 Markdown 文档流转

```
IdeationAgent                PlanningAgent              ExperimentAgent           WritingAgent
     │                            │                          │                        │
     ▼                            ▼                          ▼                        ▼
 ideation.md ──────────────► plan.md ──────────────────► plan.md (回写更新)      report.md
 (文献综述+假设)           (方案+checklist)              + experiment.md
                                                         (结果+指标)
                                  ▲                          │
                                  │   未完成 step? 回退      │
                                  └──────────────────────────┘
```

### 各 Agent 的 Markdown 规范

**ideation.md** (`literature/ideation.md`)
```markdown
# Literature Review: {research_direction}

## Papers Reviewed
| # | Title | Authors | Key Findings | Relevance |
|---|-------|---------|-------------|-----------|
| 1 | ... | ... | ... | 0.9 |

## Key Methodologies
- ...

## Research Gaps
1. Gap description...
2. ...

## Hypothesis
**Statement**: ...
**Rationale**: ...
**Supporting Evidence**: ...
```

**plan.md** (`experiments/plan.md`) — **带 checklist**
```markdown
# Experiment Plan

## Objective
{clear testing statement}

## Methodology
{detailed 300-500 words}

## Data Configuration
- Symbols: SPY
- Date Range: 2015-01-01 to present
- Interval: 1d
- Market: us_equity

## Implementation Checklist
- [ ] Step 1: Download and prepare OHLCV data
- [ ] Step 2: Implement momentum signal (20-day lookback, ref: Paper X)
- [ ] Step 3: Design entry/exit rules
- [ ] Step 4: Add position sizing and risk management
- [ ] Step 5: Run backtest
- [ ] Step 6: Calculate metrics
- [ ] Step 7: Validate against success criteria

## Success Criteria
- Sharpe Ratio > 1.0
- Max Drawdown < 30%
- Total Trades >= 20

## Risk Factors
- ...
```

**plan.md (ExperimentAgent 回写后)**
```markdown
## Implementation Checklist
- [x] Step 1: Download and prepare OHLCV data
- [x] Step 2: Implement momentum signal
- [x] Step 3: Design entry/exit rules
- [x] Step 4: Add position sizing and risk management
- [x] Step 5: Run backtest
- [x] Step 6: Calculate metrics
- [ ] Step 7: Validate against success criteria — FAILED: Sharpe=0.4 < 1.0, MaxDD=35% > 30%

## Execution Results
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Sharpe Ratio | 0.40 | > 1.0 | FAIL |
| Max Drawdown | 35.0% | < 30% | FAIL |
| Total Trades | 45 | >= 20 | PASS |
| Total Return | 15.2% | - | - |
```

**experiment.md** (`experiments/experiment.md`)
```markdown
# Experiment Results

## Strategy Code
​```python
# ... strategy.py content ...
​```

## Performance Summary
{metrics table}

## Analysis
{LLM verdict and analysis}
```

**report.md** (`reports/report.md`) — WritingAgent 最终报告

---

## 修改文件清单

### Step 1: `core/state.py` — 精简 + ExperimentFeedback

**新增 ExperimentFeedback**:
```python
class ExperimentFeedback(TypedDict):
    verdict: str        # "success" | "partial" | "revise_plan" | "failed"
    analysis: str
    suggestions: list
    failed_steps: list  # plan.md 中未完成的 step 描述
```

**ResearchState 精简** — 移除文件系统中已有的冗余字段：

移除: `papers_reviewed`, `literature_summary`, `research_gaps`, `experiment_code`, `execution_logs`, `report_draft`, `final_report`, `report_path`, `expected_outcomes`, `resource_requirements`

保留:
```python
class ResearchState(TypedDict):
    research_direction: str
    project_id: str
    hypothesis: str                           # Ideation 唯一写入 state 的字段
    experiment_plan: ExperimentPlan            # Planning → Experiment
    methodology: str                          # Planning → Experiment
    results_data: BacktestResults             # Experiment → Writing/路由
    validation_status: Literal[...]           # 路由信号
    error_messages: Optional[str]
    experiment_feedback: Optional[ExperimentFeedback]  # 新增：反馈回路
    iteration: int
    timestamp: str
    status: str
    error_log: Optional[str]
    requires_human_review: bool
    review_notes: Optional[str]
```

更新 `create_initial_state()` 匹配。

### Step 2: `core/pipeline.py` — 反馈回路

**替换 `should_retry_experiment`**:
```python
def should_continue_after_experiment(state: ResearchState) -> str:
    feedback = state.get("experiment_feedback")
    if not feedback:
        return "failed"
    verdict = feedback.get("verdict", "failed")
    if verdict == "success":
        return "writing"
    elif verdict == "partial":
        return "writing"
    elif verdict == "revise_plan" and state.get("iteration", 0) < 2:
        return "planning"
    else:
        return "failed"
```

**添加 experiment → planning 边**:
```python
workflow.add_conditional_edges("experiment", should_continue_after_experiment, {
    "writing": "writing",
    "planning": "planning",
    "failed": "failed",
})
```

### Step 3: `agents/ideation/agent.py` — 输出 ideation.md

**`_execute()` 修改**：用 `save_artifact` 保存统一的 `ideation.md`（替代现有的 5 个散落文件）。

保留 `research_synthesis.json` 作为辅助结构化数据（知识图谱需要）。

```python
# 构建统一的 ideation.md
ideation_md = self._build_ideation_markdown(submitted_results)
self.save_artifact(ideation_md, project_id, "ideation.md", "literature")

# 保留 JSON 辅助文件（知识图谱、工具读取兼容）
self.save_artifact({"papers": papers}, project_id, "papers_analyzed.json", "literature")
```

**新增 `_build_ideation_markdown()`** — 将 papers、gaps、hypothesis 格式化为一个完整的 Markdown 文档。

**`_on_submit_result()`** — 只写 `state["hypothesis"]`（其余全在 ideation.md 中）。

### Step 4: `agents/planning/agent.py` + `prompts.py` — 输出 plan.md + 修正模式

**a) `_execute()` 修改**：
- 保存 `plan.md`（带 checklist）替代 `planning_document.md`
- 保留 `data_config.json`（ExperimentAgent 的 DataFetcher 需要结构化配置）
- 删除 `experiment_plan.json` 的保存（plan.md 中已包含所有信息）

**b) `_build_task_prompt()` 双模式**：
```python
def _build_task_prompt(self, state):
    feedback = state.get("experiment_feedback")
    if feedback and feedback.get("verdict") == "revise_plan":
        # 修正模式：读取被 ExperimentAgent 标记过的 plan.md
        marked_plan = self.file_manager.load_text(
            state["project_id"], "plan.md", subdir="experiments"
        )
        return build_revision_task_prompt(
            hypothesis=state["hypothesis"],
            marked_plan=marked_plan,
            feedback=feedback,
            kg_context=self._build_kg_context(state["hypothesis"]),
        )
    else:
        # 首次模式：读取 ideation.md
        return build_task_prompt(...)
```

**c) `prompts.py` 新增 `build_revision_task_prompt()`**：
- 注入被标记的 plan.md（可以看到哪些 `[x]` 哪些 `[ ]`）
- 注入 feedback.analysis 和 suggestions
- 指示 LLM 针对失败 step 修正方案

**d) submit_result 格式调整**：要求 LLM 返回的 plan 包含 checklist 格式的 implementation_steps

**e) `_on_submit_result()` 后新增**：从 submit_result 的 plan 数据构建 plan.md 并保存

### Step 5: `agents/experiment/agent.py` — 读取 plan.md + 回写 checklist

**a) `_build_task_prompt()` 修改**：
- 读取 `plan.md` 而非从 state 提取 implementation_steps
- prompt 中指示 LLM：每完成一个 step 要报告进度

**b) `_execute()` 末尾新增 plan.md 回写逻辑**：
```python
# 读取 plan.md
plan_md = self.file_manager.load_text(project_id, "plan.md", subdir="experiments")

# 根据 metrics 和 success_criteria 更新 checklist
updated_plan = self._update_plan_checklist(plan_md, metrics, success_criteria)

# 回写 plan.md
self.save_artifact(updated_plan, project_id, "plan.md", "experiments")
```

**c) 新增 `_update_plan_checklist()`** — 解析 plan.md 中的 `- [ ]` 行，根据执行结果标记为 `[x]` 或 `[ ] — FAILED: reason`，并追加 `## Execution Results` 表格。

**d) 新增 `_build_experiment_markdown()`** — 构建 experiment.md（代码 + 指标 + 分析）。

**e) 修改结果评估逻辑**：
- `_analyze_results()` 的 verdict 枚举新增 `"revise_plan"`
- 将 feedback 写入 `state["experiment_feedback"]`
- 移除 `state["iteration"] = max_retries` hack
- 改为 `state["iteration"] = state.get("iteration", 0) + 1`

**f) 移除对已删除 state 字段的写入**（`execution_logs`, `experiment_code`）

### Step 6: `agents/writing/agent.py` — 读取上游 Markdown

**`_build_state_summary()` 精简**：移除对 `papers_reviewed`、`research_gaps` 等已删字段的引用。WritingAgent 在 agentic loop 中通过 `read_upstream_file` 直接读取 `ideation.md`、`plan.md`、`experiment.md`。

**`_on_submit_result()`** — 不再写 `state["report_draft"]` / `state["final_report"]`，仅保存到文件。

### Step 7: `agents/planning/prompts.py` — prompt 调整

**System prompt** 中 Workflow 步骤调整：
- Step 1: 读取 `literature/ideation.md`（替代原来的 3 个文件）
- Step 5: submit_result 格式中 `implementation_steps` 要求带序号，方便生成 checklist

**submit_result 格式**中明确 checklist 要求：
```json
{
  "implementation_steps": [
    "Step 1: Specific actionable step (reference Paper X)",
    "Step 2: ...",
    ...
  ]
}
```

PlanningAgent 在 `_execute()` 中将 steps 转换为 Markdown checklist 格式写入 plan.md。

### Step 8: 文档更新

| 文件 | 更新内容 |
|------|---------|
| `core/state.py` 文件头 | OUTPUT 新增 ExperimentFeedback；说明 State 精简 |
| `core/pipeline.py` 文件头 | 路由函数改为 should_continue_after_experiment |
| `core/CLAUDE.md` | state.py / pipeline.py 更新说明 |
| `agents/ideation/agent.py` 文件头 | 输出改为 ideation.md |
| `agents/ideation/CLAUDE.md` | 更新产出文件说明 |
| `agents/planning/agent.py` 文件头 | 输出改为 plan.md；新增修正模式 |
| `agents/planning/prompts.py` 文件头 | 新增 build_revision_task_prompt |
| `agents/planning/CLAUDE.md` | 更新：plan.md checklist + 修正模式 |
| `agents/experiment/agent.py` 文件头 | 新增 plan.md 回写 + experiment.md |
| `agents/experiment/CLAUDE.md` | 更新：checklist 回写 + feedback |
| `agents/writing/agent.py` 文件头 | 适配 state 精简 |
| `agents/writing/CLAUDE.md` | 更新 |
| `agents/CLAUDE.md` | 架构说明更新 |
| 根 `CLAUDE.md` | 数据流向图更新为 Markdown 流转 |

---

## 实施顺序与依赖

```
Step 1 (state.py)     ← 无依赖，先做
Step 2 (pipeline.py)  ← 依赖 Step 1 (ExperimentFeedback)
Step 3 (ideation)     ← 依赖 Step 1 (state 字段变化)
Step 4 (planning)     ← 依赖 Step 1
Step 5 (experiment)   ← 依赖 Step 1, Step 4 (plan.md 格式)
Step 6 (writing)      ← 依赖 Step 1
Step 7 (prompts)      ← 与 Step 4 一起做
Step 8 (文档)         ← 最后做
```

建议顺序：**1 → 2 → 3 → 4+7 → 5 → 6 → 8**

---

## 关键设计决策

1. **Markdown 是主要协作界面** — Agent 间通过读取上游 .md 文件获取上下文，不依赖 state 传递大块数据
2. **plan.md checklist 是进度追踪** — `- [ ]` / `- [x]` / `- [ ] — FAILED` 直接在文件中体现
3. **ExperimentAgent 回写 plan.md** — 在 `_execute()` 末尾编程式更新，不在 agentic loop 中
4. **data_config.json 保留** — DataFetcher 需要结构化配置，无法纯 Markdown 化
5. **确定性路由** — checklist 失败 → `state["experiment_feedback"]["verdict"] = "revise_plan"` → 回到 planning
6. **最多 2 次反馈** — `iteration < 2` 硬限制

---

## 验证

1. **AST 语法检查**: 所有修改文件 `ast.parse()` 通过
2. **State 兼容**: `create_initial_state()` 不含已删除字段
3. **路由测试**: feedback.verdict="revise_plan" + iteration=0 → 路由到 "planning"
4. **Markdown 产出**: 运行 IdeationAgent 后 `outputs/{pid}/literature/ideation.md` 存在
5. **Checklist 回写**: 运行 ExperimentAgent 后 `plan.md` 中有 `[x]` 标记
6. **修正模式**: PlanningAgent 二次调用时 prompt 包含 "Revise" 和被标记的 plan.md
7. **反馈边界**: iteration=2 时路由到 "failed"
