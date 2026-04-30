"""Knowledge Base (RAG) system for Jarvis using ChromaDB."""
import os
import chromadb
from chromadb.utils import embedding_functions
from jarvis.config import config
from jarvis.logger import logger

class KnowledgeBase:
    """Manages local document ingestion and retrieval."""
    
    def __init__(self):
        """Initialize ChromaDB client and collection."""
        self.client = chromadb.PersistentClient(path=config.vector_db_path)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="jarvis_knowledge",
            embedding_function=self.embedding_fn
        )
        logger.info("[KNOWLEDGE_INIT] ChromaDB initialized.")

    def add_document(self, content: str, metadata: dict, doc_id: str):
        """Add a document to the vector database."""
        self.collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id]
        )
        logger.info(f"[KNOWLEDGE_ADD] Added document: {doc_id}")

    def query(self, text: str, n_results: int = 3) -> str:
        """Search for relevant context in the knowledge base."""
        try:
            results = self.collection.query(
                query_texts=[text],
                n_results=n_results
            )
            if not results["documents"] or not results["documents"][0]:
                return ""
            
            context = "\n---\n".join(results["documents"][0])
            logger.info(f"[KNOWLEDGE_QUERY] Found {len(results['documents'][0])} matches.")
            return context
        except Exception as e:
            logger.error(f"[KNOWLEDGE_ERROR] Query failed: {e}")
            return ""

    def ingest_folder(self, folder_path: str):
        """Ingest all text files from a folder."""
        if not os.path.exists(folder_path):
            logger.warning(f"[KNOWLEDGE_INGEST] Folder not found: {folder_path}")
            return

        for filename in os.listdir(folder_path):
            if filename.endswith(".txt") or filename.endswith(".md"):
                file_path = os.path.join(folder_path, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.add_document(content, {"source": filename}, filename)

# Global KB instance
kb = KnowledgeBase()
