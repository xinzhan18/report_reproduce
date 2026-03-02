"""
Tool 定义与执行器 — PlanningAgent 工具集

1 个专用工具(submit_result) + 通用工具(read_upstream_file, search_knowledge_graph,
browse_webpage, google_search from common_tools)。
适配 ToolRegistry 的 (name, schema, executor) 格式。
"""

# INPUT:  agents.common_tools
# OUTPUT: get_tool_definitions() 函数
# POSITION: agents/planning 子包 - 工具 schema + executor (ToolRegistry 格式)

from __future__ import annotations

from agents.common_tools import get_common_tools


# ======================================================================
# Tool schemas (Anthropic API 格式) — PlanningAgent 专用
# ======================================================================

SUBMIT_RESULT_SCHEMA = {
    "name": "submit_result",
    "description": (
        "Submit the final experiment plan and end the planning phase. "
        "Must include: experiment_plan, methodology, expected_outcomes, data_config. "
        "This terminates the agentic loop."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "object",
                "description": "The final results object",
                "properties": {
                    "experiment_plan": {
                        "type": "object",
                        "description": "FactorPlan with objective, factor_description, factor_formula, data_requirements, implementation_steps, test_universe, test_period, rebalance_frequency, success_criteria, risk_factors, estimated_runtime",
                    },
                    "methodology": {
                        "type": "string",
                        "description": "Detailed methodology description (300-500 words)",
                    },
                    "expected_outcomes": {
                        "type": "string",
                        "description": "Expected outcomes and validation criteria (200-300 words)",
                    },
                    "data_config": {
                        "type": "object",
                        "description": "Data configuration with market, universe, start_date, end_date",
                    },
                },
                "required": ["experiment_plan", "methodology", "expected_outcomes", "data_config"],
            }
        },
        "required": ["results"],
    },
}


# ======================================================================
# ToolRegistry 注册接口
# ======================================================================

def get_tool_definitions(include_browser: bool = False) -> list[tuple[str, dict, callable]]:
    """返回 PlanningAgent 工具定义列表，适配 ToolRegistry.register_many()。

    Args:
        include_browser: 是否包含浏览器工具

    Returns:
        [(name, schema, executor), ...]
    """
    tools = [
        ("submit_result", SUBMIT_RESULT_SCHEMA, lambda tool_input, **_: ""),  # handled by _agentic_loop
    ]

    # 通用工具: read_upstream_file, search_knowledge_graph, browse_webpage, google_search
    tools.extend(get_common_tools(
        include_browser=include_browser,
        include_kg=True,
        include_file=True,
    ))

    return tools
