"""Thin wrapper around the Groq SDK that always returns validated Pydantic objects."""
import json
import re
import time
from typing import Type, TypeVar

from groq import Groq
from pydantic import BaseModel, ValidationError

from . import config

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Raised when the LLM call fails or returns unusable output."""


_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if not config.GROQ_API_KEY:
        raise LLMError("GROQ_API_KEY is missing. Add it to backend/.env and restart the server.")
    if _client is None:
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


def _extract_json(text: str) -> dict:
    """Parse JSON even if the model wrapped it in ```json fences or extra text."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def call_llm(system_prompt: str, user_prompt: str, schema: Type[T], retries: int = 2) -> T:
    """Call Groq in JSON mode and validate the result against `schema`."""
    client = _get_client()
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            completion = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = completion.choices[0].message.content or ""
            return schema.model_validate(_extract_json(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc  # bad output -> retry
        except Exception as exc:  # network / auth / rate-limit
            last_error = exc
            if "401" in str(exc) or "invalid_api_key" in str(exc).lower():
                raise LLMError("Invalid Groq API key. Check GROQ_API_KEY in backend/.env.") from exc
        time.sleep(0.8 * (attempt + 1))

    raise LLMError(f"The AI model did not return a valid response: {last_error}")
