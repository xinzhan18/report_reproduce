# Pipeline 架构升级：Markdown 驱动 + Checklist 反馈回路 — 执行检查清单

## Step 1: core/state.py — 精简 + ExperimentFeedback
- [x] 新增 ExperimentFeedback TypedDict (verdict/analysis/suggestions/failed_steps)
- [x] 移除冗余字段: papers_reviewed, literature_summary, research_gaps, experiment_code, execution_logs, report_draft, final_report, report_path, expected_outcomes, resource_requirements
- [x] 新增 experiment_feedback: Optional[ExperimentFeedback] 到 ResearchState
- [x] 更新 create_initial_state() 匹配精简后的字段

## Step 2: core/pipeline.py — 反馈回路
- [x] 替换 should_retry_experiment → should_continue_after_experiment
- [x] 路由逻辑: success/partial→writing, revise_plan(iteration<2)→planning, else→failed
- [x] 添加 experiment→planning 边到 conditional_edges

## Step 3: agents/ideation/agent.py — 输出 ideation.md
- [x] 新增 _build_ideation_markdown() 构建统一文档
- [x] _execute() 保存 ideation.md (核心) + papers_analyzed.json + research_synthesis.json
- [x] 移除散落文件: literature_summary.md, research_gaps.json, hypothesis.md
- [x] _on_submit_result() 只写 state["hypothesis"]

## Step 4+7: PlanningAgent plan.md + prompts 修正模式
- [x] _build_task_prompt() 双模式: 首次(build_task_prompt) + 修正(build_revision_task_prompt)
- [x] _on_submit_result() 移除 expected_outcomes 写入
- [x] 新增 _build_plan_markdown(): implementation_steps → checklist 格式
- [x] _execute() 保存 plan.md(带 checklist) 替代 planning_document.md + experiment_plan.json
- [x] 保留 data_config.json
- [x] prompts.py: 新增 build_revision_task_prompt()
- [x] prompts.py: system prompt 中 Workflow 指向 ideation.md
- [x] prompts.py: submit_result 格式要求 "Step N:" 前缀

## Step 5: ExperimentAgent 读 plan.md + 回写 checklist
- [x] _build_task_prompt() 读取 plan.md 而非从 state 提取 steps
- [x] prompts.py: build_task_prompt 接收 plan_md 参数
- [x] 新增 _update_and_save_plan() + _update_plan_checklist(): 回写 checklist 标记
- [x] 新增 _build_experiment_markdown(): 构建 experiment.md
- [x] 新增 _identify_failed_steps(): 识别失败步骤
- [x] _analyze_results() verdict 枚举: success/revise_plan/accept_partial (移除 "revise")
- [x] 写入 state["experiment_feedback"] (ExperimentFeedback)
- [x] 移除 state["iteration"] = max_retries hack → 改为递增
- [x] 移除对已删除 state 字段的写入 (execution_logs, experiment_code)

## Step 6: WritingAgent 适配 state 精简
- [x] _build_state_summary() 移除 papers_reviewed, research_gaps 引用
- [x] _on_submit_result() 不再写 state["report_draft"]/state["final_report"]
- [x] prompts.py 更新文件路径: ideation.md, plan.md, experiment.md

## Step 8: 文档更新
- [x] core/state.py 文件头注释
- [x] core/pipeline.py 文件头注释
- [x] core/CLAUDE.md
- [x] agents/ideation/agent.py 文件头注释
- [x] agents/ideation/CLAUDE.md
- [x] agents/planning/agent.py 文件头注释
- [x] agents/planning/prompts.py 文件头注释
- [x] agents/planning/CLAUDE.md
- [x] agents/experiment/agent.py 文件头注释
- [x] agents/experiment/prompts.py 文件头注释
- [x] agents/experiment/CLAUDE.md
- [x] agents/writing/agent.py 文件头注释
- [x] agents/writing/prompts.py 文件头注释
- [x] agents/writing/CLAUDE.md
- [x] agents/CLAUDE.md
- [x] 根 CLAUDE.md

## 验证
- [x] AST 语法检查: 所有 9 个修改 .py 文件通过
- [x] create_initial_state() 不含已删除字段
- [x] should_continue_after_experiment 路由逻辑正确

最后执行日期: 2026-03-01
