"""
通用工具 schema + executor — 多个 Agent 共享的工具定义

browse_webpage, google_search, search_knowledge_graph, read_upstream_file
四个工具在 4 个 Agent 中 100% 相同，统一提取到此模块。
"""

# INPUT:  agents.browser_manager, core.knowledge_graph, tools.file_manager, json
# OUTPUT: get_common_tools() 函数, 4 个 schema dict, 4 个 executor 函数
# POSITION: agents/ 层 - 通用工具定义，供各 Agent tools.py 导入

from __future__ import annotations
import json


# ======================================================================
# Tool schemas (Anthropic API 格式)
# ======================================================================

BROWSE_WEBPAGE_SCHEMA = {
    "name": "browse_webpage",
    "description": (
        "Browse a webpage and extract its text content. "
        "Use for: reading documentation, checking references, researching topics."
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
        "Use for: finding additional references, checking methodology details."
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

READ_UPSTREAM_FILE_SCHEMA = {
    "name": "read_upstream_file",
    "description": (
        "Read a file produced by previous pipeline stages. "
        "Supports JSON and text files from literature/, experiments/, and reports/ subdirectories."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "File name to read (e.g. 'papers_analyzed.json', 'literature_summary.md')",
            },
            "subdir": {
                "type": "string",
                "description": "Subdirectory (e.g. 'literature', 'experiments', 'reports'). Default: 'literature'.",
            },
        },
        "required": ["filename"],
    },
}


# ======================================================================
# Executors
# ======================================================================

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


def _exec_read_upstream_file(tool_input: dict, file_manager=None, project_id: str = "", **_) -> str:
    if file_manager is None:
        return "[ERROR] file_manager not available"
    filename = tool_input["filename"]
    subdir = tool_input.get("subdir", "literature")

    if filename.endswith(".json"):
        data = file_manager.load_json(project_id, filename, subdir=subdir)
        if data is None:
            return f"[ERROR] File not found: {subdir}/{filename}"
        return json.dumps(data, indent=2, ensure_ascii=False)[:15000]

    data = file_manager.load_text(project_id, filename, subdir=subdir)
    if data is None:
        return f"[ERROR] File not found: {subdir}/{filename}"
    return data[:15000]


# ======================================================================
# 公共接口
# ======================================================================

def get_common_tools(
    include_browser: bool = False,
    include_kg: bool = False,
    include_file: bool = False,
) -> list[tuple[str, dict, callable]]:
    """返回通用工具定义列表，供各 Agent 的 get_tool_definitions() 调用。

    Args:
        include_browser: 包含 browse_webpage + google_search
        include_kg: 包含 search_knowledge_graph
        include_file: 包含 read_upstream_file

    Returns:
        [(name, schema, executor), ...]
    """
    tools = []

    if include_browser:
        tools.extend([
            ("browse_webpage", BROWSE_WEBPAGE_SCHEMA, _exec_browse_webpage),
            ("google_search", GOOGLE_SEARCH_SCHEMA, _exec_google_search),
        ])

    if include_kg:
        tools.append(
            ("search_knowledge_graph", SEARCH_KNOWLEDGE_GRAPH_SCHEMA, _exec_search_knowledge_graph),
        )

    if include_file:
        tools.append(
            ("read_upstream_file", READ_UPSTREAM_FILE_SCHEMA, _exec_read_upstream_file),
        )

    return tools
