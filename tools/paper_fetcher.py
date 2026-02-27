"""
Paper fetching utilities for arXiv and other academic sources.
"""

import arxiv
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from core.state import PaperMetadata
from config.data_sources import ARXIV_CONFIG
import time


class PaperFetcher:
    """
    Fetches papers from arXiv and other academic sources.
    """

    def __init__(self):
        self.arxiv_client = arxiv.Client()
        self.base_url = ARXIV_CONFIG["base_url"]
        self.max_results = ARXIV_CONFIG["max_results_per_query"]

    def fetch_recent_papers(
        self,
        categories: List[str],
        days_back: int = 1,
        max_results: Optional[int] = None
    ) -> List[PaperMetadata]:
        """
        Fetch recent papers from arXiv in specified categories.

        Args:
            categories: List of arXiv categories (e.g., ["q-fin.RM", "q-fin.PM"])
            days_back: Number of days to look back (default: 1)
            max_results: Maximum number of results (default: from config)

        Returns:
            List of PaperMetadata dictionaries
        """
        if max_results is None:
            max_results = self.max_results

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Build search query for categories
        category_queries = [f"cat:{cat}" for cat in categories]
        query = " OR ".join(category_queries)

        papers = []

        try:
            # Search arXiv
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )

            for result in self.arxiv_client.results(search):
                # Filter by date
                if result.published.replace(tzinfo=None) < start_date:
                    continue

                paper = PaperMetadata(
                    arxiv_id=result.entry_id.split("/")[-1],
                    title=result.title,
                    authors=[author.name for author in result.authors],
                    abstract=result.summary,
                    published=result.published.isoformat(),
                    categories=result.categories,
                    url=result.entry_id,
                    pdf_url=result.pdf_url
                )

                papers.append(paper)

        except Exception as e:
            print(f"Error fetching papers from arXiv: {e}")

        return papers

    def fetch_papers_by_keywords(
        self,
        keywords: List[str],
        categories: Optional[List[str]] = None,
        max_results: Optional[int] = None
    ) -> List[PaperMetadata]:
        """
        Fetch papers matching specific keywords.

        Args:
            keywords: List of keywords to search for
            categories: Optional list of categories to filter by
            max_results: Maximum number of results

        Returns:
            List of PaperMetadata dictionaries
        """
        if max_results is None:
            max_results = self.max_results

        # Build keyword query
        keyword_query = " OR ".join([f'all:"{kw}"' for kw in keywords])

        # Add category filter if provided
        if categories:
            category_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query = f"({keyword_query}) AND ({category_query})"
        else:
            query = keyword_query

        papers = []

        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
                sort_order=arxiv.SortOrder.Descending
            )

            for result in self.arxiv_client.results(search):
                paper = PaperMetadata(
                    arxiv_id=result.entry_id.split("/")[-1],
                    title=result.title,
                    authors=[author.name for author in result.authors],
                    abstract=result.summary,
                    published=result.published.isoformat(),
                    categories=result.categories,
                    url=result.entry_id,
                    pdf_url=result.pdf_url
                )

                papers.append(paper)

        except Exception as e:
            print(f"Error fetching papers by keywords: {e}")

        return papers

    def fetch_paper_by_id(self, arxiv_id: str) -> Optional[PaperMetadata]:
        """
        Fetch a specific paper by arXiv ID.

        Args:
            arxiv_id: arXiv paper ID (e.g., "2301.12345")

        Returns:
            PaperMetadata or None if not found
        """
        try:
            search = arxiv.Search(id_list=[arxiv_id])
            result = next(self.arxiv_client.results(search), None)

            if result:
                return PaperMetadata(
                    arxiv_id=result.entry_id.split("/")[-1],
                    title=result.title,
                    authors=[author.name for author in result.authors],
                    abstract=result.summary,
                    published=result.published.isoformat(),
                    categories=result.categories,
                    url=result.entry_id,
                    pdf_url=result.pdf_url
                )

        except Exception as e:
            print(f"Error fetching paper {arxiv_id}: {e}")

        return None

    def download_pdf(self, paper: PaperMetadata, save_path: str) -> bool:
        """
        Download PDF for a paper.

        Args:
            paper: PaperMetadata dictionary
            save_path: Path to save the PDF

        Returns:
            True if successful, False otherwise
        """
        if not paper.get("pdf_url"):
            return False

        try:
            response = requests.get(paper["pdf_url"], timeout=30)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                f.write(response.content)

            return True

        except Exception as e:
            print(f"Error downloading PDF: {e}")
            return False

    def fetch_trending_papers(
        self,
        categories: List[str],
        days: int = 7,
        min_citations: int = 5
    ) -> List[PaperMetadata]:
        """
        Fetch trending papers (recently published with potential impact).

        Note: arXiv doesn't provide citation counts, so this is a simplified version
        that just fetches recent papers from popular categories.

        Args:
            categories: arXiv categories to search
            days: Number of days to look back
            min_citations: Minimum citations (not implemented for arXiv)

        Returns:
            List of PaperMetadata dictionaries
        """
        # For arXiv, we just fetch recent papers
        return self.fetch_recent_papers(categories, days_back=days)

    def filter_papers_by_relevance(
        self,
        papers: List[PaperMetadata],
        keywords: List[str],
        min_score: float = 0.3
    ) -> List[PaperMetadata]:
        """
        Filter papers by relevance to keywords (simple keyword matching).

        Args:
            papers: List of papers to filter
            keywords: Keywords to match against
            min_score: Minimum relevance score (0-1)

        Returns:
            Filtered list of papers
        """
        filtered = []

        for paper in papers:
            # Simple relevance scoring based on keyword matches
            text = f"{paper['title']} {paper['abstract']}".lower()
            matches = sum(1 for kw in keywords if kw.lower() in text)
            score = matches / len(keywords) if keywords else 0

            if score >= min_score:
                filtered.append(paper)

        # Sort by relevance score (descending)
        filtered.sort(key=lambda p: sum(
            1 for kw in keywords
            if kw.lower() in f"{p['title']} {p['abstract']}".lower()
        ), reverse=True)

        return filtered
