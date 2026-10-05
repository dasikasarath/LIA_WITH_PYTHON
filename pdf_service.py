import io
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Tuple
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vector_store import SpringAIPGVectorStore

logger = logging.getLogger(__name__)

class PDFService:
    def __init__(self, vector_store: SpringAIPGVectorStore):
        self.vector_store = vector_store
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

    def process_pdf(self, file_bytes: bytes, filename: str) -> Tuple[int, int, str]:
        """
        Parses PDF, chunks text, creates embeddings and stores in vector database.
        Returns: (pages_processed, chunks_stored, parent_document_id)
        """
        reader = PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)
        parent_doc_id = str(uuid.uuid4())
        upload_time = datetime.now(timezone.utc).isoformat()

        logger.info(f"Processing PDF '{filename}' with {total_pages} pages...")

        raw_page_docs: List[Document] = []
        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                raw_page_docs.append(Document(
                    page_content=text,
                    metadata={
                        "source": filename,
                        "filename": filename,
                        "file_name": filename,
                        "page_number": page_idx + 1,
                        "parent_document_id": parent_doc_id,
                        "upload_time": upload_time,
                    }
                ))

        if not raw_page_docs:
            raise ValueError(f"No extractable text found in PDF '{filename}'.")

        # Split page documents into chunks
        split_chunks = self.text_splitter.split_documents(raw_page_docs)
        total_chunks = len(split_chunks)

        # Enrich chunk metadata
        for idx, chunk in enumerate(split_chunks):
            chunk.metadata["chunk_index"] = idx
            chunk.metadata["total_chunks"] = total_chunks
            chunk.metadata["id"] = str(uuid.uuid4())

        logger.info(f"Split '{filename}' into {total_chunks} chunks. Adding to vector store...")
        self.vector_store.add_documents(split_chunks)

        return total_pages, total_chunks, parent_doc_id
