from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from app.core.config import get_settings


class ConversationStore:
    def __init__(self) -> None:
        self.db_path = get_settings().sqlite_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL DEFAULT '',
                    summarized_through_id INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                )
            """)
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(messages)").fetchall()
            }
            if "sources" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN sources TEXT NOT NULL DEFAULT '[]'")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id)")

    def create_or_get(self, conversation_id: str | None = None) -> str:
        cid = conversation_id or str(uuid.uuid4())
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM conversations WHERE id=?", (cid,)).fetchone()
            if row is None:
                if conversation_id:
                    raise ValueError("Conversation not found.")
                conn.execute("INSERT INTO conversations (id) VALUES (?)", (cid,))
        return cid

    def get_state(self, conversation_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT summary, summarized_through_id FROM conversations WHERE id=?",
                (conversation_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Conversation not found.")
            return dict(row)

    def get_messages(self, conversation_id: str, after_id: int = 0) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, role, content, sources FROM messages WHERE conversation_id=? AND id>? ORDER BY id",
                (conversation_id, after_id),
            ).fetchall()
            messages = []
            for row in rows:
                message = dict(row)
                message["sources"] = json.loads(message.pop("sources") or "[]")
                messages.append(message)
            return messages

    def get_last_messages(self, conversation_id: str, limit: int = 2) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
            return [dict(row) for row in reversed(rows)]

    def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO messages (conversation_id, role, content, sources) VALUES (?, ?, ?, ?)",
                (conversation_id, role, content, json.dumps(sources or [], ensure_ascii=False)),
            )
            conn.execute(
                "UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (conversation_id,),
            )
            return int(cursor.lastrowid)

    def update_summary(self, conversation_id: str, summary: str, summarized_through_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """UPDATE conversations
                   SET summary=?, summarized_through_id=?, updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (summary, summarized_through_id, conversation_id),
            )

    def prepare_context(self, conversation_id: str, groq_service) -> tuple[str, list[dict]]:
        """Summarize older messages when >=10 are pending, retaining the latest two."""
        state = self.get_state(conversation_id)
        summary = state["summary"] or ""
        pending = self.get_messages(conversation_id, state["summarized_through_id"])
        if len(pending) >= 10:
            to_summarize = pending[:-2]
            if to_summarize:
                summary = groq_service.summarize(summary, [
                    {"role": m["role"], "content": m["content"]} for m in to_summarize
                ])
                self.update_summary(conversation_id, summary, to_summarize[-1]["id"])
        recent = self.get_last_messages(conversation_id, 2)
        return summary, recent

    def full_history(self, conversation_id: str) -> dict:
        state = self.get_state(conversation_id)
        messages = self.get_messages(conversation_id)
        return {"conversation_id": conversation_id, "summary": state["summary"], "messages": messages}

    def list_conversations(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.created_at, c.updated_at,
                       COALESCE(
                           (SELECT content FROM messages
                            WHERE conversation_id = c.id AND role = 'user'
                            ORDER BY id LIMIT 1),
                           'محادثة جديدة'
                       ) AS title
                FROM conversations c
                WHERE EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = c.id)
                ORDER BY c.updated_at DESC, c.id DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]
