import os
import asyncio
from typing import List, Dict, Any
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from app.config import settings

class VectorStoreService:
    def __init__(self):
        # 1. Initialize Pinecone client
        pinecone_key = settings.PINECONE_API_KEY or os.getenv("PINECONE_API_KEY", "")
        self.index_name = settings.PINECONE_INDEX_NAME or os.getenv("PINECONE_INDEX_NAME", "default-index")
        
        if pinecone_key:
            self.pc = Pinecone(api_key=pinecone_key)
            self.index = self.pc.Index(self.index_name)
        else:
            self.pc = None
            self.index = None

        # 2. Initialize Embeddings (OpenRouter fallback or OpenAI)
        active_key = settings.OPENAI_API_KEY or settings.OPENROUTER_API_KEY or "dummy_key_to_prevent_startup_crash"
        base_url = "https://openrouter.ai/api/v1" if (settings.OPENROUTER_API_KEY and not settings.OPENAI_API_KEY) else None

        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=active_key,
            base_url=base_url,
            check_embedding_ctx_length=False
        )

    def has_existing_documents(self, namespace: str = "") -> bool:
        """Checks if the vector store namespace has existing indexed vectors."""
        if not self.index:
            return False
        try:
            stats = self.index.describe_index_stats()
            if namespace:
                ns_stats = stats.namespaces.get(namespace)
                return bool(ns_stats and ns_stats.vector_count > 0)
            return bool(stats.total_vector_count > 0)
        except Exception as e:
            print(f"Error checking index stats: {e}")
            return False

    def clear_vectors(self, namespace: str = ""):
        """Deletes all existing vectors in the index or namespace."""
        if not self.index:
            return
        print(f"--- [PINECONE] Clearing existing vectors (namespace='{namespace}') ---")
        try:
            if namespace:
                self.index.delete(delete_all=True, namespace=namespace)
            else:
                self.index.delete(delete_all=True)
        except Exception as e:
            print(f"Error clearing vectors: {e}")

    def add_document_chunks(self, chunks: List[Dict[str, Any]], namespace: str = ""):
        """Embeds and upserts document chunks into Pinecone."""
        if not chunks or not self.index:
            return

        # Support both 'text' and 'chunk_text' keys safely
        texts = [c.get("text") or c.get("chunk_text") for c in chunks if c.get("text") or c.get("chunk_text")]
        if not texts:
            return

        embeddings = self.embeddings.embed_documents(texts)

        vectors_to_upsert = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            text_content = chunk.get("text") or chunk.get("chunk_text", "")
            vector_id = f"doc_chunk_{chunk.get('metadata', {}).get('page_number', 1)}_{idx}_{os.urandom(4).hex()}"
            vectors_to_upsert.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "text": text_content,
                    "page_number": chunk.get("metadata", {}).get("page_number", 1),
                    "screenshot_path": chunk.get("metadata", {}).get("screenshot_path", ""),
                    "filename": chunk.get("metadata", {}).get("document_title") or chunk.get("metadata", {}).get("filename", "")
                }
            })

        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i + batch_size]
            self.index.upsert(vectors=batch, namespace=namespace)

    def similarity_search(self, query: str, k: int = 4, namespace: str = ""):
        """Searches Pinecone for vector chunks matching the query string."""
        if not self.index:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Query Pinecone index
            results = self.index.query(
                vector=query_embedding,
                top_k=k,
                include_metadata=True,
                namespace=namespace
            )
            
            # Format results into structured chunks with metadata
            matched_chunks = []
            for match in results.get("matches", []):
                metadata = match.get("metadata", {})
                matched_chunks.append({
                    "id": match.get("id"),
                    "score": match.get("score"),
                    "text": metadata.get("text", ""),
                    "metadata": metadata
                })
            return matched_chunks
        except Exception as e:
            print(f"Error during similarity search: {e}")
            return []

    async def asimilarity_search(self, query: str, k: int = 4, namespace: str = ""):
        """Asynchronously searches Pinecone for vector chunks matching the query string."""
        if not self.index:
            return []
        
        try:
            # Non-blocking network call for embeddings
            query_embedding = await self.embeddings.aembed_query(query)
            
            # Offload the synchronous Pinecone index query to a background thread
            results = await asyncio.to_thread(
                self.index.query,
                vector=query_embedding,
                top_k=k,
                include_metadata=True,
                namespace=namespace
            )
            
            # Format results into structured chunks with metadata
            matched_chunks = []
            for match in results.get("matches", []):
                metadata = match.get("metadata", {})
                matched_chunks.append({
                    "id": match.get("id"),
                    "score": match.get("score"),
                    "text": metadata.get("text", ""),
                    "metadata": metadata
                })
            return matched_chunks
        except Exception as e:
            print(f"Error during async similarity search: {e}")
            return []

vector_store_service = VectorStoreService()