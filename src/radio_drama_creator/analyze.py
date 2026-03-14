from __future__ import annotations

from collections import Counter
import re

from .models import DocumentChunk, StoryAnalysis


STOPWORDS = {
    "the", "and", "that", "with", "from", "were", "have", "their", "would", "there",
    "which", "your", "about", "into", "after", "before", "them", "they", "then", "when",
    "this", "while", "where", "been", "being", "some", "than", "through", "upon", "said",
}

PERSON_BLACKLIST = {
    "Across", "After", "Before", "By", "For", "From", "She", "He", "They", "The", "It", "This",
    "That", "Street", "Hotel", "Office", "Station", "City", "Harbor", "Mercer", "Astor",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
}


def analyze_document(chunks: list[DocumentChunk]) -> StoryAnalysis:
    full_text = " ".join(chunk.text for chunk in chunks)
    sentences = _split_sentences(full_text)
    excerpt = " ".join(sentences[:6]).strip()
    title = _guess_title(sentences, full_text)
    characters = _extract_characters(full_text)
    themes = _extract_themes(full_text)
    conflicts = _extract_conflicts(sentences)
    setting = _guess_setting(sentences)
    mood = _guess_mood(full_text)
    summary = _build_summary(sentences, themes, conflicts)

    return StoryAnalysis(
        title=title,
        summary=summary,
        themes=themes[:5] or ["mystery", "human struggle"],
        setting=setting,
        mood=mood,
        characters=characters[:6] or ["Narrator", "Lead", "Confidant", "Antagonist"],
        conflicts=conflicts[:4] or ["A secret threatens to surface"],
        source_excerpt=excerpt[:1000],
    )


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if len(part.strip()) > 20]


def _guess_title(sentences: list[str], full_text: str) -> str:
    if sentences:
        first = sentences[0][:70].strip(" .,:;!-")
        return first.title()
    return full_text[:50].title() or "Untitled Radio Drama"


def _extract_characters(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    counts: Counter[str] = Counter()

    honorific_matches = re.findall(r"\b(?:Mr|Mrs|Miss|Ms|Dr|Professor|Inspector|Captain)\.?\s+([A-Z][a-z]+)\b", text)
    for match in honorific_matches:
        counts[match] += 3

    for sentence in sentences:
        tokens = re.findall(r"\b[A-Z][a-z]{2,}\b", sentence)
        for index, token in enumerate(tokens):
            if token in PERSON_BLACKLIST or token.lower() in STOPWORDS:
                continue
            weight = 2 if index > 0 else 1
            counts[token] += weight

    ordered = [name for name, _ in counts.most_common(10)]
    return _unique_preserving_order(ordered)


def _extract_themes(text: str) -> list[str]:
    words = re.findall(r"\b[a-zA-Z]{5,}\b", text.lower())
    counts = Counter(word for word in words if word not in STOPWORDS)
    return [word for word, _ in counts.most_common(8)]


def _extract_conflicts(sentences: list[str]) -> list[str]:
    signal_words = ("danger", "secret", "afraid", "threat", "must", "cannot", "never", "lost")
    picked = [sentence for sentence in sentences if any(word in sentence.lower() for word in signal_words)]
    return [sentence[:140].strip() for sentence in picked[:4]]


def _guess_setting(sentences: list[str]) -> str:
    joined = " ".join(sentences[:10]).lower()
    if "city" in joined or "street" in joined:
        return "A restless city after dark"
    if "house" in joined or "room" in joined:
        return "An enclosed interior where every sound matters"
    if "train" in joined or "station" in joined:
        return "A station platform thick with tension"
    if "sea" in joined or "storm" in joined:
        return "A storm-haunted coast"
    return "A shadowed world shaped by memory and suspense"


def _guess_mood(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("murder", "dark", "fear", "blood", "shadow")):
        return "brooding suspense"
    if any(word in lowered for word in ("love", "heart", "longing", "hope")):
        return "melancholic romance"
    if any(word in lowered for word in ("war", "signal", "mission", "code")):
        return "urgent wartime tension"
    return "hushed dramatic intrigue"


def _build_summary(sentences: list[str], themes: list[str], conflicts: list[str]) -> str:
    lead = sentences[0] if sentences else "A drama unfolds from the source material."
    theme_text = ", ".join(themes[:3]) if themes else "mystery and consequence"
    conflict_text = conflicts[0] if conflicts else "The central conflict grows harder to ignore."
    return f"{lead} Themes include {theme_text}. Conflict focus: {conflict_text}"


def _unique_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
