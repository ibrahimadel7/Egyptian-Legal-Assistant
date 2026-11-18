from types import SimpleNamespace

from app.api import routes
from app.core.prompts import KNOWLEDGE_BASE_DISCLAIMER_AR
from app.schemas.chat import ChatRequest
from app.services.groq_service import GroqService


class FakeConversations:
    def __init__(self):
        self.saved = []

    def create_or_get(self, conversation_id=None):
        return conversation_id or "conversation-1"

    def prepare_context(self, conversation_id, groq):
        return "", []

    def save_message(self, conversation_id, role, content, sources=None):
        self.saved.append((role, content))


class FakeGroq:
    def __init__(self, intent="general", answer="إجابة عربية مفيدة"):
        self.intent = intent
        self.answer = answer
        self.rewrite_called = False

    def classify_intent(self, summary, recent, message):
        return self.intent

    def answer_without_evidence(self, question, summary, recent):
        return self.answer

    def rewrite_query(self, summary, recent, message):
        self.rewrite_called = True
        return message


def test_general_question_does_not_add_legal_disclaimer_or_retrieve(monkeypatch):
    conversations = FakeConversations()
    groq = FakeGroq()
    monkeypatch.setattr(routes, "ConversationStore", lambda: conversations)
    monkeypatch.setattr(routes, "GroqService", lambda: groq)

    response = routes.chat(ChatRequest(message="Explain Python"))

    assert response.answer == "إجابة عربية مفيدة"
    assert response.sources == []
    assert groq.rewrite_called is False
    assert KNOWLEDGE_BASE_DISCLAIMER_AR not in response.answer


def test_empty_legal_index_returns_answer_instead_of_503(monkeypatch):
    conversations = FakeConversations()
    groq = FakeGroq(intent="legal")
    monkeypatch.setattr(routes, "ConversationStore", lambda: conversations)
    monkeypatch.setattr(routes, "GroqService", lambda: groq)
    monkeypatch.setattr(routes, "get_settings", lambda: SimpleNamespace(max_cosine_distance=0.4))
    monkeypatch.setattr(
        "app.services.vector_store.get_vector_store",
        lambda: SimpleNamespace(collection=SimpleNamespace(count=lambda: 0)),
    )

    response = routes.chat(ChatRequest(message="ما هي حقوقي في الفصل التعسفي؟"))

    assert response.status == "answered"
    assert response.answer.startswith("إجابة عربية مفيدة")
    assert KNOWLEDGE_BASE_DISCLAIMER_AR in response.answer
    assert groq.rewrite_called is False


def test_partial_legal_answer_is_kept_and_invalid_citations_are_removed(monkeypatch):
    conversations = FakeConversations()
    groq = FakeGroq(intent="legal")
    groq.assess_and_answer = lambda **kwargs: {
        "sufficient": False,
        "needs_clarification": False,
        "answer": "الجزء المدعوم [S1] والمرجع غير الموجود [S99].",
        "source_ids": ["S1", "S99"],
    }

    class FakeRetrieval:
        def search(self, query):
            return [{"distance": 0.1}]

        def expand_context(self, chunks):
            return chunks

        def build_context(self, chunks):
            return "دليل قانوني", [{
                "source_id": "S1",
                "law_name": "قانون تجريبي",
                "categories": "",
                "unit_label": "",
                "unit_type": "",
                "article_number": "",
                "excerpt": "نص الدليل",
                "expanded": False,
            }]

    monkeypatch.setattr(routes, "ConversationStore", lambda: conversations)
    monkeypatch.setattr(routes, "GroqService", lambda: groq)
    monkeypatch.setattr(routes, "RetrievalService", FakeRetrieval)
    monkeypatch.setattr(routes, "get_settings", lambda: SimpleNamespace(max_cosine_distance=0.4))
    monkeypatch.setattr(
        "app.services.vector_store.get_vector_store",
        lambda: SimpleNamespace(collection=SimpleNamespace(count=lambda: 1)),
    )

    response = routes.chat(ChatRequest(message="اشرح حقوق العامل"))

    assert "الجزء المدعوم [S1]" in response.answer
    assert "[S99]" not in response.answer
    assert [source.source_id for source in response.sources] == ["S1"]


def test_malformed_classifier_response_does_not_default_everything_to_legal():
    groq = GroqService.__new__(GroqService)
    groq._completion = lambda *args, **kwargs: "not json"

    assert groq.classify_intent("", [], "Explain Python") == "general"
    assert groq.classify_intent("", [], "ما هي حقوقي في عقد العمل؟") == "legal"
