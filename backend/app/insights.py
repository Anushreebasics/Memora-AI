from collections import defaultdict
import re

from .config import settings
from .db import get_chunks_from_sources, get_recent_questions, get_recent_sources
from .embedding import Embedder


class InsightsService:
    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder

    def _semantic_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Cosine similarity between two embedding vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def _extract_claims(self, text: str) -> list[str]:
        """Extract meaningful claims/sentences from text."""
        claims = []
        sentences = re.split(r'[.!?]+', text)
        
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 15 and len(sent) < 400:
                claims.append(sent)
        
        return claims[:10]

    def _detect_key_numbers_and_entities(self, text: str) -> dict:
        """Extract numbers, entities, and key terms for contradiction detection."""
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        
        currency = re.findall(r'\$\d+(?:,\d{3})*(?:\.\d+)?|€\d+|£\d+', text)
        
        percentages = re.findall(r'\d+(?:\.\d+)?%', text)
        
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        return {
            'numbers': numbers[:5],
            'currency': currency[:3],
            'percentages': percentages[:3],
            'entities': list(set(entities))[:5],
        }

    def generate_weekly_insights(self) -> dict:
        """Generate insights from the past week of ingestion and chat activity."""
        recent_sources = get_recent_sources(days=settings.insights_window_days)
        if not recent_sources:
            return {
                "status": "no_data",
                "period_days": settings.insights_window_days,
                "sources_count": 0,
                "chunks_count": 0,
                "questions_count": 0,
                "summary": "No activity this week.",
                "message": "No sources ingested this week.",
                "topics": [],
                "contradictions": [],
                "skill_gaps": [],
                "top_sources": [],
            }

        source_ids = [s["id"] for s in recent_sources]
        recent_chunks = get_chunks_from_sources(source_ids, limit=200)
        recent_questions = get_recent_questions(days=settings.insights_window_days, limit=50)

        topics = self._detect_topics(recent_chunks)
        contradictions = self._detect_contradictions(recent_chunks)
        skill_gaps = self._detect_skill_gaps(recent_questions)
        summary = self._generate_summary(recent_sources, len(recent_chunks), len(recent_questions))

        return {
            "status": "ok",
            "period_days": settings.insights_window_days,
            "sources_count": len(recent_sources),
            "chunks_count": len(recent_chunks),
            "questions_count": len(recent_questions),
            "summary": summary,
            "topics": topics,
            "contradictions": contradictions,
            "skill_gaps": skill_gaps,
            "top_sources": [{"title": s["title"], "doc_type": s["doc_type"]} for s in recent_sources[:5]],
        }

    def _detect_topics(self, chunks: list[dict], top_k: int = 5) -> list[dict]:
        """Group chunks by semantic similarity to detect topics."""
        if not chunks or len(chunks) < 2:
            return []

        chunk_texts = [c["chunk_text"] for c in chunks]
        embeddings = self.embedder.embed_texts(chunk_texts)

        # Simple clustering: use first chunk as seed, find similar ones
        clusters = defaultdict(list)
        assigned = set()

        for seed_idx in range(min(top_k, len(embeddings))):
            if seed_idx in assigned:
                continue

            seed_embedding = embeddings[seed_idx]
            cluster = [{"text": chunk_texts[seed_idx], "source": chunks[seed_idx].get("title", "unknown")}]
            assigned.add(seed_idx)

            for other_idx in range(seed_idx + 1, len(embeddings)):
                if other_idx in assigned:
                    continue
                similarity = self._semantic_similarity(seed_embedding, embeddings[other_idx])
                if similarity > 0.65:
                    cluster.append(
                        {"text": chunk_texts[other_idx], "source": chunks[other_idx].get("title", "unknown")}
                    )
                    assigned.add(other_idx)

            if len(cluster) > 1:
                clusters[seed_idx] = cluster

        topics = []
        for seed_idx, cluster in list(clusters.items())[:top_k]:
            label = self._extract_topic_label(chunk_texts[seed_idx])
            topics.append(
                {
                    "label": label,
                    "chunk_count": len(cluster),
                    "top_source": cluster[0]["source"],
                    "confidence": min(1.0, 0.7 + (len(cluster) * 0.05)),
                }
            )

        return topics[:top_k]

    def _extract_topic_label(self, text: str, max_length: int = 60) -> str:
        """Extract a short label from the first sentence."""
        sentences = text.split(".")
        if sentences:
            label = sentences[0].strip()
            if len(label) > max_length:
                label = label[:max_length] + "..."
            return label
        return "Untitled topic"

    def _detect_contradictions(self, chunks: list[dict]) -> list[dict]:
        """
        Find potential contradictions by comparing semantic meaning of claims across sources.
        Looks for cases where two sources make conflicting statements about the same topic.
        """
        if len(chunks) < 3:
            return []

        contradictions = []
        chunk_texts = [c["chunk_text"] for c in chunks]
        embeddings = self.embedder.embed_texts(chunk_texts)

        # Group chunks by potential topic similarity to reduce cross-check overhead
        for i in range(len(embeddings)):
            source_i = chunks[i].get("title", "Unknown")
            claims_i = self._extract_claims(chunks[i]["chunk_text"])
            if not claims_i:
                continue

            # Embed all claims from chunk i for comparison
            claim_embeddings_i = self.embedder.embed_texts(claims_i)

            for j in range(i + 1, len(embeddings)):
                source_j = chunks[j].get("title", "Unknown")
                if source_i == source_j:
                    continue  # Skip same source

                claims_j = self._extract_claims(chunks[j]["chunk_text"])
                if not claims_j:
                    continue

                # Embed all claims from chunk j
                claim_embeddings_j = self.embedder.embed_texts(claims_j)

                # Find claim pairs with high semantic similarity but potentially contradictory signals
                for claim_idx_i, claim_i in enumerate(claims_i):
                    for claim_idx_j, claim_j in enumerate(claims_j):
                        claim_sim = self._semantic_similarity(claim_embeddings_i[claim_idx_i], claim_embeddings_j[claim_idx_j])

                        # High similarity (suggesting same topic) triggers deeper analysis
                        if claim_sim > 0.72:
                            # Check for factual/numerical contradictions
                            facts_i = self._detect_key_numbers_and_entities(claim_i)
                            facts_j = self._detect_key_numbers_and_entities(claim_j)

                            # Detect number/currency conflicts
                            conflict_score = 0
                            if facts_i['numbers'] and facts_j['numbers']:
                                nums_i = set(facts_i['numbers'])
                                nums_j = set(facts_j['numbers'])
                                if nums_i & nums_j == set():  # No overlap = potential conflict
                                    conflict_score += 0.4

                            if facts_i['currency'] and facts_j['currency']:
                                if facts_i['currency'][0] != facts_j['currency'][0]:
                                    conflict_score += 0.3

                            # Check for temporal or named entity conflicts
                            entities_overlap = len(set(facts_i['entities']) & set(facts_j['entities'])) > 0
                            if entities_overlap and conflict_score > 0:
                                conflict_score += 0.3

                            if conflict_score > 0.5:
                                contradictions.append(
                                    {
                                        "source_1": source_i,
                                        "source_2": source_j,
                                        "snippet_1": claim_i[:120],
                                        "snippet_2": claim_j[:120],
                                        "similarity": float(claim_sim),
                                        "conflict_score": float(conflict_score),
                                    }
                                )

        # Deduplicate and rank by conflict score
        seen = set()
        unique = []
        for c in contradictions:
            key = (c["snippet_1"][:30], c["snippet_2"][:30])
            if key not in seen:
                seen.add(key)
                unique.append(c)
        
        unique.sort(key=lambda x: x.get("conflict_score", 0), reverse=True)
        return unique[:6]

    def _detect_skill_gaps(self, questions: list[dict]) -> list[dict]:
        """Find questions that were asked but not well-answered (low confidence patterns)."""
        gaps = []
        low_confidence_count = 0

        for q in questions:
            try:
                answer_text = q.get("answer", "")
                if "could not find" in answer_text.lower() or "insufficient" in answer_text.lower():
                    low_confidence_count += 1
                    gaps.append(
                        {
                            "question": q["question"][:80],
                            "reason": "Limited context in knowledge base",
                        }
                    )
            except Exception:
                pass

        if low_confidence_count > 0:
            gaps.append(
                {
                    "insight": f"You asked {low_confidence_count} questions with low-confidence answers.",
                    "recommendation": "Ingest more materials related to these topics or rephrase questions.",
                }
            )

        return gaps[:5]

    def _generate_summary(self, sources: list[dict], chunk_count: int, question_count: int) -> str:
        """Generate a human-readable summary."""
        if not sources:
            return "No activity this week."

        summary_parts = [
            f"You ingested {len(sources)} source(s) ({chunk_count} chunks)",
            f"Asked {question_count} question(s)",
        ]

        high_trust_count = len([s for s in sources if s.get("trust_level") == "high"])
        if high_trust_count > 0:
            summary_parts.append(f"{high_trust_count} from personal notes")

        return "; ".join(summary_parts) + "."
