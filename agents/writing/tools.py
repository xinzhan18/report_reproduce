"""
Tool 定义与执行器 — WritingAgent 工具集

6 个工具：read_upstream_file, write_section, run_python,
browse_webpage, google_search, submit_result。
适配 ToolRegistry 的 (name, schema, executor) 格式。
"""

# INPUT:  tools.file_manager, agents.experiment.sandbox (SandboxManager), agents.browser_manager
# OUTPUT: get_tool_definitions() 函数
# POSITION: agents/writing 子包 - 工具 schema + executor (ToolRegistry 格式)

from __future__ import annotations
import json


# ======================================================================
# Tool schemas (Anthropic API 格式)
# ======================================================================

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
                "description": "File name to read (e.g. 'backtest_results.json', 'literature_summary.md')",
            },
            "subdir": {
                "type": "string",
                "description": "Subdirectory (e.g. 'literature', 'experiments', 'reports'). Default: 'literature'.",
            },
        },
        "required": ["filename"],
    },
}

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

RUN_PYTHON_SCHEMA = {
    "name": "run_python",
    "description": (
        "Run a Python script for generating visualizations, data analysis, or processing. "
        "Write the script content and it will be executed. Output (stdout/stderr) is returned."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "script": {
                "type": "string",
                "description": "The Python script content to execute",
            },
        },
        "required": ["script"],
    },
}

BROWSE_WEBPAGE_SCHEMA = {
    "name": "browse_webpage",
    "description": (
        "Browse a webpage and extract its text content. "
        "Use for: finding additional references, checking supplementary information."
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
        "Use for: finding reference materials, checking related works."
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
# Executors
# ======================================================================

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


def _exec_write_section(tool_input: dict, file_manager=None, project_id: str = "", **_) -> str:
    if file_manager is None:
        return "[ERROR] file_manager not available"
    filename = tool_input["filename"]
    content = tool_input["content"]
    file_manager.save_text(content=content, project_id=project_id, filename=filename, subdir="reports")
    return f"Section saved: reports/{filename} ({len(content)} characters)"


def _exec_run_python(tool_input: dict, sandbox=None, **_) -> str:
    if sandbox is None:
        return "[ERROR] Sandbox not available for Python execution"
    script = tool_input["script"]
    # 写入临时脚本并执行
    sandbox.write_file("_writing_script.py", script)
    result = sandbox.run_python("_writing_script.py", timeout=120)
    parts = []
    if result["stdout"]:
        parts.append(f"stdout:\n{result['stdout']}")
    if result["stderr"]:
        parts.append(f"stderr:\n{result['stderr']}")
    parts.append(f"exit_code: {result['returncode']}")
    return "\n".join(parts)


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

def get_tool_definitions(include_browser: bool = False, include_python: bool = False) -> list[tuple[str, dict, callable]]:
    """返回 WritingAgent 工具定义列表，适配 ToolRegistry.register_many()。

    Args:
        include_browser: 是否包含浏览器工具
        include_python: 是否包含 Python 执行工具

    Returns:
        [(name, schema, executor), ...]
    """
    tools = [
        ("read_upstream_file", READ_UPSTREAM_FILE_SCHEMA, _exec_read_upstream_file),
        ("write_section", WRITE_SECTION_SCHEMA, _exec_write_section),
        ("submit_result", SUBMIT_RESULT_SCHEMA, lambda tool_input, **_: ""),  # handled by _agentic_loop
    ]

    if include_python:
        tools.append(("run_python", RUN_PYTHON_SCHEMA, _exec_run_python))

    if include_browser:
        tools.extend([
            ("browse_webpage", BROWSE_WEBPAGE_SCHEMA, _exec_browse_webpage),
            ("google_search", GOOGLE_SEARCH_SCHEMA, _exec_google_search),
        ])

    return tools
