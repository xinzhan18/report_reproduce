"""
ToolRegistry — Agent 工具注册中心

每个 Agent 实例持有独立的 ToolRegistry，管理工具 schema 和 executor。
"""

# INPUT:  logging
# OUTPUT: ToolRegistry 类
# POSITION: Agent层 - 工具注册中心，管理 Anthropic API 格式的工具 schema 和执行器

import logging
from typing import Callable, Any

logger = logging.getLogger("agents.tool_registry")


class ToolRegistry:
    """工具注册中心。管理 Anthropic API 格式的 tool schema 和 executor。"""

    def __init__(self):
        self._schemas: dict[str, dict] = {}
        self._executors: dict[str, Callable] = {}

    def register(self, name: str, schema: dict, executor: Callable) -> "ToolRegistry":
        """注册单个工具。

        Args:
            name: 工具名称
            schema: Anthropic API tool 格式 {name, description, input_schema}
            executor: (tool_input: dict, **context) -> str
        """
        self._schemas[name] = schema
        self._executors[name] = executor
        return self

    def register_many(self, tools: list[tuple[str, dict, Callable]]) -> "ToolRegistry":
        """批量注册工具。

        Args:
            tools: [(name, schema, executor), ...]
        """
        for name, schema, executor in tools:
            self.register(name, schema, executor)
        return self

    def get_schemas(self) -> list[dict]:
        """返回 Anthropic API 格式的 tool schema 列表。"""
        return list(self._schemas.values())

    def execute(self, name: str, tool_input: dict, **context) -> str:
        """执行工具，返回结果字符串。

        Args:
            name: 工具名称
            tool_input: 工具输入参数
            **context: 运行时上下文 (sandbox, paper_fetcher 等)
        """
        executor = self._executors.get(name)
        if executor is None:
            return f"[ERROR] Unknown tool: {name}"
        try:
            return executor(tool_input, **context)
        except Exception as e:
            logger.error(f"Tool '{name}' execution failed: {e}")
            return f"[ERROR] Tool '{name}' failed: {e}"

    def get_tool_names(self) -> list[str]:
        """返回已注册的工具名称列表。"""
        return list(self._schemas.keys())

    def has_tool(self, name: str) -> bool:
        """检查工具是否已注册。"""
        return name in self._schemas
