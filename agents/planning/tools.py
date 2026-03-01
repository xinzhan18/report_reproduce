"""
Tool 定义与执行器 — PlanningAgent 工具集

5 个工具：read_upstream_file, search_knowledge_graph,
browse_webpage, google_search, submit_result。
适配 ToolRegistry 的 (name, schema, executor) 格式。
"""

# INPUT:  tools.file_manager, core.knowledge_graph, agents.browser_manager
# OUTPUT: get_tool_definitions() 函数
# POSITION: agents/planning 子包 - 工具 schema + executor (ToolRegistry 格式)

from __future__ import annotations
import json


# ======================================================================
# Tool schemas (Anthropic API 格式)
# ======================================================================

READ_UPSTREAM_FILE_SCHEMA = {
    "name": "read_upstream_file",
    "description": (
        "Read a file produced by previous pipeline stages. "
        "Supports JSON and text files from literature/ and experiments/ subdirectories."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "File name to read (e.g. 'structured_insights.json', 'literature_summary.md')",
            },
            "subdir": {
                "type": "string",
                "description": "Subdirectory (e.g. 'literature', 'experiments'). Default: 'literature'.",
            },
        },
        "required": ["filename"],
    },
}

SEARCH_KNOWLEDGE_GRAPH_SCHEMA = {
    "name": "search_knowledge_graph",
    "description": (
        "Query the knowledge graph for prior knowledge on strategies, metrics, and concepts. "
        "Returns related items with descriptions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for the knowledge graph",
            },
            "node_type": {
                "type": "string",
                "description": "Optional: filter by node type (strategy, metric, concept)",
            },
        },
        "required": ["query"],
    },
}

BROWSE_WEBPAGE_SCHEMA = {
    "name": "browse_webpage",
    "description": (
        "Browse a webpage and extract its text content. "
        "Use for: verifying data availability, checking API docs, researching methodologies."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to browse",
            }
        },
        "required": ["url"],
    },
}

GOOGLE_SEARCH_SCHEMA = {
    "name": "google_search",
    "description": (
        "Search Google for information. "
        "Use for: finding methodology references, data source documentation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            }
        },
        "required": ["query"],
    },
}

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
                        "description": "ExperimentPlan with objective, methodology, data_requirements, implementation_steps, success_criteria, risk_factors, estimated_runtime",
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
                        "description": "Data configuration with symbols, start_date, end_date, interval, market",
                    },
                },
                "required": ["experiment_plan", "methodology", "expected_outcomes", "data_config"],
            }
        },
        "required": ["results"],
    },
}


# ======================================================================
# Executors
# ======================================================================

def _exec_read_upstream_file(tool_input: dict, file_manager=None, project_id: str = "", **_) -> str:
    if file_manager is None:
        return "[ERROR] file_manager not available"
    filename = tool_input["filename"]
    subdir = tool_input.get("subdir", "literature")

    # JSON 文件
    if filename.endswith(".json"):
        data = file_manager.load_json(project_id, filename, subdir=subdir)
        if data is None:
            return f"[ERROR] File not found: {subdir}/{filename}"
        return json.dumps(data, indent=2, ensure_ascii=False)[:15000]

    # 文本文件
    data = file_manager.load_text(project_id, filename, subdir=subdir)
    if data is None:
        return f"[ERROR] File not found: {subdir}/{filename}"
    return data[:15000]


def _exec_search_knowledge_graph(tool_input: dict, knowledge_graph=None, **_) -> str:
    if knowledge_graph is None:
        return "[ERROR] knowledge_graph not available"
    query = tool_input["query"]
    node_type = tool_input.get("node_type")
    results = knowledge_graph.search_knowledge(query=query, node_type=node_type)
    if not results:
        return "No related knowledge found."
    lines = []
    for k in results[:10]:
        node_type_str = k.get("node_type", "concept")
        lines.append(f"- [{node_type_str}] {k['name']}: {k.get('description', '')[:200]}")
    return f"Found {len(results)} related items:\n\n" + "\n".join(lines)


def _exec_browse_webpage(tool_input: dict, browser=None, **_) -> str:
    if browser is None:
        return "[ERROR] Browser not available"
    result = browser.browse(tool_input["url"])
    return f"Title: {result['title']}\n\n{result['text']}"


def _exec_google_search(tool_input: dict, browser=None, **_) -> str:
    if browser is None:
        return "[ERROR] Browser not available"
    results = browser.search_google(tool_input["query"])
    lines = []
    for r in results:
        lines.append(f"- {r['title']}\n  {r['url']}\n  {r['snippet']}")
    return "\n\n".join(lines) if lines else "No results found"


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
        ("read_upstream_file", READ_UPSTREAM_FILE_SCHEMA, _exec_read_upstream_file),
        ("search_knowledge_graph", SEARCH_KNOWLEDGE_GRAPH_SCHEMA, _exec_search_knowledge_graph),
        ("submit_result", SUBMIT_RESULT_SCHEMA, lambda tool_input, **_: ""),  # handled by _agentic_loop
    ]

    if include_browser:
        tools.extend([
            ("browse_webpage", BROWSE_WEBPAGE_SCHEMA, _exec_browse_webpage),
            ("google_search", GOOGLE_SEARCH_SCHEMA, _exec_google_search),
        ])

    return tools
