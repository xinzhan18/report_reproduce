"""
PlanningAgent — Agentic Tool-Use 实验规划引擎

Pipeline 第二阶段：LLM 拥有上游文件读取、知识图谱查询、浏览器等工具，
通过多轮 tool_use 循环自主完成实验方案设计。
"""

# INPUT:  agents.base_agent (BaseAgent), core.state (ResearchState, ExperimentPlan),
#         tools.file_manager (FileManager),
#         agents.planning.tools (get_tool_definitions),
#         agents.planning.prompts (SYSTEM_PROMPT_TEMPLATE, build_task_prompt),
#         agents.browser_manager (BrowserManager, is_playwright_available)
# OUTPUT: PlanningAgent 类
# POSITION: Agent层 - 规划智能体，Pipeline 第二阶段
#           通过 BaseAgent._agentic_loop() 驱动的 Agentic Tool-Use 引擎

from typing import Dict, Any
import json
import logging

from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState, ExperimentPlan
from tools.file_manager import FileManager
from agents.planning.tools import get_tool_definitions
from agents.planning.prompts import SYSTEM_PROMPT_TEMPLATE, build_task_prompt
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
        """构建 planning task prompt。"""
        kg_context = self._build_kg_context(state["hypothesis"])
        return build_task_prompt(
            hypothesis=state["hypothesis"],
            research_direction=state["research_direction"],
            literature_summary=state.get("literature_summary", ""),
            kg_context=kg_context,
        )

    def _on_submit_result(self, results: dict, state: ResearchState):
        """映射 submit_result 结果到 state。"""
        # experiment_plan
        plan_data = results.get("experiment_plan", {})
        state["experiment_plan"] = ExperimentPlan(
            objective=plan_data.get("objective", ""),
            methodology=plan_data.get("methodology", ""),
            data_requirements=plan_data.get("data_requirements", []),
            implementation_steps=plan_data.get("implementation_steps", []),
            success_criteria=plan_data.get("success_criteria", {}),
            estimated_runtime=plan_data.get("estimated_runtime", "Unknown"),
            risk_factors=plan_data.get("risk_factors", []),
        )

        # methodology
        state["methodology"] = results.get("methodology", "")

        # expected_outcomes
        state["expected_outcomes"] = results.get("expected_outcomes", "")

        # data_config (保存供 ExperimentAgent 使用)
        self._last_data_config = results.get("data_config")

    # ==================================================================
    # 主流程
    # ==================================================================

    def _execute(self, state: ResearchState) -> ResearchState:
        hypothesis = state["hypothesis"]
        project_id = state["project_id"]
        research_direction = state["research_direction"]
        self.logger.info(f"Hypothesis: {hypothesis[:100]}...")

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
            methodology = state.get("methodology", "")

            self.logger.info(f"Objective: {experiment_plan.get('objective', 'N/A')[:100]}...")

            # 保存实验计划
            self.save_artifact(
                content=experiment_plan,
                project_id=project_id,
                filename="experiment_plan.json",
                subdir="experiments",
            )

            # 保存 data_config（供 ExperimentAgent 使用）
            data_config = getattr(self, "_last_data_config", None)
            if data_config:
                self.save_artifact(data_config, project_id, "data_config.json", "experiments")

            # 内联资源计算
            state["resource_requirements"] = {
                "compute": "Local CPU",
                "data_sources": ", ".join(experiment_plan.get("data_requirements", [])),
                "software": "Python, pandas, numpy",
                "storage": "~100MB for data cache",
                "estimated_time": experiment_plan.get("estimated_runtime", "Unknown"),
            }

            # 保存规划文档
            planning_doc = self._build_planning_document(state, methodology)
            self.save_artifact(
                content=planning_doc,
                project_id=project_id,
                filename="planning_document.md",
                subdir="experiments",
            )

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
            # 设置默认值避免下游失败
            state.setdefault("experiment_plan", ExperimentPlan(
                objective="Test hypothesis through backtesting",
                methodology="Implement and validate trading strategy",
                data_requirements=["Historical OHLCV data"],
                implementation_steps=["Design strategy", "Implement code", "Run backtest"],
                success_criteria={"sharpe_ratio": 1.0},
                estimated_runtime="1 hour",
                risk_factors=["Data quality", "Overfitting"],
            ))
            state.setdefault("methodology", "")
            state.setdefault("expected_outcomes", "")

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

    def _build_planning_document(self, state: ResearchState, methodology: str) -> str:
        """构建 Markdown 规划文档。"""
        experiment_plan = state["experiment_plan"]
        return f"""# Experiment Planning Document

## Hypothesis
{state["hypothesis"]}

## Experiment Plan
**Objective**: {experiment_plan['objective']}

**Methodology**: {experiment_plan['methodology']}

## Detailed Methodology
{methodology}

## Data Requirements
{chr(10).join(f"- {req}" for req in experiment_plan['data_requirements'])}

## Implementation Steps
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(experiment_plan['implementation_steps']))}

## Success Criteria
{json.dumps(experiment_plan['success_criteria'], indent=2)}

## Expected Outcomes
{state.get('expected_outcomes', '')}

## Resource Requirements
{json.dumps(state.get('resource_requirements', {}), indent=2)}

## Risk Factors
{chr(10).join(f"- {risk}" for risk in experiment_plan['risk_factors'])}

## Estimated Runtime
{experiment_plan['estimated_runtime']}
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
