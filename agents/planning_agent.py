"""
Planning Agent - 实验设计与规划

Pipeline 第二阶段：将假设转化为可执行的实验方案。
"""

# INPUT:  agents.base_agent (BaseAgent), core.state, tools.file_manager, json
# OUTPUT: PlanningAgent 类
# POSITION: Agent层 - 规划智能体，Pipeline 第二阶段

from typing import Dict, Any
from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState, ExperimentPlan
from tools.file_manager import FileManager
import json


class PlanningAgent(BaseAgent):
    """实验设计与规划 Agent。"""

    def __init__(self, llm: Anthropic, file_manager: FileManager):
        super().__init__(llm, file_manager, "planning")

    def _execute(self, state: ResearchState) -> ResearchState:
        self.logger.info(f"Hypothesis: {state['hypothesis'][:100]}...")

        # 查询知识图谱
        related_strategies = self.knowledge_graph.search_knowledge(
            query=state["hypothesis"][:100].lower(), node_type="strategy"
        )
        related_metrics = self.knowledge_graph.search_knowledge(
            query="performance metrics", node_type="metric"
        )
        if related_strategies:
            self.logger.info(f"Found {len(related_strategies)} related strategies in knowledge graph")
        if related_metrics:
            self.logger.info(f"Found {len(related_metrics)} relevant metrics")

        # Step 1: 设计实验计划
        experiment_plan = self.design_experiment(
            hypothesis=state["hypothesis"],
            literature_summary=state["literature_summary"],
            research_gaps=state["research_gaps"],
            research_direction=state["research_direction"],
        )
        state["experiment_plan"] = experiment_plan
        self.logger.info(f"Created experiment plan")
        self.logger.info(f"  Objective: {experiment_plan['objective'][:100]}...")

        self.save_artifact(
            content=experiment_plan,
            project_id=state["project_id"],
            filename="experiment_plan_v1.json",
            subdir="experiments",
        )

        # Step 2: 生成详细方法论
        methodology = self.generate_methodology(experiment_plan, state["hypothesis"])
        state["methodology"] = methodology
        self.logger.info("Generated detailed methodology")

        # Step 3: 定义预期结果
        expected_outcomes = self.define_expected_outcomes(experiment_plan, state["hypothesis"])
        state["expected_outcomes"] = expected_outcomes
        self.logger.info("Defined success criteria and expected outcomes")

        # Step 4: 指定资源需求
        resource_requirements = self.specify_resources(experiment_plan)
        state["resource_requirements"] = resource_requirements
        self.logger.info("Specified resource requirements")

        # Step 5: 验证可行性
        is_feasible, feasibility_notes = self.validate_feasibility(experiment_plan)
        if not is_feasible:
            self.logger.warning(f"Feasibility concerns: {feasibility_notes}")
            state["error_log"] = f"Feasibility concerns: {feasibility_notes}"

        # 保存完整规划文档
        planning_doc = f"""# Experiment Planning Document

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
{expected_outcomes}

## Resource Requirements
{json.dumps(resource_requirements, indent=2)}

## Risk Factors
{chr(10).join(f"- {risk}" for risk in experiment_plan['risk_factors'])}

## Estimated Runtime
{experiment_plan['estimated_runtime']}
"""

        self.save_artifact(
            content=planning_doc,
            project_id=state["project_id"],
            filename="planning_document.md",
            subdir="experiments",
        )

        # 更新知识图谱
        findings = [
            f"Methodology: {experiment_plan['methodology']}",
            f"Approach validated for: {state['research_direction']}",
        ]
        self.knowledge_graph.update_knowledge_from_research(
            project_id=state["project_id"], findings=findings, llm=self.llm
        )

        return state

    def _generate_execution_summary(self, state: ResearchState) -> Dict[str, Any]:
        experiment_plan = state.get("experiment_plan", {})
        return {
            "log": f"Experiment plan: {len(experiment_plan.get('implementation_steps', []))} steps, methodology={experiment_plan.get('methodology', 'N/A')}",
            "learnings": [
                f"Designed {len(experiment_plan.get('implementation_steps', []))}-step experiment plan",
                f"Methodology: {experiment_plan.get('methodology', 'N/A')}",
            ],
            "mistakes": [],
            "reflection": f"Comprehensive plan with {len(experiment_plan.get('implementation_steps', []))} steps created",
        }

    def design_experiment(self, hypothesis: str, literature_summary: str,
                          research_gaps: list, research_direction: str) -> ExperimentPlan:
        """设计实验方案。"""
        prompt = f"""You are an expert in quantitative finance and backtesting methodology.
Design a detailed experiment plan to test the following hypothesis using historical financial data.

Hypothesis:
{hypothesis}

Research Direction: {research_direction}

Create a comprehensive experiment plan with:
1. **Objective**: Clear statement of what we're testing
2. **Methodology**: High-level approach (2-3 sentences)
3. **Data Requirements**: List of required data (symbols, date ranges, frequency)
4. **Implementation Steps**: 7-10 concrete steps to implement and test the strategy
5. **Success Criteria**: Quantitative metrics and thresholds (e.g., Sharpe > 1.0, Max DD < 20%)
6. **Risk Factors**: Potential issues or limitations
7. **Estimated Runtime**: Expected computation time

Output as valid JSON matching this structure:
{{
  "objective": "string",
  "methodology": "string",
  "data_requirements": ["string"],
  "implementation_steps": ["string"],
  "success_criteria": {{"metric": value}},
  "risk_factors": ["string"],
  "estimated_runtime": "string"
}}

Be specific about technical details for implementing a quantitative trading strategy."""

        try:
            response = self.call_llm(
                prompt=prompt, max_tokens=3000,
                temperature=self.config.get("temperature", 0.3),
                response_format="json",
            )
            plan_data = response if isinstance(response, dict) else {}

            return ExperimentPlan(
                objective=plan_data.get("objective", ""),
                methodology=plan_data.get("methodology", ""),
                data_requirements=plan_data.get("data_requirements", []),
                implementation_steps=plan_data.get("implementation_steps", []),
                success_criteria=plan_data.get("success_criteria", {}),
                estimated_runtime=plan_data.get("estimated_runtime", "Unknown"),
                risk_factors=plan_data.get("risk_factors", []),
            )
        except Exception as e:
            self.logger.error(f"Error parsing experiment plan: {e}")
            return ExperimentPlan(
                objective="Test hypothesis through backtesting",
                methodology="Implement and validate trading strategy",
                data_requirements=["Historical OHLCV data"],
                implementation_steps=["Design strategy", "Implement code", "Run backtest"],
                success_criteria={"sharpe_ratio": 1.0},
                estimated_runtime="1 hour",
                risk_factors=["Data quality", "Overfitting"],
            )

    def generate_methodology(self, experiment_plan: ExperimentPlan, hypothesis: str) -> str:
        """生成详细方法论描述。"""
        prompt = f"""Given the following experiment plan for testing a quantitative finance hypothesis,
write a detailed methodology section suitable for a research paper.

Hypothesis:
{hypothesis}

Experiment Plan Objective:
{experiment_plan['objective']}

High-level Methodology:
{experiment_plan['methodology']}

Implementation Steps:
{chr(10).join(f"- {step}" for step in experiment_plan['implementation_steps'])}

Write a detailed methodology section (300-500 words) that explains:
1. Overall approach and framework
2. Data sources and preprocessing
3. Strategy implementation details
4. Backtesting methodology
5. Performance evaluation metrics
6. Validation approach

Use formal academic language appropriate for a finance research paper."""

        return self.call_llm(prompt=prompt, max_tokens=2000, temperature=self.config.get("temperature", 0.3))

    def define_expected_outcomes(self, experiment_plan: ExperimentPlan, hypothesis: str) -> str:
        """定义预期结果和验证标准。"""
        criteria_text = json.dumps(experiment_plan["success_criteria"], indent=2)
        prompt = f"""Define the expected outcomes for this experiment and how they would validate or refute the hypothesis.

Hypothesis:
{hypothesis}

Success Criteria:
{criteria_text}

Describe:
1. What results would **support** the hypothesis (specific metric ranges)
2. What results would **refute** the hypothesis
3. What results would be **inconclusive** or require further investigation
4. Alternative explanations for potential results

Write 200-300 words."""

        return self.call_llm(prompt=prompt, max_tokens=1500, temperature=self.config.get("temperature", 0.3))

    def specify_resources(self, experiment_plan: ExperimentPlan) -> Dict[str, str]:
        """指定所需资源。"""
        return {
            "compute": "Local CPU (no GPU required)",
            "data_sources": ", ".join(experiment_plan["data_requirements"]),
            "software": "Python, Backtrader, yfinance, pandas, numpy",
            "storage": "~100MB for data cache",
            "estimated_time": experiment_plan["estimated_runtime"],
        }

    def validate_feasibility(self, experiment_plan: ExperimentPlan) -> tuple[bool, str]:
        """验证实验方案可行性。"""
        issues = []
        if len(experiment_plan["implementation_steps"]) < 3:
            issues.append("Too few implementation steps defined")
        if not experiment_plan["success_criteria"]:
            issues.append("No success criteria defined")
        if not experiment_plan["data_requirements"]:
            issues.append("No data requirements specified")

        is_feasible = len(issues) == 0
        notes = "; ".join(issues) if issues else "Plan appears feasible"
        return is_feasible, notes
