from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict
from typing import Any, Iterable


# Bare "مادة N" is commonly used as an article heading in this corpus.
# Definite "المادة N" is accepted only at a structural boundary to avoid
# splitting every cross-reference such as "وفقاً للمادة 12".
_BOUNDARY = r"(?:(?<=^)|(?<=[\n\r])|(?<=[.؛])|(?<=[(]))\s*"
_ARTICLE_NUMBER = (
    r"(?P<number>[0-9٠-٩۰-۹]+|الأولى|الأولى|الاولى|الاولي|الثانية|الثالثة|"
    r"الرابعة|الخامسة|السادسة|السابعة|الثامنة|التاسعة|العاشرة)"
)
BARE_ARTICLE_RE = re.compile(
    r"(?<!\S)(?P<label>مادة\s*(?:[:：]\s*)?(?:رقم\s*)?" +
    _ARTICLE_NUMBER + r"(?:\s*(?:مكرر|مكررة))?)",
    re.IGNORECASE,
)
DEFINITE_ARTICLE_RE = re.compile(
    _BOUNDARY + r"(?P<label>المادة\s*(?:[:：]\s*)?(?:رقم\s*)?" +
    _ARTICLE_NUMBER + r"(?:\s*(?:مكرر|مكررة))?)",
    re.IGNORECASE,
)
APPEAL_RE = re.compile(
    _BOUNDARY + r"(?P<label>الطعن\s+رقم\s*[0-9٠-٩۰-۹]+(?:\s+لسنة\s*[0-9٠-٩۰-۹]+)?)",
    re.IGNORECASE,
)
SENTENCE_RE = re.compile(r"(?<=[.!؟؛])\s+|[\r\n]+")


@dataclass
class Chunk:
    id: str
    text: str
    record_id: str
    unit_id: str
    law_name: str
    categories: str
    category_path: str
    unit_type: str
    unit_label: str
    article_number: str
    unit_index: int
    chunk_index: int
    unit_chunk_index: int

    def metadata(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "unit_id": self.unit_id,
            "law_name": self.law_name or "غير محدد",
            "categories": self.categories or "",
            "category_path": self.category_path or "",
            "unit_type": self.unit_type,
            "unit_label": self.unit_label or "",
            "article_number": self.article_number or "",
            "unit_index": int(self.unit_index),
            "chunk_index": int(self.chunk_index),
            "unit_chunk_index": int(self.unit_chunk_index),
        }


def _token_count(text: str, tokenizer: Any | None) -> int:
    if tokenizer is not None:
        try:
            return len(tokenizer.encode(text, add_special_tokens=False))
        except Exception:
            pass
    # Approximation only, used in unit tests or when tokenizer is unavailable.
    return max(1, len(re.findall(r"\S+", text)))


def _split_oversized(text: str, tokenizer: Any | None, max_tokens: int) -> list[str]:
    if tokenizer is not None:
        try:
            ids = tokenizer.encode(text, add_special_tokens=False)
            if len(ids) <= max_tokens:
                return [text.strip()]
            pieces = []
            for start in range(0, len(ids), max_tokens):
                part = tokenizer.decode(ids[start:start + max_tokens], skip_special_tokens=True).strip()
                if part:
                    pieces.append(part)
            return pieces
        except Exception:
            pass
    # Character fallback is deliberately conservative; real ingestion uses the model tokenizer.
    words = text.split()
    pieces, current = [], []
    for word in words:
        trial = " ".join(current + [word])
        if current and _token_count(trial, None) > max_tokens:
            pieces.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        pieces.append(" ".join(current))
    return pieces or [text.strip()]


def _pack_sentences(text: str, tokenizer: Any | None, max_tokens: int) -> list[str]:
    sentences = [s.strip() for s in SENTENCE_RE.split(text) if s.strip()]
    if not sentences:
        sentences = [text.strip()]
    expanded: list[str] = []
    for sentence in sentences:
        if _token_count(sentence, tokenizer) > max_tokens:
            expanded.extend(_split_oversized(sentence, tokenizer, max_tokens))
        else:
            expanded.append(sentence)

    packed: list[str] = []
    current = ""
    for sentence in expanded:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if current and _token_count(candidate, tokenizer) > max_tokens:
            packed.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        packed.append(current)
    return packed


def _is_case_law(categories: list[str]) -> bool:
    joined = " ".join(categories)
    return any(marker in joined for marker in ("النقض", "المحكمة الادارية", "المحكمة الإدارية", "اداريا عليا", "إداريا عليا"))


def _make_units(text: str, categories: list[str]) -> list[tuple[str, str, str, str]]:
    """Return (unit_type, label, article_number, text) with conservative heuristics."""
    is_case = _is_case_law(categories)
    if is_case:
        matches = list(APPEAL_RE.finditer(text))
    else:
        matches = list(BARE_ARTICLE_RE.finditer(text)) + list(DEFINITE_ARTICLE_RE.finditer(text))
        matches.sort(key=lambda match: match.start())

    # Require multiple markers before treating them as boundaries. A single citation
    # inside a narrative should not force an arbitrary split.
    if len(matches) >= 2:
        units: list[tuple[str, str, str, str]] = []
        first_start = matches[0].start()
        preamble = text[:first_start].strip()
        if preamble:
            units.append(("preamble", "مقدمة السجل", "", preamble))
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            unit_text = text[start:end].strip()
            if not unit_text:
                continue
            if is_case:
                label = match.group("label").strip()
                units.append(("judgment", label, "", unit_text))
            else:
                label = match.group("label").strip()
                units.append(("article", label, match.group("number").strip(), unit_text))
        if units:
            return units

    return [("record", "السجل بالكامل", "", text.strip())]


def chunk_record(
    row: dict[str, Any],
    row_index: int,
    tokenizer: Any | None = None,
    max_tokens: int = 220,
) -> list[Chunk]:
    text = str(row.get("text") or "").strip()
    if not text:
        return []
    law_name = str(row.get("law_name") or "غير محدد")
    categories_list = row.get("categories") or []
    if not isinstance(categories_list, list):
        categories_list = [str(categories_list)]
    categories_list = [str(x) for x in categories_list]
    category_path = " / ".join(categories_list)
    record_hash = hashlib.sha1((law_name + "\n" + text).encode("utf-8")).hexdigest()[:10]
    record_id = f"record-{row_index:05d}-{record_hash}"

    units = _make_units(text, categories_list)
    chunks: list[Chunk] = []
    global_chunk_index = 0
    for unit_index, (unit_type, unit_label, article_number, unit_text) in enumerate(units):
        parts = _pack_sentences(unit_text, tokenizer, max_tokens)
        unit_id = f"{record_id}-unit-{unit_index:04d}"
        for local_index, part in enumerate(parts):
            chunk_hash = hashlib.sha1(
                f"{record_id}|{unit_index}|{local_index}|{part}".encode("utf-8")
            ).hexdigest()[:14]
            chunks.append(Chunk(
                id=f"chunk-{chunk_hash}",
                text=part,
                record_id=record_id,
                unit_id=unit_id,
                law_name=law_name,
                categories=" | ".join(categories_list),
                category_path=category_path,
                unit_type=unit_type,
                unit_label=unit_label,
                article_number=article_number,
                unit_index=unit_index,
                chunk_index=global_chunk_index,
                unit_chunk_index=local_index,
            ))
            global_chunk_index += 1
    return chunks
