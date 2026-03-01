"""
Tool 定义与执行器 — WritingAgent 工具集

2 个专用工具(write_section, submit_result) + 通用工具(read_upstream_file,
browse_webpage, google_search from common_tools)。
适配 ToolRegistry 的 (name, schema, executor) 格式。
"""

# INPUT:  tools.file_manager, agents.common_tools
# OUTPUT: get_tool_definitions() 函数
# POSITION: agents/writing 子包 - 工具 schema + executor (ToolRegistry 格式)

from __future__ import annotations

from agents.common_tools import get_common_tools


# ======================================================================
# Tool schemas (Anthropic API 格式) — WritingAgent 专用
# ======================================================================

WRITE_SECTION_SCHEMA = {
    "name": "write_section",
    "description": (
        "Write a report section to a file in the reports/ subdirectory. "
        "Use for: saving individual sections or the assembled report."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Output filename (e.g. 'abstract.md', 'final_report.md')",
            },
            "content": {
                "type": "string",
                "description": "The section content to write",
            },
        },
        "required": ["filename", "content"],
    },
}

SUBMIT_RESULT_SCHEMA = {
    "name": "submit_result",
    "description": (
        "Submit the final report and end the writing phase. "
        "Must include: report_draft and final_report. "
        "This terminates the agentic loop."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "object",
                "description": "The final results object",
                "properties": {
                    "report_draft": {
                        "type": "string",
                        "description": "The complete assembled report draft",
                    },
                    "final_report": {
                        "type": "string",
                        "description": "The polished final report",
                    },
                },
                "required": ["report_draft", "final_report"],
            }
        },
        "required": ["results"],
    },
}


# ======================================================================
# Executors — WritingAgent 专用
# ======================================================================

def _exec_write_section(tool_input: dict, file_manager=None, project_id: str = "", **_) -> str:
    if file_manager is None:
        return "[ERROR] file_manager not available"
    filename = tool_input["filename"]
    content = tool_input["content"]
    file_manager.save_text(content=content, project_id=project_id, filename=filename, subdir="reports")
    return f"Section saved: reports/{filename} ({len(content)} characters)"


# ======================================================================
# ToolRegistry 注册接口
# ======================================================================

def get_tool_definitions(include_browser: bool = False) -> list[tuple[str, dict, callable]]:
    """返回 WritingAgent 工具定义列表，适配 ToolRegistry.register_many()。

    Args:
        include_browser: 是否包含浏览器工具

    Returns:
        [(name, schema, executor), ...]
    """
    tools = [
        ("write_section", WRITE_SECTION_SCHEMA, _exec_write_section),
        ("submit_result", SUBMIT_RESULT_SCHEMA, lambda tool_input, **_: ""),  # handled by _agentic_loop
    ]

    # 通用工具: read_upstream_file, browse_webpage, google_search
    tools.extend(get_common_tools(
        include_browser=include_browser,
        include_kg=False,
        include_file=True,
    ))

    return tools
