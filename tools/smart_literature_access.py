"""
Smart Literature Access Manager

Intelligent system for accessing academic literature with multiple fallback strategies.
Handles paywalls, access restrictions, and finds alternative sources automatically.
"""

from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import requests
from core.database import get_database
import time
import json


class LiteratureAccessManager:
    """
    Manages intelligent access to academic literature.

    Tries multiple sources in order of preference:
    1. arXiv (free, no paywall)
    2. Open Access repositories
    3. Institutional access (if configured)
    4. Sci-Hub (as last resort, user must enable)
    5. Request from author
    """

    def __init__(self):
        """Initialize access manager."""
        self.db = get_database()
        self._initialize_tables()
        self.access_strategies = [
            ("arxiv", self._try_arxiv),
            ("open_access", self._try_open_access),
            ("institutional", self._try_institutional),
            ("sci_hub", self._try_sci_hub),
        ]

    def _initialize_tables(self):
        """Initialize access tracking tables."""
        cursor = self.db.conn.cursor()

        # Access attempts log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS literature_access_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id TEXT NOT NULL,
                doi TEXT,
                access_method TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                url_tried TEXT,
                response_code INTEGER,
                error_message TEXT,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Successful access methods cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_methods_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id TEXT NOT NULL,
                doi TEXT,
                successful_method TEXT NOT NULL,
                access_url TEXT NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verification_count INTEGER DEFAULT 1,
                UNIQUE(paper_id, successful_method)
            )
        """)

        # Alternative sources registry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alternative_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id TEXT NOT NULL,
                source_type TEXT NOT NULL,  -- 'preprint', 'author_page', 'institutional_repo'
                url TEXT NOT NULL,
                quality_score REAL DEFAULT 0.5,
                verified BOOLEAN DEFAULT FALSE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.db.conn.commit()

    def access_paper(
        self,
        paper_id: str,
        doi: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str], str]:
        """
        Attempt to access paper using multiple strategies.

        Args:
            paper_id: arXiv ID or other identifier
            doi: Digital Object Identifier (if available)
            metadata: Additional paper metadata

        Returns:
            Tuple of (success, pdf_path, access_method)
        """
        # Check cache first
        cached = self._check_cache(paper_id)
        if cached:
            success, path = self._verify_cached_access(cached)
            if success:
                return True, path, cached["successful_method"]

        # Try each strategy in order
        for method_name, method_func in self.access_strategies:
            try:
                success, pdf_path = method_func(paper_id, doi, metadata)

                # Log attempt
                self._log_attempt(paper_id, doi, method_name, success, pdf_path)

                if success and pdf_path:
                    # Cache successful method
                    self._cache_success(paper_id, doi, method_name, pdf_path)
                    return True, pdf_path, method_name

                # Small delay between attempts
                time.sleep(1)

            except Exception as e:
                self._log_attempt(
                    paper_id, doi, method_name, False,
                    error_message=str(e)
                )
                continue

        # All methods failed - find alternatives
        alternatives = self._find_alternatives(paper_id, doi, metadata)
        if alternatives:
            return False, None, f"no_access_but_found_{len(alternatives)}_alternatives"

        return False, None, "all_methods_failed"

    def _try_arxiv(
        self,
        paper_id: str,
        doi: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str]]:
        """Try to access via arXiv."""
        # If paper_id looks like arXiv ID, try direct download
        if "arxiv" in paper_id.lower() or "/" in paper_id or "." in paper_id:
            from tools.pdf_reader import PDFReader

            pdf_reader = PDFReader()

            try:
                pdf_path = pdf_reader.download_pdf(paper_id)
                if pdf_path and pdf_path.exists():
                    return True, str(pdf_path)
            except:
                pass

        return False, None

    def _try_open_access(
        self,
        paper_id: str,
        doi: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str]]:
        """Try open access repositories."""
        if not doi:
            return False, None

        # Try Unpaywall API
        try:
            url = f"https://api.unpaywall.org/v2/{doi}?email=research@example.com"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Check for best OA location
                if data.get("is_oa") and data.get("best_oa_location"):
                    pdf_url = data["best_oa_location"].get("url_for_pdf")

                    if pdf_url:
                        # Download PDF
                        pdf_path = self._download_pdf(pdf_url, paper_id)
                        if pdf_path:
                            return True, pdf_path

        except:
            pass

        return False, None

    def _try_institutional(
        self,
        paper_id: str,
        doi: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str]]:
        """Try institutional access (if configured)."""
        # Check if institutional access is configured
        import os
        institution_proxy = os.getenv("INSTITUTION_PROXY")

        if not institution_proxy or not doi:
            return False, None

        # Try accessing through institutional proxy
        try:
            proxy_url = f"{institution_proxy}/doi/{doi}"
            # This would require proper authentication
            # Simplified for now
            return False, None

        except:
            pass

        return False, None

    def _try_sci_hub(
        self,
        paper_id: str,
        doi: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str]]:
        """
        Try Sci-Hub as last resort.

        Note: Sci-Hub access may be illegal in some jurisdictions.
        Only enabled if explicitly configured by user.
        """
        import os
        sci_hub_enabled = os.getenv("ENABLE_SCI_HUB", "false").lower() == "true"

        if not sci_hub_enabled or not doi:
            return False, None

        # List of Sci-Hub mirrors (changes frequently)
        mirrors = [
            "https://sci-hub.se",
            "https://sci-hub.st",
            "https://sci-hub.ru",
        ]

        for mirror in mirrors:
            try:
                url = f"{mirror}/{doi}"
                # Note: Actual implementation would need to parse HTML and extract PDF
                # This is a simplified version
                return False, None

            except:
                continue

        return False, None

    def _download_pdf(self, url: str, paper_id: str) -> Optional[str]:
        """Download PDF from URL."""
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # Save to cache
            cache_dir = Path("data/literature/pdfs")
            cache_dir.mkdir(parents=True, exist_ok=True)

            safe_id = paper_id.replace("/", "_").replace(":", "_")
            pdf_path = cache_dir / f"{safe_id}.pdf"

            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return str(pdf_path)

        except:
            return None

    def _find_alternatives(
        self,
        paper_id: str,
        doi: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Find alternative sources when direct access fails.

        Returns:
            List of alternative source dictionaries
        """
        alternatives = []

        # Check for preprint versions
        if metadata and metadata.get("title"):
            title = metadata["title"]

            # Search Google Scholar for preprints
            alternatives.append({
                "type": "search",
                "platform": "Google Scholar",
                "query": title,
                "url": f"https://scholar.google.com/scholar?q={title.replace(' ', '+')}"
            })

            # Search ResearchGate
            alternatives.append({
                "type": "search",
                "platform": "ResearchGate",
                "query": title,
                "url": f"https://www.researchgate.net/search/publication?q={title.replace(' ', '%20')}"
            })

        # Suggest requesting from author
        if metadata and metadata.get("authors"):
            authors = metadata["authors"]
            if authors:
                alternatives.append({
                    "type": "request",
                    "platform": "Author Request",
                    "contact": authors[0],
                    "instruction": f"Consider emailing {authors[0]} to request a copy"
                })

        return alternatives

    def _check_cache(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Check if successful access method is cached."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM access_methods_cache
            WHERE paper_id = ?
            ORDER BY last_verified DESC
            LIMIT 1
        """, (paper_id,))

        row = cursor.fetchone()
        return dict(row) if row else None

    def _verify_cached_access(
        self,
        cached: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Verify cached access method still works."""
        pdf_path = Path(cached["access_url"])

        if pdf_path.exists():
            # Update verification
            cursor = self.db.conn.cursor()
            cursor.execute("""
                UPDATE access_methods_cache
                SET last_verified = CURRENT_TIMESTAMP,
                    verification_count = verification_count + 1
                WHERE id = ?
            """, (cached["id"],))

            self.db.conn.commit()
            return True, str(pdf_path)

        return False, None

    def _cache_success(
        self,
        paper_id: str,
        doi: Optional[str],
        method: str,
        pdf_path: str
    ):
        """Cache successful access method."""
        cursor = self.db.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO access_methods_cache (
                    paper_id, doi, successful_method, access_url
                ) VALUES (?, ?, ?, ?)
            """, (paper_id, doi, method, pdf_path))

            self.db.conn.commit()

        except:
            # Already exists, update
            cursor.execute("""
                UPDATE access_methods_cache
                SET access_url = ?,
                    last_verified = CURRENT_TIMESTAMP,
                    verification_count = verification_count + 1
                WHERE paper_id = ? AND successful_method = ?
            """, (pdf_path, paper_id, method))

            self.db.conn.commit()

    def _log_attempt(
        self,
        paper_id: str,
        doi: Optional[str],
        method: str,
        success: bool,
        url_tried: Optional[str] = None,
        response_code: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Log access attempt."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO literature_access_attempts (
                paper_id, doi, access_method, success,
                url_tried, response_code, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            paper_id, doi, method, success,
            url_tried, response_code, error_message
        ))

        self.db.conn.commit()

    def get_access_statistics(self) -> Dict[str, Any]:
        """Get statistics on access methods."""
        cursor = self.db.conn.cursor()

        # Success rate by method
        cursor.execute("""
            SELECT access_method,
                   COUNT(*) as total_attempts,
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
                   AVG(CASE WHEN success THEN 100.0 ELSE 0 END) as success_rate
            FROM literature_access_attempts
            GROUP BY access_method
        """)

        methods_stats = {}
        for row in cursor.fetchall():
            methods_stats[row["access_method"]] = {
                "total_attempts": row["total_attempts"],
                "successful": row["successful"],
                "success_rate": row["success_rate"]
            }

        # Overall stats
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
            FROM literature_access_attempts
        """)

        overall = cursor.fetchone()

        return {
            "overall": {
                "total_attempts": overall["total"],
                "successful": overall["successful"],
                "success_rate": (
                    overall["successful"] / overall["total"] * 100
                    if overall["total"] > 0 else 0
                )
            },
            "by_method": methods_stats
        }

    def suggest_access_strategy(self, paper_metadata: Dict[str, Any]) -> str:
        """
        Suggest best access strategy based on paper metadata and history.

        Args:
            paper_metadata: Paper metadata

        Returns:
            Suggested strategy description
        """
        # Check if it's arXiv
        if "arxiv" in paper_metadata.get("paper_id", "").lower():
            return "Direct arXiv download (free, no restrictions)"

        # Check if DOI exists
        if paper_metadata.get("doi"):
            return "Try Open Access repositories first, then institutional access"

        # Check publication year
        pub_year = paper_metadata.get("published", "")[:4]
        if pub_year and int(pub_year) < 2000:
            return "Older paper - try institutional archive or request from author"

        return "Try Open Access, then consider requesting from author"


def get_literature_access_manager() -> LiteratureAccessManager:
    """Get literature access manager instance."""
    return LiteratureAccessManager()
