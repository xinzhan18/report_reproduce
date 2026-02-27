"""
PDF downloading and reading capabilities.

Downloads PDFs from arXiv and extracts text content for deeper analysis.
"""

import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
import time
from core.database import get_database


class PDFReader:
    """
    Handles PDF downloading and text extraction.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize PDF reader.

        Args:
            cache_dir: Directory for caching PDFs (default: data/literature/pdfs)
        """
        self.cache_dir = cache_dir or Path("data/literature/pdfs")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db = get_database()

    def download_pdf(
        self,
        arxiv_id: str,
        pdf_url: Optional[str] = None,
        force_download: bool = False
    ) -> Optional[Path]:
        """
        Download PDF from arXiv.

        Args:
            arxiv_id: arXiv paper ID
            pdf_url: PDF URL (if not provided, constructs from arXiv ID)
            force_download: Force re-download even if cached

        Returns:
            Path to downloaded PDF or None if failed
        """
        # Check if already cached
        safe_id = arxiv_id.replace("/", "_").replace(":", "_")
        pdf_path = self.cache_dir / f"{safe_id}.pdf"

        if pdf_path.exists() and not force_download:
            print(f"Using cached PDF: {pdf_path}")
            return pdf_path

        # Construct PDF URL if not provided
        if not pdf_url:
            # arXiv PDF URL format: https://arxiv.org/pdf/XXXX.XXXXX.pdf
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        try:
            print(f"Downloading PDF from {pdf_url}...")

            # Download PDF
            response = requests.get(pdf_url, timeout=60, stream=True)
            response.raise_for_status()

            # Save to file
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"PDF downloaded: {pdf_path}")

            # Update database with PDF path
            self.db.update_paper_pdf_path(arxiv_id, str(pdf_path))

            # Rate limiting (be nice to arXiv)
            time.sleep(3)

            return pdf_path

        except Exception as e:
            print(f"Error downloading PDF: {e}")
            return None

    def extract_text(self, pdf_path: Path) -> Optional[str]:
        """
        Extract text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text or None if failed
        """
        try:
            import PyPDF2

            text_parts = []

            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                num_pages = len(reader.pages)

                for page_num in range(num_pages):
                    page = reader.pages[page_num]
                    text = page.extract_text()
                    text_parts.append(text)

            full_text = "\n\n".join(text_parts)
            return full_text

        except ImportError:
            print("PyPDF2 not installed. Install with: pip install PyPDF2")
            return None

        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return None

    def extract_sections(self, text: str) -> Dict[str, str]:
        """
        Extract common paper sections from text.

        Args:
            text: Full paper text

        Returns:
            Dictionary mapping section names to content
        """
        import re

        sections = {}

        # Common section headers
        section_patterns = {
            "abstract": r"(?i)abstract\s*\n(.*?)(?=\n\d+\s+introduction|\nintroduction|\n\d)",
            "introduction": r"(?i)(?:\d+\s+)?introduction\s*\n(.*?)(?=\n\d+\s+|\n(?:related work|background|method))",
            "methodology": r"(?i)(?:\d+\s+)?(?:method|methodology|approach)\s*\n(.*?)(?=\n\d+\s+|\n(?:experiment|result))",
            "results": r"(?i)(?:\d+\s+)?results?\s*\n(.*?)(?=\n\d+\s+|\n(?:discussion|conclusion))",
            "conclusion": r"(?i)(?:\d+\s+)?conclusions?\s*\n(.*?)(?=\n(?:reference|acknowledgment|\Z))",
        }

        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, text, re.DOTALL)
            if match:
                content = match.group(1).strip()
                # Limit to first 2000 characters
                sections[section_name] = content[:2000]

        return sections

    def get_paper_summary(
        self,
        arxiv_id: str,
        download_if_missing: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive summary of a paper including PDF content.

        Args:
            arxiv_id: arXiv paper ID
            download_if_missing: Download PDF if not cached

        Returns:
            Dictionary with paper summary
        """
        # Get paper metadata from database
        paper = self.db.get_paper(arxiv_id)

        if not paper:
            return {"error": f"Paper {arxiv_id} not found in database"}

        summary = {
            "arxiv_id": arxiv_id,
            "title": paper.get("title", ""),
            "abstract": paper.get("abstract", ""),
            "has_pdf": False,
            "sections": {}
        }

        # Try to get PDF
        pdf_path = paper.get("pdf_path")

        if not pdf_path and download_if_missing:
            pdf_path = self.download_pdf(arxiv_id, paper.get("pdf_url"))

        if pdf_path and Path(pdf_path).exists():
            summary["has_pdf"] = True

            # Extract text
            text = self.extract_text(Path(pdf_path))

            if text:
                summary["full_text_length"] = len(text)
                summary["sections"] = self.extract_sections(text)

        return summary

    def search_pdf_content(
        self,
        arxiv_id: str,
        search_terms: List[str]
    ) -> Dict[str, List[str]]:
        """
        Search for specific terms in PDF content.

        Args:
            arxiv_id: arXiv paper ID
            search_terms: List of terms to search for

        Returns:
            Dictionary mapping terms to found contexts
        """
        paper = self.db.get_paper(arxiv_id)

        if not paper or not paper.get("pdf_path"):
            return {}

        pdf_path = Path(paper["pdf_path"])

        if not pdf_path.exists():
            return {}

        text = self.extract_text(pdf_path)

        if not text:
            return {}

        results = {}

        for term in search_terms:
            # Find all occurrences with context
            import re
            pattern = re.compile(f".{{0,100}}{re.escape(term)}.{{0,100}}", re.IGNORECASE)
            matches = pattern.findall(text)

            if matches:
                results[term] = matches[:5]  # Limit to 5 contexts

        return results

    def batch_download_pdfs(
        self,
        arxiv_ids: List[str],
        delay: float = 3.0
    ) -> Dict[str, bool]:
        """
        Download multiple PDFs with rate limiting.

        Args:
            arxiv_ids: List of arXiv IDs
            delay: Delay between downloads (seconds)

        Returns:
            Dictionary mapping arXiv IDs to success status
        """
        results = {}

        for arxiv_id in arxiv_ids:
            pdf_path = self.download_pdf(arxiv_id)
            results[arxiv_id] = pdf_path is not None

            # Rate limiting
            if delay > 0:
                time.sleep(delay)

        return results

    def get_cached_pdfs(self) -> List[str]:
        """
        Get list of cached PDF arXiv IDs.

        Returns:
            List of arXiv IDs with cached PDFs
        """
        cached = []

        for pdf_file in self.cache_dir.glob("*.pdf"):
            # Convert filename back to arXiv ID
            arxiv_id = pdf_file.stem.replace("_", "/", 1).replace("_", ":")
            cached.append(arxiv_id)

        return cached

    def clean_cache(self, older_than_days: int = 90) -> int:
        """
        Clean old PDFs from cache.

        Args:
            older_than_days: Remove PDFs older than this many days

        Returns:
            Number of PDFs removed
        """
        from datetime import datetime, timedelta
        import os

        threshold = datetime.now() - timedelta(days=older_than_days)
        removed = 0

        for pdf_file in self.cache_dir.glob("*.pdf"):
            mtime = datetime.fromtimestamp(os.path.getmtime(pdf_file))

            if mtime < threshold:
                pdf_file.unlink()
                removed += 1

        return removed


def extract_key_information(text: str, max_length: int = 5000) -> Dict[str, Any]:
    """
    Extract key information from paper text using heuristics.

    Args:
        text: Full paper text
        max_length: Maximum length to analyze

    Returns:
        Dictionary with extracted information
    """
    import re

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]

    info = {
        "equations_found": 0,
        "figures_mentioned": 0,
        "key_terms": [],
        "algorithms": []
    }

    # Count equations (latex-style)
    equation_patterns = [
        r'\$.*?\$',  # Inline math
        r'\\begin\{equation\}',
        r'\\begin\{align\}',
    ]

    for pattern in equation_patterns:
        matches = re.findall(pattern, text)
        info["equations_found"] += len(matches)

    # Count figure references
    fig_pattern = r'(?:Figure|Fig\.)\s+\d+'
    info["figures_mentioned"] = len(re.findall(fig_pattern, text, re.IGNORECASE))

    # Extract algorithm blocks
    algo_pattern = r'Algorithm\s+\d+:?\s*(.{0,200})'
    algorithms = re.findall(algo_pattern, text, re.IGNORECASE)
    info["algorithms"] = algorithms[:3]  # Limit to first 3

    # Extract common quantitative finance terms
    quant_terms = [
        "sharpe ratio", "volatility", "risk", "return", "portfolio",
        "arbitrage", "momentum", "factor", "alpha", "beta"
    ]

    found_terms = []
    for term in quant_terms:
        if re.search(term, text, re.IGNORECASE):
            found_terms.append(term)

    info["key_terms"] = found_terms

    return info
