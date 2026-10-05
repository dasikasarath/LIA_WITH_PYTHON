# Lia AI - Python LangChain RAG Service

An enterprise-ready Retrieval-Augmented Generation (RAG) system built with **Python**, **LangChain**, **Google Gemini**, and **Supabase PostgreSQL (pgvector)**. 

This repository is a complete, 1-to-1 Python LangChain migration of the Spring AI `AIservice` Java application. It shares the exact same PostgreSQL `vector_store` table, Gemini embedding dimension (3072), system prompt, and multi-turn conversational memory.

---

## 🚀 Features

- **100% Schema & Vector Parity**: Interoperable with Spring AI’s `vector_store` table in Supabase.
- **Google GenAI Integration**: Uses `gemini-embedding-001` (3072-dimensional vector) and `gemini-3.6-flash` chat model.
- **Full RAG Pipeline**: Top-K cosine similarity search (`<=>`), documentation context synthesis, and fallback answering.
- **Stateful Chat Memory**: Session-isolated multi-turn memory matching `MessageChatMemoryAdvisor`.
- **PDF Ingestion Endpoint**: Accepts multipart PDF uploads (up to 50MB), extracts text, chunks recursively, generates embeddings, and indexes them into pgvector.
- **RESTful Endpoints & Swagger Docs**: Standard FastAPI REST endpoints with interactive documentation at `/docs`.
- **Premium Glassmorphic Web UI**: Interactive chat interface with PDF drag-and-drop, real-time memory management, and source pills.

---

## 📁 Project Architecture

```
LIA_PYTHON/
├── config.py             # Pydantic environment configuration (.env loader)
├── database.py           # PostgreSQL connection pool & schema initializers
├── models.py             # Pydantic DTOs (Quest, AskResponse, UploadResponse)
├── vector_store.py       # Spring AI compatible LangChain PGVectorStore
├── rag_service.py        # AIService RAG pipeline with chat memory & system prompt
├── pdf_service.py        # PDF text extractor, recursive chunker, and vector indexer
├── main.py               # FastAPI application with REST endpoints & static mount
├── test_app.py           # Automated integration test suite
├── requirements.txt      # Dependency list
├── .env                  # Environment secrets & database connection strings
└── static/               # Premium Web UI (HTML5, Vanilla CSS, JS)
    ├── index.html        # Modern chat and PDF uploader interface
    ├── style.css         # Glassmorphism, animations, and dark mode styles
    └── app.js            # Client-side chat, file upload, and session handling
```

---

## 🔄 Spring AI vs. Python LangChain Mapping

| Feature | Java Spring AI Implementation | Python LangChain Implementation |
| :--- | :--- | :--- |
| **Service Layer** | `ai.example.open.service.AIservice` | `rag_service.AIService` |
| **Query Method** | `asku(Quest quest)` / `searchres(que, convId)` | `asku(quest: Quest)` / `searchres(que, conversation_id)` |
| **Vector Store** | `org.springframework.ai.vectorstore.VectorStore` | `vector_store.SpringAIPGVectorStore` |
| **Vector Search** | `vs.similaritySearch(SearchRequest.builder().query(que).topK(5).build())` | `vs.similarity_search(query, k=5)` with pgvector `<=>` |
| **Chat Client** | `org.springframework.ai.chat.client.ChatClient` | `langchain_google_genai.ChatGoogleGenerativeAI` |
| **Chat Memory** | `MessageChatMemoryAdvisor(chatMemory)` | `rag_service.ConversationMemoryManager` |
| **Memory Clear** | `clearMemory(String conversationId)` | `clear_memory(conversation_id: str)` |
| **PDF Ingestion** | Multipart upload endpoint (`50MB`) | `POST /upload-pdf` (`pdf_service.PDFService`) |
| **Table Schema** | `vector_store (id UUID, content TEXT, metadata JSON, embedding VECTOR(3072))` | Identical table & columns in Supabase |

---

## ⚙️ Configuration (`.env`)

```properties
# Google Gemini Configuration
GOOGLE_API_KEY=your_api_key_here
CHAT_MODEL=gemini-3.6-flash
EMBEDDING_MODEL=gemini-embedding-001

# Supabase PostgreSQL / pgvector Configuration
DB_HOST=aws-0-ap-northeast-2.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.wgbxalgxcapwytrtfhyj
DB_PASSWORD=your_password
DB_SSLMODE=require

# Vector Store Settings
VECTOR_TABLE=vector_store
VECTOR_DIMENSION=3072
TOP_K=5

# Server & Upload Settings
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
MAX_UPLOAD_SIZE_MB=50
```

---

## 🏃 Running the Application

### 1. Activate the Virtual Environment
```powershell
# On Windows
.\venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Server
```bash
python main.py
```
Or with Uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The application will be live at:
- **Web UI**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🧪 Running Automated Tests

Run the integration test suite covering health checks, PDF upload, pgvector indexing, multi-turn conversation memory, and memory clearing:

```powershell
python test_app.py
```

---

## 📡 API Endpoints

### 1. Ask Question (RAG Query)
- **Method**: `POST /ask`
- **Request Body**:
```json
{
  "question": "What is Shepreneur?",
  "conversation_id": "session-123"
}
```
- **Response**:
```json
{
  "answer": "Shepreneur is an AI-powered business support platform...",
  "conversation_id": "session-123",
  "sources": ["Shepreneur_Project_Documentation.pdf"],
  "retrieved_count": 5
}
```

### 2. Upload PDF & Index into pgvector
- **Method**: `POST /upload-pdf`
- **Content-Type**: `multipart/form-data`
- **Form Field**: `file` (PDF file, up to 50MB)
- **Response**:
```json
{
  "message": "Successfully indexed 'document.pdf' into vector database.",
  "filename": "document.pdf",
  "pages_processed": 5,
  "chunks_stored": 12,
  "parent_document_id": "2495d438-b7ae-4f70-a3bc-22345091ff6d"
}
```

### 3. Clear Chat Memory
- **Method**: `POST /clear-memory` or `DELETE /memory/{conversation_id}`
- **Request Body** (for POST):
```json
{
  "conversation_id": "session-123"
}
```
- **Response**:
```json
{
  "message": "Conversation memory for 'session-123' cleared successfully.",
  "conversation_id": "session-123",
  "status": "success"
}
```

### 4. Health Check
- **Method**: `GET /health`
- **Response**:
```json
{
  "status": "healthy",
  "database_connected": true,
  "chat_model": "gemini-3.6-flash",
  "embedding_model": "gemini-embedding-001",
  "vector_dimension": 3072
}
```
