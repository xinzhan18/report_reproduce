"""
Writing Agent - Research report generation.

Responsible for:
- Integrating outputs from all previous agents
- Generating structured academic reports
- Formatting for review and publication
- Creating comprehensive documentation
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing (类型系统), anthropic (Anthropic客户端),
#                   core/state (ResearchState状态),
#                   tools/file_manager (文件管理),
#                   config/agent_config (Agent配置),
#                   config/llm_config (模型名称),
#                   core/agent_memory_manager (记忆管理),
#                   core/knowledge_graph (知识图谱),
#                   datetime (时间戳)
# OUTPUT: 对外提供 - WritingAgent类,实现execute()方法,
#                   输出完整研究报告(Markdown格式)
# POSITION: 系统地位 - Agent/Writing (智能体层-写作智能体)
#                     Pipeline第四阶段,整合所有结果生成最终报告
#
# 注意：当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import Dict, Any
from anthropic import Anthropic
from core.state import ResearchState
from tools.file_manager import FileManager
from config.agent_config import get_agent_config
from config.llm_config import get_model_name
from core.agent_memory_manager import get_agent_memory_manager
from core.knowledge_graph import get_knowledge_graph
import json
from datetime import datetime


class WritingAgent:
    """
    Agent responsible for report generation and documentation.
    Enhanced with persona, self-reflection, and knowledge graph capabilities.
    """

    def __init__(self, llm: Anthropic, file_manager: FileManager):
        """
        Initialize Writing Agent.

        Args:
            llm: Anthropic client instance
            file_manager: FileManager instance for file operations
        """
        self.llm = llm
        self.file_manager = file_manager
        self.config = get_agent_config("writing")
        self.model = get_model_name(self.config.get("model", "sonnet"))

        # Initialize agent intelligence components (NEW: Markdown-based memory system)
        self.memory_manager = get_agent_memory_manager("writing")
        self.knowledge_graph = get_knowledge_graph()

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
        Execute writing agent workflow.

        Args:
            state: Current research state

        Returns:
            Updated research state with report outputs
        """
        print(f"\n{'='*60}")
        print(f"Writing Agent: Generating research report")
        print(f"{'='*60}\n")

        # Update status
        state["status"] = "writing"

        # Load all memories (persona, memory, mistakes, daily logs)
        print("🧠 Loading agent memories...")
        self.memories = self.memory_manager.load_all_memories()
        self.system_prompt = self._build_system_prompt(self.memories)
        print(f"✓ Loaded persona, long-term memory, mistakes registry, and recent daily logs")

        # Step 1: Create report structure
        print("Creating report structure...")
        structure = self.create_report_structure(state)

        print(f"✓ Structured report with {len(structure)} sections")

        # Step 2: Generate each section
        print("\nGenerating report sections...")
        sections = {}

        for section_name, section_config in structure.items():
            print(f"  - {section_name}...")
            content = self.generate_section(
                section_name=section_name,
                section_config=section_config,
                state=state
            )
            sections[section_name] = content

        print(f"✓ Generated all sections")

        # Step 3: Assemble full report
        print("\nAssembling final report...")
        report_draft = self.assemble_report(sections, state)
        state["report_draft"] = report_draft

        # Step 4: Polish and format
        print("Polishing report...")
        final_report = self.polish_report(report_draft, state)
        state["final_report"] = final_report

        print(f"✓ Report completed ({len(final_report)} characters)")

        # Step 5: Save report
        report_path = self.file_manager.save_text(
            content=final_report,
            project_id=state["project_id"],
            filename="final_report.md",
            subdir="reports"
        )
        state["report_path"] = str(report_path)

        # Also save as HTML-friendly version
        self.file_manager.save_text(
            content=self.convert_to_html_friendly(final_report),
            project_id=state["project_id"],
            filename="final_report_formatted.md",
            subdir="reports"
        )

        # Mark for human review
        state["requires_human_review"] = True

        print(f"\n✓ Report saved to: {report_path}")

        print(f"\n{'='*60}")
        print(f"Writing Agent: Completed")
        print(f"{'='*60}\n")

        # Save daily log with execution details
        execution_log = f"""## Research Report Writing

### Report Structure
- Sections generated: {len(sections)}
- Section names: {', '.join(sections.keys())}

### Report Metrics
- Draft length: {len(report_draft)} characters
- Final report length: {len(final_report)} characters
- Improvement: {len(final_report) - len(report_draft)} characters added in polishing

### Sections Included
{chr(10).join(f'- {name}: {len(content)} chars' for name, content in sections.items())}
"""

        learnings = [
            f"Successfully generated {len(sections)}-section research report",
            f"Report integrates findings from all previous agents",
            f"Final length: {len(final_report)} characters"
        ]

        mistakes_encountered = []  # Track if any issues occurred

        reflection_text = f"""
## Reflection on Execution

### What Went Well
- Comprehensive report structure created
- All sections properly generated and polished
- Successfully integrated: hypothesis, literature review, methodology, results
- Report is ready for review

### Areas for Improvement
- Consider adding more visual elements (charts, tables)
- Enhance discussion of limitations
- Add more context for future research directions
"""

        self.memory_manager.save_daily_log(
            project_id=state["project_id"],
            execution_log=execution_log,
            learnings=learnings,
            mistakes=mistakes_encountered,
            reflection=reflection_text
        )

        print(f"✓ Daily log saved with report generation details and learnings")

        # Update final status
        state["status"] = "completed"

        return state

    def create_report_structure(self, state: ResearchState) -> Dict[str, Dict[str, Any]]:
        """
        Create structure for research report.

        Args:
            state: Research state

        Returns:
            Dictionary defining report structure
        """
        return {
            "abstract": {
                "max_words": 250,
                "required_elements": ["motivation", "method", "results", "conclusion"]
            },
            "introduction": {
                "max_words": 500,
                "required_elements": ["background", "problem_statement", "contribution"]
            },
            "literature_review": {
                "max_words": 800,
                "required_elements": ["existing_work", "gaps", "positioning"]
            },
            "methodology": {
                "max_words": 700,
                "required_elements": ["approach", "data", "implementation", "validation"]
            },
            "results": {
                "max_words": 600,
                "required_elements": ["performance_metrics", "analysis", "visualizations"]
            },
            "discussion": {
                "max_words": 500,
                "required_elements": ["interpretation", "implications", "limitations"]
            },
            "conclusion": {
                "max_words": 300,
                "required_elements": ["summary", "contributions", "future_work"]
            },
            "references": {
                "max_words": 0,
                "required_elements": ["cited_papers"]
            }
        }

    def generate_section(
        self,
        section_name: str,
        section_config: Dict[str, Any],
        state: ResearchState
    ) -> str:
        """
        Generate a specific report section.

        Args:
            section_name: Name of the section
            section_config: Configuration for the section
            state: Research state with all information

        Returns:
            Section content
        """
        # Build context specific to this section
        context = self._build_section_context(section_name, state)

        prompt = f"""You are writing the {section_name.upper()} section of a quantitative finance research paper.

Context and Information:
{context}

Requirements for this section:
- Maximum {section_config['max_words']} words
- Must include: {', '.join(section_config['required_elements'])}
- Use formal academic language
- Cite papers where appropriate (use [Author et al., Year] format)
- Be specific and quantitative where possible

Write a well-structured {section_name} section for this research paper."""

        response = self.llm.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=self.config.get("temperature", 0.4),
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def _build_section_context(self, section_name: str, state: ResearchState) -> str:
        """Build context information for a specific section."""

        if section_name == "abstract":
            return f"""
Hypothesis: {state['hypothesis'][:300]}...
Key Results: Sharpe Ratio: {state['results_data']['sharpe_ratio']:.2f},
Total Return: {state['results_data']['total_return']*100:.1f}%
"""

        elif section_name == "introduction":
            return f"""
Research Direction: {state['research_direction']}
Hypothesis: {state['hypothesis']}
Research Gaps: {'; '.join(state['research_gaps'][:3])}
"""

        elif section_name == "literature_review":
            return f"""
Literature Summary: {state['literature_summary']}

Papers Reviewed: {len(state['papers_reviewed'])} papers
Key Papers:
{self._format_key_papers(state['papers_reviewed'][:5])}
"""

        elif section_name == "methodology":
            return f"""
Methodology: {state['methodology']}
Experiment Plan: {json.dumps(state['experiment_plan'], indent=2)}
"""

        elif section_name == "results":
            results_summary = f"""
Performance Metrics:
- Total Return: {state['results_data']['total_return']*100:.2f}%
- CAGR: {state['results_data']['cagr']*100:.2f}%
- Sharpe Ratio: {state['results_data']['sharpe_ratio']:.2f}
- Sortino Ratio: {state['results_data']['sortino_ratio']:.2f}
- Maximum Drawdown: {state['results_data']['max_drawdown']*100:.2f}%
- Calmar Ratio: {state['results_data']['calmar_ratio']:.2f}
- Win Rate: {state['results_data']['win_rate']*100:.1f}%
- Profit Factor: {state['results_data']['profit_factor']:.2f}
- Total Trades: {state['results_data']['total_trades']}
- Average Trade Duration: {state['results_data']['avg_trade_duration']:.1f} days
"""
            return results_summary

        elif section_name == "discussion":
            return f"""
Hypothesis: {state['hypothesis']}
Expected Outcomes: {state['expected_outcomes']}
Actual Results: {json.dumps(dict(state['results_data']), indent=2)}
Validation Status: {state['validation_status']}
"""

        elif section_name == "conclusion":
            return f"""
Research Question: {state['hypothesis'][:200]}
Main Findings: {self._summarize_results(state['results_data'])}
Validation: {state['validation_status']}
"""

        elif section_name == "references":
            return self._format_references(state['papers_reviewed'])

        return ""

    def _format_key_papers(self, papers: list) -> str:
        """Format key papers for context."""
        formatted = []
        for paper in papers:
            formatted.append(
                f"- {paper['title']} ({paper['authors'][0]} et al., {paper['published'][:4]})"
            )
        return "\n".join(formatted)

    def _format_references(self, papers: list) -> str:
        """Format references section."""
        refs = []
        for i, paper in enumerate(papers, 1):
            authors = ", ".join(paper['authors'][:3])
            if len(paper['authors']) > 3:
                authors += " et al."
            refs.append(
                f"[{i}] {authors}. ({paper['published'][:4]}). {paper['title']}. "
                f"arXiv:{paper['arxiv_id']}"
            )
        return "\n".join(refs)

    def _summarize_results(self, results: Dict[str, Any]) -> str:
        """Create brief summary of results."""
        return (f"Sharpe ratio of {results['sharpe_ratio']:.2f}, "
                f"total return of {results['total_return']*100:.1f}%, "
                f"with {results['total_trades']} trades")

    def assemble_report(
        self,
        sections: Dict[str, str],
        state: ResearchState
    ) -> str:
        """
        Assemble all sections into complete report.

        Args:
            sections: Dictionary of section content
            state: Research state

        Returns:
            Complete report text
        """
        report_parts = [
            f"# {state['hypothesis'][:100]}",
            "",
            f"**Project ID**: {state['project_id']}",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Status**: {state['validation_status']}",
            "",
            "---",
            "",
        ]

        # Add sections in order
        section_order = [
            "abstract", "introduction", "literature_review",
            "methodology", "results", "discussion",
            "conclusion", "references"
        ]

        for section_name in section_order:
            if section_name in sections:
                report_parts.append(f"## {section_name.replace('_', ' ').title()}")
                report_parts.append("")
                report_parts.append(sections[section_name])
                report_parts.append("")
                report_parts.append("---")
                report_parts.append("")

        return "\n".join(report_parts)

    def polish_report(self, draft: str, state: ResearchState) -> str:
        """
        Polish and refine the report draft.

        Args:
            draft: Initial report draft
            state: Research state

        Returns:
            Polished report
        """
        prompt = f"""You are an expert academic editor specializing in quantitative finance.
Review and polish the following research report draft.

DRAFT:
{draft[:8000]}...

Tasks:
1. Fix any grammatical errors or awkward phrasing
2. Ensure consistent formatting and style
3. Verify logical flow between sections
4. Add transitions where needed
5. Ensure technical accuracy

Output the complete polished report. Maintain all sections and content, just improve the quality."""

        response = self.llm.messages.create(
            model=self.model,
            max_tokens=8000,
            temperature=0.3,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def convert_to_html_friendly(self, markdown: str) -> str:
        """
        Convert markdown to HTML-friendly format.

        Args:
            markdown: Markdown text

        Returns:
            HTML-friendly markdown
        """
        # Add table of contents
        toc = "\n## Table of Contents\n\n"
        lines = markdown.split("\n")

        for line in lines:
            if line.startswith("## ") and "Table of Contents" not in line:
                section = line.replace("## ", "")
                anchor = section.lower().replace(" ", "-")
                toc += f"- [{section}](#{anchor})\n"

        # Insert TOC after title
        parts = markdown.split("---", 1)
        if len(parts) == 2:
            return parts[0] + toc + "\n---" + parts[1]

        return markdown
