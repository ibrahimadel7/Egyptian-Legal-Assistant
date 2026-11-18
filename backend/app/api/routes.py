from __future__ import annotations

import logging
import re
from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse, SourceItem
from app.services.groq_service import GroqService
from app.services.retrieval import RetrievalService
from app.storage.conversations import ConversationStore
from app.core.config import get_settings
from app.core.prompts import KNOWLEDGE_BASE_DISCLAIMER_AR

logger = logging.getLogger(__name__)
router = APIRouter()


def _answer_without_knowledge_base(
    groq,
    question: str,
    summary: str,
    recent: list[dict],
    *,
    is_legal: bool,
) -> str:
    answer = groq.answer_without_evidence(question, summary, recent).strip()
    if not answer:
        raise RuntimeError("The language model returned an empty answer.")
    if is_legal and KNOWLEDGE_BASE_DISCLAIMER_AR not in answer:
        return f"{answer}\n\n{KNOWLEDGE_BASE_DISCLAIMER_AR}"
    return answer


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    settings = get_settings()
    try:
        conversations = ConversationStore()
        conversation_id = conversations.create_or_get(request.conversation_id)

        groq = GroqService()

        summary, recent = conversations.prepare_context(conversation_id, groq)
        intent = groq.classify_intent(summary, recent, request.message)
        if intent != "legal":
            answer = _answer_without_knowledge_base(
                groq, request.message, summary, recent, is_legal=False
            )
            conversations.save_message(conversation_id, "user", request.message)
            conversations.save_message(conversation_id, "assistant", answer)
            return ChatResponse(
                conversation_id=conversation_id,
                status="answered",
                answer=answer,
                sources=[],
                retrieval_query="",
            )

        retrieval_query = ""
        seed_chunks = []
        retrieval = None
        try:
            from app.services.vector_store import get_vector_store

            if get_vector_store().collection.count() > 0:
                retrieval_query = groq.rewrite_query(summary, recent, request.message)
                retrieval = RetrievalService()
                seed_chunks = retrieval.search(retrieval_query)
            else:
                logger.warning("Legal retrieval skipped because the vector index is empty.")
        except Exception:
            logger.exception("Legal retrieval infrastructure is unavailable; using fallback.")

        # Chroma uses cosine distance: lower is closer. This threshold is a
        # configurable, uncalibrated baseline and must be evaluated.
        if (
            not seed_chunks
            or min(x["distance"] for x in seed_chunks) > settings.max_cosine_distance
            or retrieval is None
        ):
            answer = _answer_without_knowledge_base(
                groq, request.message, summary, recent, is_legal=True
            )
            status = "answered"
            sources = []
        else:
            expanded = retrieval.expand_context(seed_chunks)
            evidence_context, available_sources = retrieval.build_context(expanded)
            if not evidence_context or not available_sources:
                answer = _answer_without_knowledge_base(
                    groq, request.message, summary, recent, is_legal=True
                )
                status = "answered"
                sources = []
            else:
                result = groq.assess_and_answer(
                    question=request.message,
                    summary=summary,
                    recent_messages=recent,
                    evidence_context=evidence_context,
                )
                raw_source_ids = result.get("source_ids") or []
                if isinstance(raw_source_ids, str):
                    raw_source_ids = [raw_source_ids]
                source_map = {s["source_id"]: s for s in available_sources}
                valid_ids = []
                for sid in raw_source_ids:
                    if sid in source_map and sid not in valid_ids:
                        valid_ids.append(sid)
                answer = str(result.get("answer") or "").strip()
                allowed_labels = set(source_map)
                answer = re.sub(
                    r"\[(S\d+)\]",
                    lambda match: match.group(0) if match.group(1) in allowed_labels else "",
                    answer,
                ).strip()
                cited_ids = set(re.findall(r"\[(S\d+)\]", answer))
                if cited_ids:
                    valid_ids = [sid for sid in valid_ids if sid in cited_ids]
                    valid_ids.extend(
                        sid for sid in cited_ids
                        if sid in source_map and sid not in valid_ids
                    )
                valid_sources = [source_map[sid] for sid in valid_ids]
                if answer and valid_sources and not cited_ids:
                    answer += "\n\nالمصادر: " + "، ".join(f"[{sid}]" for sid in valid_ids)
                if not answer:
                    answer = _answer_without_knowledge_base(
                        groq, request.message, summary, recent, is_legal=True
                    )
                    valid_sources = []
                needs_clarification = result.get("needs_clarification") is True or (
                    isinstance(result.get("needs_clarification"), str)
                    and result["needs_clarification"].strip().lower() in {"true", "yes", "1"}
                )
                clarifying_question = str(result.get("clarifying_question") or "").strip()
                if needs_clarification and clarifying_question:
                    answer = f"{answer}\n\n{clarifying_question}".strip()
                    status = "needs_clarification"
                else:
                    status = "answered"
                sources = [
                    SourceItem(
                        source_id=s["source_id"],
                        law_name=s["law_name"],
                        categories=s["categories"],
                        unit_label=s["unit_label"],
                        unit_type=s["unit_type"],
                        article_number=s["article_number"],
                        excerpt=s["excerpt"],
                        expanded=s["expanded"],
                    )
                    for s in valid_sources
                ]

        conversations.save_message(conversation_id, "user", request.message)
        conversations.save_message(
            conversation_id,
            "assistant",
            answer,
            [source.model_dump() for source in sources],
        )
        return ChatResponse(
            conversation_id=conversation_id,
            status=status,
            answer=answer,
            sources=sources,
            retrieval_query=retrieval_query,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail="Chat request failed. Check server logs.") from exc


@router.get("/conversations")
def list_conversations():
    return ConversationStore().list_conversations()


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    try:
        return ConversationStore().full_history(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
