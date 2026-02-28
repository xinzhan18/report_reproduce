"""
Writing Agent - 研究报告生成

Pipeline 第四阶段：整合所有前序 Agent 的输出，生成结构化学术报告。
"""

# INPUT:  agents.base_agent (BaseAgent), core.state, tools.file_manager, json, datetime
# OUTPUT: WritingAgent 类
# POSITION: Agent层 - 写作智能体，Pipeline 第四阶段

from typing import Dict, Any
from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState
from tools.file_manager import FileManager
import json
from datetime import datetime


class WritingAgent(BaseAgent):
    """研究报告生成 Agent。"""

    def __init__(self, llm: Anthropic, file_manager: FileManager):
        super().__init__(llm, file_manager, "writing")

    def _execute(self, state: ResearchState) -> ResearchState:
        # Step 1: 创建报告结构
        self.logger.info("Creating report structure...")
        structure = self.create_report_structure(state)
        self.logger.info(f"Structured report with {len(structure)} sections")

        # Step 2: 生成各节
        self.logger.info("Generating report sections...")
        sections = {}
        for section_name, section_config in structure.items():
            self.logger.info(f"  - {section_name}...")
            content = self.generate_section(
                section_name=section_name, section_config=section_config, state=state
            )
            sections[section_name] = content
        self.logger.info("Generated all sections")

        # Step 3: 组装报告
        self.logger.info("Assembling final report...")
        report_draft = self.assemble_report(sections, state)
        state["report_draft"] = report_draft

        # Step 4: 润色
        self.logger.info("Polishing report...")
        final_report = self.polish_report(report_draft, state)
        state["final_report"] = final_report
        self.logger.info(f"Report completed ({len(final_report)} characters)")

        # Step 5: 保存
        self.save_artifact(
            content=final_report,
            project_id=state["project_id"],
            filename="final_report.md",
            subdir="reports",
        )
        self.save_artifact(
            content=self.convert_to_html_friendly(final_report),
            project_id=state["project_id"],
            filename="final_report_formatted.md",
            subdir="reports",
        )

        state["requires_human_review"] = True
        state["status"] = "completed"
        return state

    def _generate_execution_summary(self, state: ResearchState) -> Dict[str, Any]:
        report_draft = state.get("report_draft", "")
        final_report = state.get("final_report", "")
        return {
            "log": f"Report: draft={len(report_draft)} chars, final={len(final_report)} chars",
            "learnings": [f"Generated research report ({len(final_report)} characters)"],
            "mistakes": [],
            "reflection": "Report integrates findings from all previous agents",
        }

    def create_report_structure(self, state: ResearchState) -> Dict[str, Dict[str, Any]]:
        """创建报告结构。"""
        return {
            "abstract": {"max_words": 250, "required_elements": ["motivation", "method", "results", "conclusion"]},
            "introduction": {"max_words": 500, "required_elements": ["background", "problem_statement", "contribution"]},
            "literature_review": {"max_words": 800, "required_elements": ["existing_work", "gaps", "positioning"]},
            "methodology": {"max_words": 700, "required_elements": ["approach", "data", "implementation", "validation"]},
            "results": {"max_words": 600, "required_elements": ["performance_metrics", "analysis", "visualizations"]},
            "discussion": {"max_words": 500, "required_elements": ["interpretation", "implications", "limitations"]},
            "conclusion": {"max_words": 300, "required_elements": ["summary", "contributions", "future_work"]},
            "references": {"max_words": 0, "required_elements": ["cited_papers"]},
        }

    def generate_section(self, section_name: str, section_config: Dict[str, Any], state: ResearchState) -> str:
        """生成报告的某一节。"""
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

        return self.call_llm(prompt=prompt, max_tokens=2000, temperature=self.config.get("temperature", 0.4))

    def _build_section_context(self, section_name: str, state: ResearchState) -> str:
        """构建某一节的上下文信息。"""
        if section_name == "abstract":
            return f"""
Hypothesis: {state['hypothesis'][:300]}...
Key Results: Sharpe Ratio: {state['results_data']['sharpe_ratio']:.2f},
Total Return: {state['results_data']['total_return'] * 100:.1f}%
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
            return f"""
Performance Metrics:
- Total Return: {state['results_data']['total_return'] * 100:.2f}%
- CAGR: {state['results_data']['cagr'] * 100:.2f}%
- Sharpe Ratio: {state['results_data']['sharpe_ratio']:.2f}
- Sortino Ratio: {state['results_data']['sortino_ratio']:.2f}
- Maximum Drawdown: {state['results_data']['max_drawdown'] * 100:.2f}%
- Calmar Ratio: {state['results_data']['calmar_ratio']:.2f}
- Win Rate: {state['results_data']['win_rate'] * 100:.1f}%
- Profit Factor: {state['results_data']['profit_factor']:.2f}
- Total Trades: {state['results_data']['total_trades']}
- Average Trade Duration: {state['results_data']['avg_trade_duration']:.1f} days
"""
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
        formatted = []
        for paper in papers:
            formatted.append(f"- {paper['title']} ({paper['authors'][0]} et al., {paper['published'][:4]})")
        return "\n".join(formatted)

    def _format_references(self, papers: list) -> str:
        refs = []
        for i, paper in enumerate(papers, 1):
            authors = ", ".join(paper['authors'][:3])
            if len(paper['authors']) > 3:
                authors += " et al."
            refs.append(f"[{i}] {authors}. ({paper['published'][:4]}). {paper['title']}. arXiv:{paper['arxiv_id']}")
        return "\n".join(refs)

    def _summarize_results(self, results: Dict[str, Any]) -> str:
        return (f"Sharpe ratio of {results['sharpe_ratio']:.2f}, "
                f"total return of {results['total_return'] * 100:.1f}%, "
                f"with {results['total_trades']} trades")

    def assemble_report(self, sections: Dict[str, str], state: ResearchState) -> str:
        """组装完整报告。"""
        report_parts = [
            f"# {state['hypothesis'][:100]}",
            "",
            f"**Project ID**: {state['project_id']}",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Status**: {state['validation_status']}",
            "", "---", "",
        ]

        section_order = [
            "abstract", "introduction", "literature_review",
            "methodology", "results", "discussion",
            "conclusion", "references",
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
        """润色报告。"""
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

        return self.call_llm(prompt=prompt, max_tokens=8000, temperature=0.3)

    def convert_to_html_friendly(self, markdown: str) -> str:
        """添加目录。"""
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
