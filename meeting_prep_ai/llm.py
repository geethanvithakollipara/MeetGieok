"""Thin Groq/OpenAI-compatible wrapper that always returns parsed JSON.

We deliberately avoid function calling (the hackathon notes warn about
tool-call errors) and instead ask for JSON, then parse defensively + retry.
"""
import json
import re
import time

from openai import OpenAI

import config

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not config.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY missing. Copy .env.example to .env and fill it in.")
        _client = OpenAI(api_key=config.GROQ_API_KEY, base_url=config.LLM_BASE_URL)
    return _client


def _extract_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def chat_json(system: str, user: str, retries: int = 3) -> dict:
    last_err = None
    for attempt in range(retries):
        try:
            kwargs = dict(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            if attempt == 0:  # strict JSON mode first, plain text on retries
                kwargs["response_format"] = {"type": "json_object"}
            resp = _get_client().chat.completions.create(**kwargs)
            return _extract_json(resp.choices[0].message.content or "")
        except Exception as e:  # rate limits, malformed JSON, provider errors
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"LLM call failed after {retries} attempts: {last_err}")
