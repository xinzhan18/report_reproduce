"""
Document tracking and persistence system.

Tracks all documents viewed, prevents duplicate processing,
and maintains comprehensive reading history.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing, datetime, core.database.get_database, pathlib.Path, json
# OUTPUT: 对外提供 - DocumentTracker类, DeduplicationManager类
# POSITION: 系统地位 - [Core/Tracking Layer] - 文档追踪器,记录论文访问历史/防重复处理/生成阅读报告
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import List, Dict, Any, Optional
from datetime import datetime
from core.database import get_database
from pathlib import Path
import json


class DocumentTracker:
    """
    Tracks document access and reading history.
    """

    def __init__(self, project_id: str):
        """
        Initialize document tracker.

        Args:
            project_id: Project identifier
        """
        self.project_id = project_id
        self.db = get_database()

    def track_paper_access(
        self,
        arxiv_id: str,
        agent_name: str,
        access_type: str = "read",
        notes: Optional[str] = None
    ):
        """
        Track access to a paper.

        Args:
            arxiv_id: arXiv paper ID
            agent_name: Name of agent accessing paper
            access_type: Type of access (scan, read, analyze, cite)
            notes: Optional notes about the access
        """
        # Ensure paper is in database
        paper = self.db.get_paper(arxiv_id)

        if not paper:
            # Paper not in database yet, skip logging
            return

        # Log access
        self.db.log_document_access(
            arxiv_id=arxiv_id,
            project_id=self.project_id,
            agent_name=agent_name,
            access_type=access_type,
            notes=notes
        )

    def has_been_read(
        self,
        arxiv_id: str,
        by_project: bool = True
    ) -> bool:
        """
        Check if paper has been read.

        Args:
            arxiv_id: arXiv paper ID
            by_project: If True, check only for this project

        Returns:
            True if paper has been read
        """
        if by_project:
            return self.db.has_paper_been_read(arxiv_id, self.project_id)
        else:
            return self.db.has_paper_been_read(arxiv_id)

    def get_reading_history(self) -> List[Dict[str, Any]]:
        """
        Get reading history for this project.

        Returns:
            List of paper access records
        """
        papers = self.db.get_papers_by_project(self.project_id)
        return papers

    def get_access_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about document access.

        Returns:
            Dictionary with statistics
        """
        cursor = self.db.conn.cursor()

        # Total papers accessed
        cursor.execute("""
            SELECT COUNT(DISTINCT paper_id) as count
            FROM document_access_log
            WHERE project_id = ?
        """, (self.project_id,))
        total_papers = cursor.fetchone()["count"]

        # Access by type
        cursor.execute("""
            SELECT access_type, COUNT(*) as count
            FROM document_access_log
            WHERE project_id = ?
            GROUP BY access_type
        """, (self.project_id,))
        by_type = {row["access_type"]: row["count"] for row in cursor.fetchall()}

        # Access by agent
        cursor.execute("""
            SELECT agent_name, COUNT(*) as count
            FROM document_access_log
            WHERE project_id = ?
            GROUP BY agent_name
        """, (self.project_id,))
        by_agent = {row["agent_name"]: row["count"] for row in cursor.fetchall()}

        return {
            "total_papers_accessed": total_papers,
            "accesses_by_type": by_type,
            "accesses_by_agent": by_agent
        }

    def filter_unread_papers(
        self,
        paper_ids: List[str]
    ) -> List[str]:
        """
        Filter out papers that have already been read.

        Args:
            paper_ids: List of arXiv IDs

        Returns:
            List of unread arXiv IDs
        """
        unread = []

        for arxiv_id in paper_ids:
            if not self.has_been_read(arxiv_id):
                unread.append(arxiv_id)

        return unread

    def get_paper_access_history(
        self,
        arxiv_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get access history for a specific paper.

        Args:
            arxiv_id: arXiv paper ID

        Returns:
            List of access records
        """
        cursor = self.db.conn.cursor()

        cursor.execute("""
            SELECT d.*, p.title
            FROM document_access_log d
            JOIN papers p ON d.paper_id = p.id
            WHERE p.arxiv_id = ? AND d.project_id = ?
            ORDER BY d.accessed_at DESC
        """, (arxiv_id, self.project_id))

        return [dict(row) for row in cursor.fetchall()]

    def mark_as_important(self, arxiv_id: str, reason: str):
        """
        Mark a paper as important for this project.

        Args:
            arxiv_id: arXiv paper ID
            reason: Why this paper is important
        """
        self.track_paper_access(
            arxiv_id=arxiv_id,
            agent_name="user",
            access_type="important",
            notes=reason
        )

    def generate_reading_report(self) -> str:
        """
        Generate a reading report for this project.

        Returns:
            Formatted report
        """
        papers = self.get_reading_history()
        stats = self.get_access_statistics()

        report_parts = [
            f"# Reading Report - {self.project_id}\n",
            f"Generated: {datetime.now().isoformat()}\n",
            "\n## Statistics\n",
            f"- Total papers accessed: {stats['total_papers_accessed']}",
            f"- Total accesses: {sum(stats['accesses_by_type'].values())}",
            "\n### Access by Type:",
        ]

        for access_type, count in stats['accesses_by_type'].items():
            report_parts.append(f"- {access_type}: {count}")

        report_parts.append("\n### Access by Agent:")
        for agent, count in stats['accesses_by_agent'].items():
            report_parts.append(f"- {agent}: {count}")

        report_parts.append("\n## Papers Read\n")

        for paper in papers[:20]:  # Limit to 20 most recent
            import json
            authors = json.loads(paper.get("authors", "[]"))
            author_str = authors[0] if authors else "Unknown"

            report_parts.append(
                f"- **{paper.get('title', 'Untitled')}**\n"
                f"  - Author: {author_str} et al.\n"
                f"  - arXiv: {paper['arxiv_id']}\n"
                f"  - Accessed: {paper['last_accessed']}\n"
            )

        return "\n".join(report_parts)

    def export_reading_list(self, format: str = "json") -> str:
        """
        Export reading list in specified format.

        Args:
            format: Export format (json, csv, markdown)

        Returns:
            Formatted reading list
        """
        papers = self.get_reading_history()

        if format == "json":
            return json.dumps(papers, indent=2)

        elif format == "csv":
            import csv
            from io import StringIO

            output = StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=["arxiv_id", "title", "authors", "published"]
            )
            writer.writeheader()

            for paper in papers:
                writer.writerow({
                    "arxiv_id": paper["arxiv_id"],
                    "title": paper.get("title", ""),
                    "authors": paper.get("authors", ""),
                    "published": paper.get("published", "")
                })

            return output.getvalue()

        elif format == "markdown":
            lines = ["# Reading List\n"]

            for i, paper in enumerate(papers, 1):
                lines.append(
                    f"{i}. [{paper.get('title', 'Untitled')}]({paper.get('url', '')})"
                )

            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported format: {format}")


class DeduplicationManager:
    """
    Manages deduplication of papers and content.
    """

    def __init__(self):
        self.db = get_database()

    def is_duplicate_paper(
        self,
        title: str,
        threshold: float = 0.9
    ) -> Optional[str]:
        """
        Check if paper is a duplicate based on title similarity.

        Args:
            title: Paper title
            threshold: Similarity threshold (0-1)

        Returns:
            arXiv ID of duplicate if found, None otherwise
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT arxiv_id, title FROM papers")

        for row in cursor.fetchall():
            existing_title = row["title"]
            similarity = self._calculate_similarity(title, existing_title)

            if similarity >= threshold:
                return row["arxiv_id"]

        return None

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate simple string similarity (Jaccard).

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score (0-1)
        """
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def find_similar_papers(
        self,
        paper_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find papers similar to given paper.

        Args:
            paper_id: arXiv ID of reference paper
            limit: Maximum number of similar papers to return

        Returns:
            List of similar papers with similarity scores
        """
        paper = self.db.get_paper(paper_id)

        if not paper:
            return []

        reference_title = paper["title"]
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE arxiv_id != ?", (paper_id,))

        similar = []

        for row in cursor.fetchall():
            similarity = self._calculate_similarity(reference_title, row["title"])

            if similarity > 0.3:  # Minimum threshold
                similar.append({
                    **dict(row),
                    "similarity": similarity
                })

        # Sort by similarity
        similar.sort(key=lambda x: x["similarity"], reverse=True)

        return similar[:limit]
