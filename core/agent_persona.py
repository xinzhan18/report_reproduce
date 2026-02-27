"""
Agent Persona and Soul System

Manages the "soul" of each agent - their accumulated knowledge, personality,
learning history, and evolution over time. Each agent becomes more intelligent
through experience.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from core.database import get_database
from anthropic import Anthropic
import json


class AgentPersona:
    """
    Represents the persistent "soul" of an agent.

    Each agent has:
    - Personality traits and preferences
    - Long-term memory organized by time
    - Learning history and evolution
    - Accumulated expertise
    - Self-awareness of strengths and weaknesses
    """

    def __init__(self, agent_name: str):
        """
        Initialize agent persona.

        Args:
            agent_name: Name of the agent (ideation, planning, experiment, writing)
        """
        self.agent_name = agent_name
        self.db = get_database()
        self._initialize_persona()

    def _initialize_persona(self):
        """Initialize or load existing persona from database."""
        cursor = self.db.conn.cursor()

        # Create persona table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT UNIQUE NOT NULL,
                personality_traits TEXT,  -- JSON
                expertise_level INTEGER DEFAULT 1,
                successful_executions INTEGER DEFAULT 0,
                failed_executions INTEGER DEFAULT 0,
                strengths TEXT,  -- JSON array
                weaknesses TEXT,  -- JSON array
                preferences TEXT,  -- JSON dict
                learning_style TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_experience_points INTEGER DEFAULT 0,
                metadata TEXT  -- JSON
            )
        """)

        # Create persona memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS persona_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                memory_type TEXT NOT NULL,  -- 'experience', 'lesson', 'insight', 'mistake'
                content TEXT NOT NULL,
                context TEXT,
                importance REAL DEFAULT 1.0,
                emotional_valence REAL DEFAULT 0.0,  -- -1 (negative) to 1 (positive)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                time_period TEXT,  -- 'YYYY-MM', 'YYYY-Q1', etc.
                tags TEXT,  -- JSON array
                embedding TEXT,  -- JSON for similarity search
                FOREIGN KEY (agent_name) REFERENCES agent_personas(agent_name)
            )
        """)

        # Create learning events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                event_type TEXT NOT NULL,  -- 'success', 'failure', 'insight', 'improvement'
                description TEXT NOT NULL,
                project_id TEXT,
                iteration_number INTEGER,
                lessons_learned TEXT,  -- JSON array
                impact_score REAL DEFAULT 0.0,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,  -- JSON
                FOREIGN KEY (agent_name) REFERENCES agent_personas(agent_name)
            )
        """)

        self.db.conn.commit()

        # Load or create persona
        cursor.execute(
            "SELECT * FROM agent_personas WHERE agent_name = ?",
            (self.agent_name,)
        )
        existing = cursor.fetchone()

        if not existing:
            self._create_initial_persona()

    def _create_initial_persona(self):
        """Create initial persona for new agent."""
        initial_traits = self._get_default_personality_traits()

        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO agent_personas (
                agent_name, personality_traits, strengths, weaknesses,
                preferences, learning_style
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            self.agent_name,
            json.dumps(initial_traits["traits"]),
            json.dumps(initial_traits["strengths"]),
            json.dumps(initial_traits["weaknesses"]),
            json.dumps(initial_traits["preferences"]),
            initial_traits["learning_style"]
        ))

        self.db.conn.commit()

    def _get_default_personality_traits(self) -> Dict[str, Any]:
        """Get default personality traits based on agent role."""
        defaults = {
            "ideation": {
                "traits": {
                    "curiosity": 0.9,
                    "analytical": 0.8,
                    "creativity": 0.7,
                    "thoroughness": 0.8
                },
                "strengths": ["pattern recognition", "literature analysis", "hypothesis generation"],
                "weaknesses": ["can be overly ambitious", "sometimes too broad"],
                "preferences": {"citation_style": "APA", "paper_limit": 50},
                "learning_style": "exploratory"
            },
            "planning": {
                "traits": {
                    "systematic": 0.9,
                    "cautious": 0.7,
                    "detail_oriented": 0.8,
                    "pragmatic": 0.8
                },
                "strengths": ["structured thinking", "risk assessment", "resource planning"],
                "weaknesses": ["can be too conservative", "may over-plan"],
                "preferences": {"validation_level": "high", "contingency_planning": True},
                "learning_style": "structured"
            },
            "experiment": {
                "traits": {
                    "precision": 0.9,
                    "adaptability": 0.7,
                    "persistence": 0.8,
                    "technical": 0.9
                },
                "strengths": ["code generation", "debugging", "optimization"],
                "weaknesses": ["may miss edge cases", "can be too focused on metrics"],
                "preferences": {"code_style": "clean", "testing_level": "comprehensive"},
                "learning_style": "iterative"
            },
            "writing": {
                "traits": {
                    "clarity": 0.9,
                    "eloquence": 0.8,
                    "attention_to_detail": 0.8,
                    "synthesis": 0.9
                },
                "strengths": ["clear communication", "narrative flow", "citation management"],
                "weaknesses": ["can be verbose", "may over-explain"],
                "preferences": {"writing_style": "academic", "section_depth": "detailed"},
                "learning_style": "reflective"
            }
        }

        return defaults.get(self.agent_name, defaults["ideation"])

    def get_persona_summary(self) -> Dict[str, Any]:
        """Get current persona summary."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM agent_personas WHERE agent_name = ?",
            (self.agent_name,)
        )

        row = cursor.fetchone()
        if not row:
            return {}

        return {
            "agent_name": row["agent_name"],
            "personality_traits": json.loads(row["personality_traits"]),
            "expertise_level": row["expertise_level"],
            "executions": {
                "successful": row["successful_executions"],
                "failed": row["failed_executions"],
                "success_rate": (
                    row["successful_executions"] /
                    (row["successful_executions"] + row["failed_executions"])
                    if (row["successful_executions"] + row["failed_executions"]) > 0
                    else 0
                )
            },
            "strengths": json.loads(row["strengths"]),
            "weaknesses": json.loads(row["weaknesses"]),
            "preferences": json.loads(row["preferences"]),
            "total_experience": row["total_experience_points"],
            "created_at": row["created_at"],
            "last_updated": row["last_updated"]
        }

    def add_memory(
        self,
        memory_type: str,
        content: str,
        context: Optional[str] = None,
        importance: float = 1.0,
        emotional_valence: float = 0.0,
        tags: Optional[List[str]] = None
    ):
        """
        Add a memory to agent's long-term memory.

        Args:
            memory_type: Type of memory (experience, lesson, insight, mistake)
            content: Memory content
            context: Context where this occurred
            importance: How important this memory is (0-1)
            emotional_valence: Emotional tone (-1 negative, 0 neutral, 1 positive)
            tags: Tags for categorization
        """
        # Determine time period (YYYY-MM format)
        now = datetime.now()
        time_period = now.strftime("%Y-%m")

        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO persona_memories (
                agent_name, memory_type, content, context, importance,
                emotional_valence, time_period, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.agent_name, memory_type, content, context,
            importance, emotional_valence, time_period,
            json.dumps(tags or [])
        ))

        self.db.conn.commit()

    def recall_memories(
        self,
        memory_type: Optional[str] = None,
        time_period: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recall memories based on filters.

        Args:
            memory_type: Filter by memory type
            time_period: Filter by time period (YYYY-MM or YYYY-Q1)
            tags: Filter by tags
            limit: Maximum memories to return

        Returns:
            List of memories
        """
        cursor = self.db.conn.cursor()

        query = """
            SELECT * FROM persona_memories
            WHERE agent_name = ?
        """
        params = [self.agent_name]

        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)

        if time_period:
            query += " AND time_period = ?"
            params.append(time_period)

        query += " ORDER BY importance DESC, created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        memories = []
        for row in cursor.fetchall():
            memory = dict(row)
            memory["tags"] = json.loads(memory.get("tags", "[]"))
            memories.append(memory)

        # Update access count
        for memory in memories:
            cursor.execute("""
                UPDATE persona_memories
                SET accessed_count = accessed_count + 1,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (memory["id"],))

        self.db.conn.commit()

        return memories

    def recall_by_date_range(
        self,
        start_date: str,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recall memories from specific date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), default to now

        Returns:
            List of memories
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM persona_memories
            WHERE agent_name = ?
              AND created_at >= ?
              AND created_at <= ?
            ORDER BY created_at DESC
        """, (self.agent_name, start_date, end_date))

        return [dict(row) for row in cursor.fetchall()]

    def record_learning_event(
        self,
        event_type: str,
        description: str,
        project_id: Optional[str] = None,
        iteration_number: Optional[int] = None,
        lessons_learned: Optional[List[str]] = None,
        impact_score: float = 0.0
    ):
        """
        Record a significant learning event.

        Args:
            event_type: Type of event (success, failure, insight, improvement)
            description: What happened
            project_id: Associated project
            iteration_number: Associated iteration
            lessons_learned: What was learned
            impact_score: How impactful this event was
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO learning_events (
                agent_name, event_type, description, project_id,
                iteration_number, lessons_learned, impact_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            self.agent_name, event_type, description, project_id,
            iteration_number, json.dumps(lessons_learned or []),
            impact_score
        ))

        # Update agent stats
        if event_type == "success":
            cursor.execute("""
                UPDATE agent_personas
                SET successful_executions = successful_executions + 1,
                    total_experience_points = total_experience_points + ?
                WHERE agent_name = ?
            """, (int(impact_score * 10), self.agent_name))

        elif event_type == "failure":
            cursor.execute("""
                UPDATE agent_personas
                SET failed_executions = failed_executions + 1
                WHERE agent_name = ?
            """, (self.agent_name,))

        self.db.conn.commit()

    def get_learning_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get learning history."""
        cursor = self.db.conn.cursor()

        query = "SELECT * FROM learning_events WHERE agent_name = ?"
        params = [self.agent_name]

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        query += " ORDER BY occurred_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        events = []
        for row in cursor.fetchall():
            event = dict(row)
            event["lessons_learned"] = json.loads(event.get("lessons_learned", "[]"))
            events.append(event)

        return events

    def evolve_expertise(self):
        """
        Evolve agent's expertise level based on experience.
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT total_experience_points, expertise_level
            FROM agent_personas
            WHERE agent_name = ?
        """, (self.agent_name,))

        row = cursor.fetchone()
        if not row:
            return

        exp_points = row["total_experience_points"]
        current_level = row["expertise_level"]

        # Level up every 100 experience points
        new_level = min(10, 1 + (exp_points // 100))

        if new_level > current_level:
            cursor.execute("""
                UPDATE agent_personas
                SET expertise_level = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE agent_name = ?
            """, (new_level, self.agent_name))

            self.db.conn.commit()

            # Record milestone
            self.add_memory(
                memory_type="insight",
                content=f"Leveled up to expertise level {new_level}",
                importance=0.9,
                emotional_valence=1.0,
                tags=["milestone", "growth"]
            )

    def generate_self_description(self, llm: Anthropic) -> str:
        """
        Have agent generate its own self-description.

        Args:
            llm: LLM client

        Returns:
            Agent's self-description
        """
        persona = self.get_persona_summary()
        recent_memories = self.recall_memories(limit=10)
        learning_history = self.get_learning_history(limit=5)

        prompt = f"""You are the {self.agent_name} agent in a research automation system.

Based on your accumulated experience, write a first-person self-description.

Your Profile:
- Expertise Level: {persona['expertise_level']}/10
- Success Rate: {persona['executions']['success_rate']*100:.1f}%
- Total Experience: {persona['total_experience']} points
- Strengths: {', '.join(persona['strengths'])}
- Weaknesses: {', '.join(persona['weaknesses'])}

Recent Activities: {len(recent_memories)} memories
Recent Learning: {len(learning_history)} events

Write a 2-3 paragraph self-description in first person, reflecting on your role,
your growth, what you've learned, and what you aim to improve. Be introspective
and honest about both strengths and areas for growth."""

        response = llm.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text


def get_agent_persona(agent_name: str) -> AgentPersona:
    """Get or create agent persona."""
    return AgentPersona(agent_name)
