"""Character identification with NER and LLM-based gender/age scoring.

Ported from audiobook-creator-mlx: identify_characters_and_output_book_to_jsonl.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Generator


def extract_dialogues(text: str) -> list[str]:
    """Extract dialogue lines enclosed in quotation marks from text."""
    patterns = [
        r'\u201c([^\u201d]+)\u201d',  # smart quotes
        r'"([^"]+)"',                  # straight quotes
    ]
    dialogues = []
    for pattern in patterns:
        dialogues.extend(re.findall(pattern, text))
    return dialogues


def identify_speaker_using_named_entity_recognition(
    line_map: dict,
    index: int,
    line: str,
    prev_speaker: str,
    protagonist: str,
    character_gender_map: dict,
) -> str:
    """Identify the speaker of a dialogue line using NER.

    Analyzes current line and context from up to 5 previous lines.
    Resolves pronouns to characters based on gender mapping.
    """
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
    except (ImportError, OSError):
        return prev_speaker or protagonist

    context_lines = []
    for i in range(max(0, index - 5), index + 1):
        if i in line_map:
            context_lines.append(line_map[i])
    context = " ".join(context_lines)
    doc = nlp(context)

    persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    if persons:
        return persons[-1]

    pronoun_map = {"he": "male", "she": "female", "him": "male", "her": "female"}
    for token in reversed(list(doc)):
        if token.text.lower() in pronoun_map:
            gender = pronoun_map[token.text.lower()]
            for char, info in character_gender_map.items():
                if info.get("gender", "").lower() == gender:
                    return char

    return prev_speaker or protagonist


def identify_character_gender_and_age_using_llm(
    openai_client,
    model_name: str,
    character_name: str,
    index: int,
    lines: list[str],
) -> dict:
    """Query LLM to infer character gender and age from name and dialogue context.

    Returns dict with name, age, gender, and numerical gender score (1-10).
    """
    context = " ".join(lines[max(0, index - 3):index + 3])
    prompt = (
        f"Given the character name '{character_name}' and the following context:\n"
        f"{context}\n\n"
        f"Determine the character's likely gender and approximate age. "
        f"Return ONLY a JSON object with keys: name, age (integer), gender (male/female/unknown), "
        f"gender_score (1=very masculine, 10=very feminine, 5=neutral)."
    )
    try:
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
        )
        content = response.choices[0].message.content or ""
        json_match = re.search(r"\{[^}]+\}", content)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass

    return {
        "name": character_name,
        "age": 30,
        "gender": "unknown",
        "gender_score": 5,
    }


def identify_characters_and_output_book_to_jsonl(
    text: str,
    protagonist: str,
    openai_client=None,
    model_name: str = "gpt-4",
    output_dir: str = ".",
) -> Generator[str, None, None]:
    """Process text to identify characters using NER.

    Assigns gender/age scores via LLM if available.
    Outputs results to JSONL and JSON files.
    Yields status messages throughout.
    """
    yield "Extracting dialogues..."
    dialogues = extract_dialogues(text)
    yield f"Found {len(dialogues)} dialogue lines."

    lines = text.split("\n")
    line_map = {i: line for i, line in enumerate(lines)}

    character_gender_map: dict[str, dict] = {}
    prev_speaker = protagonist
    speakers: list[str] = []

    yield "Identifying speakers via NER..."
    for idx, dialogue in enumerate(dialogues):
        speaker = identify_speaker_using_named_entity_recognition(
            line_map, idx, dialogue, prev_speaker, protagonist, character_gender_map
        )
        speakers.append(speaker)
        prev_speaker = speaker

    unique_characters = list(dict.fromkeys(speakers))
    yield f"Found {len(unique_characters)} unique characters."

    if openai_client:
        yield "Scoring character gender/age via LLM..."
        for idx, char in enumerate(unique_characters):
            info = identify_character_gender_and_age_using_llm(
                openai_client, model_name, char, idx, lines
            )
            character_gender_map[char] = info
            yield f"  {char}: {info.get('gender', 'unknown')}, age ~{info.get('age', '?')}"

    jsonl_path = Path(output_dir) / "characters_info.jsonl"
    json_path = Path(output_dir) / "characters_info.json"

    records = []
    for char in unique_characters:
        record = character_gender_map.get(char, {"name": char, "gender": "unknown", "age": 30, "gender_score": 5})
        record["name"] = char
        records.append(record)

    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2, ensure_ascii=False)

    yield f"Character info written to {jsonl_path} and {json_path}."
    yield "Character identification complete."
