# Memora AI

A local-first AI assistant that ingests your personal files (notes, documents, emails) and gives conversational answers grounded in your own data with citations.

## Features

### Core Capabilities
- File ingestion pipeline for `.txt`, `.md`, `.pdf`, `.docx`, `.eml`, `.mbox`, `.csv`, `.json`
- Chunking + embeddings (`sentence-transformers`) + vector retrieval (`ChromaDB`)
- Hybrid retrieval (semantic + lexical) with neural reranking
- Retrieval-Augmented Generation (RAG)
  - Uses OpenAI for answer synthesis if `OPENAI_API_KEY` is set
  - Falls back to retrieval excerpts if no API key is configured
- Local metadata and chat logging in SQLite
- Per-answer confidence scoring and hallucination detection

### Advanced Features
- **Interactive Citation Highlights** — Click any citation to view the exact source paragraph in a modal with copy/export options
- **Live Web-Scraping Ingestion** — Paste URLs (Wikipedia, docs, Notion) to dynamically scrape, clean HTML, chunk, and ingest web content
- **Interactive 2D/3D Knowledge Graph** — Visualize entity relationships extracted from your documents as a force-directed network with zoom, pan, and node focus
- **Contradiction Detection & Automated Insights** — Proactive System 2 analysis that scans documents for conflicting claims, reveals dominant topics, identifies skill gaps, and generates weekly intelligence reports
- **Knowledge Graph Extraction** — Automatically extracts [Subject, Predicate, Object] triplets from documents for relationship visualization
- **System Memory** — Global memory for system prompts and custom RAG instructions
- **Weekly Intelligence Reports** — Automated insights on ingested sources, detected contradictions, topics, and low-confidence Q&A patterns

## Architecture

### Ingestion Pipeline
- **File Upload**: Upload files (.txt, .md, .pdf, .docx, .eml, .mbox, .csv, .json) via UI
- **URL Scraping**: Paste public URLs (Wikipedia, documentation, Notion) for automatic fetching and cleaning
- **Text Extraction**: Specialized extractors for each file type
- **Checksum Detection**: Skip re-ingestion of unchanged files
- **Chunking with Overlap**: Configurable chunk size and overlap for better retrieval context

### Indexing & Storage
- **Embeddings**: Generated locally with `all-MiniLM-L6-v2` (sentence-transformers)
- **Vector Store**: Persistent Chroma collection with cosine similarity
- **Knowledge Graph**: SQLite triplets table capturing [Subject, Predicate, Object] relationships
- **Metadata**: SQLite stores source info (path, title, type, trust level, ingestion date)

### Retrieval System
- **Hybrid Retrieval**: Combines semantic (vector) and lexical (keyword) search
- **Query Expansion**: LLM-based query rewriting for better coverage
- **Trust & Recency Scoring**: Weighs results by source trust level and freshness
- **Neural Reranking**: CrossEncoder reranking for top-k results
- **Citation Tracking**: Preserves chunk IDs for clickable source lookup

### Knowledge Extraction
- **Triplet Extraction**: LLM-based extraction of entity relationships from chunks
- **Contradiction Detection**: Semantic claim comparison with numerical conflict detection
- **Topic Clustering**: Semantic grouping of similar content for insights
- **Skill Gaps**: Low-confidence Q&A pattern detection for knowledge base improvement

### Generation & Analysis
- **RAG Answer Synthesis**: Question + context → grounded answers with confidence scoring
- **Proactive Insights**: Weekly scans for contradictions, topics, and gaps
- **Hallucination Detection**: Confidence thresholds and retrieval validation

## Project structure

```text
backend/
  app/
    config.py
    db.py
    embedding.py
    ingest.py
    main.py
    models.py
    rag.py
    vector_store.py
  static/
    index.html
.env.example
requirements.txt
README.md
```

## Setup

1. Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment:

```bash
cp .env.example .env
```

4. (Optional) Add OpenAI key to `.env`:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

5. Run the server:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

6. Open app:

- `http://127.0.0.1:8000`

## Usage

### Chat with Your Knowledge Base
1. Navigate to **Chat Assistant** tab
2. Ask questions conversationally
3. Answers include citations with **relevance scores**
4. **Click any citation** to view the exact source paragraph in a modal
5. Copy or export cited text

### Ingest Knowledge
Choose any ingestion method:

**File Upload**
- Click **Upload Zone** or drag & drop files
- Supports: PDF, TXT, MD, DOCX, CSV, JSON, EML, MBOX
- Click **Ingest into Database**

**Folder Ingestion**
- Use backend API or CLI: `curl -X POST http://127.0.0.1:8000/api/ingest/folder -H "Content-Type: application/json" -d '{"folder_path": "/path/to/folder", "recursive": true}'`

**Live Web Scraping**
- Paste a public URL (Wikipedia, documentation, Notion)
- Click **Ingest URL**
- Backend automatically fetches, cleans HTML, chunks, and embeds content

### Explore Your Knowledge
**Data Sources Tab**
- View interactive **Knowledge Graph** visualization of entity relationships
- Watch nodes cluster and links form as nodes are clicked for focus
- Below graph: see all ingested sources with metadata

**Weekly Insights Tab**
- View metrics: sources ingested, total chunks, questions asked
- See **🚨 Contradictions Detected** with confidence scores
- Review **Dominant Topics** extracted from your documents
- Check **Skill Gaps** — low-confidence Q&A patterns suggesting what to ingest next
- See key sources from the past week

**Global Memory Tab**
- Add system prompts and instructions for the RAG agent
- Customize how the assistant should respond across all conversations

## Privacy and security notes

This is local-first by default:

- Embeddings and metadata are stored on your machine under `./data`
- If `OPENAI_API_KEY` is set, retrieved context is sent to OpenAI for answer synthesis
- If no key is set, no external LLM calls are made

Recommended hardening for production:

- Add authentication and per-user access controls
- Encrypt sensitive at-rest data (SQLite + uploaded files)
- Add a consented connector model for Gmail/Notion/Drive integrations
- Add PII redaction and DLP checks before external model calls
- Add audit logs and retention policies

## Planned Enhancements

- **Multi-hop Reasoning**: Chain-of-thought retrieval for complex questions
- **OAuth/Account System**: Per-user knowledge bases with authentication
- **Connectors**: Direct integrations for Gmail, Notion, Slack, calendar, Drive
- **Fine-tuned Embeddings**: Custom embeddings trained on your domain
- **Speech I/O**: Voice input and audio response generation
- **Collaborative Insights**: Multi-user knowledge base synthesis
- **Export Formats**: Generate reports, PDFs, knowledge base dumps
- **Advanced DLP**: PII redaction before external LLM calls

## API Reference

### Chat & RAG
- `POST /api/chat` — Answer a question with RAG
- `GET /api/sources` — List all ingested sources
- `GET /api/memory` — Retrieve system memory/prompts
- `POST /api/memory` — Update system memory

### Ingestion
- `POST /api/ingest/upload` — Upload files (multipart/form-data)
- `POST /api/ingest/folder` — Ingest a local folder
- `POST /api/ingest/url` — Scrape and ingest a public URL

### Knowledge Extraction & Analysis
- `GET /api/graph/triplets` — Fetch knowledge graph triplets (limit up to 10k)
- `GET /api/chunk/{chunk_id}` — Fetch full chunk text with source metadata
- `GET /api/insights/weekly` — Generate weekly insights report

### Endpoints Examples

**Ask a question:**
```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What are my key projects?"}'
```

**Ingest a URL:**
```bash
curl -X POST http://127.0.0.1:8000/api/ingest/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/docs/page"}'
```

**Get insights:**
```bash
curl http://127.0.0.1:8000/api/insights/weekly
```

## Troubleshooting

**Empty answers:**
- Ensure files are ingested and appear in **Data Sources**
- Check that chunks were extracted (see logs: `chunks_added > 0`)

**Slow first run:**
- Embedding model (`all-MiniLM-L6-v2`) downloads on first startup (~90MB)
- Large folder ingestion can take minutes depending on file count

**Knowledge Graph not showing:**
- Ensure OPENAI_API_KEY is set in `.env` (triplet extraction requires LLM)
- Ingest at least 3 documents to see meaningful relationships

**URL Scraping fails:**
- Check that URL is publicly accessible (no 403/timeouts)
- Some sites with heavy JavaScript rendering may return sparse text
- Recommendation: Paste URLs to markdown conversion tools (e.g., Markdown.link) first

**PDF extraction issues:**
- Scanned PDFs (images) won't extract text without OCR
- Use text-based PDFs or convert scans to text first

**Contradictions not detected:**
- Ensure documents are ingested (insights run on past 7 days by default)
- Ingest at least 2 conflicting sources for comparison
- Configure `insights_window_days` in `config.py` if needed

**High memory usage:**
- Large vector databases (Chroma) and embeddings can consume RAM
- Reduce `top_k` or `max_chunk_chars` in `config.py` if needed
