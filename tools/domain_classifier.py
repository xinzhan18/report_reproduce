"""
DomainClassifier - Automatic paper classification to domains

Classifies papers using:
- Keyword matching (fast)
- LLM-based classification (accurate)
- Hybrid approach (best of both)
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing, logging, core.state.PaperMetadata, core.database.get_database, config.llm_config
# OUTPUT: 对外提供 - DomainClassifier类, get_domain_classifier函数
# POSITION: 系统地位 - [Tools/Classification Layer] - 领域分类器,支持关键词/LLM/混合三种论文分类方法
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import List, Tuple, Dict, Optional
import logging

from core.state import PaperMetadata
from core.database import get_database
from config.llm_config import get_model_name


class DomainClassifier:
    """
    Classifies papers into domain taxonomy.

    Supports multiple classification methods:
    - keyword: Fast keyword-based matching
    - llm: Accurate LLM-based classification (Haiku)
    - hybrid: Keyword first, LLM if uncertain
    """

    def __init__(self, llm=None):
        """
        Initialize domain classifier.

        Args:
            llm: Optional Anthropic client for LLM classification
        """
        self.db = get_database()
        self.llm = llm
        self.domains = self._load_domain_hierarchy()
        self.logger = logging.getLogger("domain_classifier")

    def _load_domain_hierarchy(self) -> List[Dict]:
        """
        Load domain hierarchy from database.

        Returns:
            List of domain dicts
        """
        return self.db.get_all_domains()

    def classify_paper(
        self,
        paper: PaperMetadata,
        method: str = "hybrid"
    ) -> List[Tuple[str, float]]:
        """
        Classify paper into domains.

        Args:
            paper: Paper metadata
            method: Classification method ("keyword", "llm", "hybrid")

        Returns:
            List of (domain_name, confidence_score) tuples
        """
        if method == "keyword":
            return self._keyword_based_classification(paper)
        elif method == "llm":
            return self._llm_based_classification(paper)
        else:  # hybrid
            # Try keyword first
            keyword_results = self._keyword_based_classification(paper)

            # If high confidence, use keyword results
            if keyword_results and max(r[1] for r in keyword_results) > 0.8:
                self.logger.info(f"High confidence keyword match for {paper['title'][:50]}")
                return keyword_results

            # Otherwise use LLM
            if self.llm:
                self.logger.info(f"Low confidence, using LLM for {paper['title'][:50]}")
                return self._llm_based_classification(paper)
            else:
                self.logger.warning("LLM not available, using keyword results")
                return keyword_results

    def _keyword_based_classification(self, paper: PaperMetadata) -> List[Tuple[str, float]]:
        """
        Classify using keyword matching.

        Fast but less accurate.

        Args:
            paper: Paper metadata

        Returns:
            List of (domain_name, confidence_score) tuples
        """
        if not self.domains:
            self.logger.warning("No domains loaded")
            return []

        # Combine title and abstract
        text = f"{paper['title']} {paper['abstract']}".lower()

        scores = {}

        for domain in self.domains:
            keywords = domain.get("keywords", [])
            if not keywords:
                continue

            # Count keyword matches
            matches = sum(1 for kw in keywords if kw.lower() in text)

            # Calculate score
            if matches > 0:
                scores[domain["name"]] = matches / len(keywords)

        # Sort by score
        sorted_domains = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Return top 3
        return sorted_domains[:3]

    def _llm_based_classification(self, paper: PaperMetadata) -> List[Tuple[str, float]]:
        """
        Classify using LLM (Claude Haiku for speed).

        More accurate but slower and costs API tokens.

        Args:
            paper: Paper metadata

        Returns:
            List of (domain_name, confidence_score) tuples
        """
        if not self.llm:
            self.logger.error("LLM client not available")
            return []

        domain_names = [d["name"] for d in self.domains]

        prompt = f"""Classify this research paper into the most relevant domains.

Title: {paper['title']}

Abstract: {paper['abstract'][:500]}

Available domains:
{', '.join(domain_names)}

Return the top 3 most relevant domains with confidence scores (0.0 to 1.0).

Output as JSON:
{{
  "classifications": [
    {{"domain": "Domain Name", "confidence": 0.95}},
    {{"domain": "Domain Name", "confidence": 0.75}},
    {{"domain": "Domain Name", "confidence": 0.60}}
  ]
}}

Be specific and only choose domains that truly match the paper's content.
If no good matches exist, return an empty list.
"""

        try:
            response = self.llm.messages.create(
                model=get_model_name("haiku"),  # Use Haiku for speed
                max_tokens=500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text

            # Parse JSON
            import json
            import re

            # Try to extract JSON
            if "```json" in text:
                json_text = text.split("```json")[1].split("```")[0].strip()
            elif "{" in text and "}" in text:
                json_text = text[text.find("{"):text.rfind("}") + 1]
            else:
                json_text = text

            result = json.loads(json_text)

            classifications = result.get("classifications", [])

            return [(c["domain"], c["confidence"]) for c in classifications]

        except Exception as e:
            self.logger.error(f"LLM classification failed: {e}")
            return []

    def classify_batch(
        self,
        papers: List[PaperMetadata],
        method: str = "hybrid",
        save_to_db: bool = True
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Classify multiple papers.

        Args:
            papers: List of papers to classify
            method: Classification method
            save_to_db: Whether to save results to database

        Returns:
            Dict mapping arxiv_id to list of (domain, score) tuples
        """
        self.logger.info(f"Classifying {len(papers)} papers using {method} method")

        results = {}

        for i, paper in enumerate(papers, 1):
            if i % 10 == 0:
                self.logger.info(f"Progress: {i}/{len(papers)}")

            try:
                classifications = self.classify_paper(paper, method=method)
                results[paper["arxiv_id"]] = classifications

                # Save to database
                if save_to_db and classifications:
                    for domain_name, confidence in classifications:
                        # Get domain ID
                        domain = self.db.get_domain_by_name(domain_name)
                        if domain:
                            self.db.add_paper_to_domain(
                                arxiv_id=paper["arxiv_id"],
                                domain_id=domain["id"],
                                relevance_score=confidence,
                                classified_by=method
                            )

            except Exception as e:
                self.logger.error(f"Failed to classify {paper['arxiv_id']}: {e}")
                results[paper["arxiv_id"]] = []

        self.logger.info(f"Classification complete: {len(results)} papers processed")

        return results

    def get_classification_stats(self) -> Dict:
        """
        Get classification statistics.

        Returns:
            Stats dict
        """
        cursor = self.db.conn.cursor()

        # Total classifications
        cursor.execute("SELECT COUNT(*) FROM paper_domains")
        total = cursor.fetchone()[0]

        # By method
        cursor.execute("SELECT classified_by, COUNT(*) FROM paper_domains GROUP BY classified_by")
        by_method = {row[0]: row[1] for row in cursor.fetchall()}

        # Average confidence
        cursor.execute("SELECT AVG(relevance_score) FROM paper_domains")
        avg_confidence = cursor.fetchone()[0] or 0.0

        # By domain
        cursor.execute("""
            SELECT d.name, COUNT(*)
            FROM domains d
            JOIN paper_domains pd ON d.id = pd.domain_id
            GROUP BY d.id
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        top_domains = [(row[0], row[1]) for row in cursor.fetchall()]

        return {
            "total_classifications": total,
            "by_method": by_method,
            "average_confidence": round(avg_confidence, 3),
            "top_10_domains": top_domains
        }


# Singleton instance
_domain_classifier = None


def get_domain_classifier(llm=None) -> DomainClassifier:
    """
    Get singleton DomainClassifier instance.

    Args:
        llm: Optional Anthropic client

    Returns:
        DomainClassifier instance
    """
    global _domain_classifier
    if _domain_classifier is None:
        _domain_classifier = DomainClassifier(llm=llm)
    return _domain_classifier
