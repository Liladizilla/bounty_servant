"""Small, dependency-free adapter for free-tier LLM APIs.

Supported providers:
- Google Gemini API (GEMINI_API_KEY, with GEMINI as a compatible secret-name alias)
- Groq OpenAI-compatible API (GROQ_API_KEY)

No provider is contacted unless generate_text() is called.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    """Raised when no configured provider can complete a request."""


def _http_error_description(exc: HTTPError) -> str:
    """Return useful provider diagnostics without leaking configured API keys."""
    status = getattr(exc, "code", None)
    try:
        raw = exc.read().decode("utf-8", errors="replace").strip()
    except Exception:
        raw = ""

    detail = ""
    if raw:
        try:
            payload = json.loads(raw)
            provider_error = payload.get("error", payload) if isinstance(payload, dict) else payload
            if isinstance(provider_error, dict):
                detail = str(provider_error.get("message") or provider_error.get("status") or "")
            else:
                detail = str(provider_error)
        except (json.JSONDecodeError, TypeError, ValueError):
            detail = raw

    # Provider error messages should never echo credentials into GitHub logs.
    for secret_name in ("GEMINI_API_KEY", "GEMINI", "GROQ_API_KEY"):
        secret = os.environ.get(secret_name)
        if secret:
            detail = detail.replace(secret, "[REDACTED]")
    detail = " ".join(detail.split())[:400]
    prefix = f"HTTP {status}" if status is not None else "HTTP error"
    return f"{prefix}: {detail}" if detail else prefix


def _gemini(prompt: str, system: str | None, max_output_tokens: int) -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ["GEMINI"]
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{quote(model, safe='')}:generateContent?key={quote(key, safe='')}"
    )
    payload: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_output_tokens},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=45) as response:
        result = json.loads(response.read().decode("utf-8"))
    candidates = result.get("candidates") or []
    parts = (candidates[0].get("content") or {}).get("parts") or [] if candidates else []
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise ProviderError("Gemini returned no text candidate")
    return text


def _groq(prompt: str, system: str | None, max_output_tokens: int) -> str:
    key = os.environ["GROQ_API_KEY"]
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    url = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1/chat/completions")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    request = Request(
        url,
        data=json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": max_output_tokens,
            "temperature": 0.1,
        }).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=45) as response:
        result = json.loads(response.read().decode("utf-8"))
    choices = result.get("choices") or []
    text = (choices[0].get("message") or {}).get("content", "").strip() if choices else ""
    if not text:
        raise ProviderError("Groq returned no text choice")
    return text


def generate_text(
    prompt: str,
    *,
    system: str | None = None,
    max_output_tokens: int = 2048,
) -> str:
    """Generate text using configured providers, preferring Gemini by default.

    Set BOUNTY_LLM_PROVIDER to 'gemini', 'groq', or 'auto'. In auto mode,
    a failed provider may fall back to the next configured provider.
    API keys are read only from environment variables and are never logged.
    """
    if not prompt.strip():
        raise ValueError("prompt must not be empty")
    if not 1 <= max_output_tokens <= 8192:
        raise ValueError("max_output_tokens must be between 1 and 8192")

    preference = os.environ.get("BOUNTY_LLM_PROVIDER", "auto").lower()
    providers = {
        "gemini": ("GEMINI_API_KEY", _gemini),
        "groq": ("GROQ_API_KEY", _groq),
    }
    if preference not in {"auto", *providers}:
        raise ValueError("BOUNTY_LLM_PROVIDER must be auto, gemini, or groq")

    order = [preference] if preference in providers else ["gemini", "groq"]
    configured = [
        name for name in order
        if os.environ.get(providers[name][0])
        or (name == "gemini" and os.environ.get("GEMINI"))
    ]
    if not configured:
        raise ProviderError(
            "No free-tier LLM API key configured. Set GEMINI_API_KEY "
            "(or the compatible alias GEMINI) or GROQ_API_KEY."
        )

    errors = []
    for name in configured:
        try:
            return providers[name][1](prompt, system, max_output_tokens)
        except HTTPError as exc:
            errors.append(f"{name}: {_http_error_description(exc)}")
            if preference != "auto":
                break
        except (URLError, TimeoutError, OSError, ValueError, KeyError, ProviderError) as exc:
            errors.append(f"{name}: {type(exc).__name__}")
            if preference != "auto":
                break
    raise ProviderError("All configured LLM providers failed (" + "; ".join(errors) + ")")
