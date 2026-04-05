import os
import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import ensure_db, list_sources, get_user_memory, upsert_user_memory, list_graph_triplets, get_chunk_by_id
from .embedding import Embedder, Reranker
from .ingest import ingest_folder, ingest_single_file, ingest_url
from .insights import InsightsService
from .models import ChatRequest, ChatResponse, IngestFilesRequest, IngestFolderRequest, IngestResult, SourceItem, WeeklyInsights, MemoryModel, IngestUrlRequest
from .rag import RAGService
from .security import safe_filename
from .vector_store import VectorStore


os.makedirs(settings.data_dir, exist_ok=True)
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.chroma_dir, exist_ok=True)
ensure_db()

embedder = Embedder()
reranker = Reranker()
vector_store = VectorStore()
rag_service = RAGService(embedder=embedder, vector_store=vector_store, reranker=reranker)
insights_service = InsightsService(embedder=embedder)

app = FastAPI(title="Memora AI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def index():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/ingest/folder", response_model=list[IngestResult])
def api_ingest_folder(payload: IngestFolderRequest):
    results = ingest_folder(
        payload.folder_path,
        embedder=embedder,
        vector_store=vector_store,
        recursive=payload.recursive,
    )
    if not results:
        raise HTTPException(status_code=400, detail="Folder not found, not accessible, or no files discovered.")

    return [
        IngestResult(source_path=path, status=status, chunks_added=chunks)
        for path, chunks, status in results
    ]


@app.post("/api/ingest/files", response_model=list[IngestResult])
def api_ingest_files(payload: IngestFilesRequest):
    out: list[IngestResult] = []
    for file_path in payload.file_paths:
        path, chunks, status = ingest_single_file(file_path, embedder=embedder, vector_store=vector_store)
        out.append(IngestResult(source_path=path, status=status, chunks_added=chunks))
    return out


@app.post("/api/ingest/upload", response_model=list[IngestResult])
async def api_ingest_upload(files: list[UploadFile] = File(...)):
    out: list[IngestResult] = []

    for upload in files:
        safe_name = safe_filename(upload.filename or "upload.bin")
        target_path = os.path.join(settings.upload_dir, safe_name)
        if os.path.exists(target_path):
            stem = Path(safe_name).stem
            suffix = Path(safe_name).suffix
            idx = 1
            while True:
                candidate = os.path.join(settings.upload_dir, f"{stem}_{idx}{suffix}")
                if not os.path.exists(candidate):
                    target_path = candidate
                    break
                idx += 1

        with open(target_path, "wb") as f:
            shutil.copyfileobj(upload.file, f)

        path, chunks, status = ingest_single_file(target_path, embedder=embedder, vector_store=vector_store)
        out.append(IngestResult(source_path=path, status=status, chunks_added=chunks))

    return out


@app.post("/api/ingest/url", response_model=IngestResult)
def api_ingest_url(payload: IngestUrlRequest):
    source_path, chunks, status = ingest_url(payload.url, embedder=embedder, vector_store=vector_store)
    return IngestResult(source_path=source_path, status=status, chunks_added=chunks)


@app.post("/api/chat", response_model=ChatResponse)
def api_chat(payload: ChatRequest):
    answer, citations, confidence_score, confidence_label, metadata = rag_service.answer(
        payload.question,
        start_date=payload.start_date,
        end_date=payload.end_date,
        trust_levels=payload.trust_levels,
        source_types=payload.source_types,
    )
    suggestions = metadata.get("refinement_suggestions") if metadata else []
    if not isinstance(suggestions, list):
        suggestions = []

    return ChatResponse(
        answer=answer,
        citations=citations,
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        hallucination_warning=metadata.get("hallucination_warning") if metadata else None,
        refinement_suggestions=suggestions,
    )


@app.get("/api/sources", response_model=list[SourceItem])
def api_sources():
    rows = list_sources()
    return [
        SourceItem(
            id=r["id"],
            path=r["path"],
            title=r["title"],
            doc_type=r["doc_type"],
            created_at=r["created_at"],
            trust_level=r.get("trust_level", "medium"),
            source_type=r.get("source_type", "document"),
        )
        for r in rows
    ]


@app.get("/api/graph/triplets")
def api_graph_triplets(limit: int = 2000):
    safe_limit = max(1, min(limit, 10000))
    return {"triplets": list_graph_triplets(limit=safe_limit)}


@app.get("/api/chunk/{chunk_id}")
def api_get_chunk(chunk_id: int):
    chunk = get_chunk_by_id(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk


@app.get("/api/insights/weekly", response_model=WeeklyInsights)
def api_insights_weekly():
    insights = insights_service.generate_weekly_insights()
    return WeeklyInsights(**insights)


@app.get("/api/memory", response_model=MemoryModel)
def api_get_memory():
    return MemoryModel(preferences=get_user_memory())


@app.post("/api/memory")
def api_set_memory(payload: MemoryModel):
    upsert_user_memory(payload.preferences)
    return {"status": "ok"}
