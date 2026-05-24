"""
Tests for jarvis/memory/knowledge.py — KnowledgeBase (RAG layer).
"""
import os
import pytest
from unittest.mock import MagicMock, patch, mock_open


class TestKnowledgeBase:
    """Tests for the KnowledgeBase class."""

    @pytest.fixture
    def mock_chromadb(self, mocker):
        """Mock ChromaDB so tests never touch the filesystem."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mocker.patch("jarvis.memory.knowledge.chromadb.PersistentClient",
                     return_value=mock_client)
        mocker.patch("jarvis.memory.knowledge.embedding_functions.DefaultEmbeddingFunction",
                     return_value=MagicMock())
        mocker.patch("jarvis.memory.knowledge.config.vector_db_path", "./test_db")
        return mock_client, mock_collection

    def test_init_creates_collection(self, mock_chromadb):
        """KnowledgeBase should create or get the jarvis_knowledge collection when initialized."""
        mock_client, mock_collection = mock_chromadb
        from jarvis.memory.knowledge import KnowledgeBase
        kb = KnowledgeBase()
        kb._init_chroma()
        
        args, kwargs = mock_client.get_or_create_collection.call_args
        assert kwargs["name"] == "jarvis_knowledge"
        assert "embedding_function" in kwargs

    def test_add_document(self, mock_chromadb):
        """add_document should call collection.add with correct arguments."""
        _, mock_collection = mock_chromadb
        from jarvis.memory.knowledge import KnowledgeBase
        kb = KnowledgeBase()
        kb.add_document("Some content", {"source": "test.txt"}, "doc-001")
        mock_collection.add.assert_called_once_with(
            documents=["Some content"],
            metadatas=[{"source": "test.txt"}],
            ids=["doc-001"]
        )

    def test_query_returns_context_string(self, mock_chromadb):
        """query() should join document matches into a context string."""
        _, mock_collection = mock_chromadb
        mock_collection.query.return_value = {
            "documents": [["Result one.", "Result two."]]
        }
        from jarvis.memory.knowledge import KnowledgeBase
        kb = KnowledgeBase()
        result = kb.query("test query")
        assert "Result one." in result
        assert "Result two." in result

    def test_query_returns_empty_string_when_no_results(self, mock_chromadb):
        """query() should return '' when no documents match."""
        _, mock_collection = mock_chromadb
        mock_collection.query.return_value = {"documents": [[]]}
        from jarvis.memory.knowledge import KnowledgeBase
        kb = KnowledgeBase()
        result = kb.query("nothing matches")
        assert result == ""

    def test_query_handles_exception(self, mock_chromadb):
        """query() should return '' and not raise on internal errors."""
        _, mock_collection = mock_chromadb
        mock_collection.query.side_effect = Exception("ChromaDB error")
        from jarvis.memory.knowledge import KnowledgeBase
        kb = KnowledgeBase()
        result = kb.query("crashing query")
        assert result == ""

    def test_ingest_folder_nonexistent(self, mock_chromadb, tmp_path):
        """ingest_folder should skip gracefully when folder doesn't exist."""
        _, mock_collection = mock_chromadb
        from jarvis.memory.knowledge import KnowledgeBase
        kb = KnowledgeBase()
        kb.ingest_folder("/definitely/does/not/exist/folder")
        # add_document should never be called
        mock_collection.add.assert_not_called()

    def test_ingest_folder_reads_txt_files(self, mock_chromadb, tmp_path):
        """ingest_folder should ingest .txt and .md files from a folder."""
        _, mock_collection = mock_chromadb
        # Create test files
        (tmp_path / "doc1.txt").write_text("Content of doc1")
        (tmp_path / "doc2.md").write_text("Content of doc2")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")  # should be skipped

        from jarvis.memory.knowledge import KnowledgeBase
        kb = KnowledgeBase()
        kb.add_document = MagicMock()
        kb.ingest_folder(str(tmp_path))

        assert kb.add_document.call_count == 2  # only txt and md
        # Ensure the PNG was not ingested
        called_ids = [c[0][2] for c in kb.add_document.call_args_list]
        assert "image.png" not in called_ids

    def test_query_uses_n_results_param(self, mock_chromadb):
        """query() should forward n_results parameter to collection.query."""
        _, mock_collection = mock_chromadb
        mock_collection.query.return_value = {"documents": [["Doc A"]]}
        from jarvis.memory.knowledge import KnowledgeBase
        kb = KnowledgeBase()
        kb.query("test", n_results=5)
        call_kwargs = mock_collection.query.call_args[1]
        assert call_kwargs.get("n_results") == 5
