"""
Planning Agent - Experiment design and planning.

Responsible for:
- Transforming hypotheses into executable experiment plans
- Designing methodology and approach
- Specifying data requirements
- Defining success criteria
- Assessing feasibility
"""

from typing import Dict, Any
from anthropic import Anthropic
from core.state import ResearchState, ExperimentPlan
from tools.file_manager import FileManager
from config.agent_config import get_agent_config
from config.llm_config import get_model_name
from core.agent_memory_manager import get_agent_memory_manager
from core.knowledge_graph import get_knowledge_graph
import json


class PlanningAgent:
    """
    Agent responsible for experiment planning and design.
    Enhanced with persona, self-reflection, and knowledge graph capabilities.
    """

    def __init__(self, llm: Anthropic, file_manager: FileManager):
        """
        Initialize Planning Agent.

        Args:
            llm: Anthropic client instance
            file_manager: FileManager instance for file operations
        """
        self.llm = llm
        self.file_manager = file_manager
        self.config = get_agent_config("planning")
        self.model = get_model_name(self.config.get("model", "sonnet"))

        # Initialize agent intelligence components (NEW: Markdown-based memory system)
        self.memory_manager = get_agent_memory_manager("planning")
        self.knowledge_graph = get_knowledge_graph()

    def _build_system_prompt(self, memories: Dict[str, str]) -> str:
        """
        Build system prompt with persona and memory context.

        Args:
            memories: Dictionary containing persona, memory, mistakes, and daily logs

        Returns:
            Complete system prompt string
        """
        return f"""# Your Identity and Persona

{memories['persona']}

---

# Your Long-term Knowledge and Insights

{memories['memory']}

---

# Mistakes to Avoid (IMPORTANT - Review Before Each Task)

{memories['mistakes']}

---

# Recent Context (Last 3 Days of Work)

{memories['daily_recent']}

---

You are now executing a new task. Use your persona, knowledge, and past learnings to perform at your best. Avoid repeating past mistakes.
"""

    def __call__(self, state: ResearchState) -> ResearchState:
        """
        Execute planning agent workflow.

        Args:
            state: Current research state

        Returns:
            Updated research state with planning outputs
        """
        print(f"\n{'='*60}")
        print(f"Planning Agent: Designing experiment")
        print(f"{'='*60}\n")

        # Update status
        state["status"] = "planning"

        # Load all memories (persona, memory, mistakes, daily logs)
        print("🧠 Loading agent memories...")
        self.memories = self.memory_manager.load_all_memories()
        self.system_prompt = self._build_system_prompt(self.memories)
        print(f"✓ Loaded persona, long-term memory, mistakes registry, and recent daily logs")

        # Consult knowledge graph for related strategies and methodologies
        hypothesis_keywords = state["hypothesis"][:100].lower()
        related_strategies = self.knowledge_graph.search_knowledge(
            query=hypothesis_keywords,
            node_type="strategy"
        )

        related_metrics = self.knowledge_graph.search_knowledge(
            query="performance metrics",
            node_type="metric"
        )

        if related_strategies:
            print(f"✓ Found {len(related_strategies)} related strategies in knowledge graph")

        if related_metrics:
            print(f"✓ Found {len(related_metrics)} relevant metrics")

        # Step 1: Design experiment plan
        experiment_plan = self.design_experiment(
            hypothesis=state["hypothesis"],
            literature_summary=state["literature_summary"],
            research_gaps=state["research_gaps"],
            research_direction=state["research_direction"]
        )
        state["experiment_plan"] = experiment_plan

        print(f"✓ Created experiment plan")
        print(f"  Objective: {experiment_plan['objective'][:100]}...")

        # Save plan
        self.file_manager.save_json(
            data=experiment_plan,
            project_id=state["project_id"],
            filename="experiment_plan_v1.json",
            subdir="experiments"
        )

        # Step 2: Generate detailed methodology
        methodology = self.generate_methodology(
            experiment_plan,
            state["hypothesis"]
        )
        state["methodology"] = methodology

        print(f"✓ Generated detailed methodology")

        # Step 3: Define expected outcomes
        expected_outcomes = self.define_expected_outcomes(
            experiment_plan,
            state["hypothesis"]
        )
        state["expected_outcomes"] = expected_outcomes

        print(f"✓ Defined success criteria and expected outcomes")

        # Step 4: Specify resource requirements
        resource_requirements = self.specify_resources(experiment_plan)
        state["resource_requirements"] = resource_requirements

        print(f"✓ Specified resource requirements")

        # Step 5: Validate feasibility
        is_feasible, feasibility_notes = self.validate_feasibility(experiment_plan)

        if not is_feasible:
            print(f"\n⚠ Feasibility concerns: {feasibility_notes}")
            state["error_log"] = f"Feasibility concerns: {feasibility_notes}"

        # Save complete planning documentation
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

        self.file_manager.save_text(
            content=planning_doc,
            project_id=state["project_id"],
            filename="planning_document.md",
            subdir="experiments"
        )

        print(f"\n{'='*60}")
        print(f"Planning Agent: Completed")
        print(f"{'='*60}\n")

        # Save daily log with execution details
        execution_log = f"""## Experiment Planning Execution

### Hypothesis
{state["hypothesis"][:300]}...

### Experiment Plan Designed
- Methodology: {experiment_plan['methodology']}
- Implementation Steps: {len(experiment_plan["implementation_steps"])}
- Success Criteria Defined: {len(experiment_plan["success_criteria"])}
- Feasibility: {'Feasible' if is_feasible else 'Needs Review'}

### Key Components
- Data Requirements: {experiment_plan.get('data_requirements', 'Specified')}
- Backtesting Approach: {experiment_plan.get('backtesting_approach', 'Defined')}
- Risk Factors: {len(experiment_plan.get('risk_factors', []))} identified
"""

        learnings = [
            f"Successfully designed {len(experiment_plan['implementation_steps'])}-step experiment plan",
            f"Methodology: {experiment_plan['methodology']}",
            f"Plan feasibility: {'Validated' if is_feasible else 'Requires adjustments'}"
        ]

        mistakes_encountered = []  # Track if any issues occurred

        reflection_text = f"""
## Reflection on Execution

### What Went Well
- Comprehensive experiment plan created with {len(experiment_plan['implementation_steps'])} clear steps
- Success criteria well-defined: {', '.join(experiment_plan['success_criteria'].keys())}
- Feasibility assessment: {'Plan is executable' if is_feasible else 'Identified concerns'}

### Areas for Improvement
- Consider edge cases in implementation
- Validate data requirements with Experiment Agent
"""

        self.memory_manager.save_daily_log(
            project_id=state["project_id"],
            execution_log=execution_log,
            learnings=learnings,
            mistakes=mistakes_encountered,
            reflection=reflection_text
        )

        print(f"✓ Daily log saved with planning details and learnings")

        # Update knowledge graph with plan insights
        findings = [
            f"Methodology: {experiment_plan['methodology']}",
            f"Approach validated for: {state['research_direction']}"
        ]

        self.knowledge_graph.update_knowledge_from_research(
            project_id=state["project_id"],
            findings=findings,
            llm=self.llm
        )

        return state

    def design_experiment(
        self,
        hypothesis: str,
        literature_summary: str,
        research_gaps: list,
        research_direction: str
    ) -> ExperimentPlan:
        """
        Design comprehensive experiment plan.

        Args:
            hypothesis: Research hypothesis
            literature_summary: Literature review summary
            research_gaps: Identified research gaps
            research_direction: Research focus area

        Returns:
            ExperimentPlan dictionary
        """
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

        response = self.llm.messages.create(
            model=self.model,
            max_tokens=3000,
            temperature=self.config.get("temperature", 0.3),
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text

        # Parse JSON from response
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "{" in content:
                json_str = content[content.find("{"):content.rfind("}")+1]
            else:
                json_str = content

            plan_data = json.loads(json_str)

            # Ensure all required fields
            return ExperimentPlan(
                objective=plan_data.get("objective", ""),
                methodology=plan_data.get("methodology", ""),
                data_requirements=plan_data.get("data_requirements", []),
                implementation_steps=plan_data.get("implementation_steps", []),
                success_criteria=plan_data.get("success_criteria", {}),
                estimated_runtime=plan_data.get("estimated_runtime", "Unknown"),
                risk_factors=plan_data.get("risk_factors", [])
            )

        except Exception as e:
            print(f"Error parsing experiment plan: {e}")
            # Return default plan
            return ExperimentPlan(
                objective="Test hypothesis through backtesting",
                methodology="Implement and validate trading strategy",
                data_requirements=["Historical OHLCV data"],
                implementation_steps=["Design strategy", "Implement code", "Run backtest"],
                success_criteria={"sharpe_ratio": 1.0},
                estimated_runtime="1 hour",
                risk_factors=["Data quality", "Overfitting"]
            )

    def generate_methodology(
        self,
        experiment_plan: ExperimentPlan,
        hypothesis: str
    ) -> str:
        """
        Generate detailed methodology description.

        Args:
            experiment_plan: Experiment plan
            hypothesis: Research hypothesis

        Returns:
            Detailed methodology text
        """
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

        response = self.llm.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=self.config.get("temperature", 0.3),
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def define_expected_outcomes(
        self,
        experiment_plan: ExperimentPlan,
        hypothesis: str
    ) -> str:
        """
        Define expected outcomes and validation criteria.

        Args:
            experiment_plan: Experiment plan
            hypothesis: Research hypothesis

        Returns:
            Expected outcomes description
        """
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

        response = self.llm.messages.create(
            model=self.model,
            max_tokens=1500,
            temperature=self.config.get("temperature", 0.3),
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def specify_resources(self, experiment_plan: ExperimentPlan) -> Dict[str, str]:
        """
        Specify required computational and data resources.

        Args:
            experiment_plan: Experiment plan

        Returns:
            Resource requirements dictionary
        """
        return {
            "compute": "Local CPU (no GPU required)",
            "data_sources": ", ".join(experiment_plan["data_requirements"]),
            "software": "Python, Backtrader, yfinance, pandas, numpy",
            "storage": "~100MB for data cache",
            "estimated_time": experiment_plan["estimated_runtime"]
        }

    def validate_feasibility(self, experiment_plan: ExperimentPlan) -> tuple[bool, str]:
        """
        Validate that the plan is feasible with available resources.

        Args:
            experiment_plan: Experiment plan to validate

        Returns:
            Tuple of (is_feasible, notes)
        """
        issues = []

        # Check if we have implementation steps
        if len(experiment_plan["implementation_steps"]) < 3:
            issues.append("Too few implementation steps defined")

        # Check if success criteria are defined
        if not experiment_plan["success_criteria"]:
            issues.append("No success criteria defined")

        # Check if data requirements are specified
        if not experiment_plan["data_requirements"]:
            issues.append("No data requirements specified")

        is_feasible = len(issues) == 0
        notes = "; ".join(issues) if issues else "Plan appears feasible"

        return is_feasible, notes
