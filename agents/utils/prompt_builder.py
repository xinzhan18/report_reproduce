"""
PromptBuilder - Utilities for building structured prompts

Provides templates and builders for common prompt patterns.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing (类型系统)
# OUTPUT: 对外提供 - PromptBuilder类,提供build_ranking_prompt()等方法,
#                   构建结构化的Prompt模板
# POSITION: 系统地位 - Agent/Utils (智能体层-工具)
#                     Prompt构建工具,简化Agent的Prompt生成
#
# 注意：当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import List, Dict, Any


class PromptBuilder:
    """
    Helper class for building structured prompts.
    """

    @staticmethod
    def build_ranking_prompt(
        papers: List[Dict],
        research_direction: str
    ) -> str:
        """
        Build prompt for ranking papers by relevance.

        Args:
            papers: List of paper metadata dicts
            research_direction: Research direction query

        Returns:
            Formatted ranking prompt
        """
        papers_text = []
        for i, paper in enumerate(papers, 1):
            papers_text.append(
                f"{i}. **{paper['title']}**\n"
                f"   Authors: {', '.join(paper.get('authors', [])[:3])}\n"
                f"   Published: {paper.get('published', 'N/A')[:10]}\n"
                f"   Abstract: {paper.get('abstract', '')[:200]}...\n"
            )

        return f"""Rank these papers by relevance to the research direction: "{research_direction}"

Papers to rank:

{''.join(papers_text)}

For each paper, provide:
1. **relevance_score** (0.0 to 1.0)
2. **reasons** (list of strings explaining why relevant or not)

Scoring criteria:
- Keyword match with research direction (30%)
- Research direction fit (40%)
- Recency and impact (15%)
- Methodology novelty (15%)

Output as JSON:
{{
  "rankings": [
    {{
      "arxiv_id": "paper_id",
      "score": 0.85,
      "reasons": ["Direct keyword match", "Novel methodology", "Recent publication"]
    }},
    ...
  ]
}}
"""

    @staticmethod
    def build_section_analysis_prompt(
        section_text: str,
        section_name: str,
        research_direction: str
    ) -> str:
        """
        Build prompt for analyzing a paper section.

        Args:
            section_text: Extracted section text
            section_name: Name of section (e.g., "methodology", "results")
            research_direction: Research direction

        Returns:
            Formatted analysis prompt
        """
        if section_name.lower() == "methodology":
            return f"""Analyze this methodology section from a quantitative finance paper on "{research_direction}".

Extract and structure:

1. **Core Algorithm/Strategy**:
   - Main approach used
   - Signal generation method
   - Trading logic

2. **Technical Details**:
   - Key parameters and values
   - Data requirements (frequency, features)
   - Mathematical formulations (explain in plain language)

3. **Innovation & Novelty**:
   - What is novel compared to existing work?
   - What problem does it solve?
   - Novelty score (0-1)

4. **Implementation Feasibility**:
   - Data availability
   - Computational complexity
   - Reproducibility
   - Feasibility score (0-1)

Methodology Section:
{section_text[:3000]}

Output as JSON with keys: summary, innovations (list), parameters (dict), novelty_score, feasibility_score
"""

        elif section_name.lower() == "results":
            return f"""Analyze this results section from a quantitative finance paper.

Extract:

1. **Performance Metrics**:
   - Sharpe ratio, returns, drawdown, etc.
   - Specific numerical values

2. **Comparison with Baselines**:
   - What was compared?
   - How does the proposed method perform?

3. **Robustness Tests**:
   - What tests were performed?
   - Results of robustness analysis

4. **Key Findings**:
   - Main insights
   - Surprising results

5. **Limitations Discovered**:
   - What didn't work?
   - Constraints identified

Results Section:
{section_text[:3000]}

Output as JSON with keys: metrics (dict), comparisons (list), robustness (list), findings (list), limitations (list)
"""

        else:
            # Generic section analysis
            return f"""Analyze this {section_name} section from a paper on "{research_direction}".

Extract key information and insights.

Section Text:
{section_text[:2000]}

Output as JSON with key insights.
"""

    @staticmethod
    def build_synthesis_prompt(
        structured_insights: List[Dict],
        deep_insights: List[Dict],
        research_direction: str
    ) -> str:
        """
        Build prompt for cross-paper synthesis.

        Args:
            structured_insights: List of StructuredInsights dicts
            deep_insights: List of DeepInsights dicts
            research_direction: Research direction

        Returns:
            Formatted synthesis prompt
        """
        # Format structured insights
        structured_text = []
        for i, insight in enumerate(structured_insights, 1):
            structured_text.append(
                f"Paper {i}: {insight.get('title', 'Unknown')}\n"
                f"- Methodology: {insight.get('methodology_summary', 'N/A')[:200]}\n"
                f"- Innovation Score: {insight.get('innovation_score', 0):.2f}\n"
                f"- Key Innovations: {', '.join(insight.get('key_innovations', [])[:3])}\n\n"
            )

        # Format deep insights
        deep_text = []
        for i, insight in enumerate(deep_insights, 1):
            deep_text.append(
                f"Core Paper {i}: {insight.get('paper_id', 'Unknown')}\n"
                f"- Contribution: {insight.get('core_contribution', 'N/A')[:150]}\n"
                f"- Reproducibility: {insight.get('reproducibility_score', 0):.2f}\n\n"
            )

        return f"""You are synthesizing {len(structured_insights)} papers on "{research_direction}".

Structured Analysis Results:
{''.join(structured_text)}

Deep Analysis Results (Core Papers):
{''.join(deep_text)}

Perform comprehensive synthesis:

1. **Methodology Patterns**:
   - What are common approaches?
   - How do they differ?
   - Evolution of methods over time?

2. **Performance Trends**:
   - Typical Sharpe ratios, returns, drawdowns
   - Which approaches work best?
   - Performance vs complexity tradeoff

3. **Common Limitations**:
   - What problems remain unsolved?
   - What assumptions are limiting?
   - What data/computational constraints exist?

4. **Research Gaps** (5-7 specific gaps):
   - Unexplored parameter spaces
   - Methodology combination opportunities
   - Market/dataset coverage gaps
   - Theory-practice gaps

5. **Testable Hypotheses** (3-5 ranked hypotheses):
   - Based on identified gaps
   - Feasible with available data
   - Clear methodology
   - Measurable outcomes

Output as JSON with keys:
- literature_summary (str)
- methodology_patterns (list)
- performance_trends (list)
- common_limitations (list)
- research_gaps (list of objects with: description, severity, evidence, opportunity_score)
- hypotheses (list of objects with: statement, rationale, supporting_evidence, feasibility_score, novelty_score)
"""
