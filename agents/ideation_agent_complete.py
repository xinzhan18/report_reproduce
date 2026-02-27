"""
Ideation Agent - Complete Implementation with Three-Stage Analysis

包含完整的三阶段深度文献分析：
- Stage 1: Quick Filtering (快速筛选)
- Stage 2: Structured Analysis (结构化分析)
- Stage 3: Deep Understanding (深度理解)
- Cross-Paper Synthesis (综合分析)
"""

from typing import List, Dict
from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import (
    ResearchState, PaperMetadata,
    RankedPaper, StructuredInsights, DeepInsights,
    ResearchGap, Hypothesis, ResearchSynthesis
)
from tools.paper_fetcher import PaperFetcher
from tools.file_manager import FileManager
from tools.smart_literature_access import get_literature_access_manager
from tools.pdf_reader import PDFReader
from agents.utils.prompt_builder import PromptBuilder
from core.document_memory_manager import get_document_memory_manager
import json


class IdeationAgent(BaseAgent):
    """
    Ideation agent with complete three-stage literature analysis.

    Features:
    - Document memory integration
    - Three-stage filtering (50 → 20 → 8 papers)
    - PDF-based deep analysis
    - Evidence-based hypothesis generation
    """

    def __init__(
        self,
        llm: Anthropic,
        paper_fetcher: PaperFetcher,
        file_manager: FileManager
    ):
        """Initialize ideation agent with three-stage analysis."""
        super().__init__(llm, file_manager, agent_name="ideation")

        # Agent-specific tools
        self.paper_fetcher = paper_fetcher
        self.literature_access = get_literature_access_manager()
        self.pdf_reader = PDFReader()
        self.doc_memory = get_document_memory_manager()

        # Configuration
        self.enable_deep_analysis = self.config.get("enable_deep_analysis", True)
        self.analysis_depth = self.config.get("analysis_depth", "deep")  # quick/medium/deep

    def _execute(self, state: ResearchState) -> ResearchState:
        """
        Execute three-stage literature analysis.

        Workflow:
        1. Scan/retrieve papers (from memory + new)
        2. Stage 1: Quick filtering (50 → 15-20 papers)
        3. Stage 2: Structured analysis (20 → insights)
        4. Stage 3: Deep analysis (select 5-8 core papers)
        5. Cross-paper synthesis (generate gaps + hypotheses)
        """
        self.logger.info(f"Research direction: {state['research_direction']}")

        # Consult knowledge graph
        related_knowledge = self.intelligence.knowledge_graph.search_knowledge(
            query=state["research_direction"],
            node_type=None
        )
        if related_knowledge:
            self.logger.info(f"✓ Found {len(related_knowledge)} related concepts in KG")

        # === Step 1: Get papers (memory + new scan) ===
        papers = self.get_papers_with_memory(state["research_direction"], state["project_id"])
        state["papers_reviewed"] = papers
        self.logger.info(f"✓ Total papers: {len(papers)}")

        self.save_artifact(
            content={"papers": papers},
            project_id=state["project_id"],
            filename="papers_analyzed.json",
            subdir="literature",
            format="json"
        )

        # === Stage 1: Quick Filtering ===
        self.logger.info("Stage 1: Quick filtering and ranking...")
        ranked_papers = self.quick_filter_and_rank(papers, state["research_direction"])
        self.logger.info(f"✓ Ranked {len(ranked_papers)} papers")

        # Save ranked results
        ranked_data = [
            {
                "paper_id": rp.paper["arxiv_id"],
                "title": rp.paper["title"],
                "relevance_score": rp.relevance_score,
                "reasons": rp.relevance_reasons
            }
            for rp in ranked_papers[:20]
        ]
        self.save_artifact(
            content=ranked_data,
            project_id=state["project_id"],
            filename="ranked_papers.json",
            subdir="literature"
        )

        # === Stage 2: Structured Analysis ===
        if self.analysis_depth in ["medium", "deep"]:
            self.logger.info("Stage 2: Structured analysis...")
            structured_insights = self.structured_analysis(
                ranked_papers[:20],
                state["research_direction"]
            )
            self.logger.info(f"✓ Analyzed {len(structured_insights)} papers (structured)")

            # Save structured insights
            insights_data = [
                {
                    "paper_id": ins.paper_id,
                    "title": ins.title,
                    "methodology_summary": ins.methodology_summary,
                    "key_innovations": ins.key_innovations,
                    "innovation_score": ins.innovation_score,
                    "practical_feasibility": ins.practical_feasibility
                }
                for ins in structured_insights
            ]
            self.save_artifact(
                content=insights_data,
                project_id=state["project_id"],
                filename="structured_insights.json",
                subdir="literature"
            )
        else:
            structured_insights = []

        # === Stage 3: Deep Analysis ===
        deep_insights = []
        if self.analysis_depth == "deep" and structured_insights:
            self.logger.info("Stage 3: Deep analysis of core papers...")
            # Select top papers by innovation + feasibility
            core_papers_insights = sorted(
                structured_insights,
                key=lambda x: x.innovation_score * 0.6 + x.practical_feasibility * 0.4,
                reverse=True
            )[:8]

            deep_insights = self.deep_analysis(
                core_papers_insights,
                state["research_direction"]
            )
            self.logger.info(f"✓ Deep analysis of {len(deep_insights)} core papers")

            # Save deep insights
            deep_data = [
                {
                    "paper_id": di.paper_id,
                    "core_contribution": di.core_contribution,
                    "equations_count": len(di.equations),
                    "algorithms_count": len(di.algorithms),
                    "reproducibility_score": di.reproducibility_score
                }
                for di in deep_insights
            ]
            self.save_artifact(
                content=deep_data,
                project_id=state["project_id"],
                filename="deep_insights.json",
                subdir="literature"
            )

        # === Synthesis ===
        self.logger.info("Synthesizing across papers...")
        synthesis = self.cross_paper_synthesis(
            ranked_papers=ranked_papers,
            structured_insights=structured_insights,
            deep_insights=deep_insights,
            research_direction=state["research_direction"]
        )

        # Update state
        state["literature_summary"] = synthesis.literature_summary
        state["research_gaps"] = [gap.description for gap in synthesis.identified_gaps]
        state["hypothesis"] = synthesis.hypotheses[0].statement if synthesis.hypotheses else ""

        # Save synthesis
        self.save_artifact(
            content=synthesis.literature_summary,
            project_id=state["project_id"],
            filename="literature_summary.md",
            subdir="literature",
            format="markdown"
        )

        # Save hypothesis with evidence
        if synthesis.hypotheses:
            hyp = synthesis.hypotheses[0]
            hypothesis_content = f"""# Research Hypothesis

## Hypothesis Statement
{hyp.statement}

## Rationale
{hyp.rationale}

## Supporting Evidence
{chr(10).join(f'- {ev}' for ev in hyp.supporting_evidence)}

## Feasibility Score
{hyp.feasibility_score:.2f} / 1.0

## Novelty Score
{hyp.novelty_score:.2f} / 1.0

## Research Gaps Identified

{chr(10).join(f'### {i+1}. {gap.description}' + chr(10) + f'**Severity**: {gap.severity}' + chr(10) + f'**Evidence**: ' + ', '.join(gap.evidence[:2]) for i, gap in enumerate(synthesis.identified_gaps))}
"""
            self.save_artifact(
                content=hypothesis_content,
                project_id=state["project_id"],
                filename="hypothesis.md",
                subdir="literature",
                format="markdown"
            )

        # Update knowledge graph
        if synthesis.identified_gaps:
            findings = [f"Research gap: {gap.description}" for gap in synthesis.identified_gaps[:3]]
            self.intelligence.knowledge_graph.update_knowledge_from_research(
                project_id=state["project_id"],
                findings=findings,
                llm=self.llm
            )

        return state

    def get_papers_with_memory(
        self,
        research_direction: str,
        project_id: str
    ) -> List[PaperMetadata]:
        """
        Get papers using document memory + new scan.

        Strategy:
        1. Try to retrieve from document memory (by domain)
        2. If insufficient, supplement with new scan
        3. Deduplicate and return
        """
        # Infer domain from research direction
        domain = self._infer_domain(research_direction)

        if domain:
            self.logger.info(f"Retrieving papers from domain: {domain}")
            memory_papers = self.doc_memory.retrieve_by_domain(
                domain=domain,
                exclude_read=True,
                project_id=project_id,
                limit=50
            )
            self.logger.info(f"✓ Retrieved {len(memory_papers)} papers from memory")

            if len(memory_papers) >= 30:
                return memory_papers

        # Supplement with new scan
        self.logger.info("Scanning for additional papers...")
        new_papers = self.scan_papers(research_direction)
        self.logger.info(f"✓ Scanned {len(new_papers)} new papers")

        # Merge and deduplicate
        all_papers = (memory_papers if domain else []) + new_papers
        seen_ids = set()
        unique_papers = []

        for paper in all_papers:
            if paper["arxiv_id"] not in seen_ids:
                seen_ids.add(paper["arxiv_id"])
                unique_papers.append(paper)

        return unique_papers[:50]

    def _infer_domain(self, research_direction: str) -> str:
        """Infer domain from research direction."""
        direction_lower = research_direction.lower()

        # Simple keyword mapping
        domain_keywords = {
            "Momentum Strategies": ["momentum", "trend following"],
            "Mean Reversion": ["mean reversion", "contrarian", "reversal"],
            "Pairs Trading": ["pairs trading", "cointegration", "spread"],
            "Statistical Arbitrage": ["statistical arbitrage", "stat arb"],
            "Risk Management": ["risk", "var", "volatility management"],
            "Portfolio Management": ["portfolio", "asset allocation"],
            "Options Pricing": ["options", "derivatives pricing"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in direction_lower for kw in keywords):
                return domain

        # Default to parent domain
        return "Trading Strategies"

    def quick_filter_and_rank(
        self,
        papers: List[PaperMetadata],
        research_direction: str
    ) -> List[RankedPaper]:
        """
        Stage 1: Quick filtering using Haiku.

        Processes papers in batches and ranks by relevance.

        Args:
            papers: List of papers to rank
            research_direction: Research direction

        Returns:
            List of RankedPaper objects sorted by score
        """
        ranked_papers = []

        # Process in batches of 10
        batch_size = 10
        for i in range(0, len(papers), batch_size):
            batch = papers[i:i+batch_size]

            prompt = PromptBuilder.build_ranking_prompt(batch, research_direction)

            try:
                # Use Haiku for speed
                response = self.call_llm(
                    prompt=prompt,
                    model="haiku",
                    max_tokens=1500,
                    temperature=0.3,
                    response_format="json"
                )

                # Parse rankings
                if isinstance(response, dict) and "rankings" in response:
                    for ranking in response["rankings"]:
                        # Find matching paper
                        paper = next(
                            (p for p in batch if p["arxiv_id"] == ranking["arxiv_id"]),
                            None
                        )
                        if paper:
                            ranked_papers.append(RankedPaper(
                                paper=paper,
                                relevance_score=ranking.get("score", 0.0),
                                relevance_reasons=ranking.get("reasons", []),
                                should_analyze_deep=ranking.get("score", 0) > 0.7
                            ))

            except Exception as e:
                self.logger.warning(f"Batch ranking failed: {e}")
                # Fallback: assign medium scores
                for paper in batch:
                    ranked_papers.append(RankedPaper(
                        paper=paper,
                        relevance_score=0.5,
                        relevance_reasons=["Fallback scoring"],
                        should_analyze_deep=False
                    ))

        # Sort by relevance score
        ranked_papers.sort(key=lambda x: x.relevance_score, reverse=True)

        return ranked_papers

    def structured_analysis(
        self,
        ranked_papers: List[RankedPaper],
        research_direction: str
    ) -> List[StructuredInsights]:
        """
        Stage 2: Structured section-level analysis.

        For each paper:
        1. Check cache
        2. Download PDF (if needed)
        3. Extract sections
        4. Analyze methodology and results
        5. Cache results

        Args:
            ranked_papers: Top-ranked papers
            research_direction: Research direction

        Returns:
            List of StructuredInsights
        """
        insights_list = []

        for i, ranked_paper in enumerate(ranked_papers, 1):
            paper = ranked_paper.paper
            arxiv_id = paper["arxiv_id"]

            self.logger.info(f"Analyzing paper {i}/{len(ranked_papers)}: {paper['title'][:60]}...")

            # Check cache
            cached = self.doc_memory.get_cached_analysis(arxiv_id)
            if cached and cached.get("structured_insights"):
                self.logger.info(f"  ✓ Using cached analysis")
                # Reconstruct StructuredInsights from cache
                cached_insights = cached["structured_insights"]
                insights = StructuredInsights(
                    paper_id=arxiv_id,
                    title=paper["title"],
                    sections=cached.get("sections", {}),
                    key_innovations=cached_insights.get("key_innovations", []),
                    methodology_summary=cached_insights.get("methodology_summary", ""),
                    performance_metrics=cached_insights.get("performance_metrics", {}),
                    limitations=cached_insights.get("limitations", []),
                    research_gaps_mentioned=cached_insights.get("research_gaps_mentioned", []),
                    innovation_score=cached_insights.get("innovation_score", 0.5),
                    practical_feasibility=cached_insights.get("practical_feasibility", 0.5)
                )
                insights_list.append(insights)
                continue

            # Download PDF
            pdf_path = self.pdf_reader.download_pdf(
                arxiv_id=arxiv_id,
                pdf_url=paper.get("pdf_url")
            )

            if not pdf_path:
                self.logger.warning(f"  ✗ Cannot access PDF for {arxiv_id}")
                continue

            # Extract text and sections
            full_text = self.pdf_reader.extract_text(pdf_path)
            if not full_text:
                self.logger.warning(f"  ✗ Cannot extract text from PDF")
                continue

            sections = self.pdf_reader.extract_sections(full_text)

            # Analyze sections
            methodology_analysis = self._analyze_methodology_section(
                sections.get("methodology", ""),
                research_direction
            )

            results_analysis = self._analyze_results_section(
                sections.get("results", "")
            )

            # Create StructuredInsights
            insights = StructuredInsights(
                paper_id=arxiv_id,
                title=paper["title"],
                sections=sections,
                key_innovations=methodology_analysis.get("innovations", []),
                methodology_summary=methodology_analysis.get("summary", ""),
                performance_metrics=results_analysis.get("metrics", {}),
                limitations=results_analysis.get("limitations", []),
                research_gaps_mentioned=results_analysis.get("future_directions", []),
                innovation_score=methodology_analysis.get("novelty_score", 0.5),
                practical_feasibility=methodology_analysis.get("feasibility_score", 0.5)
            )

            insights_list.append(insights)

            # Save to cache
            self.doc_memory.save_analysis_results(
                arxiv_id=arxiv_id,
                sections=sections,
                structured_insights={
                    "key_innovations": insights.key_innovations,
                    "methodology_summary": insights.methodology_summary,
                    "performance_metrics": insights.performance_metrics,
                    "limitations": insights.limitations,
                    "research_gaps_mentioned": insights.research_gaps_mentioned,
                    "innovation_score": insights.innovation_score,
                    "practical_feasibility": insights.practical_feasibility
                }
            )
            self.logger.info(f"  ✓ Analysis cached")

        return insights_list

    def _analyze_methodology_section(
        self,
        section_text: str,
        research_direction: str
    ) -> Dict:
        """Analyze methodology section using LLM."""
        if not section_text or len(section_text) < 100:
            return {
                "summary": "Methodology section not found",
                "innovations": [],
                "novelty_score": 0.0,
                "feasibility_score": 0.5
            }

        prompt = PromptBuilder.build_section_analysis_prompt(
            section_text=section_text,
            section_name="methodology",
            research_direction=research_direction
        )

        try:
            response = self.call_llm(
                prompt=prompt,
                model="sonnet",
                max_tokens=2000,
                temperature=0.3,
                response_format="json"
            )
            return response if isinstance(response, dict) else {}
        except Exception as e:
            self.logger.warning(f"Methodology analysis failed: {e}")
            return {
                "summary": "Analysis failed",
                "innovations": [],
                "novelty_score": 0.5,
                "feasibility_score": 0.5
            }

    def _analyze_results_section(self, section_text: str) -> Dict:
        """Analyze results section using LLM."""
        if not section_text or len(section_text) < 100:
            return {
                "metrics": {},
                "limitations": [],
                "future_directions": []
            }

        prompt = PromptBuilder.build_section_analysis_prompt(
            section_text=section_text,
            section_name="results",
            research_direction=""
        )

        try:
            response = self.call_llm(
                prompt=prompt,
                model="sonnet",
                max_tokens=2000,
                temperature=0.3,
                response_format="json"
            )
            return response if isinstance(response, dict) else {}
        except Exception as e:
            self.logger.warning(f"Results analysis failed: {e}")
            return {"metrics": {}, "limitations": []}

    def deep_analysis(
        self,
        structured_insights: List[StructuredInsights],
        research_direction: str
    ) -> List[DeepInsights]:
        """
        Stage 3: Deep analysis of core papers.

        Extracts:
        - Equations and mathematical formulations
        - Algorithms and pseudocode
        - Implementation details
        - Reproducibility assessment

        Args:
            structured_insights: Papers to analyze deeply
            research_direction: Research direction

        Returns:
            List of DeepInsights
        """
        deep_insights_list = []

        for insight in structured_insights:
            arxiv_id = insight.paper_id

            self.logger.info(f"Deep analysis: {insight.title[:60]}...")

            # Get full text
            pdf_path = self.pdf_reader.download_pdf(arxiv_id=arxiv_id)
            if not pdf_path:
                continue

            full_text = self.pdf_reader.extract_text(pdf_path)
            if not full_text or len(full_text) < 1000:
                continue

            # Deep extraction prompt
            prompt = f"""Perform deep extraction from this quantitative finance paper on "{research_direction}".

Extract maximum detail to enable reproduction:

Paper Title: {insight.title}

Full Paper Text (truncated):
{full_text[:8000]}

Sections Available:
{json.dumps(list(insight.sections.keys()))}

Extract the following:

1. **Mathematical Formulations**:
   - All equations (in plain text or LaTeX)
   - Parameter definitions
   - Signal calculations

2. **Algorithm Details**:
   - Step-by-step algorithm
   - Entry/exit rules
   - Logic flow

3. **Implementation Hints**:
   - Code patterns mentioned
   - Programming considerations
   - Libraries/tools used

4. **Experimental Setup**:
   - Dataset details (timeframe, markets, frequency)
   - Training/testing split
   - Performance metrics used

5. **Data Requirements**:
   - Specific data fields needed
   - Data sources
   - Preprocessing steps

6. **Reproducibility**:
   - Can this be reproduced with public data? (score 0-1)
   - What is missing?
   - Complexity (low/medium/high)

Output as JSON with keys: equations (list), algorithms (list), code_patterns (list),
contribution (str), implementation (str), parameters (dict), experimental_setup (str),
data_requirements (list), computational (str), reproducibility_score (float)
"""

            try:
                response = self.call_llm(
                    prompt=prompt,
                    model="sonnet",
                    max_tokens=4000,
                    temperature=0.2,
                    response_format="json"
                )

                if isinstance(response, dict):
                    deep_insight = DeepInsights(
                        paper_id=arxiv_id,
                        equations=response.get("equations", []),
                        algorithms=response.get("algorithms", []),
                        code_patterns=response.get("code_patterns", []),
                        core_contribution=response.get("contribution", ""),
                        implementation_details=response.get("implementation", ""),
                        parameter_settings=response.get("parameters", {}),
                        experimental_setup=response.get("experimental_setup", ""),
                        data_requirements=response.get("data_requirements", []),
                        computational_requirements=response.get("computational", ""),
                        reproducibility_score=response.get("reproducibility_score", 0.5)
                    )
                    deep_insights_list.append(deep_insight)
                    self.logger.info(f"  ✓ Deep analysis complete")

            except Exception as e:
                self.logger.warning(f"Deep analysis failed: {e}")

        return deep_insights_list

    def cross_paper_synthesis(
        self,
        ranked_papers: List[RankedPaper],
        structured_insights: List[StructuredInsights],
        deep_insights: List[DeepInsights],
        research_direction: str
    ) -> ResearchSynthesis:
        """
        Synthesize insights across all analyzed papers.

        Args:
            ranked_papers: All ranked papers
            structured_insights: Structured analysis results
            deep_insights: Deep analysis results
            research_direction: Research direction

        Returns:
            ResearchSynthesis with gaps and hypotheses
        """
        prompt = PromptBuilder.build_synthesis_prompt(
            structured_insights=[
                {
                    "title": ins.title,
                    "methodology_summary": ins.methodology_summary,
                    "key_innovations": ins.key_innovations,
                    "innovation_score": ins.innovation_score,
                    "practical_feasibility": ins.practical_feasibility
                }
                for ins in structured_insights
            ],
            deep_insights=[
                {
                    "paper_id": di.paper_id,
                    "core_contribution": di.core_contribution,
                    "reproducibility_score": di.reproducibility_score
                }
                for di in deep_insights
            ],
            research_direction=research_direction
        )

        try:
            response = self.call_llm(
                prompt=prompt,
                model="sonnet",
                max_tokens=6000,
                temperature=0.7,
                response_format="json"
            )

            if isinstance(response, dict):
                # Parse gaps
                gaps = [
                    ResearchGap(
                        description=gap.get("description", ""),
                        severity=gap.get("severity", "minor"),
                        evidence=gap.get("evidence", []),
                        opportunity_score=gap.get("opportunity_score", 0.5)
                    )
                    for gap in response.get("research_gaps", [])
                ]

                # Parse hypotheses
                hypotheses = [
                    Hypothesis(
                        statement=hyp.get("statement", ""),
                        rationale=hyp.get("rationale", ""),
                        supporting_evidence=hyp.get("supporting_evidence", []),
                        feasibility_score=hyp.get("feasibility_score", 0.5),
                        novelty_score=hyp.get("novelty_score", 0.5)
                    )
                    for hyp in response.get("hypotheses", [])
                ]

                return ResearchSynthesis(
                    literature_summary=response.get("literature_summary", ""),
                    methodology_patterns=response.get("methodology_patterns", []),
                    performance_trends=response.get("performance_trends", []),
                    common_limitations=response.get("common_limitations", []),
                    identified_gaps=gaps,
                    hypotheses=hypotheses
                )

        except Exception as e:
            self.logger.error(f"Synthesis failed: {e}")

        # Fallback synthesis
        return self._fallback_synthesis(ranked_papers, structured_insights)

    def _fallback_synthesis(
        self,
        ranked_papers: List[RankedPaper],
        structured_insights: List[StructuredInsights]
    ) -> ResearchSynthesis:
        """Fallback synthesis if LLM fails."""
        return ResearchSynthesis(
            literature_summary=f"Analyzed {len(ranked_papers)} papers.",
            methodology_patterns=["Various approaches identified"],
            performance_trends=["Performance varies by methodology"],
            common_limitations=["Data availability", "Computational complexity"],
            identified_gaps=[
                ResearchGap(
                    description="Further research needed",
                    severity="minor",
                    evidence=[],
                    opportunity_score=0.5
                )
            ],
            hypotheses=[
                Hypothesis(
                    statement="Hypothesis requires manual refinement",
                    rationale="Automated synthesis failed",
                    supporting_evidence=[],
                    feasibility_score=0.5,
                    novelty_score=0.5
                )
            ]
        )

    # === Original methods from base implementation ===

    def scan_papers(self, research_direction: str) -> List[PaperMetadata]:
        """Scan and fetch relevant papers (original implementation)."""
        categories = self.config.get("focus_categories", [])
        keywords = self.config.get("keywords", [])

        recent_papers = self.paper_fetcher.fetch_recent_papers(
            categories=categories,
            days_back=7,
        )

        keyword_papers = self.paper_fetcher.fetch_papers_by_keywords(
            keywords=[research_direction] + keywords[:5],
            categories=categories,
            max_results=30,
        )

        # Combine and deduplicate
        all_papers = recent_papers + keyword_papers
        seen_ids = set()
        unique_papers = []

        for paper in all_papers:
            if paper["arxiv_id"] not in seen_ids:
                seen_ids.add(paper["arxiv_id"])
                unique_papers.append(paper)

        # Filter by relevance
        relevant_papers = self.paper_fetcher.filter_papers_by_relevance(
            unique_papers, keywords=[research_direction] + keywords, min_score=0.2
        )

        return relevant_papers[: self.config.get("max_papers_per_scan", 50)]

    def _generate_execution_summary(self, state: ResearchState) -> Dict:
        """Generate execution summary for daily log."""
        papers = state.get("papers_reviewed", [])
        research_gaps = state.get("research_gaps", [])
        hypothesis = state.get("hypothesis", "")
        literature_summary = state.get("literature_summary", "")

        execution_log = f"""## Three-Stage Literature Analysis Execution

### Papers Processed
- Total papers: {len(papers)}
- Analysis depth: {self.analysis_depth}
- Research direction: {state['research_direction']}

### Analysis Results
- Literature summary length: {len(literature_summary)} characters
- Research gaps identified: {len(research_gaps)}
- Hypothesis generated: {'Yes' if hypothesis else 'No'}

### Research Gaps
{chr(10).join(f'- {gap}' for gap in research_gaps[:5])}

### Hypothesis
{hypothesis[:500]}...
"""

        learnings = [
            f"Three-stage analysis completed for {len(papers)} papers",
            f"Identified {len(research_gaps)} research gaps with evidence",
            "Used document memory for efficient retrieval"
        ]

        reflection = f"""## Execution Reflection

### Effectiveness
- Document memory retrieval: {'Success' if len(papers) > 20 else 'Limited'}
- PDF analysis: {'Complete' if self.analysis_depth == 'deep' else 'Partial'}
- Evidence-based hypotheses: {'Yes' if hypothesis else 'No'}

### Improvements
- Continue building domain taxonomy
- Increase analysis cache coverage
- Refine synthesis algorithms
"""

        return {
            "log": execution_log,
            "learnings": learnings,
            "mistakes": [],
            "reflection": reflection
        }
