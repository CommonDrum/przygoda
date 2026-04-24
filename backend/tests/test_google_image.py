"""Cover the Google image response-parsing paths — especially the ones that
show up as '`NoneType` object is not iterable' in production: safety blocks,
empty candidate lists, text-only responses.

These exercise `_extract_image_bytes` directly so we don't need a real API key
or network."""
from types import SimpleNamespace

import pytest

from app.providers.google_image import _extract_image_bytes


def _fake_response(*, prompt_feedback=None, candidates=None):
    return SimpleNamespace(
        prompt_feedback=prompt_feedback,
        candidates=candidates or [],
    )


def _fake_image_part(data: bytes = b"PNGDATA"):
    return SimpleNamespace(
        inline_data=SimpleNamespace(mime_type="image/png", data=data),
        text=None,
    )


def _fake_text_part(text: str):
    return SimpleNamespace(inline_data=None, text=text)


def _fake_candidate(parts=None, finish_reason=None):
    if parts is None:
        content = SimpleNamespace(parts=None)
    else:
        content = SimpleNamespace(parts=parts)
    return SimpleNamespace(content=content, finish_reason=finish_reason)


class TestExtractImageBytes:
    def test_happy_path_returns_png_bytes(self):
        resp = _fake_response(
            candidates=[_fake_candidate(parts=[_fake_image_part(b"HELLO")])],
        )
        assert _extract_image_bytes(resp) == b"HELLO"

    def test_prompt_feedback_block_surfaces_reason(self):
        """If the prompt is blocked outright, we must name the reason so the
        user can edit the prompt instead of staring at a 500."""
        resp = _fake_response(
            prompt_feedback=SimpleNamespace(block_reason="SAFETY"),
        )
        with pytest.raises(ValueError, match="zablokował prompt"):
            _extract_image_bytes(resp)

    def test_empty_candidates_raises_clear_error(self):
        resp = _fake_response(candidates=[])
        with pytest.raises(ValueError, match="żadnego kandydata"):
            _extract_image_bytes(resp)

    def test_candidate_with_none_parts_includes_finish_reason(self):
        """This is the actual crash from prod: `parts=None` because the model
        refused. Must NOT raise TypeError — must raise a ValueError that names
        the finish_reason."""
        resp = _fake_response(
            candidates=[_fake_candidate(parts=None, finish_reason="IMAGE_SAFETY")],
        )
        with pytest.raises(ValueError, match="IMAGE_SAFETY"):
            _extract_image_bytes(resp)

    def test_candidate_with_empty_parts_list_also_handled(self):
        resp = _fake_response(
            candidates=[_fake_candidate(parts=[], finish_reason="RECITATION")],
        )
        with pytest.raises(ValueError, match="RECITATION"):
            _extract_image_bytes(resp)

    def test_text_only_response_surfaces_model_message(self):
        """Sometimes the model talks back instead of generating — surface the
        text so we can see what it's refusing about."""
        resp = _fake_response(
            candidates=[_fake_candidate(parts=[
                _fake_text_part("I cannot generate that image."),
            ])],
        )
        with pytest.raises(ValueError, match="I cannot generate"):
            _extract_image_bytes(resp)

    def test_first_image_part_wins_when_multiple_returned(self):
        resp = _fake_response(
            candidates=[_fake_candidate(parts=[
                _fake_image_part(b"FIRST"),
                _fake_image_part(b"SECOND"),
            ])],
        )
        assert _extract_image_bytes(resp) == b"FIRST"

    def test_image_part_picked_even_when_text_part_also_present(self):
        resp = _fake_response(
            candidates=[_fake_candidate(parts=[
                _fake_text_part("Here you go:"),
                _fake_image_part(b"IMG"),
            ])],
        )
        assert _extract_image_bytes(resp) == b"IMG"
