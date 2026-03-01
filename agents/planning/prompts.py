"""
Prompt 模板 — PlanningAgent 的 system prompt 和 task prompt

支持首次模式和修正模式（反馈回路）。
"""

# INPUT:  json
# OUTPUT: SYSTEM_PROMPT_TEMPLATE, build_task_prompt(), build_revision_task_prompt()
# POSITION: agents/planning 子包 - Prompt 模板

import json


SYSTEM_PROMPT_TEMPLATE = """\
You are an expert quantitative finance researcher specializing in experiment design and methodology planning.
You have access to tools to read upstream analysis files, query a knowledge graph, browse the web, and submit final results.

## Your Tools
- **read_upstream_file**: Read files produced by previous pipeline stages (literature analysis, etc.)
- **search_knowledge_graph**: Query the knowledge graph for prior knowledge on strategies, metrics, etc.
- **browse_webpage**: Browse a webpage to verify data availability or research methodology details
- **google_search**: Search Google for methodology references or data source information
- **submit_result**: Submit the final experiment plan

## Workflow
1. Read upstream file `literature/ideation.md` for the complete literature review and hypothesis
2. Query the knowledge graph for relevant strategies and metrics
3. Optionally browse the web to verify data availability and methodology details
4. Design a comprehensive experiment plan with:
   - Clear objective and methodology
   - Specific data requirements and configuration
   - Detailed implementation steps referencing literature (numbered: "Step 1: ...", "Step 2: ...", etc.)
   - Measurable success criteria with literature-backed thresholds
   - Risk factors and mitigation strategies
5. Call submit_result with the complete experiment plan

## Rules
1. Implementation steps MUST reference specific methodologies from the literature
2. Implementation steps MUST be numbered with "Step N:" prefix for checklist generation
3. Success criteria MUST reference benchmark values from the literature where available
4. Data configuration must specify symbols, date range, interval, and market
5. Plan must be feasible to implement as a Python backtesting strategy
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
## Task: Design an Experiment Plan

### Hypothesis
{hypothesis}

### Research Direction
{research_direction}

{kg_context}

### Instructions
1. First, read upstream files to understand the literature context:
   - `literature/ideation.md` — Complete literature review, research gaps, and hypothesis
   - `literature/papers_analyzed.json` — Papers reviewed with metadata (optional)
   - `literature/research_synthesis.json` — Cross-paper synthesis (optional)
2. Query the knowledge graph for relevant strategies and performance benchmarks
3. Optionally verify data availability by browsing relevant data source websites
4. Design a detailed experiment plan

### submit_result Format
```json
{{
  "results": {{
    "experiment_plan": {{
      "objective": "Clear statement of what we're testing",
      "methodology": "High-level approach (2-3 sentences)",
      "data_requirements": ["required data item 1", "required data item 2"],
      "implementation_steps": [
        "Step 1: Specific actionable step (reference Paper X)",
        "Step 2: Another step with literature reference",
        "Step 3: ..."
      ],
      "success_criteria": {{"metric_name": threshold_value}},
      "risk_factors": ["risk 1", "risk 2"],
      "estimated_runtime": "Expected computation time"
    }},
    "methodology": "Detailed methodology section (300-500 words)...",
    "data_config": {{
      "symbols": ["SPY"],
      "start_date": "2015-01-01",
      "end_date": null,
      "interval": "1d",
      "market": "us_equity"
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
## Task: REVISE Experiment Plan (Feedback Loop)

The previous experiment execution has identified issues. You must revise the plan.

### Hypothesis
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
3. Query the knowledge graph for alternative approaches
4. Design a REVISED experiment plan that:
   - Keeps successful elements unchanged where possible
   - Addresses each failed step with a concrete fix
   - Adjusts success criteria if they were unrealistic
   - Adds new risk mitigations based on learnings
5. Call submit_result with the revised plan

### submit_result Format
```json
{{
  "results": {{
    "experiment_plan": {{
      "objective": "Revised objective...",
      "methodology": "Revised methodology...",
      "data_requirements": ["..."],
      "implementation_steps": [
        "Step 1: Revised step (addressing failure)",
        "Step 2: ..."
      ],
      "success_criteria": {{"metric_name": revised_threshold}},
      "risk_factors": ["..."],
      "estimated_runtime": "..."
    }},
    "methodology": "Revised detailed methodology (300-500 words)...",
    "data_config": {{
      "symbols": ["SPY"],
      "start_date": "2015-01-01",
      "end_date": null,
      "interval": "1d",
      "market": "us_equity"
    }}
  }}
}}
```

Begin by analyzing the marked plan above to understand the failures.
"""
