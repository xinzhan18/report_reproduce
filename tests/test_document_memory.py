"""
Tests for DocumentMemoryManager

Tests document memory retrieval, caching, and recommendations.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from core.document_memory_manager import DocumentMemoryManager
from core.state import PaperMetadata


class TestDocumentMemoryManager:
    """Test suite for DocumentMemoryManager."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.conn = Mock()
        db.get_papers_by_domain = Mock(return_value=[])
        db.get_domain_by_name = Mock(return_value={"id": 1, "name": "Test Domain"})
        db.get_domains_for_paper = Mock(return_value=[])
        db.get_cached_analysis = Mock(return_value=None)
        db.has_cached_analysis = Mock(return_value=False)
        db.save_paper_analysis = Mock()
        db.add_paper_to_domain = Mock()
        db.get_all_domains = Mock(return_value=[])
        db.get_root_domains = Mock(return_value=[])
        return db

    @pytest.fixture
    def doc_memory(self, mock_db):
        """Create DocumentMemoryManager with mock db."""
        with patch('core.document_memory_manager.get_database', return_value=mock_db):
            dm = DocumentMemoryManager(db=mock_db)
            return dm

    def test_initialization(self, doc_memory):
        """Test initialization."""
        assert doc_memory.db is not None
        assert doc_memory.tracker is not None

    def test_retrieve_by_domain(self, doc_memory, mock_db):
        """Test domain-based retrieval."""
        # Setup mock data
        mock_papers = [
            {
                "arxiv_id": "2023.12345",
                "title": "Test Paper",
                "authors": ["Author 1"],
                "abstract": "Test abstract",
                "published": "2023-01-01",
                "categories": ["cs.LG"],
                "url": "http://test.com",
                "pdf_url": "http://test.com/pdf",
                "relevance_score": 0.9
            }
        ]
        mock_db.get_papers_by_domain.return_value = mock_papers

        # Retrieve
        papers = doc_memory.retrieve_by_domain(
            domain="Test Domain",
            exclude_read=False,
            limit=10
        )

        # Verify
        assert len(papers) == 1
        assert papers[0]["arxiv_id"] == "2023.12345"
        assert mock_db.get_papers_by_domain.called

    def test_retrieve_by_domain_with_filtering(self, doc_memory, mock_db):
        """Test retrieval with read filtering."""
        mock_papers = [
            {"arxiv_id": "2023.12345", "title": "Paper 1", "relevance_score": 0.9},
            {"arxiv_id": "2023.67890", "title": "Paper 2", "relevance_score": 0.8}
        ]
        mock_db.get_papers_by_domain.return_value = mock_papers

        # Mock tracker to filter one paper
        doc_memory.tracker.filter_unread_papers = Mock(return_value=["2023.12345"])

        # Retrieve with filtering
        papers = doc_memory.retrieve_by_domain(
            domain="Test Domain",
            exclude_read=True,
            project_id="test_project",
            limit=10
        )

        # Verify only unread paper returned
        assert len(papers) == 1
        assert papers[0]["arxiv_id"] == "2023.12345"

    def test_caching(self, doc_memory, mock_db):
        """Test analysis caching."""
        arxiv_id = "2023.12345"
        sections = {"intro": "Introduction text", "methods": "Methods text"}
        insights = {"key_innovations": ["Innovation 1"], "innovation_score": 0.8}

        # Save to cache
        doc_memory.save_analysis_results(
            arxiv_id=arxiv_id,
            sections=sections,
            structured_insights=insights
        )

        # Verify save was called
        assert mock_db.save_paper_analysis.called
        call_args = mock_db.save_paper_analysis.call_args
        assert call_args[1]["arxiv_id"] == arxiv_id
        assert call_args[1]["sections"] == sections

    def test_has_analysis_cache(self, doc_memory, mock_db):
        """Test cache checking."""
        arxiv_id = "2023.12345"

        # Test cache miss
        mock_db.has_cached_analysis.return_value = False
        assert not doc_memory.has_analysis_cache(arxiv_id)

        # Test cache hit
        mock_db.has_cached_analysis.return_value = True
        assert doc_memory.has_analysis_cache(arxiv_id)

    def test_get_memory_stats(self, doc_memory, mock_db):
        """Test memory statistics."""
        # Mock database queries
        cursor = Mock()
        cursor.fetchone = Mock(side_effect=[
            [100],  # total_papers
            [75],   # classified_papers
        ])
        mock_db.conn.cursor.return_value = cursor
        mock_db.get_all_domains.return_value = [{"id": i} for i in range(10)]
        mock_db.get_root_domains.return_value = [{"id": i} for i in range(3)]
        mock_db.get_analysis_stats = Mock(return_value={
            "total_cached": 50,
            "with_structured_insights": 30,
            "with_deep_insights": 10
        })

        # Get stats
        stats = doc_memory.get_memory_stats()

        # Verify
        assert stats["total_papers"] == 100
        assert stats["classified_papers"] == 75
        assert stats["classification_rate"] == 0.75
        assert stats["total_domains"] == 10
        assert stats["root_domains"] == 3


class TestDocumentMemoryRecommendations:
    """Test recommendation features."""

    @pytest.fixture
    def doc_memory_with_data(self, mock_db):
        """Create DocumentMemoryManager with sample data."""
        with patch('core.document_memory_manager.get_database', return_value=mock_db):
            dm = DocumentMemoryManager(db=mock_db)

            # Mock reading history
            dm.tracker.get_reading_history = Mock(return_value=[
                {"arxiv_id": "2023.11111", "title": "Paper 1"},
                {"arxiv_id": "2023.22222", "title": "Paper 2"}
            ])

            # Mock domain mappings
            mock_db.get_domains_for_paper.return_value = [
                {"name": "Momentum Strategies", "id": 1}
            ]

            # Mock domain papers
            mock_db.get_papers_by_domain.return_value = [
                {"arxiv_id": "2023.33333", "title": "Suggested Paper 1"},
                {"arxiv_id": "2023.44444", "title": "Suggested Paper 2"}
            ]

            return dm

    def test_suggest_next_papers(self, doc_memory_with_data):
        """Test paper recommendations based on history."""
        suggestions = doc_memory_with_data.suggest_next_papers(
            project_id="test_project",
            based_on_recent=5,
            limit=10
        )

        # Verify suggestions were generated
        assert isinstance(suggestions, list)

        # Verify tracker was called
        assert doc_memory_with_data.tracker.get_reading_history.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
