import math
import re
import json
from datetime import datetime

from openai import OpenAI

from .config import settings
from .db import lexical_search_chunks, save_chat, search_sources_by_date_and_trust, get_user_memory, search_graph_triplets
from .embedding import Embedder, Reranker
from .models import Citation
from .vector_store import VectorStore


class RAGService:
    def __init__(self, embedder: Embedder, vector_store: VectorStore, reranker: Reranker = None) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.reranker = reranker
        self.client = OpenAI(
            api_key=settings.openai_api_key, 
            base_url=settings.openai_base_url if settings.openai_base_url else None
        ) if settings.openai_api_key else None

    def _search_knowledge_base(self, question: str, start_date=None, end_date=None, trust_levels=None, source_types=None) -> tuple[str, list[Citation], float]:
        queries = [question]
        if self.client:
            try:
                expansion_prompt = f"Rewrite this search query into 2 different variations that might find related semantic documents. Return only the 2 variations, one per line. Query: {question}"
                completion = self.client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[{"role": "user", "content": expansion_prompt}],
                    temperature=0.7,
                )
                variations = completion.choices[0].message.content.strip().split("\n")
                valid_vars = [v.strip("- 1234567890.\"\'\\") for v in variations if v.strip()]
                queries.extend(valid_vars[:2])
            except Exception:
                pass

        qvecs = self.embedder.embed_texts(queries)
        qvec = [sum(col) / len(col) for col in zip(*qvecs)]
        
        raw = self.vector_store.query(qvec, top_k=max(8, settings.top_k * 3))

        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        allowed_sources = search_sources_by_date_and_trust(start_date, end_date, trust_levels, limit=1000)
        allowed_source_ids = {int(s["id"]) for s in allowed_sources}
        allowed_source_types = set(source_types) if source_types else None
        trust_multipliers = {"high": 1.2, "medium": 1.0, "low": 0.7}

        lexical_hits = lexical_search_chunks(question, limit=max(8, settings.top_k * 3))

        candidates: dict[str, dict] = {}
        
        def get_recency_mult(created_at_str):
            if not created_at_str:
                return 1.0
            try:
                dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00").split(".")[0])
                days_old = (datetime.utcnow() - dt).days
                decay = min(1.0, max(0.0, days_old / 365.0))
                return max(0.7, 1.0 - (decay * 0.3))
            except Exception:
                return 1.0

        for idx, (doc, meta) in enumerate(zip(docs, metas)):
            source_id = int(meta.get("source_id", 0))
            if allowed_sources and source_id not in allowed_source_ids: continue
            source_type = str(meta.get("source_type", "document"))
            if allowed_source_types and source_type not in allowed_source_types: continue
            
            distance = float(distances[idx]) if idx < len(distances) else 1.0
            semantic_score = max(0.0, 1.0 - distance)
            
            trust_level = str(meta.get("trust_level", "medium"))
            trust_mult = trust_multipliers.get(trust_level, 1.0)
            recency_mult = get_recency_mult(meta.get("created_at"))
            
            key = f"{meta.get('path', '')}:{meta.get('chunk_index', 0)}"
            candidates[key] = {
                "doc": str(doc),
                "path": str(meta.get("path", "")),
                "title": str(meta.get("title", "")),
                "chunk_index": int(meta.get("chunk_index", 0)),
                "chunk_id": int(meta.get("chunk_id", 0)),
                "semantic_score": semantic_score,
                "lexical_score": 0.0,
                "trust_level": trust_level,
                "source_type": source_type,
                "trust_mult": trust_mult,
                "recency_mult": recency_mult,
            }

        for hit in lexical_hits:
            if allowed_sources and hit["source_id"] not in allowed_source_ids: continue
            if allowed_source_types and hit["source_type"] not in allowed_source_types: continue
            
            key = f"{hit['path']}:{hit['chunk_index']}"
            trust_level = hit.get("trust_level", "medium")
            trust_mult = trust_multipliers.get(trust_level, 1.0)
            recency_mult = get_recency_mult(hit.get("created_at"))
            
            if key not in candidates:
                candidates[key] = {
                    "doc": hit["chunk_text"],
                    "path": hit["path"],
                    "title": hit["title"],
                    "chunk_index": int(hit["chunk_index"]),
                    "chunk_id": int(hit.get("chunk_id", 0)),
                    "semantic_score": 0.0,
                    "lexical_score": float(hit["lexical_score"]),
                    "trust_level": trust_level,
                    "source_type": hit["source_type"],
                    "trust_mult": trust_mult,
                    "recency_mult": recency_mult,
                }
            else:
                candidates[key]["lexical_score"] = max(
                    float(candidates[key].get("lexical_score", 0.0)),
                    float(hit["lexical_score"]),
                )

        query_terms = [t for t in re.findall(r"[a-zA-Z0-9]+", question.lower()) if len(t) >= 3][:12]

        ranked: list[dict] = []
        for item in candidates.values():
            semantic = float(item["semantic_score"])
            lexical = float(item["lexical_score"])
            text = str(item["doc"]).lower()
            combined = (0.65 * semantic) + (0.35 * lexical)
            
            if query_terms:
                covered = sum(1 for term in query_terms if term in text)
                coverage = covered / len(query_terms)
            else:
                coverage = 0.0

            rerank_signal = (0.8 * coverage) + (0.2 * semantic)
            base_score = (0.7 * combined) + (0.3 * rerank_signal)
            final_score = base_score * item["trust_mult"] * item.get("recency_mult", 1.0)

            ranked.append({
                **item,
                "combined_score": combined,
                "final_score": max(0.0, min(1.0, final_score)),
            })

        ranked.sort(key=lambda x: x["final_score"], reverse=True)
        top_ranked = ranked[: settings.top_k * 3]
        
        if self.reranker and top_ranked:
            docs_to_rerank = [item["doc"] for item in top_ranked]
            rerank_scores = self.reranker.rerank(question, docs_to_rerank)
            for i, score in enumerate(rerank_scores):
                # Use CrossEncoder strictly for sorting, preserve original hybrid score for confidence % thresholds
                top_ranked[i]["rerank_score"] = float(score)
            top_ranked.sort(key=lambda x: x["rerank_score"], reverse=True)
            
        top_ranked = top_ranked[: settings.top_k]

        citations: list[Citation] = []
        context_parts: list[str] = []

        # Graph RAG Fetch
        triplets = search_graph_triplets(question)
        if triplets:
            graph_context = "Knowledge Graph Matches:\n" + "\n".join([f"- {t['subject']} {t['predicate']} {t['object_node']}" for t in triplets])
            context_parts.append(graph_context)

        for idx, hit in enumerate(top_ranked):
            citation = Citation(
                source_path=str(hit.get("path", "")),
                title=str(hit.get("title", "")),
                chunk_index=int(hit.get("chunk_index", 0)),
                chunk_id=int(hit.get("chunk_id", 0)),
                relevance=float(hit.get("final_score", 0.0)),
                semantic_score=float(hit.get("semantic_score", 0.0)),
                lexical_score=float(hit.get("lexical_score", 0.0)),
                final_score=float(hit.get("final_score", 0.0)),
            )
            citations.append(citation)
            context_parts.append(f"[Source {idx + 1}] title={citation.title}\n{hit.get('doc', '')}")

        context = "\n\n".join(context_parts)
        confidence_score = sum(float(h["final_score"]) for h in top_ranked[:3]) / min(3, len(top_ranked)) if top_ranked else 0.0
        
        return context, citations, confidence_score


    def answer(self, question: str, start_date: str = None, end_date: str = None, trust_levels: list[str] = None, source_types: list[str] = None):
        """Answer a question using Agentic Multi-hop Reasoning and Graph RAG."""
        user_memory = get_user_memory()
        system_prompt = (
            "You are an intelligent private knowledge assistant. Answer the user's question accurately using the provided context as your factual foundation. "
            "You are ALLOWED to use your general world knowledge to draw obvious logical conclusions, define common acronyms, or perform basic math based on the retrieved facts (e.g. knowing a B.Tech is 4 years). However, NEVER invent personal or specific details that aren't in the context. "
            "If the provided context does not contain enough information to formulate a complete answer, immediately call the `search_knowledge_base` tool to query for more specific details. "
            "If after using the `search_knowledge_base` tool you still don't have enough information, admit that you don't know based on available documents. "
            "Always end your final answer with a short 'Citations' section mapping your claims to specific Source titles."
        )
        if user_memory:
            system_prompt += f"\n\nUser Preferences and Memory:\nEnsure you strictly adhere to these instructions:\n{user_memory}"

        all_citations: list[Citation] = []
        best_confidence = 0.0

        def run_search(q: str):
            nonlocal all_citations, best_confidence
            ctx, citations, conf = self._search_knowledge_base(q, start_date, end_date, trust_levels, source_types)
            for c in citations:
                if not any(ex.source_path == c.source_path and ex.chunk_index == c.chunk_index for ex in all_citations):
                    all_citations.append(c)
            best_confidence = max(best_confidence, conf)
            return ctx

        if not self.client:
            ctx = run_search(question)
            answer = "No LLM API key configured. Here are excerpts:\n\n" + ctx[:2000]
            save_chat(question, answer, [c.model_dump() for c in all_citations])
            return answer, all_citations, best_confidence, "low", {}

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": "Searches the vector database and knowledge graph for relevant context. Formulate your query using highly specific keywords.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The specific query to search."}
                        },
                        "required": ["query"],
                    },
                }
            }
        ]

        # Force initial retrieval to avoid wasting one full LLM roundtrip just to do standard search
        initial_ctx = run_search(question)
        if initial_ctx.strip():
            messages.append({"role": "system", "content": f"INITIAL RETRIEVED CONTEXT:\n{initial_ctx}"})

        max_hops = 3
        final_answer = "No answer generated."

        for _ in range(max_hops):
            try:
                completion = self.client.chat.completions.create(
                    model=settings.openai_model,
                    messages=messages,
                    tools=tools,
                    temperature=0.2,
                )
            except Exception as e:
                err_msg = str(e)
                if "rate limit" in err_msg.lower() or "429" in err_msg:
                    final_answer = "I'm currently hitting my API Rate Limit (too many tokens processed). Please wait 10 seconds and try your search again!"
                else:
                    final_answer = f"API Error: {err_msg}"
                break
                
            message = completion.choices[0].message
            
            if message.tool_calls:
                messages.append(message)  # Add Assistant's tool_call choice
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "search_knowledge_base":
                        try:
                            args = json.loads(tool_call.function.arguments)
                            hop_query = args.get("query", "")
                            hop_ctx = run_search(hop_query)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": "search_knowledge_base",
                                "content": hop_ctx or "No relevant documents found for that query."
                            })
                        except Exception:
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": "search_knowledge_base",
                                "content": "Tool execution failed."
                            })
            else:
                final_answer = message.content or "No answer generated."
                break
        else:
            # Reached max hops
            final_answer = "Max reasoning hops reached. " + (completion.choices[0].message.content or "")

        save_chat(question, final_answer, [c.model_dump() for c in all_citations])

        if best_confidence >= 0.72:
            confidence_label = "high"
        elif best_confidence >= 0.45:
            confidence_label = "medium"
        else:
            confidence_label = "low"

        hallucination_warning = None
        if best_confidence < settings.confidence_threshold:
            hallucination_warning = f"Low confidence ({int(best_confidence * 100)}%). Multi-hop retrieval could not find strong definitive evidence."

        return final_answer, all_citations, best_confidence, confidence_label, {
            "hallucination_warning": hallucination_warning,
            "refinement_suggestions": []
        }
