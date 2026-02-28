"""
Ideation Agent - 文献综述与假设生成

Pipeline 第一阶段：扫描论文、分析文献、识别研究缺口、生成假设。
"""

# INPUT:  agents.base_agent (BaseAgent), core.state, tools.paper_fetcher,
#         tools.file_manager, tools.smart_literature_access
# OUTPUT: IdeationAgent 类
# POSITION: Agent层 - 文献智能体，Pipeline 第一阶段

from typing import List, Dict
from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState, PaperMetadata
from tools.paper_fetcher import PaperFetcher
from tools.file_manager import FileManager
from tools.smart_literature_access import get_literature_access_manager


class IdeationAgent(BaseAgent):
    """文献综述与假设生成 Agent。"""

    def __init__(self, llm: Anthropic, paper_fetcher: PaperFetcher, file_manager: FileManager):
        super().__init__(llm, file_manager, "ideation", paper_fetcher=paper_fetcher)
        self.literature_access = get_literature_access_manager()

    def _execute(self, state: ResearchState) -> ResearchState:
        self.logger.info(f"Research direction: {state['research_direction']}")

        # 查询知识图谱
        related_knowledge = self.knowledge_graph.search_knowledge(
            query=state["research_direction"], node_type=None
        )
        if related_knowledge:
            self.logger.info(f"Found {len(related_knowledge)} related concepts in knowledge graph")
            for k in related_knowledge[:3]:
                self.logger.info(f"  - {k['name']}: {k['description'][:80]}...")

        # Step 1: 扫描论文
        papers = self.scan_papers(state["research_direction"])
        state["papers_reviewed"] = papers
        self.logger.info(f"Found {len(papers)} relevant papers")

        self.save_artifact(
            content={"papers": papers},
            project_id=state["project_id"],
            filename="papers_analyzed.json",
            subdir="literature",
        )

        # Step 2: 分析文献
        literature_summary = self.analyze_literature(papers, state["research_direction"])
        state["literature_summary"] = literature_summary
        self.logger.info("Completed literature analysis")

        self.save_artifact(
            content=literature_summary,
            project_id=state["project_id"],
            filename="literature_summary.md",
            subdir="literature",
        )

        # Step 3: 识别研究缺口
        research_gaps = self.identify_research_gaps(literature_summary, papers)
        state["research_gaps"] = research_gaps
        self.logger.info(f"Identified {len(research_gaps)} research gaps")

        # Step 4: 生成假设
        hypothesis = self.generate_hypothesis(
            research_gaps, literature_summary, state["research_direction"]
        )
        state["hypothesis"] = hypothesis
        self.logger.info(f"Generated research hypothesis")
        self.logger.info(f"Hypothesis: {hypothesis[:200]}...")

        hypothesis_content = (
            f"# Research Hypothesis\n\n{hypothesis}\n\n"
            f"## Research Gaps\n\n" +
            "\n".join(f"- {gap}" for gap in research_gaps)
        )
        self.save_artifact(
            content=hypothesis_content,
            project_id=state["project_id"],
            filename="hypothesis.md",
            subdir="literature",
        )

        # 更新知识图谱
        if research_gaps:
            findings = [f"Research gap: {gap}" for gap in research_gaps[:3]]
            self.knowledge_graph.update_knowledge_from_research(
                project_id=state["project_id"], findings=findings, llm=self.llm
            )

        return state

    def _generate_execution_summary(self, state: ResearchState) -> Dict:
        papers = state.get("papers_reviewed", [])
        research_gaps = state.get("research_gaps", [])
        hypothesis = state.get("hypothesis", "")
        literature_summary = state.get("literature_summary", "")

        return {
            "log": f"Literature Review: {len(papers)} papers, {len(research_gaps)} gaps, hypothesis={'Yes' if hypothesis else 'No'}",
            "learnings": [
                f"Analyzed {len(papers)} papers on {state['research_direction']}",
                f"Identified {len(research_gaps)} research gaps",
            ],
            "mistakes": [],
            "reflection": f"Literature scan retrieved {len(papers)} papers, gap analysis identified {len(research_gaps)} opportunities",
        }

    def scan_papers(self, research_direction: str) -> List[PaperMetadata]:
        """扫描并获取相关论文。"""
        categories = self.config.get("focus_categories", [])
        keywords = self.config.get("keywords", [])

        recent_papers = self.paper_fetcher.fetch_recent_papers(
            categories=categories, days_back=7
        )
        keyword_papers = self.paper_fetcher.fetch_papers_by_keywords(
            keywords=[research_direction] + keywords[:5],
            categories=categories, max_results=30,
        )

        # 去重
        all_papers = recent_papers + keyword_papers
        seen_ids = set()
        unique_papers = []
        for paper in all_papers:
            if paper["arxiv_id"] not in seen_ids:
                seen_ids.add(paper["arxiv_id"])
                unique_papers.append(paper)

        relevant_papers = self.paper_fetcher.filter_papers_by_relevance(
            unique_papers, keywords=[research_direction] + keywords, min_score=0.2
        )
        return relevant_papers[:self.config.get("max_papers_per_scan", 50)]

    def analyze_literature(self, papers: List[PaperMetadata], research_direction: str) -> str:
        """分析论文并生成文献综述。"""
        paper_texts = []
        for i, paper in enumerate(papers[:20], 1):
            paper_texts.append(
                f"{i}. **{paper['title']}** ({paper['published'][:10]})\n"
                f"   Authors: {', '.join(paper['authors'][:3])}\n"
                f"   Abstract: {paper['abstract'][:300]}...\n"
            )

        prompt = f"""Analyze the following recent papers related to "{research_direction}" and provide a comprehensive literature review.

Papers to analyze:
{chr(10).join(paper_texts)}

Please provide:
1. **Overall Trends**: What are the main themes and trends in this research area?
2. **Key Methodologies**: What methods and approaches are researchers using?
3. **Important Findings**: What are the most significant results or insights?
4. **Emerging Directions**: What new directions are emerging in this field?
5. **Connections**: How do these papers relate to each other?

Write a detailed literature review (800-1000 words) that synthesizes these papers."""

        return self.call_llm(prompt=prompt, max_tokens=4000, temperature=self.config.get("temperature", 0.7))

    def identify_research_gaps(self, literature_summary: str, papers: List[PaperMetadata]) -> List[str]:
        """识别研究缺口。"""
        prompt = f"""Based on the following literature review, identify specific research gaps and opportunities in quantitative finance.

Literature Review:
{literature_summary}

Please identify 5-7 specific research gaps or opportunities. For each gap:
- Be concrete and specific
- Explain why it's important
- Suggest how it could be addressed

Format each gap as a single paragraph (2-3 sentences).

Output as JSON array of strings."""

        try:
            response = self.call_llm(prompt=prompt, max_tokens=2000,
                                     temperature=self.config.get("temperature", 0.7),
                                     response_format="json")
            if isinstance(response, list):
                return response
            return []
        except Exception as e:
            self.logger.warning(f"JSON parsing failed, using text fallback: {e}")
            text_response = self.call_llm(prompt=prompt, max_tokens=2000,
                                          temperature=self.config.get("temperature", 0.7))
            lines = [line.strip() for line in text_response.split("\n") if line.strip()]
            return [line for line in lines if len(line) > 50][:7]

    def generate_hypothesis(self, research_gaps: List[str], literature_summary: str, research_direction: str) -> str:
        """生成可测试的研究假设。"""
        gaps_text = "\n".join(f"- {gap}" for gap in research_gaps)

        prompt = f"""Based on the identified research gaps, generate a specific, testable research hypothesis that can be validated through backtesting.

Research Direction: {research_direction}

Research Gaps:
{gaps_text}

Literature Context (abbreviated):
{literature_summary[:1000]}...

Generate a research hypothesis that:
1. Addresses one or more of the identified gaps
2. Can be tested using historical financial data
3. Is specific and measurable
4. Has practical implications for quantitative trading
5. Can be implemented and validated within reasonable computational constraints

Format your response as:
**Hypothesis**: [One clear sentence stating the hypothesis]

**Rationale**: [2-3 paragraphs explaining why this hypothesis is interesting and testable]

**Expected Contribution**: [What this research would add to the field]

**Testability**: [How this can be validated through backtesting]"""

        return self.call_llm(prompt=prompt, max_tokens=2000, temperature=self.config.get("temperature", 0.7))
