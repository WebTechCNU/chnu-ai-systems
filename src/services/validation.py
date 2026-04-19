# pip install langdetect pymorphy3 pymorphy3-dicts-uk
import re
import math
from collections import Counter
from langdetect import detect, LangDetectException
import pymorphy3

morph = pymorphy3.MorphAnalyzer(lang="uk")

# ── helpers ──────────────────────────────────────────────────────────────────
min_chars = 3
min_entropy = 2.5
min_known_word_ratio = 0.4
min_real_words = 1
allowed_langs = ("uk", "ru", "en")

def _shannon_entropy(text: str) -> float:
    """Low entropy = repetitive gibberish ('lalala' → ~1.5 bits)."""
    if not text:
        return 0.0
    counts = Counter(text)
    print(counts)
    length = len(text)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def _known_word_ratio(tokens: list[str]) -> float:
    """Fraction of tokens that pymorphy3 can parse as real Ukrainian words."""
    if not tokens:
        return 0.0
    known = sum(
        1 for t in tokens
        if morph.word_is_known(t) or
           any(p.score > 0.1 for p in morph.parse(t))
    )
    return known / len(tokens)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[а-яіїєґёА-ЯІЇЄҐЁa-zA-Z]+", text.lower())

def validate(text: str) -> dict:
    text = text.strip()
    reasons = []

    # 1. Length check
    if len(text) < min_chars:
        reasons.append("too_short")

    # 2. Entropy check (catches 'ааааа', 'lalala', '123123')
    entropy = _shannon_entropy(text)
    if entropy < min_entropy:
        reasons.append(f"low_entropy:{entropy:.2f}")

    # 3. Tokenize
    tokens = _tokenize(text)

    # 4. Known-word ratio via morphological analyser
    ratio = _known_word_ratio(tokens) if tokens else 0.0
    real_words = int(ratio * len(tokens))

    if real_words < min_real_words:
        reasons.append("no_real_words")
    elif ratio < min_known_word_ratio:
        reasons.append(f"low_word_ratio:{ratio:.2f}")

    # 5. Language detection (only if text is long enough to be reliable)
    if len(text) >= 10:
        try:
            lang = detect(text)
            if lang not in allowed_langs:
                reasons.append(f"wrong_language:{lang}")
        except LangDetectException:
            reasons.append("language_undetectable")

    is_meaningful = len(reasons) == 0
    return {"meaningful": is_meaningful, "reasons": reasons}