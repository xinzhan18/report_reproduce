"""
Tests for DomainClassifier

Tests paper classification into domain taxonomy.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - pytest, unittest.mock, tools.domain_classifier.DomainClassifier, core.state.PaperMetadata
# OUTPUT: 对外提供 - 测试函数集(test_keyword_classification/test_llm_classification/test_hybrid等)
# POSITION: 系统地位 - [Tests/Unit Tests] - 领域分类器测试,验证关键词/LLM/混合三种分类方法
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import pytest
from unittest.mock import Mock, MagicMock, patch
from tools.domain_classifier import DomainClassifier
from core.state import PaperMetadata


class TestDomainClassifier:
    """Test suite for DomainClassifier."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.get_all_domains = Mock(return_value=[
            {
                "id": 1,
                "name": "Momentum Strategies",
                "keywords": ["momentum", "trend", "following"]
            },
            {
                "id": 2,
                "name": "Mean Reversion",
                "keywords": ["mean reversion", "contrarian", "reversal"]
            }
        ])
        db.get_domain_by_name = Mock(return_value={"id": 1, "name": "Momentum Strategies"})
        db.add_paper_to_domain = Mock()
        db.conn = Mock()
        return db

    @pytest.fixture
    def classifier(self, mock_db):
        """Create DomainClassifier with mock db."""
        with patch('tools.domain_classifier.get_database', return_value=mock_db):
            return DomainClassifier(llm=None)

    @pytest.fixture
    def sample_paper(self):
        """Create sample paper for testing."""
        return {
            "arxiv_id": "2023.12345",
            "title": "Momentum Trading Strategies in Equity Markets",
            "authors": ["Author 1", "Author 2"],
            "abstract": "This paper presents a momentum-based trading strategy that follows trends in equity markets. We demonstrate strong performance using historical data.",
            "published": "2023-01-01",
            "categories": ["q-fin.PM"],
            "url": "http://test.com",
            "pdf_url": "http://test.com/pdf"
        }

    def test_initialization(self, classifier):
        """Test classifier initialization."""
        assert classifier.db is not None
        assert len(classifier.domains) == 2

    def test_keyword_classification(self, classifier, sample_paper):
        """Test keyword-based classification."""
        classifications = classifier._keyword_based_classification(sample_paper)

        # Verify
        assert len(classifications) > 0
        assert classifications[0][0] == "Momentum Strategies"  # Top match
        assert classifications[0][1] > 0.5  # Good confidence

    def test_keyword_classification_no_match(self, classifier):
        """Test classification with no keyword matches."""
        paper = {
            "arxiv_id": "2023.99999",
            "title": "Unrelated Topic",
            "abstract": "This paper discusses something completely unrelated.",
        }

        classifications = classifier._keyword_based_classification(paper)

        # Should return empty or low scores
        if classifications:
            assert all(score < 0.5 for _, score in classifications)

    def test_batch_classification(self, classifier, sample_paper, mock_db):
        """Test batch classification."""
        papers = [sample_paper] * 3  # 3 identical papers

        results = classifier.classify_batch(
            papers=papers,
            method="keyword",  # Use keyword to avoid LLM calls
            save_to_db=True
        )

        # Verify
        assert len(results) == 3
        assert mock_db.add_paper_to_domain.call_count >= 3

    def test_classification_with_llm(self, mock_db):
        """Test LLM-based classification."""
        # Create mock LLM
        mock_llm = Mock()
        response = Mock()
        response.content = [Mock(text='''
        ```json
        {
            "classifications": [
                {"domain": "Momentum Strategies", "confidence": 0.95},
                {"domain": "Mean Reversion", "confidence": 0.3}
            ]
        }
        ```
        ''')]
        mock_llm.messages.create = Mock(return_value=response)

        with patch('tools.domain_classifier.get_database', return_value=mock_db):
            classifier = DomainClassifier(llm=mock_llm)

        paper = {
            "arxiv_id": "2023.12345",
            "title": "Test Paper",
            "abstract": "Momentum trading strategy"
        }

        classifications = classifier._llm_based_classification(paper)

        # Verify
        assert len(classifications) == 2
        assert classifications[0][0] == "Momentum Strategies"
        assert classifications[0][1] == 0.95

    def test_hybrid_classification_high_confidence(self, classifier, sample_paper):
        """Test hybrid method with high keyword confidence."""
        classifications = classifier.classify_paper(sample_paper, method="hybrid")

        # Should use keyword results (no LLM call)
        assert len(classifications) > 0
        assert classifications[0][0] == "Momentum Strategies"

    def test_get_classification_stats(self, classifier, mock_db):
        """Test statistics retrieval."""
        # Mock cursor
        cursor = Mock()
        cursor.fetchone = Mock(side_effect=[
            [100],  # total
            [0.85],  # avg confidence
        ])
        cursor.fetchall = Mock(return_value=[
            ["keyword", 60],
            ["llm", 40]
        ])
        mock_db.conn.cursor.return_value = cursor

        stats = classifier.get_classification_stats()

        # Verify
        assert stats["total_classifications"] == 100
        assert stats["average_confidence"] == 0.85
        assert "by_method" in stats


class TestDomainClassifierEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_paper_list(self):
        """Test classification with empty list."""
        mock_db = Mock()
        mock_db.get_all_domains = Mock(return_value=[])

        with patch('tools.domain_classifier.get_database', return_value=mock_db):
            classifier = DomainClassifier()

            results = classifier.classify_batch(papers=[], method="keyword")

            assert len(results) == 0

    def test_llm_failure_handling(self, mock_db):
        """Test handling of LLM API failures."""
        mock_llm = Mock()
        mock_llm.messages.create = Mock(side_effect=Exception("API Error"))

        mock_db.get_all_domains = Mock(return_value=[
            {"id": 1, "name": "Test", "keywords": ["test"]}
        ])

        with patch('tools.domain_classifier.get_database', return_value=mock_db):
            classifier = DomainClassifier(llm=mock_llm)

            paper = {"arxiv_id": "test", "title": "Test", "abstract": "Test"}

            # Should not raise, should return empty list
            result = classifier._llm_based_classification(paper)

            assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
