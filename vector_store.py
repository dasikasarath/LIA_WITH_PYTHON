import logging
import uuid
import json
from typing import List, Optional, Tuple
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config import get_settings
from database import get_db_pool

logger = logging.getLogger(__name__)
settings = get_settings()

class SpringAIPGVectorStore:
    """
    VectorStore fully compatible with Spring AI's pgvector schema:
    Table: vector_store
    Columns: id (UUID), content (TEXT), metadata (JSON), embedding (VECTOR)
    """

    def __init__(self, embeddings: Optional[GoogleGenerativeAIEmbeddings] = None):
        self.embeddings = embeddings or GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=settings.google_api_key
        )
        self.pool = get_db_pool()
        self._embed_cache = {}
        self._max_cache_size = 500

    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """
        Executes similarity search matching Spring AI's SearchRequest.builder().query(que).topK(5).build()
        """
        results_with_scores = self.similarity_search_with_score(query, k=k)
        return [doc for doc, _ in results_with_scores]

    # Alias for Java camelCase similaritySearch
    similaritySearch = similarity_search

    def similarity_search_with_score(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """
        Returns (Document, similarity_score) tuples ordered by cosine distance.
        Uses in-memory LRU embedding cache for ultra-fast query embedding retrieval.
        """
        query_str = query.strip() if query else ""
        if not query_str:
            return []

        try:
            # Check embedding cache
            cache_key = query_str.lower()
            if cache_key in self._embed_cache:
                query_vector = self._embed_cache[cache_key]
            else:
                query_vector = self.embeddings.embed_query(query_str)
                if len(self._embed_cache) >= self._max_cache_size:
                    # Remove oldest item
                    self._embed_cache.pop(next(iter(self._embed_cache)))
                self._embed_cache[cache_key] = query_vector

            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        SELECT id, content, metadata, 1 - (embedding <=> %s::vector) AS similarity
                        FROM {settings.vector_table}
                        ORDER BY embedding <=> %s::vector ASC
                        LIMIT %s;
                    """, (query_vector, query_vector, k))
                    rows = cur.fetchall()

                    documents_with_scores = []
                    for row in rows:
                        doc_id, content, metadata, score = row
                        meta = metadata if isinstance(metadata, dict) else json.loads(metadata or "{}")
                        meta["id"] = str(doc_id)
                        doc = Document(page_content=content or "", metadata=meta)
                        documents_with_scores.append((doc, float(score)))

                    return documents_with_scores
        except Exception as e:
            logger.warning(f"Vector search warning: {e}")
            return []

    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Embeds and stores documents in pgvector using batch inserts.
        """
        if not documents:
            return []

        texts = [doc.page_content for doc in documents]
        try:
            vectors = self.embeddings.embed_documents(texts)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise e

        doc_ids: List[str] = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                for doc, vec in zip(documents, vectors):
                    doc_id = doc.metadata.get("id") or str(uuid.uuid4())
                    doc_ids.append(doc_id)
                    metadata_json = json.dumps(doc.metadata)

                    cur.execute(f"""
                        INSERT INTO {settings.vector_table} (id, content, metadata, embedding)
                        VALUES (%s, %s, %s, %s::vector);
                    """, (doc_id, doc.page_content, metadata_json, vec))
            conn.commit()

        logger.info(f"Successfully added {len(doc_ids)} chunks into {settings.vector_table}.")
        return doc_ids

    def get_total_documents(self) -> int:
        try:
            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM {settings.vector_table};")
                    return cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            return 0
