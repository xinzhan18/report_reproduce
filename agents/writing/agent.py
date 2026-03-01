"""
WritingAgent — Agentic Tool-Use 研究报告生成引擎

Pipeline 第四阶段：LLM 拥有上游文件读取、报告写入、Python 可视化、浏览器等工具，
通过多轮 tool_use 循环自主完成报告生成。
"""

# INPUT:  agents.base_agent (BaseAgent), core.state (ResearchState),
#         tools.file_manager (FileManager),
#         agents.writing.tools (get_tool_definitions),
#         agents.writing.prompts (SYSTEM_PROMPT_TEMPLATE, build_task_prompt),
#         agents.browser_manager (BrowserManager, is_playwright_available),
#         datetime, json
# OUTPUT: WritingAgent 类
# POSITION: Agent层 - 写作智能体，Pipeline 第四阶段
#           通过 BaseAgent._agentic_loop() 驱动的 Agentic Tool-Use 引擎

from typing import Dict, Any
import json
import logging
from datetime import datetime

from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState
from tools.file_manager import FileManager
from agents.writing.tools import get_tool_definitions
from agents.writing.prompts import SYSTEM_PROMPT_TEMPLATE, build_task_prompt
from agents.browser_manager import BrowserManager, is_playwright_available

logger = logging.getLogger("agents.writing")


class WritingAgent(BaseAgent):
    """Agentic Tool-Use 研究报告生成引擎。"""

    def __init__(self, llm: Anthropic, file_manager: FileManager):
        super().__init__(llm, file_manager, "writing")

    # ==================================================================
    # Agentic 钩子
    # ==================================================================

    def _register_tools(self, state: ResearchState):
        """注册写作工具 + 浏览器工具到 ToolRegistry。"""
        include_browser = is_playwright_available()
        tool_defs = get_tool_definitions(
            include_browser=include_browser,
            include_python=False,  # 默认不启用 Python，需要 sandbox
        )
        self.tool_registry.register_many(tool_defs)
        self.logger.info(f"Registered {len(tool_defs)} tools: {self.tool_registry.get_tool_names()}")

    def _build_tool_system_prompt(self, state: ResearchState) -> str:
        """构建 writing system prompt。"""
        agent_memory = self._system_prompt
        return SYSTEM_PROMPT_TEMPLATE.format(agent_memory=agent_memory)

    def _build_task_prompt(self, state: ResearchState) -> str:
        """构建 writing task prompt。"""
        state_summary = self._build_state_summary(state)
        return build_task_prompt(state_summary=state_summary)

    def _on_submit_result(self, results: dict, state: ResearchState):
        """映射 submit_result 结果到 state。"""
        state["report_draft"] = results.get("report_draft", "")
        state["final_report"] = results.get("final_report", results.get("report_draft", ""))

    # ==================================================================
    # 主流程
    # ==================================================================

    def _execute(self, state: ResearchState) -> ResearchState:
        project_id = state["project_id"]
        self.logger.info("Starting report generation...")

        # 构建 tool context
        browser = BrowserManager.get_instance() if is_playwright_available() else None

        # 运行 agentic loop
        submitted_results, execution_log = self._agentic_loop(
            state=state,
            file_manager=self.file_manager,
            project_id=project_id,
            browser=browser,
        )

        if submitted_results:
            report_draft = state.get("report_draft", "")
            final_report = state.get("final_report", "")
            self.logger.info(f"Report completed ({len(final_report)} characters)")

            # 保存报告
            self.save_artifact(
                content=final_report,
                project_id=project_id,
                filename="final_report.md",
                subdir="reports",
            )

            # 添加目录版本
            formatted = self._add_table_of_contents(final_report)
            self.save_artifact(
                content=formatted,
                project_id=project_id,
                filename="final_report_formatted.md",
                subdir="reports",
            )
        else:
            self.logger.warning("Agentic loop ended without submitting results")
            state.setdefault("report_draft", "")
            state.setdefault("final_report", "")

        # 保存执行日志
        self.save_artifact(execution_log, project_id, "execution_logs.txt", "reports")

        state["requires_human_review"] = True
        state["status"] = "completed"
        return state

    # ==================================================================
    # 辅助方法
    # ==================================================================

    def _build_state_summary(self, state: ResearchState) -> str:
        """构建 state 摘要，供 task prompt 使用。"""
        parts = [
            f"**Project ID**: {state['project_id']}",
            f"**Research Direction**: {state['research_direction']}",
            f"**Hypothesis**: {state['hypothesis'][:500]}",
        ]

        # 结果摘要
        rd = state.get("results_data")
        if rd:
            parts.append(f"**Validation Status**: {state.get('validation_status', 'N/A')}")
            parts.append(f"**Key Metrics**: Sharpe={rd.get('sharpe_ratio', 0):.2f}, "
                         f"Return={rd.get('total_return', 0)*100:.1f}%, "
                         f"MaxDD={rd.get('max_drawdown', 0)*100:.1f}%, "
                         f"Trades={rd.get('total_trades', 0)}")

        # 论文数
        papers = state.get("papers_reviewed", [])
        if papers:
            parts.append(f"**Papers Reviewed**: {len(papers)}")

        # 研究缺口
        gaps = state.get("research_gaps", [])
        if gaps:
            parts.append(f"**Research Gaps**: {len(gaps)} identified")

        return "\n".join(parts)

    def _add_table_of_contents(self, markdown: str) -> str:
        """为报告添加目录。"""
        toc = "\n## Table of Contents\n\n"
        lines = markdown.split("\n")
        for line in lines:
            if line.startswith("## ") and "Table of Contents" not in line:
                section = line.replace("## ", "")
                anchor = section.lower().replace(" ", "-")
                toc += f"- [{section}](#{anchor})\n"

        parts = markdown.split("---", 1)
        if len(parts) == 2:
            return parts[0] + toc + "\n---" + parts[1]
        return markdown

    def _generate_execution_summary(self, state: ResearchState) -> Dict[str, Any]:
        report_draft = state.get("report_draft", "")
        final_report = state.get("final_report", "")
        return {
            "log": f"Report: draft={len(report_draft)} chars, final={len(final_report)} chars",
            "learnings": [f"Generated research report ({len(final_report)} characters)"],
            "mistakes": [],
            "reflection": "Agentic report generation integrates findings from all previous agents",
        }
