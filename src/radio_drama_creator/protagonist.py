"""Protagonist detection via web search and LLM.

Ported from audiobook-creator-mlx: utils/find_book_protagonist.py
"""

from __future__ import annotations

import re

import requests


def find_book_protagonist_using_search_engine_and_llm(
    book_title: str,
    openai_client,
    model_name: str,
    search_method: str = "duckduckgo",
) -> str:
    """Find the protagonist of a book by scraping search results and using LLM.

    search_method options: 'google', 'duckduckgo', 'bing', 'goodreads', 'wikipedia'
    Returns protagonist name or 'unknown'.
    """
    search_query = f"{book_title} protagonist main character"
    search_text = ""

    try:
        if search_method == "wikipedia":
            url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={book_title}+novel&format=json"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if data.get("query", {}).get("search"):
                snippet = data["query"]["search"][0].get("snippet", "")
                search_text = re.sub(r"<[^>]+>", "", snippet)
        elif search_method == "duckduckgo":
            url = f"https://html.duckduckgo.com/html/?q={search_query}"
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            search_text = resp.text[:3000]
            search_text = re.sub(r"<[^>]+>", " ", search_text)
        else:
            url = f"https://html.duckduckgo.com/html/?q={search_query}"
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            search_text = resp.text[:3000]
            search_text = re.sub(r"<[^>]+>", " ", search_text)
    except requests.exceptions.RequestException:
        search_text = ""

    if not search_text:
        return "unknown"

    prompt = (
        f"Based on the following search results about the book '{book_title}', "
        f"who is the main character (protagonist)? Reply with ONLY the character's name.\n\n"
        f"{search_text[:2000]}"
    )

    try:
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
        )
        name = (response.choices[0].message.content or "").strip()
        if name and len(name) < 100:
            return name
    except Exception:
        pass

    return "unknown"


def find_book_protagonist(
    book_title: str, openai_client, model_name: str
) -> str:
    """Find protagonist using default search method."""
    return find_book_protagonist_using_search_engine_and_llm(
        book_title, openai_client, model_name
    )
