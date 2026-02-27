"""
Iteration memory and learning system.

Records discoveries, issues, and improvements from each iteration,
enabling agents to learn and improve over time.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing, datetime, core.database.get_database, anthropic.Anthropic, json
# OUTPUT: 对外提供 - IterationMemory类, IterationAnalyzer类
# POSITION: 系统地位 - [Core/Memory Layer] - 迭代记忆系统,记录发现/问题/改进建议,支持跨迭代学习
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import List, Dict, Any, Optional
from datetime import datetime
from core.database import get_database
from anthropic import Anthropic
import json


class IterationMemory:
    """
    Manages iteration history and learning for continuous improvement.
    """

    def __init__(self, project_id: str):
        """
        Initialize iteration memory.

        Args:
            project_id: Project identifier
        """
        self.project_id = project_id
        self.db = get_database()
        self.current_iteration = 0

    def start_iteration(self, iteration_number: int, agent_name: str) -> int:
        """
        Start a new iteration.

        Args:
            iteration_number: Iteration number
            agent_name: Name of agent starting iteration

        Returns:
            Iteration ID
        """
        self.current_iteration = iteration_number

        iteration_id = self.db.create_iteration(
            project_id=self.project_id,
            iteration_number=iteration_number,
            agent_name=agent_name
        )

        return iteration_id

    def record_finding(
        self,
        finding: str,
        importance: float = 1.0,
        tags: Optional[List[str]] = None
    ):
        """
        Record a discovery or finding from current iteration.

        Args:
            finding: Description of what was discovered
            importance: Importance score (0-1)
            tags: Optional tags for categorization
        """
        self.db.add_memory(
            memory_type="finding",
            content=finding,
            context=f"Project {self.project_id}, Iteration {self.current_iteration}",
            project_id=self.project_id,
            importance=importance,
            tags=tags
        )

    def record_issue(
        self,
        issue: str,
        severity: str = "medium",
        tags: Optional[List[str]] = None
    ):
        """
        Record a problem or issue encountered.

        Args:
            issue: Description of the issue
            severity: Severity level (low, medium, high)
            tags: Optional tags
        """
        importance_map = {"low": 0.3, "medium": 0.6, "high": 0.9}

        self.db.add_memory(
            memory_type="issue",
            content=issue,
            context=f"Project {self.project_id}, Iteration {self.current_iteration}, Severity: {severity}",
            project_id=self.project_id,
            importance=importance_map.get(severity, 0.6),
            tags=tags or [severity]
        )

    def record_improvement(
        self,
        improvement: str,
        category: str = "general",
        tags: Optional[List[str]] = None
    ):
        """
        Record a suggested improvement for future iterations.

        Args:
            improvement: Description of improvement
            category: Category (code, methodology, performance, etc.)
            tags: Optional tags
        """
        self.db.add_memory(
            memory_type="improvement",
            content=improvement,
            context=f"Project {self.project_id}, Iteration {self.current_iteration}, Category: {category}",
            project_id=self.project_id,
            importance=0.8,
            tags=tags or [category]
        )

    def record_pattern(
        self,
        pattern: str,
        context: str,
        tags: Optional[List[str]] = None
    ):
        """
        Record an observed pattern for future reference.

        Args:
            pattern: Description of pattern
            context: Context where pattern was observed
            tags: Optional tags
        """
        self.db.add_memory(
            memory_type="pattern",
            content=pattern,
            context=context,
            project_id=self.project_id,
            importance=0.7,
            tags=tags
        )

    def complete_iteration(
        self,
        iteration_id: int,
        status: str,
        findings: List[str],
        issues: List[str],
        improvements: List[str],
        metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Mark iteration as complete with summary.

        Args:
            iteration_id: Iteration ID
            status: Final status (success, partial, failed)
            findings: List of findings
            issues: List of issues
            improvements: List of improvements
            metrics: Optional performance metrics
        """
        self.db.update_iteration(
            iteration_id=iteration_id,
            status=status,
            findings=findings,
            issues=issues,
            improvements=improvements,
            metrics=metrics
        )

    def get_previous_findings(self, limit: int = 10) -> List[str]:
        """
        Get findings from previous iterations.

        Args:
            limit: Maximum number of findings to retrieve

        Returns:
            List of finding descriptions
        """
        memories = self.db.get_relevant_memories(memory_type="finding", limit=limit)
        return [m["content"] for m in memories]

    def get_previous_issues(self, limit: int = 10) -> List[str]:
        """
        Get issues from previous iterations.

        Args:
            limit: Maximum number of issues to retrieve

        Returns:
            List of issue descriptions
        """
        memories = self.db.get_relevant_memories(memory_type="issue", limit=limit)
        return [m["content"] for m in memories]

    def get_previous_improvements(self, limit: int = 10) -> List[str]:
        """
        Get improvement suggestions from previous iterations.

        Args:
            limit: Maximum number to retrieve

        Returns:
            List of improvement suggestions
        """
        memories = self.db.get_relevant_memories(memory_type="improvement", limit=limit)
        return [m["content"] for m in memories]

    def get_iteration_summary(self) -> str:
        """
        Get a formatted summary of all previous iterations.

        Returns:
            Formatted summary text
        """
        iterations = self.db.get_iteration_history(self.project_id)

        if not iterations:
            return "No previous iterations found."

        summary_parts = [
            "# Previous Iteration Summary\n",
            f"Total iterations: {len(iterations)}\n"
        ]

        for iteration in iterations:
            iter_num = iteration["iteration_number"]
            agent = iteration["agent_name"]
            status = iteration["status"]

            summary_parts.append(f"\n## Iteration {iter_num} ({agent})")
            summary_parts.append(f"Status: {status}")

            # Findings
            findings = json.loads(iteration.get("findings", "[]"))
            if findings:
                summary_parts.append("\n### Findings:")
                for finding in findings:
                    summary_parts.append(f"- {finding}")

            # Issues
            issues = json.loads(iteration.get("issues", "[]"))
            if issues:
                summary_parts.append("\n### Issues:")
                for issue in issues:
                    summary_parts.append(f"- {issue}")

            # Improvements
            improvements = json.loads(iteration.get("improvements", "[]"))
            if improvements:
                summary_parts.append("\n### Suggested Improvements:")
                for improvement in improvements:
                    summary_parts.append(f"- {improvement}")

        return "\n".join(summary_parts)

    def generate_learning_insights(self, llm: Anthropic) -> str:
        """
        Use LLM to generate insights from iteration history.

        Args:
            llm: LLM client

        Returns:
            Generated insights
        """
        history = self.get_iteration_summary()

        if history == "No previous iterations found.":
            return "No previous iterations to learn from."

        prompt = f"""Analyze the following iteration history and provide key insights and recommendations:

{history}

Please provide:
1. **Key Learnings**: What patterns emerged across iterations?
2. **Common Issues**: What problems appeared repeatedly?
3. **Successful Approaches**: What worked well?
4. **Recommendations**: What should be done differently in the next iteration?

Be specific and actionable."""

        response = llm.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def get_metrics_trend(self) -> Dict[str, List[float]]:
        """
        Get trends in metrics across iterations.

        Returns:
            Dictionary mapping metric names to values over time
        """
        iterations = self.db.get_iteration_history(self.project_id)

        trends = {}

        for iteration in iterations:
            metrics = json.loads(iteration.get("metrics", "{}"))

            for metric_name, value in metrics.items():
                if metric_name not in trends:
                    trends[metric_name] = []

                trends[metric_name].append(float(value))

        return trends

    def should_continue_iterating(
        self,
        max_iterations: int = 5,
        improvement_threshold: float = 0.05
    ) -> tuple[bool, str]:
        """
        Determine if another iteration should be attempted.

        Args:
            max_iterations: Maximum allowed iterations
            improvement_threshold: Minimum improvement to continue

        Returns:
            Tuple of (should_continue, reason)
        """
        iterations = self.db.get_iteration_history(self.project_id)

        if len(iterations) >= max_iterations:
            return False, f"Reached maximum iterations ({max_iterations})"

        if len(iterations) < 2:
            return True, "Insufficient data to assess"

        # Check if metrics are improving
        trends = self.get_metrics_trend()

        if "sharpe_ratio" in trends and len(trends["sharpe_ratio"]) >= 2:
            recent_sharpe = trends["sharpe_ratio"][-2:]
            improvement = recent_sharpe[-1] - recent_sharpe[-2]

            if improvement < improvement_threshold:
                return False, f"Insufficient improvement (Sharpe: {improvement:.3f})"

        return True, "Continuing to improve"


class IterationAnalyzer:
    """
    Analyzes results and generates structured feedback for next iteration.
    """

    def __init__(self, llm: Anthropic):
        self.llm = llm

    def analyze_results(
        self,
        hypothesis: str,
        methodology: str,
        results: Dict[str, Any],
        expected_outcomes: str
    ) -> Dict[str, List[str]]:
        """
        Analyze experiment results and generate structured feedback.

        Args:
            hypothesis: Original hypothesis
            methodology: Methodology used
            results: Experiment results
            expected_outcomes: Expected outcomes

        Returns:
            Dictionary with findings, issues, improvements
        """
        results_summary = json.dumps(results, indent=2)

        prompt = f"""Analyze the following experiment results and provide structured feedback:

**Hypothesis**: {hypothesis}

**Methodology**: {methodology}

**Expected Outcomes**: {expected_outcomes}

**Actual Results**:
{results_summary}

Please provide:

1. **Findings**: What did we discover? (3-5 key findings)
2. **Issues**: What problems or limitations were observed? (2-4 issues)
3. **Improvements**: Specific suggestions for next iteration (3-5 improvements)

Format your response as JSON:
{{
  "findings": ["finding 1", "finding 2", ...],
  "issues": ["issue 1", "issue 2", ...],
  "improvements": ["improvement 1", "improvement 2", ...]
}}"""

        response = self.llm.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text

        # Parse JSON response
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                json_str = content

            feedback = json.loads(json_str)

            return {
                "findings": feedback.get("findings", []),
                "issues": feedback.get("issues", []),
                "improvements": feedback.get("improvements", [])
            }

        except:
            # Fallback if JSON parsing fails
            return {
                "findings": ["Analysis completed"],
                "issues": ["Unable to parse structured feedback"],
                "improvements": ["Review analysis manually"]
            }
