"""Central error taxonomy — turn internal exceptions into user-facing messages.

Non-technical users should never see `NoneType`, stack traces, or API codes.
Everything funnels through `classify_error()` which returns a `UserFacingError`
with:
  - code: a short machine-readable tag (frontend can branch on it)
  - title: 1-line Polish message the user sees
  - hint: actionable next step ("zmień prompt", "spróbuj ponownie", etc.)
  - retryable: whether the UI should show a retry button
  - status: HTTP status for the API response

The classifier is conservative — anything it can't identify becomes UNKNOWN
with a generic "coś poszło nie tak" message, and we log the real exception
separately for ops.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

ErrorCode = Literal[
    "SAFETY_BLOCK",       # provider refused content (edit prompt)
    "RATE_LIMITED",       # 429 / overloaded (wait + retry)
    "TIMEOUT",            # took too long (retry)
    "NETWORK",            # can't reach provider (retry)
    "CONFIG_MISSING",     # API key missing (admin action)
    "AUTH_FAILED",        # provider rejected our credentials (admin action)
    "CONTENT_INVALID",    # LLM returned malformed output (retry)
    "BUSY",               # another generation in flight (wait)
    "NOT_FOUND",          # project/page missing
    "STATE_CONFLICT",     # wrong project status (ok to ignore)
    "UNKNOWN",            # catch-all
]


@dataclass(frozen=True)
class UserFacingError:
    code: ErrorCode
    title: str
    hint: str
    retryable: bool
    status: int

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "detail": self.title,  # FastAPI convention — old clients keep working
            "title": self.title,
            "hint": self.hint,
            "retryable": self.retryable,
        }


# Pre-built entries — most paths go through these.
_SAFETY_BLOCK = lambda detail: UserFacingError(
    "SAFETY_BLOCK",
    "Dostawca AI odrzucił ten opis",
    f"Filtry bezpieczeństwa uznały prompt za nieodpowiedni. Spróbuj opisać "
    f"postać/scenę ogólniej (mniej szczegółów o wieku, mniej mocnych słów). "
    f"Szczegóły: {detail}",
    retryable=False,
    status=422,
)

_RATE_LIMITED = UserFacingError(
    "RATE_LIMITED",
    "Dostawca AI jest chwilowo przeciążony",
    "Serwer dostawcy (Anthropic / OpenAI / Google) ma chwilowy pik. "
    "Poczekaj 30–60 sekund i spróbuj ponownie.",
    retryable=True,
    status=503,
)

_TIMEOUT = UserFacingError(
    "TIMEOUT",
    "Dostawca AI nie odpowiada",
    "Żądanie trwało za długo. Spróbuj ponownie — jeśli powtarza się kilka razy, "
    "sprawdź czy usługa AI nie ma awarii.",
    retryable=True,
    status=504,
)

_NETWORK = UserFacingError(
    "NETWORK",
    "Problem z połączeniem do dostawcy AI",
    "Nie udało się dotrzeć do API. Sprawdź połączenie z internetem i spróbuj "
    "ponownie.",
    retryable=True,
    status=503,
)

_CONFIG_MISSING = lambda provider: UserFacingError(
    "CONFIG_MISSING",
    f"Brakuje konfiguracji dla {provider}",
    f"Klucz API dla {provider} nie jest ustawiony. "
    f"Przejdź do Ustawień i wpisz klucz, albo skontaktuj się z administratorem.",
    retryable=False,
    status=503,
)

_AUTH_FAILED = lambda provider: UserFacingError(
    "AUTH_FAILED",
    f"{provider} odrzucił nasze dane logowania",
    f"Klucz API jest nieprawidłowy lub wygasł. "
    f"Sprawdź klucz w Ustawieniach lub skontaktuj się z administratorem.",
    retryable=False,
    status=401,
)

_CONTENT_INVALID = lambda what: UserFacingError(
    "CONTENT_INVALID",
    "AI zwrócił odpowiedź w złym formacie",
    f"Model odpowiedział czymś czego nie potrafimy użyć ({what}). "
    f"Spróbuj ponownie — najczęściej drugi strzał się udaje.",
    retryable=True,
    status=502,
)

_BUSY = UserFacingError(
    "BUSY",
    "Dla tego projektu już trwa operacja",
    "Poczekaj aż obecna operacja się skończy i spróbuj ponownie.",
    retryable=True,
    status=409,
)

_NOT_FOUND = lambda what: UserFacingError(
    "NOT_FOUND",
    f"Nie znaleziono: {what}",
    "Obiekt mógł zostać usunięty. Odśwież stronę.",
    retryable=False,
    status=404,
)

_STATUS_LABELS_PL = {
    "draft": "szkic",
    "ref_pic_generating": "generowanie postaci",
    "ref_pic_review": "podgląd postaci",
    "story_generating": "generowanie historii",
    "story_generated": "historia gotowa",
    "prompts_generating": "generowanie promptów",
    "prompts_generated": "prompty gotowe",
    "images_generating": "generowanie obrazków",
    "images_partial": "część obrazków brakuje",
    "review": "podgląd",
    "exported": "wyeksportowano",
}


def _humanize_state_conflict(msg: str) -> str:
    """Turn 'Cannot generate images: project status is \\'draft\\', expected
    \\'prompts_generated\\'' into plain Polish. Best-effort — falls back to the
    generic hint if the message doesn't match the expected shape."""
    import re
    m = re.search(r"status is '(\w+)'.*expected '(\w+)'", msg)
    if m:
        got = _STATUS_LABELS_PL.get(m.group(1), m.group(1))
        need = _STATUS_LABELS_PL.get(m.group(2), m.group(2))
        return (
            f"Projekt jest teraz w stanie „{got}” — najpierw musi być „{need}”. "
            f"Odśwież stronę lub wróć do poprzedniego kroku."
        )
    return "Odśwież stronę. Ten krok może być dostępny dopiero po skończeniu poprzedniego."


def _STATE_CONFLICT(detail: str) -> "UserFacingError":
    return UserFacingError(
        "STATE_CONFLICT",
        "Nie można wykonać tej akcji w obecnym stanie",
        _humanize_state_conflict(detail),
        retryable=False,
        status=409,
    )

_UNKNOWN = UserFacingError(
    "UNKNOWN",
    "Coś poszło nie tak",
    "Spróbuj ponownie. Jeśli problem się powtarza, odśwież stronę lub "
    "skontaktuj się z administratorem.",
    retryable=True,
    status=500,
)


def _lower(e: Exception) -> str:
    return str(e).lower()


def classify_error(e: Exception) -> UserFacingError:
    """Turn any exception into a user-facing error. Always succeeds — worst
    case returns UNKNOWN, which is still a clean message."""
    import asyncio
    import httpx

    msg = _lower(e)

    # --- Our own signals (we raise ValueError with specific phrases) ---

    # Safety blocks from google_image._extract_image_bytes
    if "zablokował prompt" in msg or "odrzucił obrazek" in msg \
            or "finish_reason" in msg or "safety" in msg or "block_reason" in msg:
        return _SAFETY_BLOCK(str(e)[:200])

    # Google INVALID_ARGUMENT — usually a bad image_size / aspect_ratio combo
    # for a model that doesn't support it. Surface a useful message instead of
    # the raw provider blob.
    if "invalid_argument" in msg or "is not supported for this model" in msg:
        return UserFacingError(
            "CONTENT_INVALID",
            "Nieprawidłowy parametr generowania",
            f"Dostawca AI odrzucił parametr (np. rozmiar / aspect ratio "
            f"niedostępny dla wybranego modelu). Sprawdź ustawienia. "
            f"Szczegóły: {str(e)[:200]}",
            retryable=False,
            status=400,
        )

    # "Google API key not configured" etc.
    if "api key not configured" in msg or "api key" in msg and "not" in msg:
        if "google" in msg:
            return _CONFIG_MISSING("Google")
        if "anthropic" in msg:
            return _CONFIG_MISSING("Anthropic")
        if "openai" in msg:
            return _CONFIG_MISSING("OpenAI")
        return _CONFIG_MISSING("dostawca AI")

    # Our business validation errors from story_service
    if "oczekiwano" in msg and ("segmentów" in msg or "promptów" in msg):
        return _CONTENT_INVALID(str(e))
    if "za krótki" in msg:
        return _CONTENT_INVALID(str(e))

    # Project-state preconditions
    if "cannot " in msg or "expected '" in msg or "ref_pic_review" in msg \
            or "prompts_generated" in msg or "story_generating" in msg:
        return _STATE_CONFLICT(str(e))

    if "not found" in msg:
        return _NOT_FOUND(str(e))

    if "project" in msg and "already busy" in msg:
        return _BUSY

    # --- Network / timeout ---
    if isinstance(e, (asyncio.TimeoutError, httpx.TimeoutException)):
        return _TIMEOUT
    if isinstance(e, (httpx.ConnectError, httpx.NetworkError, ConnectionError)):
        return _NETWORK

    # --- Provider SDK exceptions ---
    try:
        import anthropic
        if isinstance(e, anthropic.APIStatusError):
            sc = getattr(e, "status_code", None)
            if sc in (401, 403):
                return _AUTH_FAILED("Anthropic")
            if sc == 429 or sc == 529:
                return _RATE_LIMITED
            if sc and 500 <= sc < 600:
                return _RATE_LIMITED
        if isinstance(e, anthropic.APIConnectionError):
            return _NETWORK
    except ImportError:
        pass

    try:
        import openai
        if isinstance(e, openai.RateLimitError):
            return _RATE_LIMITED
        if isinstance(e, (openai.APIConnectionError, openai.APITimeoutError)):
            return _NETWORK if isinstance(e, openai.APIConnectionError) else _TIMEOUT
        if isinstance(e, openai.AuthenticationError):
            return _AUTH_FAILED("OpenAI")
        if isinstance(e, openai.APIStatusError):
            sc = getattr(e, "status_code", None)
            if sc in (401, 403):
                return _AUTH_FAILED("OpenAI")
            if sc == 429:
                return _RATE_LIMITED
            if sc and 500 <= sc < 600:
                return _RATE_LIMITED
    except ImportError:
        pass

    # --- HTTP errors with a status code ---
    if isinstance(e, httpx.HTTPStatusError):
        sc = e.response.status_code
        if sc in (401, 403):
            return _AUTH_FAILED("dostawca AI")
        if sc == 429:
            return _RATE_LIMITED
        if 500 <= sc < 600:
            return _RATE_LIMITED

    # --- Text-match fallback for providers we don't isinstance ---
    if any(tag in msg for tag in (
        "429", "rate limit", "overloaded", "529", "unavailable",
        "resource_exhausted", "503", "504",
    )):
        return _RATE_LIMITED
    if any(tag in msg for tag in ("401", "403", "unauthorized", "forbidden",
                                    "invalid api key", "authentication")):
        return _AUTH_FAILED("dostawca AI")
    if "timeout" in msg or "timed out" in msg:
        return _TIMEOUT

    # --- Give up — log full traceback, return generic ---
    logger.exception("Unclassified error: %s", e)
    return _UNKNOWN
