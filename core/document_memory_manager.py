"""
DocumentMemoryManager - Unified interface for document memory system

Provides intelligent paper retrieval based on:
- Domain taxonomy
- Semantic similarity
- Reading history
- Analysis caching
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing, logging, pathlib.Path, core.state.PaperMetadata, core.database, core.database_extensions, tools.document_tracker
# OUTPUT: 对外提供 - DocumentMemoryManager类, get_document_memory_manager函数
# POSITION: 系统地位 - [Core/Memory Layer] - 文档记忆管理器,提供智能论文检索/领域分类/阅读历史/分析缓存
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import List, Dict, Optional, Any
import logging
from pathlib import Path

from core.state import PaperMetadata
from core.database import ResearchDatabase
from core.database_extensions import DocumentMemoryExtensions
from tools.document_tracker import DocumentTracker


class DocumentMemoryManager:
    """
    Manages document memory and intelligent paper retrieval.

    Features:
    - Domain-based retrieval
    - Semantic search (future: embeddings)
    - Reading history tracking
    - Analysis result caching
    - Smart recommendations
    """

    def __init__(self, db: Optional[ResearchDatabase] = None):
        """
        Initialize document memory manager.

        Args:
            db: ResearchDatabase instance (creates new if None)
        """
        if db is None:
            from core.database import get_database
            self.db = get_database()
        else:
            self.db = db

        # Add extension methods to database
        self._add_extensions()

        self.tracker = DocumentTracker(self.db)
        self.logger = logging.getLogger("document_memory")

    def _add_extensions(self):
        """Add DocumentMemoryExtensions methods to database instance."""
        # Mix in extension methods
        for method_name in dir(DocumentMemoryExtensions):
            if not method_name.startswith('_'):
                method = getattr(DocumentMemoryExtensions, method_name)
                if callable(method):
                    # Bind method to database instance
                    bound_method = method.__get__(self.db, type(self.db))
                    setattr(self.db, method_name, bound_method)

    def retrieve_by_domain(
        self,
        domain: str,
        exclude_read: bool = True,
        project_id: Optional[str] = None,
        limit: int = 50,
        min_relevance: float = 0.5
    ) -> List[PaperMetadata]:
        """
        Retrieve papers by domain.

        Args:
            domain: Domain name (e.g., "Momentum Strategies")
            exclude_read: Whether to filter out already-read papers
            project_id: Project ID for read filtering
            limit: Maximum number of papers
            min_relevance: Minimum relevance score (0-1)

        Returns:
            List of PaperMetadata
        """
        self.logger.info(f"Retrieving papers from domain: {domain}")

        # Get papers from database
        papers = self.db.get_papers_by_domain(
            domain_name=domain,
            limit=limit * 2,  # Get more initially for filtering
            min_relevance=min_relevance
        )

        self.logger.info(f"Found {len(papers)} papers in domain")

        # Filter out already-read papers if requested
        if exclude_read and project_id:
            paper_ids = [p["arxiv_id"] for p in papers]
            unread_ids = self.tracker.filter_unread_papers(
                paper_ids=paper_ids,
                project_id=project_id
            )

            papers = [p for p in papers if p["arxiv_id"] in unread_ids]
            self.logger.info(f"After filtering read papers: {len(papers)} remaining")

        # Sort by relevance score
        papers.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        return papers[:limit]

    def retrieve_by_semantic_search(
        self,
        query: str,
        domains: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[PaperMetadata]:
        """
        Semantic search for papers (future: use embeddings).

        Currently falls back to keyword matching.

        Args:
            query: Search query
            domains: Optional list of domains to search within
            limit: Maximum results

        Returns:
            List of PaperMetadata
        """
        self.logger.info(f"Semantic search for: {query}")

        # TODO: Implement embeddings-based search
        # For now, fallback to keyword search within domains

        if domains:
            all_papers = []
            for domain in domains:
                domain_papers = self.db.get_papers_by_domain(
                    domain_name=domain,
                    limit=100
                )
                all_papers.extend(domain_papers)

            # Remove duplicates
            seen_ids = set()
            unique_papers = []
            for paper in all_papers:
                if paper["arxiv_id"] not in seen_ids:
                    seen_ids.add(paper["arxiv_id"])
                    unique_papers.append(paper)

            # Simple keyword matching
            query_keywords = query.lower().split()
            scored_papers = []

            for paper in unique_papers:
                score = self._calculate_keyword_relevance(paper, query_keywords)
                if score > 0:
                    paper["search_score"] = score
                    scored_papers.append(paper)

            # Sort by score
            scored_papers.sort(key=lambda x: x["search_score"], reverse=True)
            return scored_papers[:limit]

        else:
            self.logger.warning("Semantic search without domains not yet implemented")
            return []

    def suggest_next_papers(
        self,
        project_id: str,
        based_on_recent: int = 5,
        limit: int = 10
    ) -> List[PaperMetadata]:
        """
        Suggest papers based on reading history.

        Args:
            project_id: Project ID
            based_on_recent: Number of recent papers to base suggestions on
            limit: Maximum suggestions

        Returns:
            List of suggested PaperMetadata
        """
        self.logger.info(f"Generating suggestions for project {project_id}")

        # Get reading history
        recent_papers = self.tracker.get_reading_history(
            project_id=project_id,
            limit=based_on_recent
        )

        if not recent_papers:
            self.logger.warning("No reading history found")
            return []

        # Get domains of recent papers
        all_domains = []
        for paper in recent_papers:
            paper_domains = self.db.get_domains_for_paper(paper["arxiv_id"])
            all_domains.extend(paper_domains)

        # Count domain frequencies
        domain_counts = {}
        for domain in all_domains:
            domain_name = domain["name"]
            domain_counts[domain_name] = domain_counts.get(domain_name, 0) + 1

        # Get papers from most frequent domains
        suggestions = []
        for domain_name in sorted(domain_counts, key=domain_counts.get, reverse=True):
            domain_papers = self.retrieve_by_domain(
                domain=domain_name,
                exclude_read=True,
                project_id=project_id,
                limit=5
            )
            suggestions.extend(domain_papers)

            if len(suggestions) >= limit:
                break

        # Remove duplicates and limit
        seen_ids = set()
        unique_suggestions = []
        for paper in suggestions:
            if paper["arxiv_id"] not in seen_ids:
                seen_ids.add(paper["arxiv_id"])
                unique_suggestions.append(paper)

                if len(unique_suggestions) >= limit:
                    break

        self.logger.info(f"Generated {len(unique_suggestions)} suggestions")
        return unique_suggestions

    def save_analysis_results(
        self,
        arxiv_id: str,
        sections: Dict[str, str],
        structured_insights: Optional[Dict] = None,
        domains: Optional[List[str]] = None
    ):
        """
        Save analysis results to cache.

        Args:
            arxiv_id: arXiv ID
            sections: Extracted paper sections
            structured_insights: StructuredInsights dict
            domains: List of domain names to associate with
        """
        self.logger.info(f"Saving analysis for {arxiv_id}")

        # Save to cache
        self.db.save_paper_analysis(
            arxiv_id=arxiv_id,
            sections=sections,
            structured_insights=structured_insights
        )

        # Add to domains
        if domains:
            for domain_name in domains:
                domain = self.db.get_domain_by_name(domain_name)
                if domain:
                    self.db.add_paper_to_domain(
                        arxiv_id=arxiv_id,
                        domain_id=domain["id"],
                        relevance_score=0.8,  # Default score
                        classified_by="analysis"
                    )
                    self.logger.info(f"Added {arxiv_id} to domain: {domain_name}")

    def get_cached_analysis(self, arxiv_id: str) -> Optional[Dict]:
        """
        Get cached analysis for a paper.

        Args:
            arxiv_id: arXiv ID

        Returns:
            Cached analysis dict or None
        """
        return self.db.get_cached_analysis(arxiv_id)

    def has_analysis_cache(self, arxiv_id: str) -> bool:
        """
        Check if paper has cached analysis.

        Args:
            arxiv_id: arXiv ID

        Returns:
            True if cached
        """
        return self.db.has_cached_analysis(arxiv_id)

    def get_memory_stats(self) -> Dict:
        """
        Get statistics about document memory.

        Returns:
            Stats dict
        """
        # Domain stats
        all_domains = self.db.get_all_domains()
        root_domains = self.db.get_root_domains()

        # Analysis stats
        analysis_stats = self.db.get_analysis_stats()

        # Paper count
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM papers")
        total_papers = cursor.fetchone()[0]

        # Classified papers
        cursor.execute("SELECT COUNT(DISTINCT paper_id) FROM paper_domains")
        classified_papers = cursor.fetchone()[0]

        return {
            "total_papers": total_papers,
            "classified_papers": classified_papers,
            "classification_rate": classified_papers / total_papers if total_papers > 0 else 0,
            "total_domains": len(all_domains),
            "root_domains": len(root_domains),
            "analysis_cache": analysis_stats
        }

    def _calculate_keyword_relevance(self, paper: Dict, keywords: List[str]) -> float:
        """
        Calculate keyword relevance score.

        Args:
            paper: Paper dict
            keywords: List of keywords

        Returns:
            Relevance score (0-1)
        """
        # Combine title and abstract
        text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()

        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword in text)

        # Normalize by keyword count
        return matches / len(keywords) if keywords else 0


# Singleton instance
_document_memory_manager = None


def get_document_memory_manager() -> DocumentMemoryManager:
    """
    Get singleton DocumentMemoryManager instance.

    Returns:
        DocumentMemoryManager instance
    """
    global _document_memory_manager
    if _document_memory_manager is None:
        _document_memory_manager = DocumentMemoryManager()
    return _document_memory_manager
