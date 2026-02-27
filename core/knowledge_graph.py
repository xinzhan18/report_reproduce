"""
Quantitative Finance Knowledge Graph

Structured knowledge base that evolves through research iterations.
Stores concepts, strategies, metrics, relationships, and domain expertise.
"""

from typing import Dict, Any, List, Optional, Tuple
from core.database import get_database
from anthropic import Anthropic
import json


class QuantFinanceKnowledgeGraph:
    """
    Dynamic knowledge graph for quantitative finance domain.

    Nodes represent concepts, strategies, metrics, etc.
    Edges represent relationships between them.
    Knowledge evolves as agents learn from research.
    """

    def __init__(self):
        """Initialize knowledge graph."""
        self.db = get_database()
        self._initialize_schema()
        self._populate_base_knowledge()

    def _initialize_schema(self):
        """Create knowledge graph tables."""
        cursor = self.db.conn.cursor()

        # Knowledge nodes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_type TEXT NOT NULL,  -- 'concept', 'strategy', 'metric', 'tool'
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                category TEXT,
                importance REAL DEFAULT 1.0,
                confidence REAL DEFAULT 0.5,  -- How confident we are in this knowledge
                source TEXT,  -- Where this knowledge came from
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                metadata TEXT  -- JSON
            )
        """)

        # Relationships between nodes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_node_id INTEGER NOT NULL,
                target_node_id INTEGER NOT NULL,
                relationship_type TEXT NOT NULL,  -- 'uses', 'improves', 'contradicts', 'requires'
                strength REAL DEFAULT 1.0,
                evidence TEXT,  -- Supporting evidence
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validated BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (source_node_id) REFERENCES knowledge_nodes(id),
                FOREIGN KEY (target_node_id) REFERENCES knowledge_nodes(id)
            )
        """)

        # Knowledge evolution log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_evolution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER NOT NULL,
                change_type TEXT NOT NULL,  -- 'created', 'updated', 'validated', 'deprecated'
                old_value TEXT,
                new_value TEXT,
                reason TEXT,
                project_id TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (node_id) REFERENCES knowledge_nodes(id)
            )
        """)

        self.db.conn.commit()

    def _populate_base_knowledge(self):
        """Populate with foundational quantitative finance knowledge."""
        cursor = self.db.conn.cursor()

        # Check if already populated
        cursor.execute("SELECT COUNT(*) as count FROM knowledge_nodes")
        if cursor.fetchone()["count"] > 0:
            return

        # Base concepts
        base_knowledge = [
            # Core concepts
            ("concept", "Risk-Adjusted Return", "Returns normalized by risk taken", "performance"),
            ("concept", "Market Efficiency", "Degree to which prices reflect all available information", "theory"),
            ("concept", "Mean Reversion", "Tendency for prices to return to average", "patterns"),
            ("concept", "Momentum", "Tendency for winning assets to continue winning", "patterns"),
            ("concept", "Volatility Clustering", "Periods of high/low volatility cluster together", "patterns"),

            # Metrics
            ("metric", "Sharpe Ratio", "Risk-adjusted return metric", "performance"),
            ("metric", "Sortino Ratio", "Downside risk-adjusted return", "performance"),
            ("metric", "Maximum Drawdown", "Largest peak-to-trough decline", "risk"),
            ("metric", "Calmar Ratio", "Return over maximum drawdown", "performance"),
            ("metric", "Information Ratio", "Excess return per unit of tracking error", "performance"),
            ("metric", "Win Rate", "Percentage of profitable trades", "statistics"),
            ("metric", "Profit Factor", "Gross profit divided by gross loss", "statistics"),

            # Strategies
            ("strategy", "Momentum Trading", "Buy winners, sell losers", "trend_following"),
            ("strategy", "Mean Reversion", "Buy oversold, sell overbought", "contrarian"),
            ("strategy", "Pairs Trading", "Trade correlated assets", "statistical_arbitrage"),
            ("strategy", "Factor Investing", "Exposure to risk factors", "systematic"),
            ("strategy", "Risk Parity", "Equal risk contribution", "allocation"),

            # Tools
            ("tool", "Moving Average", "Smoothed price series", "indicator"),
            ("tool", "RSI", "Relative Strength Index momentum indicator", "indicator"),
            ("tool", "Bollinger Bands", "Volatility-based bands", "indicator"),
            ("tool", "MACD", "Moving Average Convergence Divergence", "indicator"),
        ]

        for node_type, name, description, category in base_knowledge:
            cursor.execute("""
                INSERT INTO knowledge_nodes (
                    node_type, name, description, category,
                    confidence, source
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (node_type, name, description, category, 0.8, "base_knowledge"))

        # Add some relationships
        relationships = [
            ("Sharpe Ratio", "Risk-Adjusted Return", "measures"),
            ("Momentum Trading", "Momentum", "exploits"),
            ("Mean Reversion", "Mean Reversion", "exploits"),
            ("Moving Average", "Momentum Trading", "used_by"),
            ("RSI", "Mean Reversion", "used_by"),
        ]

        for source_name, target_name, rel_type in relationships:
            cursor.execute("""
                INSERT INTO knowledge_edges (
                    source_node_id, target_node_id, relationship_type, strength
                )
                SELECT s.id, t.id, ?, 0.8
                FROM knowledge_nodes s, knowledge_nodes t
                WHERE s.name = ? AND t.name = ?
            """, (rel_type, source_name, target_name))

        self.db.conn.commit()

    def add_knowledge(
        self,
        node_type: str,
        name: str,
        description: str,
        category: str,
        source: str,
        confidence: float = 0.5,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Add new knowledge to the graph.

        Args:
            node_type: Type of node
            name: Name of concept/strategy/metric
            description: Description
            category: Category for organization
            source: Where this knowledge came from
            confidence: Confidence level (0-1)
            metadata: Additional metadata

        Returns:
            Node ID
        """
        cursor = self.db.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO knowledge_nodes (
                    node_type, name, description, category,
                    confidence, source, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                node_type, name, description, category,
                confidence, source, json.dumps(metadata or {})
            ))

            node_id = cursor.lastrowid

            # Log creation
            cursor.execute("""
                INSERT INTO knowledge_evolution (
                    node_id, change_type, new_value, reason
                ) VALUES (?, 'created', ?, ?)
            """, (node_id, description, f"Added from {source}"))

            self.db.conn.commit()
            return node_id

        except:
            # Node might already exist
            cursor.execute(
                "SELECT id FROM knowledge_nodes WHERE name = ?",
                (name,)
            )
            row = cursor.fetchone()
            return row["id"] if row else -1

    def add_relationship(
        self,
        source_name: str,
        target_name: str,
        relationship_type: str,
        strength: float = 1.0,
        evidence: Optional[str] = None
    ):
        """
        Add relationship between concepts.

        Args:
            source_name: Source node name
            target_name: Target node name
            relationship_type: Type of relationship
            strength: Strength of relationship (0-1)
            evidence: Supporting evidence
        """
        cursor = self.db.conn.cursor()

        cursor.execute("""
            INSERT INTO knowledge_edges (
                source_node_id, target_node_id, relationship_type,
                strength, evidence
            )
            SELECT s.id, t.id, ?, ?, ?
            FROM knowledge_nodes s, knowledge_nodes t
            WHERE s.name = ? AND t.name = ?
        """, (relationship_type, strength, evidence, source_name, target_name))

        self.db.conn.commit()

    def update_knowledge_from_research(
        self,
        project_id: str,
        findings: List[str],
        llm: Anthropic
    ):
        """
        Update knowledge graph based on research findings.

        Args:
            project_id: Project ID
            findings: Research findings
            llm: LLM for extraction
        """
        findings_text = "\n".join(f"- {f}" for f in findings)

        prompt = f"""Extract quantitative finance knowledge from these research findings:

{findings_text}

Identify:
1. New concepts/strategies/metrics learned
2. Relationships between concepts
3. Validations or contradictions of existing knowledge

Output as JSON:
{{
  "new_knowledge": [
    {{"type": "concept/strategy/metric", "name": "...", "description": "...", "category": "..."}}
  ],
  "relationships": [
    {{"source": "...", "target": "...", "type": "uses/improves/contradicts/requires", "strength": 0-1}}
  ],
  "validations": [
    {{"concept": "...", "validation": "confirmed/refuted", "evidence": "..."}}
  ]
}}"""

        response = llm.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            content = response.content[0].text
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                json_str = content

            extracted = json.loads(json_str)

            # Add new knowledge
            for knowledge in extracted.get("new_knowledge", []):
                self.add_knowledge(
                    node_type=knowledge["type"],
                    name=knowledge["name"],
                    description=knowledge["description"],
                    category=knowledge.get("category", "general"),
                    source=f"project_{project_id}",
                    confidence=0.6
                )

            # Add relationships
            for rel in extracted.get("relationships", []):
                self.add_relationship(
                    source_name=rel["source"],
                    target_name=rel["target"],
                    relationship_type=rel["type"],
                    strength=rel.get("strength", 0.7),
                    evidence=f"From project {project_id}"
                )

            # Update validations
            for val in extracted.get("validations", []):
                self.update_confidence(
                    concept_name=val["concept"],
                    validated=val["validation"] == "confirmed",
                    evidence=val["evidence"],
                    project_id=project_id
                )

        except Exception as e:
            print(f"Error updating knowledge: {e}")

    def update_confidence(
        self,
        concept_name: str,
        validated: bool,
        evidence: str,
        project_id: str
    ):
        """Update confidence in a concept based on validation."""
        cursor = self.db.conn.cursor()

        # Get current confidence
        cursor.execute("""
            SELECT id, confidence FROM knowledge_nodes
            WHERE name = ?
        """, (concept_name,))

        row = cursor.fetchone()
        if not row:
            return

        node_id = row["id"]
        current_confidence = row["confidence"]

        # Update confidence
        if validated:
            new_confidence = min(1.0, current_confidence + 0.1)
        else:
            new_confidence = max(0.0, current_confidence - 0.15)

        cursor.execute("""
            UPDATE knowledge_nodes
            SET confidence = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_confidence, node_id))

        # Log change
        cursor.execute("""
            INSERT INTO knowledge_evolution (
                node_id, change_type, old_value, new_value,
                reason, project_id
            ) VALUES (?, 'validated', ?, ?, ?, ?)
        """, (
            node_id, str(current_confidence), str(new_confidence),
            evidence, project_id
        ))

        self.db.conn.commit()

    def get_related_knowledge(
        self,
        concept_name: str,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get knowledge related to a concept.

        Args:
            concept_name: Starting concept
            max_depth: Maximum relationship depth

        Returns:
            Related knowledge graph
        """
        cursor = self.db.conn.cursor()

        # Get starting node
        cursor.execute("""
            SELECT * FROM knowledge_nodes WHERE name = ?
        """, (concept_name,))

        start_node = cursor.fetchone()
        if not start_node:
            return {}

        # Get direct relationships
        cursor.execute("""
            SELECT e.*,
                   source.name as source_name,
                   target.name as target_name
            FROM knowledge_edges e
            JOIN knowledge_nodes source ON e.source_node_id = source.id
            JOIN knowledge_nodes target ON e.target_node_id = target.id
            WHERE source.name = ? OR target.name = ?
        """, (concept_name, concept_name))

        relationships = [dict(row) for row in cursor.fetchall()]

        return {
            "node": dict(start_node),
            "relationships": relationships
        }

    def search_knowledge(
        self,
        query: str,
        node_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search knowledge base."""
        cursor = self.db.conn.cursor()

        sql = """
            SELECT * FROM knowledge_nodes
            WHERE (name LIKE ? OR description LIKE ?)
        """
        params = [f"%{query}%", f"%{query}%"]

        if node_type:
            sql += " AND node_type = ?"
            params.append(node_type)

        sql += " ORDER BY confidence DESC, importance DESC LIMIT 10"

        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_knowledge_graph() -> QuantFinanceKnowledgeGraph:
    """Get or create knowledge graph instance."""
    return QuantFinanceKnowledgeGraph()
