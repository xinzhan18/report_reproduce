"""
Self-Reflection and Error Learning Mechanism

Agents automatically reflect on their performance, learn from mistakes,
and continuously improve. Mistakes are recorded and never repeated.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing, datetime, anthropic.Anthropic, core.agent_persona, core.database, json
# OUTPUT: 对外提供 - SelfReflectionEngine类
# POSITION: 系统地位 - [Core/Intelligence Layer] - 自我反思引擎,实现错误学习/性能反思/持续改进机制
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import Dict, Any, List, Optional
from datetime import datetime
from anthropic import Anthropic
from core.agent_persona import get_agent_persona
from core.database import get_database
import json


class SelfReflectionEngine:
    """
    Enables agents to reflect on their performance and learn from experience.
    """

    def __init__(self, agent_name: str, llm: Anthropic):
        """
        Initialize self-reflection engine.

        Args:
            agent_name: Name of the agent
            llm: LLM client for generating reflections
        """
        self.agent_name = agent_name
        self.llm = llm
        self.persona = get_agent_persona(agent_name)
        self.db = get_database()
        self._initialize_tables()

    def _initialize_tables(self):
        """Initialize reflection-related tables."""
        cursor = self.db.conn.cursor()

        # Mistakes registry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mistake_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                mistake_type TEXT NOT NULL,
                description TEXT NOT NULL,
                context TEXT,
                root_cause TEXT,
                correction TEXT,
                prevention_strategy TEXT,
                severity INTEGER DEFAULT 1,  -- 1-5
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE,
                recurrence_count INTEGER DEFAULT 1,
                project_id TEXT,
                tags TEXT  -- JSON
            )
        """)

        # Reflection sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reflection_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                session_type TEXT NOT NULL,  -- 'post_execution', 'periodic', 'triggered'
                project_id TEXT,
                reflection_content TEXT NOT NULL,
                insights TEXT,  -- JSON array
                action_items TEXT,  -- JSON array
                mood TEXT,  -- 'positive', 'negative', 'neutral'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Improvement tracker
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvement_tracker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                improvement_type TEXT NOT NULL,
                baseline_metric REAL,
                current_metric REAL,
                target_metric REAL,
                progress REAL DEFAULT 0.0,  -- 0-100%
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'in_progress'
            )
        """)

        self.db.conn.commit()

    def reflect_on_execution(
        self,
        project_id: str,
        execution_context: Dict[str, Any],
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reflect on a completed execution.

        Args:
            project_id: Project identifier
            execution_context: Context of execution (inputs, parameters, etc.)
            results: Execution results

        Returns:
            Reflection insights
        """
        # Get recent history
        persona_summary = self.persona.get_persona_summary()
        recent_mistakes = self._get_recent_mistakes(limit=5)

        # Build reflection prompt
        prompt = self._build_reflection_prompt(
            execution_context,
            results,
            persona_summary,
            recent_mistakes
        )

        # Generate reflection
        response = self.llm.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.6,
            messages=[{"role": "user", "content": prompt}]
        )

        reflection_text = response.content[0].text

        # Parse reflection
        insights = self._parse_reflection(reflection_text)

        # Save reflection session
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO reflection_sessions (
                agent_name, session_type, project_id,
                reflection_content, insights, action_items, mood
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            self.agent_name, 'post_execution', project_id,
            reflection_text,
            json.dumps(insights.get("insights", [])),
            json.dumps(insights.get("action_items", [])),
            insights.get("mood", "neutral")
        ))

        self.db.conn.commit()

        # Record mistakes if any identified
        for mistake in insights.get("mistakes", []):
            self.record_mistake(
                mistake_type=mistake.get("type", "unknown"),
                description=mistake.get("description", ""),
                context=str(execution_context),
                root_cause=mistake.get("root_cause", ""),
                correction=mistake.get("correction", ""),
                severity=mistake.get("severity", 2),
                project_id=project_id
            )

        # Update persona memories
        for insight in insights.get("insights", []):
            self.persona.add_memory(
                memory_type="insight",
                content=insight,
                context=f"Project: {project_id}",
                importance=0.7,
                emotional_valence=0.5
            )

        return insights

    def _build_reflection_prompt(
        self,
        execution_context: Dict[str, Any],
        results: Dict[str, Any],
        persona_summary: Dict[str, Any],
        recent_mistakes: List[Dict[str, Any]]
    ) -> str:
        """Build reflection prompt."""
        recent_mistakes_text = "\n".join(
            f"- {m['description']} (Severity: {m['severity']}/5)"
            for m in recent_mistakes
        ) if recent_mistakes else "No recent mistakes recorded"

        prompt = f"""You are the {self.agent_name} agent performing self-reflection.

Your Current Profile:
- Expertise Level: {persona_summary['expertise_level']}/10
- Success Rate: {persona_summary['executions']['success_rate']*100:.1f}%
- Strengths: {', '.join(persona_summary['strengths'])}
- Known Weaknesses: {', '.join(persona_summary['weaknesses'])}

Recent Mistakes to Avoid:
{recent_mistakes_text}

Last Execution Context:
{json.dumps(execution_context, indent=2)[:500]}...

Results:
{json.dumps(results, indent=2)[:500]}...

Please reflect deeply on this execution:

1. **Performance Analysis**: How well did I perform? What went right? What went wrong?

2. **Mistakes Identified**: Did I make any mistakes? What were they? Why did they happen?

3. **Learning Insights**: What did I learn from this execution?

4. **Improvement Actions**: What specific actions should I take to improve?

5. **Pattern Recognition**: Do I see any patterns in my behavior or mistakes?

Output as JSON:
{{
  "mood": "positive/negative/neutral",
  "performance_score": 0-10,
  "insights": ["insight 1", "insight 2", ...],
  "mistakes": [
    {{
      "type": "logic/execution/planning/communication",
      "description": "what went wrong",
      "root_cause": "why it happened",
      "correction": "how to fix",
      "severity": 1-5
    }}
  ],
  "action_items": ["action 1", "action 2", ...],
  "patterns_observed": ["pattern 1", "pattern 2", ...]
}}

Be honest and self-critical. The goal is continuous improvement."""

        return prompt

    def _parse_reflection(self, reflection_text: str) -> Dict[str, Any]:
        """Parse reflection text into structured data."""
        try:
            # Extract JSON from response
            if "```json" in reflection_text:
                json_str = reflection_text.split("```json")[1].split("```")[0].strip()
            elif "{" in reflection_text:
                json_str = reflection_text[reflection_text.find("{"):reflection_text.rfind("}")+1]
            else:
                json_str = reflection_text

            return json.loads(json_str)

        except:
            # Fallback parsing
            return {
                "mood": "neutral",
                "performance_score": 5,
                "insights": ["Reflection completed"],
                "mistakes": [],
                "action_items": ["Continue monitoring"],
                "patterns_observed": []
            }

    def record_mistake(
        self,
        mistake_type: str,
        description: str,
        context: str,
        root_cause: str,
        correction: str,
        severity: int = 1,
        project_id: Optional[str] = None,
        prevention_strategy: Optional[str] = None
    ):
        """
        Record a mistake for future prevention.

        Args:
            mistake_type: Type of mistake
            description: What went wrong
            context: Context where it occurred
            root_cause: Why it happened
            correction: How it was fixed
            severity: How severe (1-5)
            project_id: Associated project
            prevention_strategy: How to prevent in future
        """
        cursor = self.db.conn.cursor()

        # Check if similar mistake exists
        cursor.execute("""
            SELECT id, recurrence_count FROM mistake_registry
            WHERE agent_name = ?
              AND mistake_type = ?
              AND description LIKE ?
              AND resolved = FALSE
        """, (self.agent_name, mistake_type, f"%{description[:50]}%"))

        existing = cursor.fetchone()

        if existing:
            # Update recurrence count
            cursor.execute("""
                UPDATE mistake_registry
                SET recurrence_count = recurrence_count + 1,
                    occurred_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (existing["id"],))
        else:
            # Insert new mistake
            cursor.execute("""
                INSERT INTO mistake_registry (
                    agent_name, mistake_type, description, context,
                    root_cause, correction, prevention_strategy,
                    severity, project_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.agent_name, mistake_type, description, context,
                root_cause, correction, prevention_strategy,
                severity, project_id
            ))

        self.db.conn.commit()

        # Add to persona memory
        self.persona.add_memory(
            memory_type="mistake",
            content=description,
            context=context,
            importance=min(1.0, severity / 5.0),
            emotional_valence=-0.5,
            tags=[mistake_type, "error", "learning"]
        )

        # Record learning event
        self.persona.record_learning_event(
            event_type="failure",
            description=description,
            project_id=project_id,
            lessons_learned=[correction, prevention_strategy] if prevention_strategy else [correction],
            impact_score=severity / 5.0
        )

    def _get_recent_mistakes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent unresolved mistakes."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM mistake_registry
            WHERE agent_name = ?
              AND resolved = FALSE
            ORDER BY severity DESC, occurred_at DESC
            LIMIT ?
        """, (self.agent_name, limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_mistake_prevention_guide(self) -> str:
        """
        Generate a guide of mistakes to avoid.

        Returns:
            Formatted guide
        """
        mistakes = self._get_recent_mistakes(limit=10)

        if not mistakes:
            return "No mistakes recorded. Keep up the good work!"

        guide_parts = [
            f"# Mistake Prevention Guide for {self.agent_name.title()} Agent\n",
            f"Generated: {datetime.now().isoformat()}\n",
            "\n## Critical Mistakes to Avoid\n"
        ]

        for mistake in mistakes:
            guide_parts.append(
                f"\n### {mistake['mistake_type'].title()}: {mistake['description'][:80]}\n"
                f"- **Severity**: {mistake['severity']}/5\n"
                f"- **Root Cause**: {mistake['root_cause']}\n"
                f"- **Prevention**: {mistake['prevention_strategy'] or 'Review and validate'}\n"
                f"- **Recurrence**: {mistake['recurrence_count']} times\n"
            )

        return "\n".join(guide_parts)

    def mark_mistake_resolved(self, mistake_id: int):
        """Mark a mistake as resolved."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE mistake_registry
            SET resolved = TRUE
            WHERE id = ? AND agent_name = ?
        """, (mistake_id, self.agent_name))

        self.db.conn.commit()

    def track_improvement(
        self,
        improvement_type: str,
        baseline_metric: float,
        target_metric: float
    ) -> int:
        """
        Start tracking an improvement goal.

        Args:
            improvement_type: What to improve
            baseline_metric: Starting point
            target_metric: Goal

        Returns:
            Tracker ID
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO improvement_tracker (
                agent_name, improvement_type, baseline_metric,
                current_metric, target_metric
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            self.agent_name, improvement_type,
            baseline_metric, baseline_metric, target_metric
        ))

        self.db.conn.commit()
        return cursor.lastrowid

    def update_improvement_progress(
        self,
        tracker_id: int,
        current_metric: float
    ):
        """Update progress on improvement goal."""
        cursor = self.db.conn.cursor()

        # Get baseline and target
        cursor.execute("""
            SELECT baseline_metric, target_metric
            FROM improvement_tracker
            WHERE id = ?
        """, (tracker_id,))

        row = cursor.fetchone()
        if not row:
            return

        baseline = row["baseline_metric"]
        target = row["target_metric"]

        # Calculate progress
        if target != baseline:
            progress = ((current_metric - baseline) / (target - baseline)) * 100
            progress = max(0, min(100, progress))
        else:
            progress = 100

        # Update
        cursor.execute("""
            UPDATE improvement_tracker
            SET current_metric = ?,
                progress = ?,
                status = CASE
                    WHEN ? >= 100 THEN 'completed'
                    ELSE 'in_progress'
                END
            WHERE id = ?
        """, (current_metric, progress, progress, tracker_id))

        self.db.conn.commit()

    def periodic_self_review(self, period_days: int = 30) -> str:
        """
        Perform periodic self-review.

        Args:
            period_days: Review period in days

        Returns:
            Review summary
        """
        from datetime import timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        # Get memories from period
        memories = self.persona.recall_by_date_range(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )

        # Get learning events
        learning_events = self.persona.get_learning_history(limit=50)
        period_events = [
            e for e in learning_events
            if datetime.fromisoformat(e["occurred_at"]) >= start_date
        ]

        prompt = f"""Perform a {period_days}-day self-review for {self.agent_name} agent.

Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}

Memories from period: {len(memories)}
Learning events: {len(period_events)}

Success events: {len([e for e in period_events if e['event_type'] == 'success'])}
Failures: {len([e for e in period_events if e['event_type'] == 'failure'])}

Write a comprehensive self-review covering:
1. **Overall Performance**: How have I performed this period?
2. **Growth Areas**: What have I improved at?
3. **Persistent Challenges**: What am I still struggling with?
4. **Key Lessons**: What are my top 3 learnings?
5. **Goals for Next Period**: What should I focus on?

Write in first person, 300-400 words."""

        response = self.llm.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1500,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )

        review = response.content[0].text

        # Save review
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO reflection_sessions (
                agent_name, session_type, reflection_content, mood
            ) VALUES (?, ?, ?, ?)
        """, (self.agent_name, 'periodic', review, 'reflective'))

        self.db.conn.commit()

        return review
