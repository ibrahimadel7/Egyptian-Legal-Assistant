from app.services.chunker import chunk_record, _make_units


class FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return text.split()

    def decode(self, ids, skip_special_tokens=True):
        return " ".join(ids)


def test_legislation_article_boundaries_preserved():
    row = {
        "law_name": "قانون تجريبي",
        "categories": ["قوانين"],
        "text": "مقدمة القانون. مادة 1 النص الاول. مادة 2 النص الثاني.",
    }
    chunks = chunk_record(row, 0, tokenizer=FakeTokenizer(), max_tokens=100)
    assert any(c.unit_type == "article" and c.article_number == "1" for c in chunks)
    assert any(c.unit_type == "article" and c.article_number == "2" for c in chunks)
    assert all(c.record_id.startswith("record-00000-") for c in chunks)


def test_case_law_splits_by_appeal_not_article_citations():
    row = {
        "law_name": "موضوع نقض",
        "categories": ["النقض و المحكمة الادارية", "نقض مدني"],
        "text": "الطعن رقم 10 لسنة 20 النص الاول والمادة 5. الطعن رقم 11 لسنة 21 النص الثاني.",
    }
    units = _make_units(row["text"], row["categories"])
    assert len([u for u in units if u[0] == "judgment"]) == 2


def test_long_text_is_split_under_limit():
    row = {
        "law_name": "قانون",
        "categories": ["قوانين"],
        "text": " ".join(["كلمة"] * 120),
    }
    chunks = chunk_record(row, 1, tokenizer=FakeTokenizer(), max_tokens=30)
    assert len(chunks) >= 4
    assert all(len(c.text.split()) <= 30 for c in chunks)


def test_original_text_is_not_normalized():
    text = "مادة 1: أكرم"
    row = {"law_name": "قانون", "categories": ["قوانين"], "text": text}
    chunks = chunk_record(row, 2, tokenizer=FakeTokenizer(), max_tokens=50)
    assert chunks[0].text == text
