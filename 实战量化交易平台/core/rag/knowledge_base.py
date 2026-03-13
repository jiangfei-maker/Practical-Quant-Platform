
import os
from typing import List, Optional
from loguru import logger
import chromadb
from chromadb.config import Settings
from zhipuai import ZhipuAI
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
import pandas as pd

class ZhipuEmbedding(Embeddings):
    """
    ZhipuAI Embedding Wrapper for LangChain
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ZHIPUAI_API_KEY")
        if not self.api_key:
            raise ValueError("ZHIPUAI_API_KEY is not set")
        self.client = ZhipuAI(api_key=self.api_key)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs."""
        embeddings = []
        for text in texts:
            # Zhipu API limit batch size usually, safer to do one by one or small batch
            # Also handle potential errors
            try:
                response = self.client.embeddings.create(
                    model="embedding-2", # Or embedding-3
                    input=text
                )
                embeddings.append(response.data[0].embedding)
            except Exception as e:
                logger.error(f"Embedding failed for text: {text[:20]}... Error: {e}")
                # Append zero vector or skip? Better to raise or handle gracefully
                embeddings.append([0.0] * 1024) # Assuming 1024 dim for embedding-2
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""
        try:
            response = self.client.embeddings.create(
                model="embedding-2",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            return [0.0] * 1024

class KnowledgeBase:
    """
    RAG Knowledge Base Manager using ChromaDB and ZhipuAI Embeddings
    """
    def __init__(self, persist_directory: str = "./data/chroma_db"):
        self.persist_directory = persist_directory
        self.api_key = os.getenv("ZHIPUAI_API_KEY")
        
        if not self.api_key:
            logger.warning("ZHIPUAI_API_KEY not found. Knowledge Base will not function correctly.")
            self.embedding_fn = None
            self.vector_store = None
            return

        self.embedding_fn = ZhipuEmbedding(api_key=self.api_key)
        
        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        try:
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embedding_fn,
                collection_name="quant_research_kb"
            )
            logger.info(f"Knowledge Base initialized at {persist_directory}")
        except Exception as e:
            logger.error(f"Failed to init ChromaDB: {e}")
            self.vector_store = None

    def add_document(self, file_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> str:
        """
        Add a document (PDF/TXT) to the knowledge base
        """
        if not self.vector_store:
            return "Knowledge Base not initialized (Missing API Key?)"

        try:
            # 1. Load Document
            if file_path.lower().endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            elif file_path.lower().endswith(".txt") or file_path.lower().endswith(".md"):
                loader = TextLoader(file_path, encoding='utf-8')
            else:
                return f"Unsupported file format: {file_path}"
            
            docs = loader.load()
            logger.info(f"Loaded {len(docs)} pages/docs from {file_path}")

            # 2. Split Text
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", "。", "！", "？", " ", ""]
            )
            splits = text_splitter.split_documents(docs)
            logger.info(f"Split into {len(splits)} chunks")

            # 3. Add to Vector Store
            # Add source metadata
            for doc in splits:
                doc.metadata["source"] = os.path.basename(file_path)
            
            self.vector_store.add_documents(splits)
            self.vector_store.persist() # Old langchain version might need this, newer auto-persists
            
            return f"Successfully added {len(splits)} chunks to Knowledge Base."

        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return f"Error adding document: {str(e)}"

    def search(self, query: str, k: int = 3) -> List[str]:
        """
        Search for relevant context
        """
        if not self.vector_store:
            return []

        try:
            results = self.vector_store.similarity_search(query, k=k)
            return [doc.page_content for doc in results]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def search_with_score(self, query: str, k: int = 3):
        """
        Search with similarity scores
        """
        if not self.vector_store:
            return []
            
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

# Singleton instance
knowledge_base = KnowledgeBase()
