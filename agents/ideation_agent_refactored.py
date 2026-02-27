"""
Ideation Agent - Literature review and hypothesis generation (REFACTORED)

Refactored to inherit from BaseAgent, eliminating infrastructure duplication.
Now focuses purely on business logic.

Responsible for:
- Scanning and fetching papers from arXiv and other sources
- Analyzing literature and identifying trends
- Discovering research gaps
- Generating testable hypotheses
"""

from typing import List, Dict
from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState, PaperMetadata
from tools.paper_fetcher import PaperFetcher
from tools.file_manager import FileManager
from tools.smart_literature_access import get_literature_access_manager


class IdeationAgent(BaseAgent):
    """
    Agent responsible for literature review and idea generation.

    Refactored to use BaseAgent for infrastructure.
    All memory, LLM calling, and output management handled by base class.
    """

    def __init__(
        self,
        llm: Anthropic,
        paper_fetcher: PaperFetcher,
        file_manager: FileManager
    ):
        """
        Initialize Ideation Agent.

        Args:
            llm: Anthropic client instance
            paper_fetcher: PaperFetcher instance for retrieving papers
            file_manager: FileManager instance for file operations
        """
        # Initialize base agent (handles memory, LLM service, output manager)
        super().__init__(llm, file_manager, agent_name="ideation")

        # Agent-specific tools
        self.paper_fetcher = paper_fetcher
        self.literature_access = get_literature_access_manager()

    def _execute(self, state: ResearchState) -> ResearchState:
        """
        Execute ideation agent workflow (business logic only).

        All infrastructure (memory loading, logging, etc.) handled by BaseAgent.

        Args:
            state: Current research state

        Returns:
            Updated research state with ideation outputs
        """
        self.logger.info(f"Research direction: {state['research_direction']}")

        # Consult knowledge graph for related concepts
        related_knowledge = self.intelligence.knowledge_graph.search_knowledge(
            query=state["research_direction"],
            node_type=None
        )

        if related_knowledge:
            self.logger.info(
                f"✓ Found {len(related_knowledge)} related concepts in knowledge graph"
            )
            for knowledge in related_knowledge[:3]:
                self.logger.info(
                    f"  - {knowledge['name']}: {knowledge['description'][:80]}..."
                )

        # Step 1: Scan and fetch papers
        papers = self.scan_papers(state["research_direction"])
        state["papers_reviewed"] = papers
        self.logger.info(f"✓ Found {len(papers)} relevant papers")

        # Save papers to project
        self.save_artifact(
            content={"papers": papers},
            project_id=state["project_id"],
            filename="papers_analyzed.json",
            subdir="literature",
            format="json"
        )

        # Step 2: Analyze literature
        literature_summary = self.analyze_literature(
            papers, state["research_direction"]
        )
        state["literature_summary"] = literature_summary
        self.logger.info("✓ Completed literature analysis")

        # Save literature summary
        self.save_artifact(
            content=literature_summary,
            project_id=state["project_id"],
            filename="literature_summary.md",
            subdir="literature",
            format="markdown"
        )

        # Step 3: Identify research gaps
        research_gaps = self.identify_research_gaps(literature_summary, papers)
        state["research_gaps"] = research_gaps
        self.logger.info(f"✓ Identified {len(research_gaps)} research gaps")

        # Step 4: Generate hypothesis
        hypothesis = self.generate_hypothesis(
            research_gaps, literature_summary, state["research_direction"]
        )
        state["hypothesis"] = hypothesis
        self.logger.info("✓ Generated research hypothesis")
        self.logger.info(f"Hypothesis: {hypothesis[:200]}...")

        # Save hypothesis
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
            format="markdown"
        )

        # Update knowledge graph with new insights
        if research_gaps:
            findings = [f"Research gap: {gap}" for gap in research_gaps[:3]]
            self.intelligence.knowledge_graph.update_knowledge_from_research(
                project_id=state["project_id"],
                findings=findings,
                llm=self.llm
            )

        return state

    def _generate_execution_summary(self, state: ResearchState) -> Dict:
        """
        Generate execution summary for daily log.

        Overrides base class to provide agent-specific summary.

        Args:
            state: Current research state

        Returns:
            Execution summary dict
        """
        papers = state.get("papers_reviewed", [])
        research_gaps = state.get("research_gaps", [])
        hypothesis = state.get("hypothesis", "")
        literature_summary = state.get("literature_summary", "")

        execution_log = f"""## Literature Review Execution

### Papers Scanned
- Total papers found: {len(papers)}
- Research direction: {state['research_direction']}

### Analysis Results
- Literature summary length: {len(literature_summary)} characters
- Research gaps identified: {len(research_gaps)}
- Hypothesis generated: {'Yes' if hypothesis else 'No'}

### Research Gaps Found
{chr(10).join(f'- {gap}' for gap in research_gaps)}

### Hypothesis
{hypothesis[:500]}...
"""

        learnings = [
            f"Successfully analyzed {len(papers)} papers on {state['research_direction']}",
            f"Identified {len(research_gaps)} distinct research gaps",
        ]

        reflection_text = f"""## Reflection on Execution

### What Went Well
- Literature scan successfully retrieved {len(papers)} relevant papers
- Gap analysis identified {len(research_gaps)} testable opportunities
- Hypothesis is clear and actionable

### Areas for Improvement
- Consider expanding search keywords for broader coverage
- Validate hypothesis testability with Planning Agent
"""

        return {
            "log": execution_log,
            "learnings": learnings,
            "mistakes": [],
            "reflection": reflection_text
        }

    def scan_papers(self, research_direction: str) -> List[PaperMetadata]:
        """
        Scan and fetch relevant papers.

        Args:
            research_direction: Research focus area

        Returns:
            List of PaperMetadata
        """
        categories = self.config.get("focus_categories", [])
        keywords = self.config.get("keywords", [])

        # Fetch recent papers from categories
        recent_papers = self.paper_fetcher.fetch_recent_papers(
            categories=categories,
            days_back=7,  # Last week
        )

        # Also search by keywords
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

    def analyze_literature(
        self, papers: List[PaperMetadata], research_direction: str
    ) -> str:
        """
        Analyze papers and create comprehensive literature summary.

        Args:
            papers: List of papers to analyze
            research_direction: Research focus

        Returns:
            Literature analysis summary
        """
        # Prepare paper summaries
        paper_texts = []
        for i, paper in enumerate(papers[:20], 1):  # Limit to 20 for context
            paper_texts.append(
                f"{i}. **{paper['title']}** ({paper['published'][:10]})\n"
                f"   Authors: {', '.join(paper['authors'][:3])}\n"
                f"   Abstract: {paper['abstract'][:300]}...\n"
            )

        papers_text = "\n".join(paper_texts)

        # Create analysis prompt (use LLMService)
        prompt = f"""Analyze the following recent papers related to "{research_direction}" and provide a comprehensive literature review.

Papers to analyze:
{papers_text}

Please provide:
1. **Overall Trends**: What are the main themes and trends in this research area?
2. **Key Methodologies**: What methods and approaches are researchers using?
3. **Important Findings**: What are the most significant results or insights?
4. **Emerging Directions**: What new directions are emerging in this field?
5. **Connections**: How do these papers relate to each other?

Write a detailed literature review (800-1000 words) that synthesizes these papers."""

        # Use BaseAgent's call_llm method
        return self.call_llm(
            prompt=prompt,
            model=self.config.get("model", "sonnet"),
            max_tokens=4000,
            temperature=self.config.get("temperature", 0.7)
        )

    def identify_research_gaps(
        self, literature_summary: str, papers: List[PaperMetadata]
    ) -> List[str]:
        """
        Identify research gaps and opportunities.

        Args:
            literature_summary: Summary of literature
            papers: List of analyzed papers

        Returns:
            List of research gaps
        """
        prompt = f"""Based on the following literature review, identify specific research gaps and opportunities in quantitative finance.

Literature Review:
{literature_summary}

Please identify 5-7 specific research gaps or opportunities. For each gap:
- Be concrete and specific
- Explain why it's important
- Suggest how it could be addressed

Format each gap as a single paragraph (2-3 sentences).

Output as JSON array of strings."""

        # Use BaseAgent's call_llm with JSON format
        try:
            response = self.call_llm(
                prompt=prompt,
                model=self.config.get("model", "sonnet"),
                max_tokens=2000,
                temperature=self.config.get("temperature", 0.7),
                response_format="json"
            )

            # Extract gaps array
            if isinstance(response, dict):
                return response if isinstance(response, list) else []
            elif isinstance(response, list):
                return response
            return []

        except Exception as e:
            self.logger.warning(f"JSON parsing failed, using text fallback: {e}")
            # Fallback: call as text and parse manually
            text_response = self.call_llm(
                prompt=prompt,
                model=self.config.get("model", "sonnet"),
                max_tokens=2000,
                temperature=self.config.get("temperature", 0.7)
            )

            # Split by newlines
            lines = [line.strip() for line in text_response.split("\n") if line.strip()]
            return [line for line in lines if len(line) > 50][:7]

    def generate_hypothesis(
        self, research_gaps: List[str], literature_summary: str, research_direction: str
    ) -> str:
        """
        Generate testable research hypothesis.

        Args:
            research_gaps: Identified research gaps
            literature_summary: Literature summary
            research_direction: Research focus

        Returns:
            Research hypothesis
        """
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

        # Use BaseAgent's call_llm
        return self.call_llm(
            prompt=prompt,
            model=self.config.get("model", "sonnet"),
            max_tokens=2000,
            temperature=self.config.get("temperature", 0.7)
        )
