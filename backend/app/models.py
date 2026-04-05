from typing import Optional

from pydantic import BaseModel, Field


class IngestFolderRequest(BaseModel):
    folder_path: str
    recursive: bool = True


class IngestFilesRequest(BaseModel):
    file_paths: list[str] = Field(default_factory=list)


class IngestUrlRequest(BaseModel):
    url: str


class IngestResult(BaseModel):
    source_path: str
    status: str
    chunks_added: int = 0
    reason: str = ""


class ChatRequest(BaseModel):
    question: str
    start_date: Optional[str] = None  # ISO format: 2026-01-01
    end_date: Optional[str] = None
    trust_levels: Optional[list[str]] = None  # e.g., ["high", "medium"] or None for all
    source_types: Optional[list[str]] = None  # e.g., ["personal_note", "email"] or None for all


class Citation(BaseModel):
    source_path: str
    title: str
    chunk_index: int
    chunk_id: Optional[int] = None
    relevance: float
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    final_score: float = 0.0


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence_score: float = 0.0
    confidence_label: str = "low"
    hallucination_warning: Optional[str] = None  # Warning if confidence too low
    refinement_suggestions: list[str] = Field(default_factory=list)  # Suggestions to improve answer quality


class TopicInsight(BaseModel):
    label: str
    chunk_count: int
    top_source: str
    confidence: float


class ContradictionItem(BaseModel):
    source_1: str
    source_2: str
    snippet_1: str
    snippet_2: str
    similarity: float


class SkillGap(BaseModel):
    question: Optional[str] = None
    reason: Optional[str] = None
    insight: Optional[str] = None
    recommendation: Optional[str] = None


class WeeklyInsights(BaseModel):
    status: str
    period_days: int = 7
    sources_count: int = 0
    chunks_count: int = 0
    questions_count: int = 0
    summary: str = ""
    message: Optional[str] = None
    topics: list[TopicInsight] = Field(default_factory=list)
    contradictions: list[ContradictionItem] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    top_sources: list[dict] = Field(default_factory=list)


class SourceItem(BaseModel):
    id: int
    path: str
    title: str
    doc_type: str
    created_at: str
    trust_level: str = "medium"
    source_type: str = "document"


class MemoryModel(BaseModel):
    preferences: str
