"""
IdeationAgent — Agentic Tool-Use 文献分析与假设生成引擎

Pipeline 第一阶段：LLM 拥有论文搜索、PDF 阅读、知识图谱查询、浏览器等工具，
通过多轮 tool_use 循环自主完成文献综述、研究缺口识别和假设生成。
输出统一的 ideation.md 供下游 PlanningAgent 读取。
"""

# INPUT:  agents.base_agent (BaseAgent), core.state (ResearchState),
#         tools.paper_fetcher, tools.file_manager, tools.pdf_reader,
#         agents.ideation.tools (get_tool_definitions),
#         agents.ideation.prompts (SYSTEM_PROMPT_TEMPLATE, build_task_prompt),
#         agents.browser_manager (BrowserManager, is_playwright_available)
# OUTPUT: IdeationAgent 类
#         产出文件: literature/ideation.md (核心), literature/papers_analyzed.json (辅助),
#                  literature/research_synthesis.json (辅助)
# POSITION: Agent层 - 文献智能体，Pipeline 第一阶段
#           通过 BaseAgent._agentic_loop() 驱动的 Agentic Tool-Use 引擎

from typing import Dict, Any
import json
import logging

from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState
from tools.paper_fetcher import PaperFetcher
from tools.file_manager import FileManager
from agents.ideation.tools import get_tool_definitions
from agents.ideation.prompts import SYSTEM_PROMPT_TEMPLATE, build_task_prompt
from agents.browser_manager import BrowserManager, is_playwright_available

logger = logging.getLogger("agents.ideation")


class IdeationAgent(BaseAgent):
    """Agentic Tool-Use 文献分析与假设生成引擎。"""

    def __init__(
        self, llm: Anthropic, paper_fetcher: PaperFetcher, file_manager: FileManager,
        **kwargs,
    ):
        super().__init__(llm, file_manager, "ideation", paper_fetcher=paper_fetcher, **kwargs)

    # ==================================================================
    # Agentic 钩子
    # ==================================================================

    def _register_tools(self, state: ResearchState):
        """注册文献工具 + 浏览器工具到 ToolRegistry。"""
        include_browser = is_playwright_available()
        tool_defs = get_tool_definitions(include_browser=include_browser)
        self.tool_registry.register_many(tool_defs)
        self.logger.info(f"Registered {len(tool_defs)} tools: {self.tool_registry.get_tool_names()}")

    def _build_tool_system_prompt(self, state: ResearchState) -> str:
        """构建 ideation system prompt。"""
        agent_memory = self._system_prompt
        return SYSTEM_PROMPT_TEMPLATE.format(agent_memory=agent_memory)

    def _build_task_prompt(self, state: ResearchState) -> str:
        """构建 ideation task prompt。"""
        kg_context = self._build_kg_context(state["research_direction"])
        return build_task_prompt(
            research_direction=state["research_direction"],
            kg_context=kg_context,
        )

    def _on_submit_result(self, results: dict, state: ResearchState):
        """映射 submit_result 结果到 state — 只写 hypothesis。"""
        hyp = results.get("hypothesis", {})
        if isinstance(hyp, dict):
            hypothesis_text = (
                f"**Hypothesis**: {hyp.get('statement', '')}\n\n"
                f"**Rationale**: {hyp.get('rationale', '')}\n\n"
                f"**Supporting Evidence**: {chr(10).join('- ' + e for e in hyp.get('supporting_evidence', []))}\n\n"
                f"**Feasibility Score**: {hyp.get('feasibility_score', 0.0)}\n\n"
                f"**Novelty Score**: {hyp.get('novelty_score', 0.0)}"
            )
        else:
            hypothesis_text = str(hyp)
        state["hypothesis"] = hypothesis_text

    # ==================================================================
    # 主流程
    # ==================================================================

    def _execute(self, state: ResearchState) -> ResearchState:
        direction = state["research_direction"]
        project_id = state["project_id"]
        self.logger.info(f"Research direction: {direction}")

        # 构建 tool context
        pdf_reader = getattr(self, "pdf_reader", None)
        browser = BrowserManager.get_instance() if is_playwright_available() else None

        # 运行 agentic loop
        submitted_results, execution_log = self._agentic_loop(
            state=state,
            paper_fetcher=self.paper_fetcher,
            pdf_reader=pdf_reader,
            knowledge_graph=self.knowledge_graph,
            browser=browser,
        )

        # 保存产出物
        if submitted_results:
            self.logger.info("Building ideation.md from submitted results")

            # 构建并保存统一的 ideation.md
            ideation_md = self._build_ideation_markdown(submitted_results, direction)
            self.save_artifact(ideation_md, project_id, "ideation.md", "literature")

            # 保留 JSON 辅助文件（知识图谱、工具读取兼容）
            papers = submitted_results.get("papers_reviewed", [])
            self.save_artifact(
                content={"papers": papers},
                project_id=project_id,
                filename="papers_analyzed.json",
                subdir="literature",
            )

            # 保存完整综合结果
            self.save_artifact(
                content=submitted_results,
                project_id=project_id,
                filename="research_synthesis.json",
                subdir="literature",
            )

            self.logger.info(f"Reviewed {len(papers)} papers")
            self.logger.info(f"Hypothesis: {state.get('hypothesis', '')[:200]}...")

            # 更新知识图谱
            gaps_raw = submitted_results.get("research_gaps", [])
            research_gaps = [
                g.get("description", str(g)) if isinstance(g, dict) else str(g)
                for g in gaps_raw
            ]
            if research_gaps:
                findings = [f"Research gap: {g}" for g in research_gaps[:3]]
                self.knowledge_graph.update_knowledge_from_research(
                    project_id=project_id, findings=findings, llm=self.llm
                )
        else:
            self.logger.warning("Agentic loop ended without submitting results")
            state.setdefault("hypothesis", "No hypothesis generated")

        # 保存执行日志
        self.save_artifact(execution_log, project_id, "execution_logs.txt", "literature")

        return state

    # ==================================================================
    # 辅助方法
    # ==================================================================

    def _build_ideation_markdown(self, results: dict, research_direction: str) -> str:
        """构建统一的 ideation.md 文档。"""
        parts = [f"# Literature Review: {research_direction}\n"]

        # Papers Reviewed 表格
        papers = results.get("papers_reviewed", [])
        if papers:
            parts.append("## Papers Reviewed")
            parts.append("| # | Title | Authors | Key Findings | Relevance |")
            parts.append("|---|-------|---------|-------------|-----------|")
            for i, p in enumerate(papers, 1):
                if isinstance(p, dict):
                    title = p.get("title", "N/A")
                    authors = ", ".join(p.get("authors", [])[:3])
                    if len(p.get("authors", [])) > 3:
                        authors += " et al."
                    findings = p.get("abstract", "")[:100]
                    relevance = p.get("relevance_score", "N/A")
                else:
                    title = str(p)
                    authors = "N/A"
                    findings = ""
                    relevance = "N/A"
                parts.append(f"| {i} | {title} | {authors} | {findings} | {relevance} |")
            parts.append("")

        # Key Methodologies
        lit_summary = results.get("literature_summary", "")
        if lit_summary:
            parts.append("## Key Methodologies")
            parts.append(lit_summary)
            parts.append("")

        # Research Gaps
        gaps_raw = results.get("research_gaps", [])
        if gaps_raw:
            parts.append("## Research Gaps")
            for i, g in enumerate(gaps_raw, 1):
                if isinstance(g, dict):
                    desc = g.get("description", str(g))
                else:
                    desc = str(g)
                parts.append(f"{i}. {desc}")
            parts.append("")

        # Hypothesis
        hyp = results.get("hypothesis", {})
        if hyp:
            parts.append("## Hypothesis")
            if isinstance(hyp, dict):
                parts.append(f"**Statement**: {hyp.get('statement', '')}")
                parts.append(f"**Rationale**: {hyp.get('rationale', '')}")
                evidence = hyp.get("supporting_evidence", [])
                if evidence:
                    parts.append("**Supporting Evidence**:")
                    for e in evidence:
                        parts.append(f"- {e}")
                parts.append(f"**Feasibility Score**: {hyp.get('feasibility_score', 0.0)}")
                parts.append(f"**Novelty Score**: {hyp.get('novelty_score', 0.0)}")
            else:
                parts.append(str(hyp))
            parts.append("")

        return "\n".join(parts)

    def _build_kg_context(self, research_direction: str) -> str:
        """查询知识图谱并格式化为 prompt 可注入的上下文段落。"""
        related = self.knowledge_graph.search_knowledge(
            query=research_direction, node_type=None
        )
        if not related:
            return ""

        self.logger.info(f"Found {len(related)} related concepts in knowledge graph")
        lines = ["## Prior Knowledge (from knowledge graph):"]
        for k in related[:5]:
            lines.append(f"- **{k['name']}**: {k['description'][:150]}")
        return "\n".join(lines) + "\n"

    def _generate_execution_summary(self, state: ResearchState) -> Dict:
        hypothesis = state.get("hypothesis", "")

        return {
            "log": (
                f"Literature Review: hypothesis={'Yes' if hypothesis else 'No'}"
            ),
            "learnings": [
                f"Analyzed papers on {state['research_direction']}",
            ],
            "mistakes": [],
            "reflection": "Agentic literature review completed",
        }
