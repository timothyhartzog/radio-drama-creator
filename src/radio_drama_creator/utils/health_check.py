"""Health check utilities for external APIs."""

from __future__ import annotations

from typing import Optional


def check_if_kokoro_api_is_up(client) -> tuple[bool, Optional[str]]:
    """Test connectivity to the Kokoro TTS API.

    Returns (True, None) on success, (False, error_message) on failure.
    """
    try:
        response = client.audio.speech.create(
            model="kokoro",
            voice="af_heart",
            input="Health check.",
            response_format="aac",
            speed=0.85,
        )
        _ = response.read()
        return True, None
    except Exception as exc:
        return False, str(exc)


def check_if_llm_is_up(openai_client, model_name: str) -> tuple[bool, str]:
    """Verify whether a configured language model is operational.

    Returns (success_bool, model_response_or_error_message).
    """
    try:
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Reply with any word if you're working"}],
            max_tokens=10,
        )
        content = response.choices[0].message.content or ""
        return True, content.strip()
    except Exception as exc:
        return False, str(exc)
