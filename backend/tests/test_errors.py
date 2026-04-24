"""Tests for the error taxonomy. Non-technical users must never see
'NoneType' or stack traces — classify_error is the bottleneck every message
passes through."""
import asyncio

import anthropic
import httpx
import openai
import pytest

from app.errors import classify_error


class TestClassifyError:
    # --- Provider safety / content blocks ---

    def test_google_safety_block_phrase(self):
        err = classify_error(ValueError("Google zablokował prompt (block_reason=SAFETY)"))
        assert err.code == "SAFETY_BLOCK"
        assert err.retryable is False
        assert "filtry" in err.hint.lower() or "prompt" in err.hint.lower()

    def test_google_finish_reason_is_safety_block(self):
        err = classify_error(ValueError(
            "Google odrzucił obrazek (finish_reason=IMAGE_SAFETY)."
        ))
        assert err.code == "SAFETY_BLOCK"

    # --- Config / auth ---

    def test_missing_google_api_key(self):
        err = classify_error(ValueError("Google API key not configured"))
        assert err.code == "CONFIG_MISSING"
        assert "Google" in err.title or "Google" in err.hint

    def test_missing_anthropic_api_key(self):
        err = classify_error(ValueError("Anthropic API key not configured"))
        assert err.code == "CONFIG_MISSING"

    def test_openai_auth_failure_via_sdk(self):
        # Mock an openai.AuthenticationError
        resp = httpx.Response(401, request=httpx.Request("GET", "http://x"))
        err = classify_error(openai.AuthenticationError(
            "invalid_api_key", response=resp, body=None,
        ))
        assert err.code == "AUTH_FAILED"
        assert err.retryable is False

    # --- Rate limits ---

    def test_anthropic_529_overloaded(self):
        resp = httpx.Response(529, request=httpx.Request("POST", "http://x"))
        err = classify_error(anthropic.APIStatusError(
            "overloaded", response=resp, body=None,
        ))
        assert err.code == "RATE_LIMITED"
        assert err.retryable is True

    def test_openai_rate_limit(self):
        resp = httpx.Response(429, request=httpx.Request("POST", "http://x"))
        err = classify_error(openai.RateLimitError(
            "rate limit", response=resp, body=None,
        ))
        assert err.code == "RATE_LIMITED"

    def test_httpx_5xx(self):
        resp = httpx.Response(503, request=httpx.Request("GET", "http://x"))
        err = classify_error(httpx.HTTPStatusError(
            "503", request=resp.request, response=resp,
        ))
        assert err.code == "RATE_LIMITED"

    def test_string_match_429_fallback(self):
        """Google genai stringifies errors oddly — text match catches them."""
        err = classify_error(RuntimeError("429 Too Many Requests"))
        assert err.code == "RATE_LIMITED"

    def test_string_match_overloaded(self):
        err = classify_error(RuntimeError("Service is overloaded right now"))
        assert err.code == "RATE_LIMITED"

    # --- Network / timeout ---

    def test_asyncio_timeout(self):
        err = classify_error(asyncio.TimeoutError("..."))
        assert err.code == "TIMEOUT"
        assert err.retryable is True

    def test_httpx_timeout(self):
        err = classify_error(httpx.ReadTimeout("timeout"))
        assert err.code == "TIMEOUT"

    def test_connection_error(self):
        err = classify_error(ConnectionError("connection refused"))
        assert err.code == "NETWORK"

    def test_httpx_connect_error(self):
        err = classify_error(httpx.ConnectError("can't connect"))
        assert err.code == "NETWORK"

    # --- Content validation ---

    def test_content_validation_error(self):
        err = classify_error(ValueError("Oczekiwano 15 segmentów historii, otrzymano 9."))
        assert err.code == "CONTENT_INVALID"
        assert err.retryable is True

    # --- State conflicts ---

    def test_state_conflict(self):
        err = classify_error(ValueError(
            "Cannot generate images: project status is 'draft', expected 'prompts_generated'"
        ))
        assert err.code == "STATE_CONFLICT"
        assert err.retryable is False
        # Must not leak the internal English message — user gets Polish labels
        assert "Cannot " not in err.hint
        assert "szkic" in err.hint  # 'draft' → 'szkic'
        assert "prompty gotowe" in err.hint  # 'prompts_generated' → label

    def test_not_found(self):
        err = classify_error(ValueError("Project 42 not found"))
        assert err.code == "NOT_FOUND"

    # --- Unknown ---

    def test_fully_unknown_falls_back_to_generic(self):
        err = classify_error(RuntimeError("Some wildly unexpected thing"))
        assert err.code == "UNKNOWN"
        assert "spróbuj" in err.hint.lower()
        assert "NoneType" not in err.title  # no leaks
        assert err.title != "Some wildly unexpected thing"  # user gets friendly text

    def test_all_results_have_filled_fields(self):
        """Paranoia: every returned UserFacingError must be presentable."""
        samples = [
            ValueError("Google zablokował prompt"),
            ValueError("api key not configured"),
            RuntimeError("overloaded"),
            asyncio.TimeoutError(),
            httpx.ConnectError("..."),
            ValueError("project 1 already busy"),
            ValueError("Oczekiwano 17 promptów"),
            RuntimeError("something brand new"),
        ]
        for s in samples:
            err = classify_error(s)
            assert err.title, f"empty title for {s}"
            assert err.hint, f"empty hint for {s}"
            assert err.code
            assert 400 <= err.status < 600
            # No raw Python types in user-facing strings
            assert "Traceback" not in err.title
            assert "Exception" not in err.title


class TestToDict:
    def test_envelope_shape(self):
        err = classify_error(ValueError("Google zablokował prompt"))
        d = err.to_dict()
        # Must have all four fields the frontend expects
        assert set(d.keys()) >= {"code", "detail", "title", "hint", "retryable"}
        # `detail` mirrors `title` for backwards-compat with old clients
        assert d["detail"] == d["title"]
