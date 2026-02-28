"""
Ideation Agent - 三阶段深度文献分析与假设生成

Pipeline 第一阶段：
  Stage 1: 扫描论文 + LLM 排序 → RankedPaper
  Stage 2: PDF 深度阅读 + 缓存 → StructuredInsights
  Stage 3: 跨论文综合 → ResearchSynthesis → ResearchGap → Hypothesis
"""

# INPUT:  agents.base_agent (BaseAgent), core.state (ResearchState, RankedPaper,
#         StructuredInsights, ResearchGap, Hypothesis, ResearchSynthesis),
#         tools.paper_fetcher, tools.file_manager, tools.pdf_reader,
#         core.document_memory_manager
# OUTPUT: IdeationAgent 类
# POSITION: Agent层 - 文献智能体，Pipeline 第一阶段

from typing import List, Dict
from dataclasses import asdict
from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import (
    ResearchState, PaperMetadata,
    RankedPaper, StructuredInsights,
    ResearchGap, Hypothesis, ResearchSynthesis,
)
from tools.paper_fetcher import PaperFetcher
from tools.file_manager import FileManager
from tools.pdf_reader import PDFReader
from core.document_memory_manager import get_document_memory_manager


class IdeationAgent(BaseAgent):
    """三阶段深度文献分析与假设生成 Agent。"""

    def __init__(
        self, llm: Anthropic, paper_fetcher: PaperFetcher, file_manager: FileManager,
        **kwargs,
    ):
        super().__init__(llm, file_manager, "ideation", paper_fetcher=paper_fetcher, **kwargs)
        self.doc_memory = get_document_memory_manager()

    # ==================================================================
    # 主流程
    # ==================================================================

    def _execute(self, state: ResearchState) -> ResearchState:
        direction = state["research_direction"]
        project_id = state["project_id"]
        self.logger.info(f"Research direction: {direction}")

        # 构建知识图谱上下文（注入后续所有 prompt）
        kg_context = self._build_kg_context(direction)

        # ---- Stage 1: 扫描 + 排序 ----
        papers = self.scan_papers(direction)
        state["papers_reviewed"] = papers
        self.logger.info(f"Found {len(papers)} relevant papers")

        self.save_artifact(
            content={"papers": papers},
            project_id=project_id,
            filename="papers_analyzed.json",
            subdir="literature",
        )

        ranked = self.rank_papers(papers, direction, kg_context)
        self.save_artifact(
            content=[asdict(r) for r in ranked],
            project_id=project_id,
            filename="ranked_papers.json",
            subdir="literature",
        )

        # ---- Stage 2: 深度阅读 ----
        deep_papers = [r for r in ranked if r.should_analyze_deep]
        insights = self.deep_analyze_papers(deep_papers)
        self.save_artifact(
            content=[asdict(ins) for ins in insights],
            project_id=project_id,
            filename="structured_insights.json",
            subdir="literature",
        )

        # 未深度分析的论文摘要（供 Stage 3 综合用）
        deep_ids = {ins.paper_id for ins in insights}
        shallow_papers = [r.paper for r in ranked if r.paper["arxiv_id"] not in deep_ids]

        # ---- Stage 3: 跨论文综合 ----
        synthesis = self.synthesize_literature(insights, shallow_papers, direction, kg_context)
        state["literature_summary"] = synthesis.literature_summary
        self.logger.info("Completed literature synthesis")

        self.save_artifact(
            content=synthesis.literature_summary,
            project_id=project_id,
            filename="literature_summary.md",
            subdir="literature",
        )
        self.save_artifact(
            content=asdict(synthesis),
            project_id=project_id,
            filename="research_synthesis.json",
            subdir="literature",
        )

        # 识别研究缺口
        gaps = self.identify_research_gaps(synthesis, insights)
        state["research_gaps"] = [g.description for g in gaps]
        self.logger.info(f"Identified {len(gaps)} research gaps")

        # 生成假设
        hyp = self.generate_hypothesis(gaps, synthesis, direction, kg_context)
        hypothesis_text = (
            f"**Hypothesis**: {hyp.statement}\n\n"
            f"**Rationale**: {hyp.rationale}\n\n"
            f"**Supporting Evidence**: {chr(10).join('- ' + e for e in hyp.supporting_evidence)}\n\n"
            f"**Feasibility Score**: {hyp.feasibility_score}\n\n"
            f"**Novelty Score**: {hyp.novelty_score}"
        )
        state["hypothesis"] = hypothesis_text
        self.logger.info("Generated research hypothesis")
        self.logger.info(f"Hypothesis: {hyp.statement[:200]}...")

        hypothesis_content = (
            f"# Research Hypothesis\n\n{hypothesis_text}\n\n"
            f"## Research Gaps\n\n"
            + "\n".join(
                f"- [{g.severity}] {g.description} (score: {g.opportunity_score})"
                for g in gaps
            )
        )
        self.save_artifact(
            content=hypothesis_content,
            project_id=project_id,
            filename="hypothesis.md",
            subdir="literature",
        )

        # 更新知识图谱
        if gaps:
            findings = [f"Research gap: {g.description}" for g in gaps[:3]]
            self.knowledge_graph.update_knowledge_from_research(
                project_id=project_id, findings=findings, llm=self.llm
            )

        return state

    def _generate_execution_summary(self, state: ResearchState) -> Dict:
        papers = state.get("papers_reviewed", [])
        research_gaps = state.get("research_gaps", [])
        hypothesis = state.get("hypothesis", "")

        return {
            "log": (
                f"Literature Review: {len(papers)} papers scanned, "
                f"{len(research_gaps)} gaps, hypothesis={'Yes' if hypothesis else 'No'}"
            ),
            "learnings": [
                f"Analyzed {len(papers)} papers on {state['research_direction']}",
                f"Identified {len(research_gaps)} research gaps",
            ],
            "mistakes": [],
            "reflection": (
                f"Three-stage pipeline: scanned {len(papers)} papers, "
                f"gap analysis identified {len(research_gaps)} opportunities"
            ),
        }

    # ==================================================================
    # Stage 1: 扫描 + 排序
    # ==================================================================

    def scan_papers(self, research_direction: str) -> List[PaperMetadata]:
        """扫描并获取相关论文。"""
        categories = self.config.get("focus_categories", [])
        keywords = self.config.get("keywords", [])

        recent_papers = self.paper_fetcher.fetch_recent_papers(
            categories=categories, days_back=7
        )
        keyword_papers = self.paper_fetcher.fetch_papers_by_keywords(
            keywords=[research_direction] + keywords[:5],
            categories=categories,
            max_results=30,
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
        return relevant_papers[: self.config.get("max_papers_per_scan", 50)]

    def rank_papers(
        self, papers: List[PaperMetadata], research_direction: str, kg_context: str,
    ) -> List[RankedPaper]:
        """LLM 评估论文相关性并排序，选出深度分析候选。"""
        deep_count = self.config.get("deep_analysis_count", 5)

        paper_list = []
        for i, p in enumerate(papers[:30]):
            paper_list.append(
                f"{i}. [{p['arxiv_id']}] {p['title']}\n"
                f"   Authors: {', '.join(p['authors'][:3])}\n"
                f"   Abstract: {p['abstract']}\n"
            )

        prompt = f"""You are a quantitative finance research analyst. Evaluate the following papers for relevance to the research direction: "{research_direction}".

{kg_context}

Papers:
{chr(10).join(paper_list)}

For each paper, provide:
- relevance_score (0.0 to 1.0)
- relevance_reasons (list of strings)
- should_analyze_deep (true for the top {deep_count} most relevant papers)

Output as a JSON array:
[
  {{"index": 0, "relevance_score": 0.85, "relevance_reasons": ["..."], "should_analyze_deep": true}},
  ...
]

Only include papers with relevance_score > 0.3. Output ONLY the JSON array."""

        try:
            result = self.call_llm(
                prompt=prompt,
                max_tokens=4000,
                temperature=0.3,
                response_format="json",
            )
            if not isinstance(result, list):
                raise ValueError("Expected JSON array")

            ranked = []
            for item in result:
                idx = item.get("index", 0)
                if idx < len(papers):
                    ranked.append(RankedPaper(
                        paper=papers[idx],
                        relevance_score=float(item.get("relevance_score", 0.5)),
                        relevance_reasons=item.get("relevance_reasons", []),
                        should_analyze_deep=bool(item.get("should_analyze_deep", False)),
                    ))

            ranked.sort(key=lambda r: r.relevance_score, reverse=True)
            self.logger.info(
                f"Ranked {len(ranked)} papers, "
                f"{sum(1 for r in ranked if r.should_analyze_deep)} selected for deep analysis"
            )
            return ranked

        except Exception as e:
            self.logger.warning(f"Ranking failed ({e}), falling back to top-N selection")
            ranked = []
            for i, p in enumerate(papers[:20]):
                ranked.append(RankedPaper(
                    paper=p,
                    relevance_score=1.0 - i * 0.05,
                    relevance_reasons=["fallback ranking"],
                    should_analyze_deep=i < deep_count,
                ))
            return ranked

    # ==================================================================
    # Stage 2: 深度阅读
    # ==================================================================

    def deep_analyze_paper(self, ranked_paper: RankedPaper) -> StructuredInsights:
        """对单篇论文进行深度分析（PDF 全文 → LLM 提取结构化洞察）。"""
        paper = ranked_paper.paper
        arxiv_id = paper["arxiv_id"]
        fallback = self.config.get("fallback_to_abstract", True)

        # 1. 检查缓存
        cached = self.doc_memory.get_cached_analysis(arxiv_id)
        if cached and cached.get("structured_insights"):
            self.logger.info(f"Using cached analysis for {arxiv_id}")
            si = cached["structured_insights"]
            return StructuredInsights(
                paper_id=arxiv_id,
                title=paper["title"],
                sections=cached.get("sections", {}),
                key_innovations=si.get("key_innovations", []),
                methodology_summary=si.get("methodology_summary", ""),
                performance_metrics=si.get("performance_metrics", {}),
                limitations=si.get("limitations", []),
                research_gaps_mentioned=si.get("research_gaps_mentioned", []),
                innovation_score=si.get("innovation_score", 0.0),
                practical_feasibility=si.get("practical_feasibility", 0.0),
            )

        # 2. 下载 PDF + 提取文本
        sections = {}
        full_text = None
        try:
            pdf_path = self.pdf_reader.download_pdf(arxiv_id, paper.get("pdf_url"))
            if pdf_path:
                full_text = self.pdf_reader.extract_text(pdf_path)
                if full_text:
                    sections = self.pdf_reader.extract_sections(full_text)
        except Exception as e:
            self.logger.warning(f"PDF processing failed for {arxiv_id}: {e}")

        # 3. 降级判断
        if not sections:
            if not fallback:
                self.logger.warning(f"No PDF for {arxiv_id} and fallback disabled, skipping")
                return self._abstract_only_insights(paper)
            self.logger.info(f"Falling back to abstract-only analysis for {arxiv_id}")
            return self._abstract_only_insights(paper)

        # 4. LLM 深度分析
        section_text = ""
        for name, content in sections.items():
            section_text += f"\n### {name.upper()}\n{content}\n"

        prompt = f"""Analyze this quantitative finance paper in depth.

Title: {paper['title']}
Authors: {', '.join(paper['authors'][:5])}

{section_text}

Provide a structured analysis as JSON:
{{
  "key_innovations": ["innovation 1", "innovation 2", ...],
  "methodology_summary": "Detailed description of the methodology...",
  "performance_metrics": {{"metric_name": value, ...}},
  "limitations": ["limitation 1", ...],
  "research_gaps_mentioned": ["gap 1", ...],
  "innovation_score": 0.0-1.0,
  "practical_feasibility": 0.0-1.0
}}

Output ONLY the JSON object."""

        try:
            result = self.call_llm(
                prompt=prompt,
                max_tokens=3000,
                temperature=0.3,
                response_format="json",
            )
            if not isinstance(result, dict):
                raise ValueError("Expected JSON object")

            insights = StructuredInsights(
                paper_id=arxiv_id,
                title=paper["title"],
                sections=sections,
                key_innovations=result.get("key_innovations", []),
                methodology_summary=result.get("methodology_summary", ""),
                performance_metrics=result.get("performance_metrics", {}),
                limitations=result.get("limitations", []),
                research_gaps_mentioned=result.get("research_gaps_mentioned", []),
                innovation_score=float(result.get("innovation_score", 0.0)),
                practical_feasibility=float(result.get("practical_feasibility", 0.0)),
            )

        except Exception as e:
            self.logger.warning(f"Deep analysis LLM call failed for {arxiv_id}: {e}")
            return self._abstract_only_insights(paper)

        # 5. 写缓存
        try:
            self.doc_memory.save_analysis_results(
                arxiv_id=arxiv_id,
                sections=sections,
                structured_insights=asdict(insights),
            )
        except Exception as e:
            self.logger.warning(f"Failed to cache analysis for {arxiv_id}: {e}")

        self.logger.info(f"Deep analysis complete for {arxiv_id}: innovation={insights.innovation_score:.2f}")
        return insights

    def deep_analyze_papers(self, deep_papers: List[RankedPaper]) -> List[StructuredInsights]:
        """批量深度分析论文。"""
        insights = []
        for rp in deep_papers:
            try:
                ins = self.deep_analyze_paper(rp)
                insights.append(ins)
            except Exception as e:
                self.logger.error(f"Failed to analyze {rp.paper['arxiv_id']}: {e}")
        self.logger.info(f"Deep analysis completed: {len(insights)}/{len(deep_papers)} papers")
        return insights

    def _abstract_only_insights(self, paper: PaperMetadata) -> StructuredInsights:
        """PDF 失败时的降级：仅用 abstract 构造精简版 StructuredInsights。"""
        return StructuredInsights(
            paper_id=paper["arxiv_id"],
            title=paper["title"],
            sections={"abstract": paper["abstract"]},
            key_innovations=[],
            methodology_summary=f"(Abstract only) {paper['abstract'][:500]}",
            performance_metrics={},
            limitations=["Full text not available for analysis"],
            research_gaps_mentioned=[],
            innovation_score=0.0,
            practical_feasibility=0.0,
        )

    # ==================================================================
    # Stage 3: 跨论文综合
    # ==================================================================

    def synthesize_literature(
        self,
        insights: List[StructuredInsights],
        shallow_papers: List[PaperMetadata],
        research_direction: str,
        kg_context: str,
    ) -> ResearchSynthesis:
        """跨论文综合分析，生成 ResearchSynthesis。"""
        # 构建深度分析论文摘要
        deep_summaries = []
        for ins in insights:
            deep_summaries.append(
                f"### {ins.title} [{ins.paper_id}]\n"
                f"- Methodology: {ins.methodology_summary[:300]}\n"
                f"- Key innovations: {', '.join(ins.key_innovations[:3])}\n"
                f"- Limitations: {', '.join(ins.limitations[:3])}\n"
                f"- Innovation score: {ins.innovation_score}, Feasibility: {ins.practical_feasibility}\n"
            )

        # 构建浅层论文摘要
        shallow_summaries = []
        for p in shallow_papers[:10]:
            shallow_summaries.append(f"- **{p['title']}**: {p['abstract'][:200]}...")

        prompt = f"""You are synthesizing a literature review on "{research_direction}" in quantitative finance.

{kg_context}

## Deeply Analyzed Papers ({len(insights)} papers):
{chr(10).join(deep_summaries)}

## Additional Papers (abstract only, {len(shallow_papers)} papers):
{chr(10).join(shallow_summaries)}

Provide a comprehensive synthesis as JSON:
{{
  "literature_summary": "A detailed literature review (800-1200 words) synthesizing all papers, covering trends, methodologies, key findings, and emerging directions...",
  "methodology_patterns": ["pattern 1", "pattern 2", ...],
  "performance_trends": ["trend 1", "trend 2", ...],
  "common_limitations": ["limitation 1", "limitation 2", ...]
}}

Output ONLY the JSON object."""

        try:
            result = self.call_llm(
                prompt=prompt,
                max_tokens=5000,
                temperature=self.config.get("temperature", 0.7),
                response_format="json",
            )
            if not isinstance(result, dict):
                raise ValueError("Expected JSON object")

            return ResearchSynthesis(
                literature_summary=result.get("literature_summary", ""),
                methodology_patterns=result.get("methodology_patterns", []),
                performance_trends=result.get("performance_trends", []),
                common_limitations=result.get("common_limitations", []),
            )

        except Exception as e:
            self.logger.warning(f"Synthesis LLM call failed: {e}, using fallback")
            # 降级：拼接摘要作为 literature_summary
            fallback_summary = f"# Literature Review: {research_direction}\n\n"
            for ins in insights:
                fallback_summary += f"## {ins.title}\n{ins.methodology_summary}\n\n"
            return ResearchSynthesis(literature_summary=fallback_summary)

    def identify_research_gaps(
        self, synthesis: ResearchSynthesis, insights: List[StructuredInsights],
    ) -> List[ResearchGap]:
        """基于综合分析识别结构化研究缺口。"""
        # 收集论文提到的 gaps
        paper_gaps = []
        for ins in insights:
            for gap in ins.research_gaps_mentioned:
                paper_gaps.append(f"[{ins.paper_id}] {gap}")

        prompt = f"""Based on the following literature synthesis and paper-level analysis, identify specific research gaps in quantitative finance.

## Literature Synthesis:
{synthesis.literature_summary[:2000]}

## Methodology Patterns:
{chr(10).join('- ' + p for p in synthesis.methodology_patterns[:5])}

## Common Limitations:
{chr(10).join('- ' + l for l in synthesis.common_limitations[:5])}

## Gaps Mentioned by Individual Papers:
{chr(10).join('- ' + g for g in paper_gaps[:10])}

Identify 5-7 research gaps. For each gap, provide evidence referencing specific papers.

Output as a JSON array:
[
  {{
    "description": "Detailed description of the research gap...",
    "severity": "major" or "minor",
    "evidence": ["Paper X shows...", "Paper Y lacks..."],
    "opportunity_score": 0.0-1.0
  }},
  ...
]

Output ONLY the JSON array."""

        try:
            result = self.call_llm(
                prompt=prompt,
                max_tokens=3000,
                temperature=self.config.get("temperature", 0.7),
                response_format="json",
            )
            if not isinstance(result, list):
                raise ValueError("Expected JSON array")

            gaps = []
            for item in result:
                gaps.append(ResearchGap(
                    description=item.get("description", ""),
                    severity=item.get("severity", "minor"),
                    evidence=item.get("evidence", []),
                    opportunity_score=float(item.get("opportunity_score", 0.5)),
                ))
            self.logger.info(f"Identified {len(gaps)} structured research gaps")
            return gaps

        except Exception as e:
            self.logger.warning(f"Gap identification failed: {e}, using fallback")
            # 降级：从 common_limitations 构造
            return [
                ResearchGap(
                    description=lim,
                    severity="minor",
                    evidence=["Identified from literature synthesis"],
                    opportunity_score=0.5,
                )
                for lim in synthesis.common_limitations[:5]
            ]

    def generate_hypothesis(
        self,
        gaps: List[ResearchGap],
        synthesis: ResearchSynthesis,
        research_direction: str,
        kg_context: str,
    ) -> Hypothesis:
        """基于研究缺口生成可回测假设。"""
        gaps_text = "\n".join(
            f"- [{g.severity}, score={g.opportunity_score}] {g.description}\n"
            f"  Evidence: {'; '.join(g.evidence[:2])}"
            for g in gaps
        )

        prompt = f"""Based on the identified research gaps, generate a specific, testable research hypothesis for quantitative finance backtesting.

Research Direction: {research_direction}

{kg_context}

## Research Gaps:
{gaps_text}

## Literature Context:
{synthesis.literature_summary[:1500]}

Generate ONE hypothesis that:
1. Addresses the highest-scoring research gap
2. Can be tested using historical financial data
3. Is specific and measurable
4. Has practical implications for quantitative trading

Output as JSON:
{{
  "statement": "One clear sentence stating the hypothesis",
  "rationale": "2-3 paragraphs explaining why this hypothesis is interesting and testable",
  "supporting_evidence": ["Reference to paper/finding 1", "Reference 2", ...],
  "feasibility_score": 0.0-1.0,
  "novelty_score": 0.0-1.0
}}

Output ONLY the JSON object."""

        try:
            result = self.call_llm(
                prompt=prompt,
                max_tokens=2000,
                temperature=self.config.get("temperature", 0.7),
                response_format="json",
            )
            if not isinstance(result, dict):
                raise ValueError("Expected JSON object")

            return Hypothesis(
                statement=result.get("statement", ""),
                rationale=result.get("rationale", ""),
                supporting_evidence=result.get("supporting_evidence", []),
                feasibility_score=float(result.get("feasibility_score", 0.5)),
                novelty_score=float(result.get("novelty_score", 0.5)),
            )

        except Exception as e:
            self.logger.warning(f"Hypothesis generation failed: {e}, using fallback")
            top_gap = gaps[0] if gaps else ResearchGap(
                description="General research opportunity",
                severity="minor", evidence=[], opportunity_score=0.5,
            )
            return Hypothesis(
                statement=f"Addressing: {top_gap.description}",
                rationale="Hypothesis generated from top research gap identified in literature review.",
                supporting_evidence=top_gap.evidence,
                feasibility_score=0.5,
                novelty_score=0.5,
            )

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
