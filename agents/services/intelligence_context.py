"""
IntelligenceContext - Unified interface for agent intelligence

Manages:
- Agent persona and memories (long-term, mistakes, daily logs)
- Knowledge graph queries
- System prompt building
- Execution log saving
"""

from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

from core.memory.agent_memory_manager import get_agent_memory_manager
from core.knowledge_graph import get_knowledge_graph
from core.state import ResearchState


class IntelligenceContext:
    """
    Unified intelligence context for agents.

    Provides single interface to:
    - Memory system (persona, long-term memory, mistakes)
    - Knowledge graph
    - System prompt generation
    - Daily log persistence
    """

    def __init__(self, agent_name: str):
        """
        Initialize intelligence context for an agent.

        Args:
            agent_name: Name of the agent (e.g., "ideation", "planning")
        """
        self.agent_name = agent_name
        self.memory_manager = get_agent_memory_manager(agent_name)
        self.knowledge_graph = get_knowledge_graph()
        self.system_prompt = ""
        self.memories = {}
        self.logger = logging.getLogger(f"intelligence.{agent_name}")

    def load_context(self) -> tuple[Dict[str, Any], List[Dict]]:
        """
        Load all intelligence context for the agent.

        Loads:
        - Agent persona
        - Long-term memory entries
        - Mistakes registry
        - Daily execution logs
        - Related knowledge graph nodes

        Returns:
            Tuple of (memories dict, knowledge graph nodes)
        """
        # Load memories from memory manager
        self.memories = self.memory_manager.load_all_memories()

        # Build system prompt with memories
        self.system_prompt = self._build_system_prompt(self.memories)

        # Query knowledge graph for related knowledge
        related_knowledge = self._query_knowledge_graph()

        return self.memories, related_knowledge

    def _build_system_prompt(self, memories: Dict[str, Any]) -> str:
        """
        Build system prompt incorporating memories.

        Combines:
        - Agent persona
        - Long-term memory highlights
        - Common mistakes to avoid
        - Recent daily logs (last 5)

        Args:
            memories: Dictionary containing all memory types

        Returns:
            Comprehensive system prompt
        """
        prompt_parts = []

        # 1. Agent Persona
        if "persona" in memories and memories["persona"]:
            prompt_parts.append("# Agent Persona\n")
            prompt_parts.append(memories["persona"])
            prompt_parts.append("\n\n")

        # 2. Long-term Memory
        if "long_term" in memories and memories["long_term"]:
            prompt_parts.append("# Long-term Memory\n")
            prompt_parts.append("Key learnings from past executions:\n\n")
            for i, entry in enumerate(memories["long_term"][:10], 1):  # Top 10
                prompt_parts.append(f"{i}. {entry.get('content', entry)}\n")
            prompt_parts.append("\n")

        # 3. Mistakes Registry
        if "mistakes" in memories and memories["mistakes"]:
            prompt_parts.append("# Common Mistakes to Avoid\n")
            prompt_parts.append("Learn from past errors:\n\n")
            for i, mistake in enumerate(memories["mistakes"][:5], 1):  # Top 5
                mistake_text = mistake.get('description', mistake)
                solution = mistake.get('solution', '')
                prompt_parts.append(f"{i}. ❌ {mistake_text}\n")
                if solution:
                    prompt_parts.append(f"   ✓ Solution: {solution}\n")
            prompt_parts.append("\n")

        # 4. Recent Daily Logs (context from recent executions)
        if "daily_logs" in memories and memories["daily_logs"]:
            prompt_parts.append("# Recent Execution Context\n")
            prompt_parts.append("Insights from recent runs:\n\n")
            for i, log in enumerate(memories["daily_logs"][:3], 1):  # Last 3
                project_id = log.get('project_id', 'unknown')
                reflection = log.get('reflection', '')
                if reflection:
                    prompt_parts.append(f"{i}. [Project {project_id}] {reflection}\n")
            prompt_parts.append("\n")

        return "".join(prompt_parts)

    def _query_knowledge_graph(self) -> List[Dict]:
        """
        Query knowledge graph for related knowledge.

        Searches for:
        - Agent-specific patterns and insights
        - Domain knowledge relevant to agent
        - Cross-agent collaboration patterns

        Returns:
            List of related knowledge graph nodes
        """
        try:
            related_nodes = self.knowledge_graph.search_knowledge(
                query=self.agent_name,
                node_type=None,
                limit=20
            )
            return related_nodes
        except Exception as e:
            self.logger.warning(f"Failed to query knowledge graph: {e}")
            return []

    def save_execution_log(
        self,
        project_id: str,
        execution_summary: Dict[str, Any]
    ):
        """
        Save execution log to memory system.

        Creates daily log entry with:
        - Execution log
        - Learnings extracted
        - Mistakes encountered
        - Reflection on execution

        Args:
            project_id: Project identifier
            execution_summary: Summary dict with keys:
                - log: Execution log text
                - learnings: List of learnings
                - mistakes: List of mistakes
                - reflection: Reflection text
        """
        try:
            self.memory_manager.save_daily_log(
                project_id=project_id,
                execution_log=execution_summary.get("log", ""),
                learnings=execution_summary.get("learnings", []),
                mistakes=execution_summary.get("mistakes", []),
                reflection=execution_summary.get("reflection", "")
            )
            self.logger.info(f"✓ Saved execution log for project {project_id}")
        except Exception as e:
            self.logger.error(f"Failed to save execution log: {e}")
            raise

    def update_knowledge(self, state: ResearchState):
        """
        Update knowledge graph with new learnings from execution.

        Extracts and adds:
        - Research insights
        - Methodologies discovered
        - Agent collaboration patterns

        Args:
            state: Current research state
        """
        try:
            # Extract relevant information from state
            knowledge_entries = self._extract_knowledge_from_state(state)

            # Add to knowledge graph
            for entry in knowledge_entries:
                self.knowledge_graph.add_knowledge(
                    content=entry["content"],
                    node_type=entry.get("type", "insight"),
                    metadata=entry.get("metadata", {})
                )

            self.logger.info(f"✓ Added {len(knowledge_entries)} knowledge entries")

        except Exception as e:
            self.logger.warning(f"Failed to update knowledge graph: {e}")

    def _extract_knowledge_from_state(self, state: ResearchState) -> List[Dict]:
        """
        Extract knowledge entries from research state.

        Agent-specific extraction can be overridden by subclasses.

        Args:
            state: Research state

        Returns:
            List of knowledge entries
        """
        knowledge = []

        # Extract based on agent type
        if self.agent_name == "ideation":
            if "hypothesis" in state and state["hypothesis"]:
                knowledge.append({
                    "content": f"Hypothesis: {state['hypothesis']}",
                    "type": "hypothesis",
                    "metadata": {
                        "project_id": state.get("project_id"),
                        "research_direction": state.get("research_direction")
                    }
                })

            if "research_gaps" in state and state["research_gaps"]:
                for gap in state["research_gaps"][:3]:  # Top 3
                    knowledge.append({
                        "content": f"Research Gap: {gap}",
                        "type": "research_gap",
                        "metadata": {
                            "project_id": state.get("project_id")
                        }
                    })

        elif self.agent_name == "planning":
            if "experiment_plan" in state and state["experiment_plan"]:
                knowledge.append({
                    "content": f"Experiment Plan: {state['experiment_plan'].get('approach', '')}",
                    "type": "methodology",
                    "metadata": {
                        "project_id": state.get("project_id")
                    }
                })

        # Add more agent-specific extractions as needed

        return knowledge

    def get_memory_stats(self) -> Dict[str, int]:
        """
        Get statistics about loaded memories.

        Returns:
            Dict with counts of different memory types
        """
        return {
            "persona_loaded": bool(self.memories.get("persona")),
            "long_term_entries": len(self.memories.get("long_term", [])),
            "mistakes_count": len(self.memories.get("mistakes", [])),
            "daily_logs_count": len(self.memories.get("daily_logs", []))
        }
