from app.services.arabic_text import normalize_arabic_for_retrieval


def test_minimal_alif_normalization():
    assert normalize_arabic_for_retrieval("أ إ آ") == "ا ا ا"


def test_original_spacing_collapsed_only_in_helper():
    assert normalize_arabic_for_retrieval("قانون   العمل") == "قانون العمل"
