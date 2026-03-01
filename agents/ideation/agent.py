"""
IdeationAgent — Agentic Tool-Use 文献分析与假设生成引擎

Pipeline 第一阶段：LLM 拥有论文搜索、PDF 阅读、知识图谱查询、浏览器等工具，
通过多轮 tool_use 循环自主完成文献综述、研究缺口识别和假设生成。
"""

# INPUT:  agents.base_agent (BaseAgent), core.state (ResearchState),
#         tools.paper_fetcher, tools.file_manager, tools.pdf_reader,
#         core.document_memory_manager,
#         agents.ideation.tools (get_tool_definitions),
#         agents.ideation.prompts (SYSTEM_PROMPT_TEMPLATE, build_task_prompt),
#         agents.browser_manager (BrowserManager, is_playwright_available)
# OUTPUT: IdeationAgent 类
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
        """映射 submit_result 结果到 state。"""
        # papers_reviewed
        papers = results.get("papers_reviewed", [])
        state["papers_reviewed"] = papers

        # literature_summary
        state["literature_summary"] = results.get("literature_summary", "")

        # research_gaps
        gaps_raw = results.get("research_gaps", [])
        state["research_gaps"] = [
            g.get("description", str(g)) if isinstance(g, dict) else str(g)
            for g in gaps_raw
        ]

        # hypothesis
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
            # 保存论文列表
            papers = state.get("papers_reviewed", [])
            self.logger.info(f"Reviewed {len(papers)} papers")
            self.save_artifact(
                content={"papers": papers},
                project_id=project_id,
                filename="papers_analyzed.json",
                subdir="literature",
            )

            # 保存文献综述
            lit_summary = state.get("literature_summary", "")
            self.save_artifact(
                content=lit_summary,
                project_id=project_id,
                filename="literature_summary.md",
                subdir="literature",
            )

            # 保存研究缺口
            gaps_raw = submitted_results.get("research_gaps", [])
            self.save_artifact(
                content=gaps_raw,
                project_id=project_id,
                filename="research_gaps.json",
                subdir="literature",
            )

            # 保存假设
            hypothesis_content = state.get("hypothesis", "")
            gaps_text = "\n".join(
                f"- {g.get('description', str(g))}" if isinstance(g, dict) else f"- {g}"
                for g in gaps_raw
            )
            self.save_artifact(
                content=f"# Research Hypothesis\n\n{hypothesis_content}\n\n## Research Gaps\n\n{gaps_text}",
                project_id=project_id,
                filename="hypothesis.md",
                subdir="literature",
            )

            # 保存完整综合结果
            self.save_artifact(
                content=submitted_results,
                project_id=project_id,
                filename="research_synthesis.json",
                subdir="literature",
            )

            self.logger.info("Generated research hypothesis")
            self.logger.info(f"Hypothesis: {state.get('hypothesis', '')[:200]}...")

            # 更新知识图谱
            research_gaps = state.get("research_gaps", [])
            if research_gaps:
                findings = [f"Research gap: {g}" for g in research_gaps[:3]]
                self.knowledge_graph.update_knowledge_from_research(
                    project_id=project_id, findings=findings, llm=self.llm
                )
        else:
            self.logger.warning("Agentic loop ended without submitting results")
            # 设置空默认值避免下游失败
            state.setdefault("papers_reviewed", [])
            state.setdefault("literature_summary", "")
            state.setdefault("research_gaps", [])
            state.setdefault("hypothesis", "No hypothesis generated")

        # 保存执行日志
        self.save_artifact(execution_log, project_id, "execution_logs.txt", "literature")

        return state

    # ==================================================================
    # 辅助方法
    # ==================================================================

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
        papers = state.get("papers_reviewed", [])
        research_gaps = state.get("research_gaps", [])
        hypothesis = state.get("hypothesis", "")

        return {
            "log": (
                f"Literature Review: {len(papers)} papers reviewed, "
                f"{len(research_gaps)} gaps, hypothesis={'Yes' if hypothesis else 'No'}"
            ),
            "learnings": [
                f"Analyzed {len(papers)} papers on {state['research_direction']}",
                f"Identified {len(research_gaps)} research gaps",
            ],
            "mistakes": [],
            "reflection": (
                f"Agentic literature review: {len(papers)} papers, "
                f"{len(research_gaps)} gaps identified"
            ),
        }
