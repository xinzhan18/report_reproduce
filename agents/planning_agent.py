"""
Planning Agent - 文献驱动的迭代实验规划

Pipeline 第二阶段：将假设转化为可执行的实验方案。
采用迭代修订流程：generate_plan → evaluate_feasibility → revise（最多 max_iterations 轮）。
"""

# INPUT:  agents.base_agent (BaseAgent), core.state (ResearchState, ExperimentPlan),
#         tools.file_manager (FileManager), json
# OUTPUT: PlanningAgent 类
# POSITION: Agent层 - 规划智能体，Pipeline 第二阶段
#           注入 KG 上下文 + IdeationAgent 结构化文献数据，迭代生成可行实验方案
#           额外产出 data_config.json 供 ExperimentAgent 使用

from typing import Dict, Any
from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState, ExperimentPlan
from tools.file_manager import FileManager
import json


class PlanningAgent(BaseAgent):
    """文献驱动的迭代实验规划 Agent。"""

    def __init__(self, llm: Anthropic, file_manager: FileManager):
        super().__init__(llm, file_manager, "planning")

    # ==================================================================
    # 主流程
    # ==================================================================

    def _execute(self, state: ResearchState) -> ResearchState:
        hypothesis = state["hypothesis"]
        project_id = state["project_id"]
        research_direction = state["research_direction"]
        self.logger.info(f"Hypothesis: {hypothesis[:100]}...")

        # Step 1: 构建上下文
        kg_context = self._build_kg_context(hypothesis)
        lit_context = self._load_literature_context(project_id, state)

        # Step 2: 迭代规划
        max_iterations = self.config.get("max_iterations", 3)
        revision_feedback = ""
        experiment_plan = None
        methodology = ""
        iteration_count = 0
        is_feasible = False

        for i in range(1, max_iterations + 1):
            iteration_count = i
            self.logger.info(f"Planning iteration {i}/{max_iterations}")

            # 生成计划
            experiment_plan, methodology = self.generate_plan(
                hypothesis=hypothesis,
                research_direction=research_direction,
                literature_context=lit_context,
                kg_context=kg_context,
                revision_feedback=revision_feedback,
            )

            self.save_artifact(
                content=experiment_plan,
                project_id=project_id,
                filename=f"experiment_plan_v{i}.json",
                subdir="experiments",
            )
            self.logger.info(f"  Objective: {experiment_plan['objective'][:100]}...")

            # 评估可行性
            if self.config.get("require_feasibility_check", True):
                is_feasible, revision_feedback = self.evaluate_feasibility(
                    experiment_plan=experiment_plan,
                    methodology=methodology,
                    hypothesis=hypothesis,
                    literature_context=lit_context,
                )
                self.logger.info(f"  Feasibility: {'PASS' if is_feasible else 'FAIL'}")

                if is_feasible:
                    break
                elif i < max_iterations:
                    self.logger.info(f"  Revising plan based on feedback...")
            else:
                is_feasible = True
                break

        if not is_feasible:
            self.logger.warning("Plan did not pass feasibility after all iterations, proceeding with last version")

        state["experiment_plan"] = experiment_plan
        state["methodology"] = methodology
        self.logger.info(f"Final plan after {iteration_count} iteration(s)")

        # 保存 data_config（供 ExperimentAgent 使用）
        data_config = getattr(self, "_last_data_config", None)
        if data_config:
            self.save_artifact(data_config, project_id, "data_config.json", "experiments")

        # Step 3: 定义预期结果
        expected_outcomes = self.define_expected_outcomes(
            experiment_plan=experiment_plan,
            hypothesis=hypothesis,
            literature_context=lit_context,
        )
        state["expected_outcomes"] = expected_outcomes
        self.logger.info("Defined success criteria and expected outcomes")

        # Step 4: 内联资源计算
        state["resource_requirements"] = {
            "compute": "Local CPU",
            "data_sources": ", ".join(experiment_plan["data_requirements"]),
            "software": "Python, Backtrader, yfinance, pandas, numpy",
            "storage": "~100MB for data cache",
            "estimated_time": experiment_plan["estimated_runtime"],
        }

        # Step 5: 保存规划文档
        planning_doc = self._build_planning_document(state, methodology, iteration_count, is_feasible)
        self.save_artifact(
            content=planning_doc,
            project_id=project_id,
            filename="planning_document.md",
            subdir="experiments",
        )

        # Step 6: 更新知识图谱
        findings = [
            f"Methodology designed: {experiment_plan['methodology'][:150]}",
            f"Research direction: {research_direction}",
        ]
        self.knowledge_graph.update_knowledge_from_research(
            project_id=project_id, findings=findings, llm=self.llm
        )

        return state

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
                f"Iterative planning completed with "
                f"{len(experiment_plan.get('implementation_steps', []))} steps"
            ),
        }

    # ==================================================================
    # Step 1: 上下文构建
    # ==================================================================

    def _build_kg_context(self, hypothesis: str) -> str:
        """查询知识图谱，格式化为 prompt 可注入的上下文段落。"""
        strategies = self.knowledge_graph.search_knowledge(
            query=hypothesis[:100].lower(), node_type="strategy"
        )
        metrics = self.knowledge_graph.search_knowledge(
            query="performance metrics", node_type="metric"
        )

        # 合并去重
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

    def _load_literature_context(self, project_id: str, state: ResearchState) -> str:
        """加载 IdeationAgent 保存的结构化数据，降级为 state 字段。"""
        sections = []

        # 1. 加载 research_synthesis.json
        synthesis = self.file_manager.load_json(project_id, "research_synthesis.json", subdir="literature")
        if synthesis:
            self.logger.info("Loaded research_synthesis.json from literature stage")
            sections.append("### Research Synthesis")
            if synthesis.get("methodology_patterns"):
                sections.append("**Methodology patterns**:")
                for p in synthesis["methodology_patterns"][:5]:
                    sections.append(f"- {p}")
            if synthesis.get("performance_trends"):
                sections.append("**Performance trends**:")
                for t in synthesis["performance_trends"][:5]:
                    sections.append(f"- {t}")
            if synthesis.get("common_limitations"):
                sections.append("**Common limitations**:")
                for lim in synthesis["common_limitations"][:5]:
                    sections.append(f"- {lim}")
            sections.append("")

        # 2. 加载 structured_insights.json
        insights = self.file_manager.load_json(project_id, "structured_insights.json", subdir="literature")
        if insights and isinstance(insights, list):
            self.logger.info(f"Loaded structured_insights.json: {len(insights)} papers")
            sections.append("### Key Paper Methodologies (deep analysis)")
            for idx, ins in enumerate(insights[:5], 1):
                title = ins.get("title", "Unknown")
                meth = ins.get("methodology_summary", "N/A")[:300]
                innovations = ins.get("key_innovations", [])
                metrics = ins.get("performance_metrics", {})
                sections.append(f"{idx}. **{title}**")
                sections.append(f"   - Methodology: {meth}")
                if innovations:
                    sections.append(f"   - Innovations: {', '.join(innovations[:3])}")
                if metrics:
                    metrics_str = ", ".join(f"{k}={v}" for k, v in list(metrics.items())[:5])
                    sections.append(f"   - Metrics: {metrics_str}")
            sections.append("")

        # 3. Research gaps from state
        research_gaps = state.get("research_gaps", [])
        if research_gaps:
            sections.append("### Research Gaps")
            for gap in research_gaps[:5]:
                sections.append(f"- {gap}")
            sections.append("")

        # 4. Literature summary (abbreviated) from state
        lit_summary = state.get("literature_summary", "")
        if lit_summary:
            sections.append("### Literature Summary (abbreviated)")
            sections.append(lit_summary[:1500])
            sections.append("")

        if not sections:
            return ""

        return "## Literature Context\n\n" + "\n".join(sections)

    # ==================================================================
    # Step 2: 迭代规划
    # ==================================================================

    def generate_plan(
        self,
        hypothesis: str,
        research_direction: str,
        literature_context: str,
        kg_context: str,
        revision_feedback: str = "",
    ) -> tuple[ExperimentPlan, str]:
        """单次 LLM 调用，同时产出实验计划和详细方法论。"""
        revision_block = ""
        if revision_feedback:
            revision_block = f"""

## REVISION REQUIRED
The previous plan was evaluated and found issues. You MUST address the following feedback:
{revision_feedback}

Revise the plan to fix all identified issues while maintaining the overall research direction.
"""

        prompt = f"""You are an expert in quantitative finance and backtesting methodology.
Design a detailed experiment plan to test the following hypothesis using historical financial data.

## Hypothesis
{hypothesis}

## Research Direction
{research_direction}

{kg_context}

{literature_context}
{revision_block}
Create a comprehensive experiment plan. Your implementation steps MUST reference specific methodologies from the literature above where applicable. Your success criteria MUST reference benchmark values from the literature where available.

Output as valid JSON:
{{
  "objective": "Clear statement of what we're testing",
  "methodology": "High-level approach (2-3 sentences)",
  "data_requirements": ["required data item 1", "required data item 2"],
  "implementation_steps": ["step 1 (reference paper methodology if applicable)", "step 2", ...],
  "success_criteria": {{"metric_name": threshold_value}},
  "risk_factors": ["risk 1", "risk 2"],
  "estimated_runtime": "Expected computation time",
  "data_config": {{
    "symbols": ["SPY"],
    "start_date": "2015-01-01",
    "end_date": null,
    "interval": "1d",
    "market": "us_equity"
  }},
  "detailed_methodology": "A detailed methodology section (300-500 words) covering: 1) Overall approach and framework 2) Data sources and preprocessing 3) Strategy implementation details 4) Backtesting methodology 5) Performance evaluation metrics 6) Validation approach. Use formal academic language. Reference specific papers and their methods from the literature context."
}}

Be specific about technical details for implementing a quantitative trading strategy."""

        try:
            response = self.call_llm(
                prompt=prompt,
                max_tokens=4000,
                temperature=self.config.get("temperature", 0.3),
                response_format="json",
            )
            plan_data = response if isinstance(response, dict) else {}

            detailed_methodology = plan_data.pop("detailed_methodology", "")
            self._last_data_config = plan_data.pop("data_config", None)

            experiment_plan = ExperimentPlan(
                objective=plan_data.get("objective", ""),
                methodology=plan_data.get("methodology", ""),
                data_requirements=plan_data.get("data_requirements", []),
                implementation_steps=plan_data.get("implementation_steps", []),
                success_criteria=plan_data.get("success_criteria", {}),
                estimated_runtime=plan_data.get("estimated_runtime", "Unknown"),
                risk_factors=plan_data.get("risk_factors", []),
            )

            return experiment_plan, detailed_methodology

        except Exception as e:
            self.logger.error(f"Error parsing experiment plan: {e}")
            fallback_plan = ExperimentPlan(
                objective="Test hypothesis through backtesting",
                methodology="Implement and validate trading strategy",
                data_requirements=["Historical OHLCV data"],
                implementation_steps=["Design strategy", "Implement code", "Run backtest"],
                success_criteria={"sharpe_ratio": 1.0},
                estimated_runtime="1 hour",
                risk_factors=["Data quality", "Overfitting"],
            )
            return fallback_plan, "Methodology generation failed; using fallback plan."

    def evaluate_feasibility(
        self,
        experiment_plan: ExperimentPlan,
        methodology: str,
        hypothesis: str,
        literature_context: str,
    ) -> tuple[bool, str]:
        """LLM 评估 5 个维度的可行性。"""
        prompt = f"""You are reviewing a quantitative finance experiment plan for feasibility.

## Hypothesis
{hypothesis}

## Experiment Plan
{json.dumps(dict(experiment_plan), indent=2)}

## Detailed Methodology
{methodology[:2000]}

{literature_context[:2000]}

Evaluate the plan on these 5 dimensions (score each 1-5):

1. **Data availability** - Can all required data be obtained from Yahoo Finance (yfinance)?
2. **Computational feasibility** - Can this be implemented as a Backtrader strategy and run locally?
3. **Methodological soundness** - Is the approach appropriate for testing this hypothesis?
4. **Success criteria realism** - Are the metric thresholds reasonable compared to literature benchmarks?
5. **Implementation completeness** - Are the steps specific enough for code generation?

A plan is feasible if ALL dimensions score >= 3.

Output as JSON:
{{
  "scores": {{"data_availability": 4, "computational_feasibility": 5, "methodological_soundness": 3, "success_criteria_realism": 4, "implementation_completeness": 3}},
  "is_feasible": true,
  "issues": ["issue 1 if any", ...],
  "suggestions": ["suggestion 1 if any", ...]
}}"""

        try:
            result = self.call_llm(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.2,
                response_format="json",
            )
            if not isinstance(result, dict):
                self.logger.warning("Feasibility check returned non-dict, assuming feasible")
                return True, ""

            is_feasible = result.get("is_feasible", True)
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            scores = result.get("scores", {})

            self.logger.info(f"  Feasibility scores: {scores}")

            if is_feasible:
                return True, ""

            # 构造 revision feedback
            feedback_parts = []
            if issues:
                feedback_parts.append("Issues found:\n" + "\n".join(f"- {iss}" for iss in issues))
            if suggestions:
                feedback_parts.append("Suggestions:\n" + "\n".join(f"- {sug}" for sug in suggestions))
            return False, "\n\n".join(feedback_parts)

        except Exception as e:
            self.logger.warning(f"Feasibility evaluation failed ({e}), assuming feasible")
            return True, ""

    # ==================================================================
    # Step 3: 预期结果
    # ==================================================================

    def define_expected_outcomes(
        self, experiment_plan: ExperimentPlan, hypothesis: str, literature_context: str
    ) -> str:
        """定义预期结果和验证标准，引用文献基准。"""
        criteria_text = json.dumps(experiment_plan["success_criteria"], indent=2)
        prompt = f"""Define the expected outcomes for this experiment and how they would validate or refute the hypothesis.

## Hypothesis
{hypothesis}

## Success Criteria
{criteria_text}

{literature_context[:1500]}

Describe:
1. What results would **support** the hypothesis (specific metric ranges, referencing literature benchmarks where available)
2. What results would **refute** the hypothesis
3. What results would be **inconclusive** or require further investigation
4. Alternative explanations for potential results

Write 200-300 words."""

        return self.call_llm(
            prompt=prompt,
            max_tokens=1500,
            temperature=self.config.get("temperature", 0.3),
        )

    # ==================================================================
    # 辅助方法
    # ==================================================================

    def _build_planning_document(
        self, state: ResearchState, methodology: str,
        iteration_count: int, is_feasible: bool,
    ) -> str:
        """构建 Markdown 规划文档。"""
        experiment_plan = state["experiment_plan"]
        return f"""# Experiment Planning Document

## Planning Summary
- **Iterations**: {iteration_count}
- **Feasibility**: {'PASS' if is_feasible else 'FAIL (proceeding with best effort)'}

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
