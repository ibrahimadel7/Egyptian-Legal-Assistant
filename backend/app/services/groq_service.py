from __future__ import annotations

import json
import logging
import re
from typing import Any

from groq import Groq

from app.core.config import get_settings
from app.core.prompts import (
    INTENT_CLASSIFIER_SYSTEM,
    QUERY_REWRITE_SYSTEM,
    SUMMARY_SYSTEM,
    ANSWER_SYSTEM,
    GENERAL_ANSWER_SYSTEM,
)

logger = logging.getLogger(__name__)


def _parse_json(content: str) -> dict[str, Any]:
    content = (content or "").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


class GroqService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is missing. Add it to the .env file.")
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    def _completion(self, messages: list[dict], max_tokens: int = 1200, json_mode: bool = True) -> str:
        if not json_mode:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as first_error:
            # Fallback for model/API combinations that reject JSON mode.
            logger.warning("JSON response mode failed; retrying without it: %s", first_error)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=max_tokens,
            )
        return response.choices[0].message.content or ""

    def rewrite_query(self, summary: str, recent_messages: list[dict], current_message: str) -> str:
        context = {
            "summary": summary,
            "recent_messages": recent_messages,
            "current_question": current_message,
        }
        raw = self._completion([
            {"role": "system", "content": QUERY_REWRITE_SYSTEM},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ], max_tokens=350)
        try:
            query = str(_parse_json(raw).get("query", "")).strip()
            return query or current_message
        except Exception:
            return current_message

    def classify_intent(
        self,
        summary: str,
        recent_messages: list[dict],
        current_message: str,
    ) -> str:
        payload = {
            "conversation_summary": summary,
            "last_two_messages": recent_messages,
            "current_message": current_message,
        }
        raw = self._completion([
            {"role": "system", "content": INTENT_CLASSIFIER_SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ], max_tokens=120)
        try:
            intent = str(_parse_json(raw).get("intent", "")).strip().lower()
            if intent in {"conversation", "general", "legal"}:
                return intent
            logger.warning("Classifier returned an unexpected intent: %s", intent)
        except Exception:
            logger.exception("Could not parse intent JSON")

        # A conservative fallback prevents malformed classifier output from
        # turning every message into a retrieval request.
        lowered = f"{summary} {current_message}".lower()
        legal_markers = (
            "law", "legal", "contract", "court", "employer", "dismiss",
            "قانون", "قانوني", "محكمة", "عقد", "فصل", "حقوقي", "دعوى",
        )
        return "legal" if any(marker in lowered for marker in legal_markers) else "general"

    def summarize(self, old_summary: str, messages: list[dict]) -> str:
        if not messages:
            return old_summary
        payload = {"previous_summary": old_summary, "new_messages": messages}
        raw = self._completion([
            {"role": "system", "content": SUMMARY_SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ], max_tokens=900, json_mode=False)
        return raw.strip() or old_summary

    def assess_and_answer(
        self,
        question: str,
        summary: str,
        recent_messages: list[dict],
        evidence_context: str,
    ) -> dict[str, Any]:
        payload = {
            "current_question": question,
            "conversation_summary": summary,
            "last_two_messages": recent_messages,
            "retrieved_legal_evidence": evidence_context,
        }
        raw = self._completion([
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ], max_tokens=1800)
        try:
            return _parse_json(raw)
        except Exception:
            logger.exception("Could not parse answer JSON")
            return {
                "sufficient": False,
                "reason": "تعذر التحقق من بنية الإجابة",
                "needs_clarification": False,
                "clarifying_question": None,
                "answer": "",
                "source_ids": [],
            }

    def answer_without_evidence(
        self,
        question: str,
        summary: str,
        recent_messages: list[dict],
    ) -> str:
        payload = {
            "current_question": question,
            "conversation_summary": summary,
            "last_two_messages": recent_messages,
        }
        answer = self._completion([
            {"role": "system", "content": GENERAL_ANSWER_SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ], max_tokens=1200, json_mode=False).strip()
        if not answer:
            raise RuntimeError("The language model returned an empty answer.")
        return answer
