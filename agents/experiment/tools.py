"""
Tool 定义与执行器 — ExperimentAgent 工具集

6 个沙箱工具 + 2 个浏览器工具 + submit_result。
适配 ToolRegistry 的 (name, schema, executor) 格式。
"""

# INPUT:  agents.experiment.sandbox (SandboxManager), agents.browser_manager
# OUTPUT: get_tool_definitions() 函数
# POSITION: agents/experiment 子包 - 工具 schema + executor (ToolRegistry 格式)

from __future__ import annotations
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.experiment.sandbox import SandboxManager


# ======================================================================
# Tool schemas (Anthropic API 格式)
# ======================================================================

BASH_SCHEMA = {
    "name": "bash",
    "description": (
        "Execute a shell command in the sandbox working directory. "
        "Use for: installing packages (pip install), listing files (ls/dir), "
        "data processing, and other shell operations."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute",
            }
        },
        "required": ["command"],
    },
}

WRITE_FILE_SCHEMA = {
    "name": "write_file",
    "description": (
        "Write content to a file in the sandbox. Creates parent directories if needed. "
        "Use for: writing Python scripts, saving intermediate results, creating config files."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative file path within the sandbox (e.g. 'strategy.py', 'src/utils.py')",
            },
            "content": {
                "type": "string",
                "description": "The full file content to write",
            },
        },
        "required": ["path", "content"],
    },
}

READ_FILE_SCHEMA = {
    "name": "read_file",
    "description": (
        "Read the content of a file in the sandbox. "
        "Use for: inspecting data files, checking script output, reviewing code."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative file path within the sandbox to read",
            }
        },
        "required": ["path"],
    },
}

DELETE_FILE_SCHEMA = {
    "name": "delete_file",
    "description": "Delete a file in the sandbox.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative file path within the sandbox to delete",
            }
        },
        "required": ["path"],
    },
}

RUN_PYTHON_SCHEMA = {
    "name": "run_python",
    "description": (
        "Run a Python script file in the sandbox via subprocess. "
        "The script runs with the sandbox as its working directory. "
        "Use for: executing strategy code, running analysis scripts."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "script_path": {
                "type": "string",
                "description": "Relative path to the Python script to run (e.g. 'strategy.py')",
            }
        },
        "required": ["script_path"],
    },
}

SUBMIT_RESULT_SCHEMA = {
    "name": "submit_result",
    "description": (
        "Submit the final experiment results and end the experiment loop. "
        "Call this ONLY when you have valid results to report. "
        "This terminates the agentic loop."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "object",
                "description": "The final results object",
                "properties": {
                    "metrics": {
                        "type": "object",
                        "description": "Dict of metric name -> value. Required keys: total_return, sharpe_ratio, max_drawdown, total_trades",
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of the strategy and its results",
                    },
                },
                "required": ["metrics", "description"],
            }
        },
        "required": ["results"],
    },
}

BROWSE_WEBPAGE_SCHEMA = {
    "name": "browse_webpage",
    "description": (
        "Browse a webpage and extract its text content. "
        "Use for: reading documentation, checking API references, researching libraries."
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
        "Use for: finding documentation, debugging errors, researching methods."
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


# ======================================================================
# Executors
# ======================================================================

def _exec_bash(tool_input: dict, sandbox: "SandboxManager" = None, timeout: int = 300, **_) -> str:
    result = sandbox.run_command(tool_input["command"], timeout=timeout)
    parts = []
    if result["stdout"]:
        parts.append(f"stdout:\n{result['stdout']}")
    if result["stderr"]:
        parts.append(f"stderr:\n{result['stderr']}")
    parts.append(f"exit_code: {result['returncode']}")
    return "\n".join(parts)


def _exec_write_file(tool_input: dict, sandbox: "SandboxManager" = None, **_) -> str:
    return sandbox.write_file(tool_input["path"], tool_input["content"])


def _exec_read_file(tool_input: dict, sandbox: "SandboxManager" = None, **_) -> str:
    return sandbox.read_file(tool_input["path"])


def _exec_delete_file(tool_input: dict, sandbox: "SandboxManager" = None, **_) -> str:
    return sandbox.delete_file(tool_input["path"])


def _exec_run_python(tool_input: dict, sandbox: "SandboxManager" = None, timeout: int = 300, **_) -> str:
    result = sandbox.run_python(tool_input["script_path"], timeout=timeout)
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

def get_tool_definitions(include_browser: bool = False) -> list[tuple[str, dict, callable]]:
    """返回 ExperimentAgent 工具定义列表，适配 ToolRegistry.register_many()。

    Args:
        include_browser: 是否包含浏览器工具

    Returns:
        [(name, schema, executor), ...]
    """
    tools = [
        ("bash", BASH_SCHEMA, _exec_bash),
        ("write_file", WRITE_FILE_SCHEMA, _exec_write_file),
        ("read_file", READ_FILE_SCHEMA, _exec_read_file),
        ("delete_file", DELETE_FILE_SCHEMA, _exec_delete_file),
        ("run_python", RUN_PYTHON_SCHEMA, _exec_run_python),
        ("submit_result", SUBMIT_RESULT_SCHEMA, lambda tool_input, **_: ""),  # handled by _agentic_loop
    ]

    if include_browser:
        tools.extend([
            ("browse_webpage", BROWSE_WEBPAGE_SCHEMA, _exec_browse_webpage),
            ("google_search", GOOGLE_SEARCH_SCHEMA, _exec_google_search),
        ])

    return tools
