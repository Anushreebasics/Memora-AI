import email
import hashlib
import mailbox
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import docx2txt
import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

import json
from openai import OpenAI

from .config import settings
from .db import get_source_by_path, insert_chunks, upsert_source, insert_triplets
from .embedding import Embedder
from .vector_store import VectorStore

ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".eml",
    ".mbox",
    ".csv",
    ".json",
}

BLOCKED_HOSTS = {"localhost", "127.0.0.1", "::1"}


def file_checksum(file_path: str) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(1024 * 1024)
            if not data:
                break
            sha.update(data)
    return sha.hexdigest()


def extract_text(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()

    if suffix in {".txt", ".md", ".csv", ".json"}:
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        reader = PdfReader(file_path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    if suffix == ".docx":
        return docx2txt.process(file_path) or ""

    if suffix == ".eml":
        with open(file_path, "rb") as f:
            msg = email.message_from_binary_file(f)
        parts: list[str] = []
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    parts.append(payload.decode(errors="ignore"))
        return "\n".join(parts)

    if suffix == ".mbox":
        parts: list[str] = []
        box = mailbox.mbox(file_path)
        for msg in box:
            payload = msg.get_payload(decode=True)
            if payload:
                parts.append(payload.decode(errors="ignore"))
        return "\n\n".join(parts)

    return ""


def split_chunks(text: str) -> list[str]:
    max_chars = settings.max_chunk_chars
    overlap = settings.chunk_overlap_chars

    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    n = len(normalized)
    while start < n:
        end = min(start + max_chars, n)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(0, end - overlap)
    return chunks


def detect_trust_level(file_path: str, doc_type: str) -> tuple[str, str]:
    """Infer trust level and source type from file metadata."""
    path_lower = file_path.lower()
    
    source_type = "document"
    trust_level = "medium"
    
    if doc_type in ["eml", "mbox"]:
        source_type = "email"
        trust_level = "medium"
    elif doc_type in ["md", "txt"]:
        if any(pattern in path_lower for pattern in ["notes", "journal", "personal", "my_", "todo", "log"]):
            source_type = "personal_note"
            trust_level = "high"
        else:
            source_type = "text_document"
            trust_level = "medium"
    elif doc_type == "pdf":
        source_type = "pdf"
        trust_level = "medium"
    elif doc_type in ["docx"]:
        if any(pattern in path_lower for pattern in ["notes", "my_", "personal"]):
            source_type = "personal_document"
            trust_level = "high"
        else:
            source_type = "document"
            trust_level = "medium"
    
    return source_type, trust_level


def _persist_text_source(
    source_path: str,
    title: str,
    doc_type: str,
    source_type: str,
    trust_level: str,
    text: str,
    embedder: Embedder,
    vector_store: VectorStore,
) -> tuple[str, int, str]:
    if not text.strip():
        return source_path, 0, "empty_or_unreadable"

    chunks = split_chunks(text)
    if not chunks:
        return source_path, 0, "no_chunks"

    checksum = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    existing = get_source_by_path(source_path)
    if existing and existing["checksum"] == checksum:
        return source_path, 0, "unchanged"

    source_id, created_at = upsert_source(
        source_path,
        title=title,
        doc_type=doc_type,
        checksum=checksum,
        trust_level=trust_level,
        source_type=source_type,
    )

    vector_store.remove_source_chunks(source_id)

    chunk_db_ids = insert_chunks(source_id, chunks)
    embeddings = embedder.embed_texts(chunks)

    vector_ids = [f"{source_id}:{chunk_idx}" for chunk_idx in range(len(chunks))]
    metadatas = [
        {
            "source_id": source_id,
            "chunk_id": chunk_db_ids[i],
            "path": source_path,
            "title": title,
            "chunk_index": i,
            "trust_level": trust_level,
            "source_type": source_type,
            "created_at": created_at,
        }
        for i in range(len(chunks))
    ]

    vector_store.add_chunks(vector_ids, chunks, embeddings, metadatas)

    if settings.openai_api_key:
        try:
            client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url if settings.openai_base_url else None
            )
            all_triplets = []
            for chunk in chunks[:4]:
                extraction_prompt = "Extract up to 4 key entity relationships from the following text. Return in strictly valid JSON format like: [{\"s\": \"Subject\", \"p\": \"predicate\", \"o\": \"Object\"}]. Only valid JSON list. Text: " + chunk
                completion = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[{"role": "user", "content": extraction_prompt}],
                    temperature=0.1
                )
                raw = completion.choices[0].message.content
                if "```json" in raw:
                    raw = raw.split("```json")[-1].split("```")[0]
                elif "```" in raw:
                    raw = raw.split("```")[-1].split("```")[0]
                triplets = json.loads(raw.strip())
                all_triplets.extend(triplets)
            insert_triplets(source_id, all_triplets)
        except Exception:
            pass

    return source_path, len(chunks), "ingested"


def _validate_public_url(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False, "unsupported_scheme"

    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False, "invalid_url"
    if host in BLOCKED_HOSTS:
        return False, "blocked_host"

    try:
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            ip = info[4][0]
            if ip.startswith("127.") or ip == "::1":
                return False, "blocked_host"
    except socket.gaierror:
        return False, "host_resolution_failed"

    return True, "ok"


def _extract_web_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "canvas", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()

    title = "Web page"
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    body = soup.body if soup.body else soup
    text = body.get_text(separator="\n", strip=True)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned_lines: list[str] = []
    for line in lines:
        if len(line) < 2:
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines), title


def ingest_url(url: str, embedder: Embedder, vector_store: VectorStore) -> tuple[str, int, str]:
    normalized_url = url.strip()
    is_valid, validation_status = _validate_public_url(normalized_url)
    if not is_valid:
        return normalized_url, 0, validation_status

    try:
        with httpx.Client(timeout=20.0, follow_redirects=True, headers={"User-Agent": "KnowledgeAssistantBot/1.0"}) as client:
            response = client.get(normalized_url)
            response.raise_for_status()
            html = response.text
    except httpx.TimeoutException:
        return normalized_url, 0, "request_timeout"
    except httpx.HTTPStatusError as e:
        return normalized_url, 0, f"http_error_{e.response.status_code}"
    except Exception:
        return normalized_url, 0, "request_failed"

    text, title = _extract_web_text(html)
    return _persist_text_source(
        source_path=normalized_url,
        title=title[:255] or "Web page",
        doc_type="web",
        source_type="web_page",
        trust_level="medium",
        text=text,
        embedder=embedder,
        vector_store=vector_store,
    )


def ingest_single_file(file_path: str, embedder: Embedder, vector_store: VectorStore) -> tuple[str, int, str]:
    abs_path = os.path.abspath(file_path)
    suffix = Path(abs_path).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return abs_path, 0, "unsupported_file_type"

    if not os.path.isfile(abs_path):
        return abs_path, 0, "file_not_found"

    text = extract_text(abs_path)

    title = Path(abs_path).name
    doc_type_str = suffix.lstrip(".")
    source_type, trust_level = detect_trust_level(abs_path, doc_type_str)
    return _persist_text_source(
        source_path=abs_path,
        title=title,
        doc_type=doc_type_str,
        source_type=source_type,
        trust_level=trust_level,
        text=text,
        embedder=embedder,
        vector_store=vector_store,
    )


def ingest_folder(folder_path: str, embedder: Embedder, vector_store: VectorStore, recursive: bool = True):
    root = Path(folder_path)
    if not root.exists() or not root.is_dir():
        return []

    pattern = "**/*" if recursive else "*"
    files = [str(p) for p in root.glob(pattern) if p.is_file()]
    results = []
    for fp in files:
        results.append(ingest_single_file(fp, embedder=embedder, vector_store=vector_store))
    return results
