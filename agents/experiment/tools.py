"""
Tool 定义与分发 — Anthropic tool_use API 格式

6 个工具：bash, write_file, read_file, delete_file, run_python, submit_result。
"""

# INPUT:  agents.experiment.sandbox (SandboxManager)
# OUTPUT: TOOL_SCHEMAS list, execute_tool() 函数
# POSITION: agents/experiment 子包 - 工具 schema + dispatch

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.experiment.sandbox import SandboxManager

# ======================================================================
# Anthropic API tool schema 定义
# ======================================================================

TOOL_SCHEMAS = [
    {
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
    },
    {
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
    },
    {
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
    },
    {
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
    },
    {
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
    },
    {
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
    },
]


def execute_tool(name: str, tool_input: dict, sandbox: "SandboxManager", timeout: int = 300) -> str:
    """分发工具调用，返回结果字符串。

    注意：submit_result 不在这里处理，由 agentic loop 直接截获。
    """
    if name == "bash":
        result = sandbox.run_command(tool_input["command"], timeout=timeout)
        parts = []
        if result["stdout"]:
            parts.append(f"stdout:\n{result['stdout']}")
        if result["stderr"]:
            parts.append(f"stderr:\n{result['stderr']}")
        parts.append(f"exit_code: {result['returncode']}")
        return "\n".join(parts)

    elif name == "write_file":
        return sandbox.write_file(tool_input["path"], tool_input["content"])

    elif name == "read_file":
        return sandbox.read_file(tool_input["path"])

    elif name == "delete_file":
        return sandbox.delete_file(tool_input["path"])

    elif name == "run_python":
        result = sandbox.run_python(tool_input["script_path"], timeout=timeout)
        parts = []
        if result["stdout"]:
            parts.append(f"stdout:\n{result['stdout']}")
        if result["stderr"]:
            parts.append(f"stderr:\n{result['stderr']}")
        parts.append(f"exit_code: {result['returncode']}")
        return "\n".join(parts)

    else:
        return f"[ERROR] Unknown tool: {name}"
