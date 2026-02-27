"""
Database Extensions for Document Memory System

Extends ResearchDatabase with methods for:
- Domain management
- Paper-domain mappings
- Analysis caching
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - json, typing, datetime, sqlite3
# OUTPUT: 对外提供 - DocumentMemoryExtensions类(Mixin)
# POSITION: 系统地位 - [Core/Persistence Layer] - 数据库扩展,添加领域管理/论文分类/分析缓存功能
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import json
from typing import List, Dict, Any, Optional
from datetime import datetime


class DocumentMemoryExtensions:
    """
    Mixin class providing document memory methods for ResearchDatabase.

    Add these methods to ResearchDatabase or use as standalone.
    """

    # ============= Domain Management =============

    def add_domain(
        self,
        name: str,
        parent_id: Optional[int] = None,
        description: str = "",
        keywords: List[str] = None
    ) -> int:
        """
        Add a domain to the taxonomy.

        Args:
            name: Domain name (e.g., "Momentum Strategies")
            parent_id: Parent domain ID (None for root domains)
            description: Domain description
            keywords: List of keywords associated with this domain

        Returns:
            Domain ID
        """
        cursor = self.conn.cursor()

        if keywords is None:
            keywords = []

        cursor.execute("""
            INSERT INTO domains (name, parent_id, description, keywords)
            VALUES (?, ?, ?, ?)
        """, (name, parent_id, description, json.dumps(keywords)))

        self.conn.commit()
        return cursor.lastrowid

    def get_domain_by_name(self, name: str) -> Optional[Dict]:
        """
        Get domain by name.

        Args:
            name: Domain name

        Returns:
            Domain dict or None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM domains WHERE name = ?", (name,))
        row = cursor.fetchone()

        if row:
            return self._domain_row_to_dict(row)
        return None

    def get_domain_by_id(self, domain_id: int) -> Optional[Dict]:
        """
        Get domain by ID.

        Args:
            domain_id: Domain ID

        Returns:
            Domain dict or None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM domains WHERE id = ?", (domain_id,))
        row = cursor.fetchone()

        if row:
            return self._domain_row_to_dict(row)
        return None

    def get_all_domains(self) -> List[Dict]:
        """
        Get all domains.

        Returns:
            List of domain dicts
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM domains ORDER BY name")
        rows = cursor.fetchall()

        return [self._domain_row_to_dict(row) for row in rows]

    def get_child_domains(self, parent_id: int) -> List[Dict]:
        """
        Get child domains of a parent.

        Args:
            parent_id: Parent domain ID

        Returns:
            List of child domain dicts
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM domains WHERE parent_id = ? ORDER BY name", (parent_id,))
        rows = cursor.fetchall()

        return [self._domain_row_to_dict(row) for row in rows]

    def get_root_domains(self) -> List[Dict]:
        """
        Get root domains (no parent).

        Returns:
            List of root domain dicts
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM domains WHERE parent_id IS NULL ORDER BY name")
        rows = cursor.fetchall()

        return [self._domain_row_to_dict(row) for row in rows]

    def update_domain_paper_count(self, domain_id: int):
        """
        Update paper count for a domain.

        Args:
            domain_id: Domain ID
        """
        cursor = self.conn.cursor()

        # Count papers in this domain
        cursor.execute("""
            SELECT COUNT(*) FROM paper_domains WHERE domain_id = ?
        """, (domain_id,))
        count = cursor.fetchone()[0]

        # Update domain
        cursor.execute("""
            UPDATE domains
            SET paper_count = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (count, domain_id))

        self.conn.commit()

    def _domain_row_to_dict(self, row) -> Dict:
        """Convert domain row to dict."""
        return {
            "id": row["id"],
            "name": row["name"],
            "parent_id": row["parent_id"],
            "description": row["description"],
            "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
            "paper_count": row["paper_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }

    # ============= Paper-Domain Mappings =============

    def add_paper_to_domain(
        self,
        arxiv_id: str,
        domain_id: int,
        relevance_score: float = 1.0,
        classified_by: str = "auto"
    ) -> int:
        """
        Map a paper to a domain.

        Args:
            arxiv_id: arXiv ID
            domain_id: Domain ID
            relevance_score: Relevance score (0-1)
            classified_by: Classification method ('keyword', 'llm', 'manual')

        Returns:
            Mapping ID
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO paper_domains (paper_id, domain_id, relevance_score, classified_by)
                VALUES (?, ?, ?, ?)
            """, (arxiv_id, domain_id, relevance_score, classified_by))

            self.conn.commit()

            # Update domain paper count
            self.update_domain_paper_count(domain_id)

            return cursor.lastrowid

        except sqlite3.IntegrityError:
            # Already exists, update instead
            cursor.execute("""
                UPDATE paper_domains
                SET relevance_score = ?, classified_by = ?, classified_at = CURRENT_TIMESTAMP
                WHERE paper_id = ? AND domain_id = ?
            """, (relevance_score, classified_by, arxiv_id, domain_id))

            self.conn.commit()
            return cursor.lastrowid

    def get_papers_by_domain(
        self,
        domain_name: str,
        limit: int = 50,
        min_relevance: float = 0.0
    ) -> List[Dict]:
        """
        Get papers in a domain.

        Args:
            domain_name: Domain name
            limit: Maximum number of papers
            min_relevance: Minimum relevance score

        Returns:
            List of paper dicts with relevance scores
        """
        cursor = self.conn.cursor()

        # Get domain ID
        domain = self.get_domain_by_name(domain_name)
        if not domain:
            return []

        domain_id = domain["id"]

        # Get papers
        cursor.execute("""
            SELECT p.*, pd.relevance_score, pd.classified_at
            FROM papers p
            JOIN paper_domains pd ON p.arxiv_id = pd.paper_id
            WHERE pd.domain_id = ? AND pd.relevance_score >= ?
            ORDER BY pd.relevance_score DESC, p.published DESC
            LIMIT ?
        """, (domain_id, min_relevance, limit))

        rows = cursor.fetchall()

        papers = []
        for row in rows:
            paper = {
                "arxiv_id": row["arxiv_id"],
                "title": row["title"],
                "authors": json.loads(row["authors"]),
                "abstract": row["abstract"],
                "published": row["published"],
                "categories": json.loads(row["categories"]),
                "url": row["url"],
                "pdf_url": row["pdf_url"],
                "relevance_score": row["relevance_score"],
                "classified_at": row["classified_at"]
            }
            papers.append(paper)

        return papers

    def get_domains_for_paper(self, arxiv_id: str) -> List[Dict]:
        """
        Get all domains a paper belongs to.

        Args:
            arxiv_id: arXiv ID

        Returns:
            List of domains with relevance scores
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT d.*, pd.relevance_score, pd.classified_at
            FROM domains d
            JOIN paper_domains pd ON d.id = pd.domain_id
            WHERE pd.paper_id = ?
            ORDER BY pd.relevance_score DESC
        """, (arxiv_id,))

        rows = cursor.fetchall()

        domains = []
        for row in rows:
            domain = self._domain_row_to_dict(row)
            domain["relevance_score"] = row["relevance_score"]
            domain["classified_at"] = row["classified_at"]
            domains.append(domain)

        return domains

    # ============= Analysis Caching =============

    def save_paper_analysis(
        self,
        arxiv_id: str,
        sections: Dict[str, str],
        structured_insights: Optional[Dict] = None,
        deep_insights: Optional[Dict] = None,
        analysis_version: str = "v1.0"
    ):
        """
        Save analysis results to cache.

        Args:
            arxiv_id: arXiv ID
            sections: Extracted sections dict
            structured_insights: StructuredInsights dict (optional)
            deep_insights: DeepInsights dict (optional)
            analysis_version: Analysis version
        """
        cursor = self.conn.cursor()

        # Calculate full text length
        full_text_length = sum(len(text) for text in sections.values())

        cursor.execute("""
            INSERT OR REPLACE INTO paper_analysis_cache
            (arxiv_id, full_text_length, sections_extracted, structured_insights, deep_insights, analysis_version)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            arxiv_id,
            full_text_length,
            json.dumps(sections),
            json.dumps(structured_insights) if structured_insights else None,
            json.dumps(deep_insights) if deep_insights else None,
            analysis_version
        ))

        self.conn.commit()

    def get_cached_analysis(self, arxiv_id: str) -> Optional[Dict]:
        """
        Get cached analysis for a paper.

        Args:
            arxiv_id: arXiv ID

        Returns:
            Analysis dict or None
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM paper_analysis_cache WHERE arxiv_id = ?
        """, (arxiv_id,))

        row = cursor.fetchone()

        if row:
            return {
                "arxiv_id": row["arxiv_id"],
                "full_text_length": row["full_text_length"],
                "sections": json.loads(row["sections_extracted"]) if row["sections_extracted"] else {},
                "structured_insights": json.loads(row["structured_insights"]) if row["structured_insights"] else None,
                "deep_insights": json.loads(row["deep_insights"]) if row["deep_insights"] else None,
                "analysis_version": row["analysis_version"],
                "analyzed_at": row["analyzed_at"]
            }

        return None

    def has_cached_analysis(self, arxiv_id: str, min_version: str = "v1.0") -> bool:
        """
        Check if paper has cached analysis.

        Args:
            arxiv_id: arXiv ID
            min_version: Minimum analysis version

        Returns:
            True if cached and up-to-date
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM paper_analysis_cache
            WHERE arxiv_id = ? AND analysis_version >= ?
        """, (arxiv_id, min_version))

        count = cursor.fetchone()[0]
        return count > 0

    def get_analysis_stats(self) -> Dict:
        """
        Get statistics about cached analyses.

        Returns:
            Stats dict
        """
        cursor = self.conn.cursor()

        # Total cached analyses
        cursor.execute("SELECT COUNT(*) FROM paper_analysis_cache")
        total_cached = cursor.fetchone()[0]

        # With structured insights
        cursor.execute("SELECT COUNT(*) FROM paper_analysis_cache WHERE structured_insights IS NOT NULL")
        with_structured = cursor.fetchone()[0]

        # With deep insights
        cursor.execute("SELECT COUNT(*) FROM paper_analysis_cache WHERE deep_insights IS NOT NULL")
        with_deep = cursor.fetchone()[0]

        # By version
        cursor.execute("SELECT analysis_version, COUNT(*) FROM paper_analysis_cache GROUP BY analysis_version")
        by_version = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_cached": total_cached,
            "with_structured_insights": with_structured,
            "with_deep_insights": with_deep,
            "by_version": by_version
        }


# Import sqlite3 for the exception
import sqlite3
