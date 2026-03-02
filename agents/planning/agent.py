"""
PlanningAgent — Agentic Tool-Use 实验规划引擎

Pipeline 第二阶段：LLM 拥有上游文件读取、知识图谱查询、浏览器等工具，
通过多轮 tool_use 循环自主完成实验方案设计。
输出 plan.md（带 Implementation Checklist）供 ExperimentAgent 读取和回写。
支持修正模式：当 ExperimentAgent 回写失败标记后，pipeline 路由回此 Agent 读取标记后的 plan.md 修正方案。
"""

# INPUT:  agents.base_agent (BaseAgent), core.state (ResearchState, FactorPlan),
#         tools.file_manager (FileManager),
#         agents.planning.tools (get_tool_definitions),
#         agents.planning.prompts (SYSTEM_PROMPT_TEMPLATE, build_task_prompt, build_revision_task_prompt),
#         agents.browser_manager (BrowserManager, is_playwright_available)
# OUTPUT: PlanningAgent 类
#         产出文件: experiments/plan.md (核心, 带 checklist),
#                  experiments/data_config.json (结构化配置)
# POSITION: Agent层 - 规划智能体，Pipeline 第二阶段
#           通过 BaseAgent._agentic_loop() 驱动的 Agentic Tool-Use 引擎
#           支持首次模式 + 修正模式（反馈回路）

from typing import Dict, Any
import json
import logging

from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState, FactorPlan
from tools.file_manager import FileManager
from agents.planning.tools import get_tool_definitions
from agents.planning.prompts import SYSTEM_PROMPT_TEMPLATE, build_task_prompt, build_revision_task_prompt
from agents.browser_manager import BrowserManager, is_playwright_available

logger = logging.getLogger("agents.planning")


class PlanningAgent(BaseAgent):
    """Agentic Tool-Use 实验规划引擎。"""

    def __init__(self, llm: Anthropic, file_manager: FileManager):
        super().__init__(llm, file_manager, "planning")

    # ==================================================================
    # Agentic 钩子
    # ==================================================================

    def _register_tools(self, state: ResearchState):
        """注册规划工具 + 浏览器工具到 ToolRegistry。"""
        include_browser = is_playwright_available()
        tool_defs = get_tool_definitions(include_browser=include_browser)
        self.tool_registry.register_many(tool_defs)
        self.logger.info(f"Registered {len(tool_defs)} tools: {self.tool_registry.get_tool_names()}")

    def _build_tool_system_prompt(self, state: ResearchState) -> str:
        """构建 planning system prompt。"""
        agent_memory = self._system_prompt
        return SYSTEM_PROMPT_TEMPLATE.format(agent_memory=agent_memory)

    def _build_task_prompt(self, state: ResearchState) -> str:
        """构建 planning task prompt — 支持首次模式和修正模式。"""
        feedback = state.get("experiment_feedback")
        kg_context = self._build_kg_context(state["hypothesis"])

        if feedback and feedback.get("verdict") == "revise_plan":
            # 修正模式：读取被 ExperimentAgent 标记过的 plan.md
            marked_plan = self.file_manager.load_text(
                state["project_id"], "plan.md", subdir="experiments"
            ) or ""
            return build_revision_task_prompt(
                hypothesis=state["hypothesis"],
                marked_plan=marked_plan,
                feedback=feedback,
                kg_context=kg_context,
            )
        else:
            # 首次模式
            return build_task_prompt(
                hypothesis=state["hypothesis"],
                research_direction=state["research_direction"],
                kg_context=kg_context,
            )

    def _on_submit_result(self, results: dict, state: ResearchState):
        """映射 submit_result 结果到 state。"""
        plan_data = results.get("experiment_plan", {})
        state["experiment_plan"] = FactorPlan(
            objective=plan_data.get("objective", ""),
            factor_description=plan_data.get("factor_description", ""),
            factor_formula=plan_data.get("factor_formula", ""),
            data_requirements=plan_data.get("data_requirements", []),
            implementation_steps=plan_data.get("implementation_steps", []),
            test_universe=plan_data.get("test_universe", "a_shares"),
            test_period=plan_data.get("test_period", ""),
            rebalance_frequency=plan_data.get("rebalance_frequency", "daily"),
            success_criteria=plan_data.get("success_criteria", {}),
            risk_factors=plan_data.get("risk_factors", []),
            estimated_runtime=plan_data.get("estimated_runtime", "Unknown"),
        )
        state["methodology"] = results.get("methodology", "")

        # 保存 data_config 供后续使用
        self._last_data_config = results.get("data_config")

    # ==================================================================
    # 主流程
    # ==================================================================

    def _execute(self, state: ResearchState) -> ResearchState:
        hypothesis = state["hypothesis"]
        project_id = state["project_id"]
        research_direction = state["research_direction"]
        self.logger.info(f"Hypothesis: {hypothesis[:100]}...")

        is_revision = (
            state.get("experiment_feedback", {}) or {}
        ).get("verdict") == "revise_plan"
        if is_revision:
            self.logger.info("REVISION MODE: Revising plan based on experiment feedback")

        # 构建 tool context
        browser = BrowserManager.get_instance() if is_playwright_available() else None

        # 运行 agentic loop
        submitted_results, execution_log = self._agentic_loop(
            state=state,
            file_manager=self.file_manager,
            project_id=project_id,
            knowledge_graph=self.knowledge_graph,
            browser=browser,
        )

        if submitted_results:
            experiment_plan = state.get("experiment_plan", {})
            self.logger.info(f"Objective: {experiment_plan.get('objective', 'N/A')[:100]}...")

            # 构建并保存 plan.md（带 checklist）
            plan_md = self._build_plan_markdown(state)
            self.save_artifact(plan_md, project_id, "plan.md", "experiments")

            # 保存 data_config（供 ExperimentAgent 使用）
            data_config = getattr(self, "_last_data_config", None)
            if data_config:
                self.save_artifact(data_config, project_id, "data_config.json", "experiments")

            # 更新知识图谱
            findings = [
                f"Methodology designed: {experiment_plan.get('methodology', 'N/A')[:150]}",
                f"Research direction: {research_direction}",
            ]
            self.knowledge_graph.update_knowledge_from_research(
                project_id=project_id, findings=findings, llm=self.llm
            )
        else:
            self.logger.warning("Agentic loop ended without submitting results")
            state.setdefault("experiment_plan", FactorPlan(
                objective="Test factor hypothesis through IC analysis",
                factor_description="",
                factor_formula="",
                data_requirements=["Historical OHLCV data"],
                implementation_steps=["Compute factor values", "Run evaluate_factor", "Analyze results"],
                test_universe="a_shares",
                test_period="",
                rebalance_frequency="daily",
                success_criteria={"ic_mean": 0.02, "icir": 0.3},
                risk_factors=["Data quality", "Overfitting"],
                estimated_runtime="1 hour",
            ))
            state.setdefault("methodology", "")

        # 保存执行日志
        self.save_artifact(execution_log, project_id, "execution_logs.txt", "experiments")

        return state

    # ==================================================================
    # 辅助方法
    # ==================================================================

    def _build_kg_context(self, hypothesis: str) -> str:
        """查询知识图谱，格式化为 prompt 可注入的上下文段落。"""
        strategies = self.knowledge_graph.search_knowledge(
            query=hypothesis[:100].lower(), node_type="strategy"
        )
        metrics = self.knowledge_graph.search_knowledge(
            query="performance metrics", node_type="metric"
        )

        seen_names = set()
        items = []
        for item in (strategies or []) + (metrics or []):
            name = item.get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                items.append(item)

        if not items:
            return ""

        self.logger.info(f"Found {len(items)} related concepts in knowledge graph")
        lines = ["## Prior Knowledge (from knowledge graph):"]
        for k in items[:8]:
            node_type = k.get("node_type", "concept")
            lines.append(f"- **[{node_type}] {k['name']}**: {k.get('description', '')[:150]}")
        return "\n".join(lines) + "\n"

    def _build_plan_markdown(self, state: ResearchState) -> str:
        """构建 plan.md，将 implementation_steps 转为 checklist 格式（因子研究版本）。"""
        experiment_plan = state["experiment_plan"]
        methodology = state.get("methodology", "")

        # Success criteria 格式化
        criteria_lines = []
        for metric, threshold in experiment_plan.get("success_criteria", {}).items():
            if metric in ("turnover_mean", "max_turnover"):
                criteria_lines.append(f"- {metric} < {threshold}")
            elif isinstance(threshold, (int, float)):
                criteria_lines.append(f"- {metric} > {threshold}")
            else:
                criteria_lines.append(f"- {metric}: {threshold}")

        # Implementation checklist
        checklist_lines = []
        for step in experiment_plan.get("implementation_steps", []):
            checklist_lines.append(f"- [ ] {step}")

        # Risk factors
        risk_lines = [f"- {risk}" for risk in experiment_plan.get("risk_factors", [])]

        return f"""# Factor Test Plan

## Objective
{experiment_plan.get('objective', '')}

## Factor Description
{experiment_plan.get('factor_description', '')}

## Factor Formula
```
{experiment_plan.get('factor_formula', '')}
```

## Methodology
{methodology}

## Test Configuration
- **Universe**: {experiment_plan.get('test_universe', 'a_shares')}
- **Test Period**: {experiment_plan.get('test_period', '')}
- **Rebalance Frequency**: {experiment_plan.get('rebalance_frequency', 'daily')}

## Data Requirements
{chr(10).join(f"- {req}" for req in experiment_plan.get('data_requirements', []))}

## Implementation Checklist
{chr(10).join(checklist_lines)}

## Success Criteria
{chr(10).join(criteria_lines)}

## Risk Factors
{chr(10).join(risk_lines)}

## Estimated Runtime
{experiment_plan.get('estimated_runtime', 'Unknown')}
"""

    def _generate_execution_summary(self, state: ResearchState) -> Dict[str, Any]:
        experiment_plan = state.get("experiment_plan", {})
        return {
            "log": (
                f"Experiment plan: {len(experiment_plan.get('implementation_steps', []))} steps, "
                f"methodology={experiment_plan.get('methodology', 'N/A')}"
            ),
            "learnings": [
                f"Designed {len(experiment_plan.get('implementation_steps', []))}-step experiment plan",
                f"Methodology: {experiment_plan.get('methodology', 'N/A')}",
            ],
            "mistakes": [],
            "reflection": (
                f"Agentic planning completed with "
                f"{len(experiment_plan.get('implementation_steps', []))} steps"
            ),
        }
