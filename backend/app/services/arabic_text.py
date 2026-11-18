import re

# Separate retrieval-only normalization helper. Original legal text is never modified.
_TRANSLATION = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا",
})


def normalize_arabic_for_retrieval(text: str) -> str:
    """Minimal alif normalization; preserve original text elsewhere."""
    text = (text or "").translate(_TRANSLATION)
    return re.sub(r"\s+", " ", text).strip()
