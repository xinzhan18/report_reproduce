"""
Citation and reference management system.

Automatically tracks citations and generates properly formatted references.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing, core.database.get_database, datetime, re
# OUTPUT: 对外提供 - CitationManager类
# POSITION: 系统地位 - [Tools/Citation Layer] - 引用管理器,支持APA/IEEE/Chicago等格式,生成参考文献列表和BibTeX
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import List, Dict, Any, Optional, Literal
from core.database import get_database
from datetime import datetime
import re


CitationStyle = Literal["APA", "IEEE", "Chicago", "Harvard", "Vancouver"]


class CitationManager:
    """
    Manages citations and references for research projects.
    """

    def __init__(self, project_id: str, citation_style: CitationStyle = "APA"):
        """
        Initialize citation manager.

        Args:
            project_id: Project identifier
            citation_style: Citation format (APA, IEEE, etc.)
        """
        self.project_id = project_id
        self.citation_style = citation_style
        self.db = get_database()
        self.citation_counter = {}  # Track citations per paper

    def cite_paper(
        self,
        arxiv_id: str,
        context: Optional[str] = None
    ) -> str:
        """
        Cite a paper and return citation key.

        Args:
            arxiv_id: arXiv ID of paper
            context: Context where paper is cited

        Returns:
            Citation key (e.g., [Smith2023])
        """
        # Get paper from database
        paper = self.db.get_paper(arxiv_id)

        if not paper:
            raise ValueError(f"Paper {arxiv_id} not found in database")

        # Generate citation key
        citation_key = self._generate_citation_key(paper)

        # Add to database
        self.db.add_citation(
            project_id=self.project_id,
            arxiv_id=arxiv_id,
            citation_context=context or "",
            citation_key=citation_key
        )

        return citation_key

    def _generate_citation_key(self, paper: Dict[str, Any]) -> str:
        """
        Generate citation key for a paper.

        Args:
            paper: Paper metadata

        Returns:
            Citation key like [Smith2023] or [Smith+2023]
        """
        import json

        authors = json.loads(paper["authors"])

        if not authors:
            return "[Unknown]"

        # Get first author's last name
        first_author = authors[0]
        last_name = first_author.split()[-1] if first_author else "Unknown"

        # Get year
        published = paper.get("published", "")
        year = published[:4] if published else "XXXX"

        # Generate key
        if len(authors) == 1:
            key = f"{last_name}{year}"
        elif len(authors) == 2:
            second_name = authors[1].split()[-1]
            key = f"{last_name}+{second_name}{year}"
        else:
            key = f"{last_name}+{year}"

        # Handle duplicates
        base_key = key
        counter = self.citation_counter.get(base_key, 0)
        self.citation_counter[base_key] = counter + 1

        if counter > 0:
            key = f"{base_key}{chr(96 + counter)}"  # a, b, c, ...

        return f"[{key}]"

    def get_all_citations(self) -> List[Dict[str, Any]]:
        """
        Get all citations for the project.

        Returns:
            List of citation records
        """
        return self.db.get_citations(self.project_id)

    def generate_bibliography(self) -> str:
        """
        Generate formatted bibliography/references section.

        Returns:
            Formatted bibliography text
        """
        citations = self.get_all_citations()

        if not citations:
            return ""

        # Sort citations by first author's last name
        sorted_citations = sorted(
            citations,
            key=lambda c: self._get_sort_key(c)
        )

        # Format according to style
        if self.citation_style == "APA":
            return self._format_apa(sorted_citations)
        elif self.citation_style == "IEEE":
            return self._format_ieee(sorted_citations)
        elif self.citation_style == "Chicago":
            return self._format_chicago(sorted_citations)
        else:
            return self._format_apa(sorted_citations)  # Default to APA

    def _get_sort_key(self, citation: Dict[str, Any]) -> str:
        """Get sorting key for citation."""
        import json
        authors = json.loads(citation.get("authors", "[]"))

        if authors:
            return authors[0].split()[-1].lower()
        return "zzz"

    def _format_apa(self, citations: List[Dict[str, Any]]) -> str:
        """
        Format citations in APA style.

        Format:
        Author, A. A., Author, B. B., & Author, C. C. (Year). Title of article.
        Journal Name, volume(issue), pages. https://doi.org/xxxxx
        """
        import json

        references = []

        for i, citation in enumerate(citations, 1):
            authors = json.loads(citation.get("authors", "[]"))
            title = citation.get("title", "")
            year = citation.get("published", "")[:4] if citation.get("published") else "n.d."
            arxiv_id = citation.get("arxiv_id", "")

            # Format authors
            if len(authors) == 0:
                author_str = "Unknown."
            elif len(authors) == 1:
                author_str = self._format_author_apa(authors[0]) + "."
            elif len(authors) <= 7:
                author_str = ", ".join(self._format_author_apa(a) for a in authors[:-1])
                author_str += f", & {self._format_author_apa(authors[-1])}."
            else:
                # More than 7 authors: list first 6, then ... then last author
                author_str = ", ".join(self._format_author_apa(a) for a in authors[:6])
                author_str += f", ... {self._format_author_apa(authors[-1])}."

            # Build reference
            ref = f"{author_str} ({year}). {title}. arXiv preprint arXiv:{arxiv_id}."

            references.append(ref)

        return "\n\n".join(references)

    def _format_author_apa(self, author_name: str) -> str:
        """Format author name for APA (Last, F. M.)"""
        parts = author_name.split()

        if len(parts) == 0:
            return "Unknown"
        elif len(parts) == 1:
            return parts[0]
        else:
            # Last name, First initial. Middle initial.
            last = parts[-1]
            initials = ". ".join(p[0] for p in parts[:-1]) + "."
            return f"{last}, {initials}"

    def _format_ieee(self, citations: List[Dict[str, Any]]) -> str:
        """
        Format citations in IEEE style.

        Format:
        [1] A. Author, B. Author, and C. Author, "Title of article,"
        Journal Abbrev., vol. x, no. x, pp. xxx-xxx, Month Year.
        """
        import json

        references = []

        for i, citation in enumerate(citations, 1):
            authors = json.loads(citation.get("authors", "[]"))
            title = citation.get("title", "")
            year = citation.get("published", "")[:4] if citation.get("published") else "n.d."
            arxiv_id = citation.get("arxiv_id", "")

            # Format authors (F. Last)
            if len(authors) == 0:
                author_str = "Unknown"
            elif len(authors) == 1:
                author_str = self._format_author_ieee(authors[0])
            elif len(authors) == 2:
                author_str = f"{self._format_author_ieee(authors[0])} and {self._format_author_ieee(authors[1])}"
            else:
                author_str = ", ".join(self._format_author_ieee(a) for a in authors[:-1])
                author_str += f", and {self._format_author_ieee(authors[-1])}"

            # Build reference
            ref = f"[{i}] {author_str}, \"{title},\" arXiv:{arxiv_id}, {year}."

            references.append(ref)

        return "\n".join(references)

    def _format_author_ieee(self, author_name: str) -> str:
        """Format author name for IEEE (F. M. Last)"""
        parts = author_name.split()

        if len(parts) == 0:
            return "Unknown"
        elif len(parts) == 1:
            return parts[0]
        else:
            last = parts[-1]
            initials = ". ".join(p[0] for p in parts[:-1]) + "."
            return f"{initials} {last}"

    def _format_chicago(self, citations: List[Dict[str, Any]]) -> str:
        """
        Format citations in Chicago style.

        Format:
        Author, First. "Title of Article." Journal Name, volume, no. issue (Year): pages.
        """
        import json

        references = []

        for citation in citations:
            authors = json.loads(citation.get("authors", "[]"))
            title = citation.get("title", "")
            year = citation.get("published", "")[:4] if citation.get("published") else "n.d."
            arxiv_id = citation.get("arxiv_id", "")

            # Format first author (Last, First)
            if len(authors) == 0:
                author_str = "Unknown"
            else:
                first_author = authors[0]
                parts = first_author.split()
                if len(parts) > 1:
                    author_str = f"{parts[-1]}, {' '.join(parts[:-1])}"
                else:
                    author_str = first_author

                # Add "et al." if more than 3 authors
                if len(authors) > 3:
                    author_str += " et al."

            # Build reference
            ref = f"{author_str}. \"{title}.\" arXiv preprint arXiv:{arxiv_id} ({year})."

            references.append(ref)

        return "\n\n".join(references)

    def get_citation_statistics(self) -> Dict[str, Any]:
        """
        Get citation statistics for the project.

        Returns:
            Dictionary with statistics
        """
        citations = self.get_all_citations()

        import json

        unique_papers = set(c["arxiv_id"] for c in citations)
        total_authors = set()

        for citation in citations:
            authors = json.loads(citation.get("authors", "[]"))
            total_authors.update(authors)

        return {
            "total_citations": len(citations),
            "unique_papers": len(unique_papers),
            "unique_authors": len(total_authors),
            "citation_style": self.citation_style
        }

    def export_bibtex(self) -> str:
        """
        Export citations as BibTeX format.

        Returns:
            BibTeX formatted string
        """
        import json

        citations = self.get_all_citations()
        bibtex_entries = []

        for citation in citations:
            authors = json.loads(citation.get("authors", "[]"))
            title = citation.get("title", "")
            year = citation.get("published", "")[:4] if citation.get("published") else ""
            arxiv_id = citation.get("arxiv_id", "")

            # Generate BibTeX key
            if authors:
                first_author_last = authors[0].split()[-1].lower()
                key = f"{first_author_last}{year}"
            else:
                key = f"unknown{year}"

            # Format authors for BibTeX
            author_str = " and ".join(authors)

            entry = f"""@article{{{key},
  author = {{{author_str}}},
  title = {{{title}}},
  journal = {{arXiv preprint arXiv:{arxiv_id}}},
  year = {{{year}}},
  eprint = {{{arxiv_id}}},
  archivePrefix = {{arXiv}}
}}"""

            bibtex_entries.append(entry)

        return "\n\n".join(bibtex_entries)

    def validate_citations(self) -> List[str]:
        """
        Validate all citations and return list of issues.

        Returns:
            List of validation issues
        """
        citations = self.get_all_citations()
        issues = []

        for citation in citations:
            # Check for missing information
            if not citation.get("title"):
                issues.append(f"Citation {citation['citation_key']} missing title")

            if not citation.get("authors"):
                issues.append(f"Citation {citation['citation_key']} missing authors")

            if not citation.get("published"):
                issues.append(f"Citation {citation['citation_key']} missing publication date")

        return issues
