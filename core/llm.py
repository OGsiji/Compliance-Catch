"""LLM client abstraction.

One thin wrapper around Gemini plus a factory that decides, at runtime, whether
a real model is available. The flagger and verifier take a client that is either
a GeminiClient or None; None means 'use the deterministic offline heuristics'.
This keeps provider selection in exactly one place.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Optional, Tuple

# Defaults chosen for free-tier friendliness: gemini-2.5-flash has a much
# larger free daily quota than the `-latest` alias (which currently resolves to
# a newer model capped at ~20 requests/day). Flagger and verifier use different
# models so their per-model quotas don't compete. Override via env.
DEFAULT_FLAGGER_MODEL = os.getenv("FLAGGER_MODEL", "gemini-2.5-flash")
DEFAULT_VERIFIER_MODEL = os.getenv("VERIFIER_MODEL", "gemini-flash-lite-latest")

# Transient statuses worth retrying: rate limit + server-side unavailability.
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "5"))
MAX_BACKOFF_SECONDS = int(os.getenv("LLM_MAX_BACKOFF", "60"))


class LLMError(RuntimeError):
    pass


def _is_retryable(exc: Exception) -> bool:
    """True for transient upstream failures (rate limit / server unavailable)."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if isinstance(code, int) and code in RETRYABLE_STATUS:
        return True
    text = str(exc)
    return any(str(s) in text for s in RETRYABLE_STATUS) or "UNAVAILABLE" in text


def _suggested_delay(exc: Exception) -> Optional[float]:
    """Extract a server-suggested retry delay (seconds) from a 429 if present."""
    import re
    m = re.search(r"[Rr]etry in (\d+(?:\.\d+)?)s", str(exc)) \
        or re.search(r"retryDelay['\"]?:\s*['\"]?(\d+(?:\.\d+)?)s", str(exc))
    if m:
        try:
            return float(m.group(1)) + 1.0  # small cushion
        except ValueError:
            return None
    return None


def api_key_present() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


class GeminiClient:
    """Minimal JSON-mode wrapper over google-genai.

    Imported lazily so the offline path never requires the SDK to be installed.
    """

    def __init__(self, api_key: Optional[str] = None,
                 flagger_model: Optional[str] = None,
                 verifier_model: Optional[str] = None):
        try:
            from google import genai  # noqa: F401
        except ImportError as exc:  # pragma: no cover - depends on env
            raise LLMError(
                "google-genai is not installed. Run `pip install -r requirements.txt` "
                "or use the offline provider."
            ) from exc
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise LLMError("No GEMINI_API_KEY / GOOGLE_API_KEY set.")
        from google import genai
        self._genai = genai
        self._client = genai.Client(api_key=key)
        self.flagger_model = flagger_model or DEFAULT_FLAGGER_MODEL
        self.verifier_model = verifier_model or DEFAULT_VERIFIER_MODEL

    def complete_json(self, system_prompt: str, user_prompt: str,
                      model: str) -> Tuple[Any, str]:
        """Return (parsed_json, raw_text). Temperature 0 for reproducibility.

        Transient upstream errors (429/5xx — e.g. 'model experiencing high
        demand') are retried with exponential backoff so a momentary spike does
        not abort a whole eval run.
        """
        from google.genai import types
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0,
        )
        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = self._client.models.generate_content(
                    model=model, contents=user_prompt, config=config)
                raw = (resp.text or "").strip()
                try:
                    return json.loads(raw), raw
                except json.JSONDecodeError as exc:
                    raise LLMError(f"Model did not return valid JSON: {raw[:200]}") from exc
            except LLMError:
                raise
            except Exception as exc:  # pragma: no cover - network dependent
                last_exc = exc
                if not _is_retryable(exc) or attempt == MAX_RETRIES:
                    raise LLMError(f"Gemini request failed: {exc}") from exc
                # Prefer the server-suggested retry delay (429s carry one),
                # else exponential backoff, capped.
                delay = _suggested_delay(exc) or (2 ** attempt)
                time.sleep(min(delay, MAX_BACKOFF_SECONDS))
        raise LLMError(f"Gemini request failed: {last_exc}")  # unreachable


def make_client(provider: str = "auto",
                flagger_model: Optional[str] = None,
                verifier_model: Optional[str] = None) -> Optional[GeminiClient]:
    """Resolve the provider.

    provider="auto"    -> Gemini if a key is present, otherwise offline (None)
    provider="gemini"  -> Gemini, error if unavailable
    provider="offline" -> None (deterministic heuristics)
    """
    provider = (provider or "auto").lower()
    if provider == "offline":
        return None
    if provider == "gemini":
        return GeminiClient(flagger_model=flagger_model, verifier_model=verifier_model)
    # auto
    if api_key_present():
        try:
            return GeminiClient(flagger_model=flagger_model, verifier_model=verifier_model)
        except LLMError:
            return None
    return None


def provider_name(client: Optional[GeminiClient]) -> str:
    return "gemini" if client is not None else "offline"
