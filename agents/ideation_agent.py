"""
Ideation Agent - Literature review and hypothesis generation.

Responsible for:
- Scanning and fetching papers from arXiv and other sources
- Analyzing literature and identifying trends
- Discovering research gaps
- Generating testable hypotheses
"""

from typing import List, Dict
from anthropic import Anthropic
from core.state import ResearchState, PaperMetadata
from tools.paper_fetcher import PaperFetcher
from tools.file_manager import FileManager
from config.agent_config import get_agent_config
from config.llm_config import get_model_name
from core.agent_memory_manager import get_agent_memory_manager
from core.knowledge_graph import get_knowledge_graph
from tools.smart_literature_access import get_literature_access_manager
import json


class IdeationAgent:
    """
    Agent responsible for literature review and idea generation.
    Enhanced with persona, self-reflection, and knowledge graph capabilities.
    """

    def __init__(
        self, llm: Anthropic, paper_fetcher: PaperFetcher, file_manager: FileManager
    ):
        """
        Initialize Ideation Agent.

        Args:
            llm: Anthropic client instance
            paper_fetcher: PaperFetcher instance for retrieving papers
            file_manager: FileManager instance for file operations
        """
        self.llm = llm
        self.paper_fetcher = paper_fetcher
        self.file_manager = file_manager
        self.config = get_agent_config("ideation")
        self.model = get_model_name(self.config.get("model", "sonnet"))

        # Initialize agent intelligence components (NEW: Markdown-based memory system)
        self.memory_manager = get_agent_memory_manager("ideation")
        self.knowledge_graph = get_knowledge_graph()
        self.literature_access = get_literature_access_manager()

    def _build_system_prompt(self, memories: Dict[str, str]) -> str:
        """
        Build system prompt with persona and memory context.

        Args:
            memories: Dictionary containing persona, memory, mistakes, and daily logs

        Returns:
            Complete system prompt string
        """
        return f"""# Your Identity and Persona

{memories['persona']}

---

# Your Long-term Knowledge and Insights

{memories['memory']}

---

# Mistakes to Avoid (IMPORTANT - Review Before Each Task)

{memories['mistakes']}

---

# Recent Context (Last 3 Days of Work)

{memories['daily_recent']}

---

You are now executing a new task. Use your persona, knowledge, and past learnings to perform at your best. Avoid repeating past mistakes.
"""

    def __call__(self, state: ResearchState) -> ResearchState:
        """
        Execute ideation agent workflow.

        Args:
            state: Current research state

        Returns:
            Updated research state with ideation outputs
        """
        print(f"\n{'='*60}")
        print("Ideation Agent: Starting literature review")
        print(f"Research direction: {state['research_direction']}")
        print(f"{'='*60}\n")

        # Update status
        state["status"] = "ideation"

        # Load all memories (persona, memory, mistakes, daily logs)
        print("🧠 Loading agent memories...")
        self.memories = self.memory_manager.load_all_memories()
        self.system_prompt = self._build_system_prompt(self.memories)
        print(
            "✓ Loaded persona, long-term memory, mistakes registry, and recent daily logs"
        )

        # Consult knowledge graph for related concepts
        related_knowledge = self.knowledge_graph.search_knowledge(
            query=state["research_direction"], node_type=None
        )

        if related_knowledge:
            print(
                f"✓ Found {len(related_knowledge)} related concepts in knowledge graph"
            )
            for knowledge in related_knowledge[:3]:
                print(f"  - {knowledge['name']}: {knowledge['description'][:80]}...")

        # Step 1: Scan and fetch papers
        papers = self.scan_papers(state["research_direction"])
        state["papers_reviewed"] = papers

        print(f"✓ Found {len(papers)} relevant papers")

        # Save papers to project
        self.file_manager.save_json(
            data={"papers": papers},
            project_id=state["project_id"],
            filename="papers_analyzed.json",
            subdir="literature",
        )

        # Step 2: Analyze literature
        literature_summary = self.analyze_literature(
            papers, state["research_direction"]
        )
        state["literature_summary"] = literature_summary

        print("✓ Completed literature analysis")

        # Save literature summary
        self.file_manager.save_text(
            content=literature_summary,
            project_id=state["project_id"],
            filename="literature_summary.md",
            subdir="literature",
        )

        # Step 3: Identify research gaps
        research_gaps = self.identify_research_gaps(literature_summary, papers)
        state["research_gaps"] = research_gaps

        print(f"✓ Identified {len(research_gaps)} research gaps")

        # Step 4: Generate hypothesis
        hypothesis = self.generate_hypothesis(
            research_gaps, literature_summary, state["research_direction"]
        )
        state["hypothesis"] = hypothesis

        print("✓ Generated research hypothesis")
        print(f"\nHypothesis: {hypothesis[:200]}...")

        # Save hypothesis
        self.file_manager.save_text(
            content=f"# Research Hypothesis\n\n{hypothesis}\n\n## Research Gaps\n\n"
            + "\n".join(f"- {gap}" for gap in research_gaps),
            project_id=state["project_id"],
            filename="hypothesis.md",
            subdir="literature",
        )

        print(f"\n{'='*60}")
        print("Ideation Agent: Completed")
        print(f"{'='*60}\n")

        # Save daily log with execution details
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

        mistakes_encountered = []  # Track if any issues occurred

        reflection_text = f"""
## Reflection on Execution

### What Went Well
- Literature scan successfully retrieved {len(papers)} relevant papers
- Gap analysis identified {len(research_gaps)} testable opportunities
- Hypothesis is clear and actionable

### Areas for Improvement
- Consider expanding search keywords for broader coverage
- Validate hypothesis testability with Planning Agent
"""

        self.memory_manager.save_daily_log(
            project_id=state["project_id"],
            execution_log=execution_log,
            learnings=learnings,
            mistakes=mistakes_encountered,
            reflection=reflection_text,
        )

        print("✓ Daily log saved with execution details and learnings")

        # Update knowledge graph with new insights
        if research_gaps:
            findings = [f"Research gap: {gap}" for gap in research_gaps[:3]]
            self.knowledge_graph.update_knowledge_from_research(
                project_id=state["project_id"], findings=findings, llm=self.llm
            )

        return state

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

        # Create analysis prompt (task-specific, persona is in system prompt)
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

        response = self.llm.messages.create(
            model=self.model,
            max_tokens=4000,
            temperature=self.config.get("temperature", 0.7),
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

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

        response = self.llm.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=self.config.get("temperature", 0.7),
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response
        content = response.content[0].text

        try:
            # Try to extract JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "[" in content and "]" in content:
                json_str = content[content.find("[") : content.rfind("]") + 1]
            else:
                json_str = content

            gaps = json.loads(json_str)

            if isinstance(gaps, list):
                return gaps
        except:
            pass

        # Fallback: split by newlines
        lines = [line.strip() for line in content.split("\n") if line.strip()]
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

        response = self.llm.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=self.config.get("temperature", 0.7),
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text
