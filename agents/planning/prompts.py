"""
Prompt 模板 — PlanningAgent 的 system prompt 和 task prompt

因子研究模式：设计因子测试方案（因子公式、测试 universe、测试期间、再平衡频率）。
支持首次模式和修正模式（反馈回路）。
"""

# INPUT:  json
# OUTPUT: SYSTEM_PROMPT_TEMPLATE, build_task_prompt(), build_revision_task_prompt()
# POSITION: agents/planning 子包 - Prompt 模板

import json


SYSTEM_PROMPT_TEMPLATE = """\
You are an expert quantitative factor researcher specializing in factor test design and methodology planning.
You have access to tools to read upstream analysis files, query a knowledge graph, browse the web, and submit final results.

## Your Tools
- **read_upstream_file**: Read files produced by previous pipeline stages (literature analysis, etc.)
- **search_knowledge_graph**: Query the knowledge graph for prior knowledge on factors, metrics, etc.
- **browse_webpage**: Browse a webpage to verify data availability or research methodology details
- **google_search**: Search Google for methodology references or data source information
- **submit_result**: Submit the final factor test plan

## Workflow
1. Read upstream file `literature/ideation.md` for the complete literature review and factor hypothesis
2. Query the knowledge graph for relevant factors and evaluation benchmarks
3. Optionally browse the web to verify data availability and methodology details
4. Design a comprehensive factor test plan with:
   - Clear factor description and construction formula
   - Test universe (A-shares or crypto) and test period
   - Rebalance frequency and holding period
   - Detailed implementation steps referencing literature
   - Measurable success criteria (IC/ICIR thresholds)
   - Risk factors and mitigation strategies
5. Call submit_result with the complete factor test plan

## Rules
1. Factor formula MUST be specific enough to implement in Python (e.g., "20-day momentum = close[t] / close[t-20] - 1")
2. Implementation steps MUST be numbered with "Step N:" prefix for checklist generation
3. Success criteria MUST include ic_mean and icir thresholds
4. Data configuration must specify market, universe, and date range
5. Plan must be feasible to implement using only OHLCV data
6. You MUST call submit_result when done — the planning does not end otherwise

{agent_memory}
"""


def build_task_prompt(
    hypothesis: str,
    research_direction: str,
    kg_context: str = "",
) -> str:
    """构建首次模式的 task prompt。"""
    return f"""\
## Task: Design a Factor Test Plan

### Factor Hypothesis
{hypothesis}

### Research Direction
{research_direction}

{kg_context}

### Instructions
1. First, read upstream files to understand the literature context:
   - `literature/ideation.md` — Complete literature review, factor construction methods, and hypothesis
   - `literature/papers_analyzed.json` — Papers reviewed with metadata (optional)
   - `literature/research_synthesis.json` — Cross-paper synthesis (optional)
2. Query the knowledge graph for relevant factors and performance benchmarks
3. Optionally verify data availability by browsing relevant data source websites
4. Design a detailed factor test plan

### submit_result Format
```json
{{
  "results": {{
    "experiment_plan": {{
      "objective": "Clear statement of what factor we're testing",
      "factor_description": "What the factor measures (economic intuition)",
      "factor_formula": "Specific formula or pseudocode (e.g., 'close[t]/close[t-20] - 1')",
      "data_requirements": ["OHLCV data for A-shares", "at least 3 years of history"],
      "implementation_steps": [
        "Step 1: Load price data and build price matrix",
        "Step 2: Compute factor values cross-sectionally",
        "Step 3: Handle missing values and outliers",
        "Step 4: Call evaluate_factor to compute IC/ICIR metrics",
        "Step 5: Validate results against success criteria"
      ],
      "test_universe": "a_shares",
      "test_period": "2018-01-01 to 2024-12-31",
      "rebalance_frequency": "daily",
      "success_criteria": {{"ic_mean": 0.03, "icir": 0.5}},
      "risk_factors": ["Survivorship bias", "Look-ahead bias", "Overfitting"],
      "estimated_runtime": "Expected computation time"
    }},
    "methodology": "Detailed methodology section (300-500 words)...",
    "data_config": {{
      "market": "a_shares",
      "universe": "all",
      "start_date": "2018-01-01",
      "end_date": "2024-12-31"
    }}
  }}
}}
```

Begin by reading the upstream literature analysis files.
"""


def build_revision_task_prompt(
    hypothesis: str,
    marked_plan: str,
    feedback: dict,
    kg_context: str = "",
) -> str:
    """构建修正模式的 task prompt。

    在反馈回路中使用：ExperimentAgent 已标记 plan.md 中的 checklist，
    PlanningAgent 读取标记后的 plan.md 并修正失败的步骤。
    """
    suggestions_text = "\n".join(
        f"- {s}" for s in feedback.get("suggestions", [])
    )
    failed_steps_text = "\n".join(
        f"- {s}" for s in feedback.get("failed_steps", [])
    )

    return f"""\
## Task: REVISE Factor Test Plan (Feedback Loop)

The previous factor evaluation has identified issues. You must revise the plan.

### Factor Hypothesis
{hypothesis}

{kg_context}

### Previous Plan (with execution marks)
The following is the plan.md after ExperimentAgent marked completed/failed steps:

```markdown
{marked_plan}
```

### Experiment Feedback
**Verdict**: {feedback.get("verdict", "revise_plan")}
**Analysis**: {feedback.get("analysis", "")}

**Failed Steps**:
{failed_steps_text}

**Suggestions for Improvement**:
{suggestions_text}

### Instructions
1. Analyze the marked plan to understand what succeeded and what failed
2. Read `literature/ideation.md` for additional context if needed
3. Query the knowledge graph for alternative factor construction approaches
4. Design a REVISED factor test plan that:
   - Keeps successful elements unchanged where possible
   - Addresses each failed step with a concrete fix
   - May adjust factor formula, holding period, or universe
   - Adjusts success criteria if they were unrealistic
   - Adds new risk mitigations based on learnings
5. Call submit_result with the revised plan

### submit_result Format
```json
{{
  "results": {{
    "experiment_plan": {{
      "objective": "Revised objective...",
      "factor_description": "Revised factor description...",
      "factor_formula": "Revised factor formula...",
      "data_requirements": ["..."],
      "implementation_steps": [
        "Step 1: Revised step (addressing failure)",
        "Step 2: ..."
      ],
      "test_universe": "a_shares",
      "test_period": "2018-01-01 to 2024-12-31",
      "rebalance_frequency": "daily",
      "success_criteria": {{"ic_mean": revised_threshold, "icir": revised_threshold}},
      "risk_factors": ["..."],
      "estimated_runtime": "..."
    }},
    "methodology": "Revised detailed methodology (300-500 words)...",
    "data_config": {{
      "market": "a_shares",
      "universe": "all",
      "start_date": "2018-01-01",
      "end_date": "2024-12-31"
    }}
  }}
}}
```

Begin by analyzing the marked plan above to understand the failures.
"""
