"""
Database management for research automation system.

Provides persistent storage for papers, citations, iterations, and memories.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - sqlite3, pathlib.Path, typing, datetime, json
# OUTPUT: 对外提供 - ResearchDatabase类, get_database函数
# POSITION: 系统地位 - [Core/Persistence Layer] - SQLite数据库核心,管理papers/citations/projects/iterations/memories表
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json


class ResearchDatabase:
    """
    Central database for all research data persistence.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to database file (default: data/research.db)
        """
        if db_path is None:
            db_path = Path("data/research.db")

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create all database tables."""
        cursor = self.conn.cursor()

        # Papers table - stores all papers ever viewed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                authors TEXT NOT NULL,  -- JSON array
                abstract TEXT,
                published TEXT,
                categories TEXT,  -- JSON array
                url TEXT,
                pdf_url TEXT,
                pdf_path TEXT,  -- Local cached PDF path
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1,
                embedding TEXT,  -- JSON array for similarity search
                metadata TEXT  -- JSON for additional metadata
            )
        """)

        # Citations table - tracks which papers cite which
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                paper_id INTEGER NOT NULL,
                citation_context TEXT,  -- Where/how it was cited
                citation_key TEXT,  -- [Author2023]
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            )
        """)

        # Projects table - research projects
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT UNIQUE NOT NULL,
                research_direction TEXT NOT NULL,
                status TEXT NOT NULL,
                hypothesis TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                iteration_number INTEGER DEFAULT 0,
                parent_project_id TEXT,  -- For iteration chains
                metadata TEXT  -- JSON
            )
        """)

        # Iterations table - tracks each iteration within a project
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS iterations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                iteration_number INTEGER NOT NULL,
                agent_name TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                findings TEXT,  -- JSON array of discoveries
                issues TEXT,  -- JSON array of problems found
                improvements TEXT,  -- JSON array of suggested improvements
                metrics TEXT,  -- JSON of performance metrics
                metadata TEXT,  -- JSON
                FOREIGN KEY (project_id) REFERENCES projects(project_id)
            )
        """)

        # Memories table - long-term learning across projects
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type TEXT NOT NULL,  -- 'finding', 'issue', 'improvement', 'pattern'
                content TEXT NOT NULL,
                context TEXT,  -- Where this was learned
                project_id TEXT,
                importance REAL DEFAULT 1.0,  -- Weight for retrieval
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                tags TEXT,  -- JSON array
                embedding TEXT,  -- JSON array for similarity search
                FOREIGN KEY (project_id) REFERENCES projects(project_id)
            )
        """)

        # Agent executions table - detailed log of agent runs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                iteration_number INTEGER NOT NULL,
                agent_name TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT NOT NULL,
                input_state TEXT,  -- JSON
                output_state TEXT,  -- JSON
                api_calls INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                error_log TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(project_id)
            )
        """)

        # Document access log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                project_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                access_type TEXT NOT NULL,  -- 'scan', 'read', 'analyze', 'cite'
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (paper_id) REFERENCES papers(id),
                FOREIGN KEY (project_id) REFERENCES projects(project_id)
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_arxiv_id ON papers(arxiv_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_citations_project ON citations(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_iterations_project ON iterations(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_exec_project ON agent_executions(project_id)")

        self.conn.commit()

    # ============= Paper Management =============

    def add_paper(self, paper_data: Dict[str, Any]) -> int:
        """
        Add or update a paper in the database.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            Paper ID
        """
        cursor = self.conn.cursor()

        # Check if paper exists
        cursor.execute("SELECT id FROM papers WHERE arxiv_id = ?", (paper_data["arxiv_id"],))
        existing = cursor.fetchone()

        if existing:
            # Update access count and timestamp
            cursor.execute("""
                UPDATE papers
                SET last_accessed = CURRENT_TIMESTAMP,
                    access_count = access_count + 1
                WHERE id = ?
            """, (existing["id"],))
            self.conn.commit()
            return existing["id"]

        # Insert new paper
        cursor.execute("""
            INSERT INTO papers (
                arxiv_id, title, authors, abstract, published,
                categories, url, pdf_url, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            paper_data["arxiv_id"],
            paper_data["title"],
            json.dumps(paper_data.get("authors", [])),
            paper_data.get("abstract", ""),
            paper_data.get("published", ""),
            json.dumps(paper_data.get("categories", [])),
            paper_data.get("url", ""),
            paper_data.get("pdf_url", ""),
            json.dumps(paper_data.get("metadata", {}))
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_paper(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """Get paper by arXiv ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_papers_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all papers accessed by a project."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT p.* FROM papers p
            JOIN document_access_log d ON p.id = d.paper_id
            WHERE d.project_id = ?
            ORDER BY d.accessed_at DESC
        """, (project_id,))

        return [dict(row) for row in cursor.fetchall()]

    def update_paper_pdf_path(self, arxiv_id: str, pdf_path: str):
        """Update local PDF path for a paper."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE papers SET pdf_path = ? WHERE arxiv_id = ?
        """, (pdf_path, arxiv_id))
        self.conn.commit()

    # ============= Citation Management =============

    def add_citation(
        self,
        project_id: str,
        arxiv_id: str,
        citation_context: str,
        citation_key: str
    ) -> int:
        """Add a citation record."""
        # Get paper ID
        paper = self.get_paper(arxiv_id)
        if not paper:
            raise ValueError(f"Paper {arxiv_id} not found in database")

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO citations (project_id, paper_id, citation_context, citation_key)
            VALUES (?, ?, ?, ?)
        """, (project_id, paper["id"], citation_context, citation_key))

        self.conn.commit()
        return cursor.lastrowid

    def get_citations(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all citations for a project."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.*, p.* FROM citations c
            JOIN papers p ON c.paper_id = p.id
            WHERE c.project_id = ?
            ORDER BY c.added_at
        """, (project_id,))

        return [dict(row) for row in cursor.fetchall()]

    # ============= Project Management =============

    def create_project(self, project_id: str, research_direction: str) -> int:
        """Create new project record."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO projects (project_id, research_direction, status)
            VALUES (?, ?, 'initialized')
        """, (project_id, research_direction))

        self.conn.commit()
        return cursor.lastrowid

    def update_project(
        self,
        project_id: str,
        status: Optional[str] = None,
        hypothesis: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Update project information."""
        cursor = self.conn.cursor()

        updates = ["updated_at = CURRENT_TIMESTAMP"]
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)

        if hypothesis:
            updates.append("hypothesis = ?")
            params.append(hypothesis)

        if metadata:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        params.append(project_id)

        cursor.execute(f"""
            UPDATE projects SET {', '.join(updates)}
            WHERE project_id = ?
        """, params)

        self.conn.commit()

    # ============= Iteration Management =============

    def create_iteration(
        self,
        project_id: str,
        iteration_number: int,
        agent_name: str
    ) -> int:
        """Create new iteration record."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO iterations (
                project_id, iteration_number, agent_name, status
            ) VALUES (?, ?, ?, 'running')
        """, (project_id, iteration_number, agent_name))

        self.conn.commit()
        return cursor.lastrowid

    def update_iteration(
        self,
        iteration_id: int,
        status: Optional[str] = None,
        findings: Optional[List[str]] = None,
        issues: Optional[List[str]] = None,
        improvements: Optional[List[str]] = None,
        metrics: Optional[Dict] = None
    ):
        """Update iteration record."""
        cursor = self.conn.cursor()

        updates = ["completed_at = CURRENT_TIMESTAMP"]
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)

        if findings:
            updates.append("findings = ?")
            params.append(json.dumps(findings))

        if issues:
            updates.append("issues = ?")
            params.append(json.dumps(issues))

        if improvements:
            updates.append("improvements = ?")
            params.append(json.dumps(improvements))

        if metrics:
            updates.append("metrics = ?")
            params.append(json.dumps(metrics))

        params.append(iteration_id)

        cursor.execute(f"""
            UPDATE iterations SET {', '.join(updates)}
            WHERE id = ?
        """, params)

        self.conn.commit()

    def get_iteration_history(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all iterations for a project."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM iterations
            WHERE project_id = ?
            ORDER BY iteration_number, started_at
        """, (project_id,))

        return [dict(row) for row in cursor.fetchall()]

    # ============= Memory Management =============

    def add_memory(
        self,
        memory_type: str,
        content: str,
        context: Optional[str] = None,
        project_id: Optional[str] = None,
        importance: float = 1.0,
        tags: Optional[List[str]] = None
    ) -> int:
        """Add a memory."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO memories (
                memory_type, content, context, project_id, importance, tags
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            memory_type,
            content,
            context,
            project_id,
            importance,
            json.dumps(tags or [])
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_relevant_memories(
        self,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most relevant memories."""
        cursor = self.conn.cursor()

        if memory_type:
            cursor.execute("""
                SELECT * FROM memories
                WHERE memory_type = ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
            """, (memory_type, limit))
        else:
            cursor.execute("""
                SELECT * FROM memories
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
            """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    # ============= Document Access Logging =============

    def log_document_access(
        self,
        arxiv_id: str,
        project_id: str,
        agent_name: str,
        access_type: str,
        notes: Optional[str] = None
    ):
        """Log document access."""
        paper = self.get_paper(arxiv_id)
        if not paper:
            return

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO document_access_log (
                paper_id, project_id, agent_name, access_type, notes
            ) VALUES (?, ?, ?, ?, ?)
        """, (paper["id"], project_id, agent_name, access_type, notes))

        self.conn.commit()

    def has_paper_been_read(
        self,
        arxiv_id: str,
        project_id: Optional[str] = None
    ) -> bool:
        """Check if paper has been read before."""
        cursor = self.conn.cursor()

        if project_id:
            cursor.execute("""
                SELECT COUNT(*) as count FROM document_access_log d
                JOIN papers p ON d.paper_id = p.id
                WHERE p.arxiv_id = ? AND d.project_id = ?
            """, (arxiv_id, project_id))
        else:
            cursor.execute("""
                SELECT COUNT(*) as count FROM document_access_log d
                JOIN papers p ON d.paper_id = p.id
                WHERE p.arxiv_id = ?
            """, (arxiv_id,))

        result = cursor.fetchone()
        return result["count"] > 0

    # ============= Agent Execution Tracking =============

    def log_agent_execution(
        self,
        project_id: str,
        iteration_number: int,
        agent_name: str,
        status: str,
        api_calls: int = 0,
        tokens_used: int = 0,
        cost: float = 0.0
    ) -> int:
        """Log agent execution."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO agent_executions (
                project_id, iteration_number, agent_name, status,
                api_calls, tokens_used, cost, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            project_id, iteration_number, agent_name, status,
            api_calls, tokens_used, cost
        ))

        self.conn.commit()
        return cursor.lastrowid

    def close(self):
        """Close database connection."""
        self.conn.close()


# Global database instance
_db: Optional[ResearchDatabase] = None


def get_database() -> ResearchDatabase:
    """Get or create global database instance."""
    global _db
    if _db is None:
        _db = ResearchDatabase()
    return _db
