"""Tests for src/ui/app.py pure helper functions."""

from pathlib import Path

import httpx
import pytest

from src.ui.app import _fetch_recipe
from src.ui.app import _read_brew_notes


class _MockTransport(httpx.MockTransport):
    def __init__(self, status_code: int, body: bytes = b"{}") -> None:
        self._status_code = status_code
        self._body = body

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(self._status_code, content=self._body)


def _patch_client(monkeypatch: pytest.MonkeyPatch, status: int, body: bytes) -> None:
    def _fake_get(url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(status, content=body)

    monkeypatch.setattr(httpx, "get", _fake_get)


def test_fetch_recipe_returns_dict_on_200(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b'{"id":"abc","name":"IPA"}'
    _patch_client(monkeypatch, 200, payload)
    result = _fetch_recipe("abc")
    assert result == {"id": "abc", "name": "IPA"}


def test_fetch_recipe_returns_none_on_404(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, 404, b'{"detail":"not found"}')
    result = _fetch_recipe("missing")
    assert result is None


def test_fetch_recipe_returns_none_on_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.RequestError("connection refused")

    monkeypatch.setattr(httpx, "get", _raise)
    assert _fetch_recipe("abc") is None


def test_fetch_recipe_returns_none_for_empty_id() -> None:
    assert _fetch_recipe("") is None


def test_read_brew_notes_returns_content_when_file_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = tmp_path / "brew_notes"
    notes_dir.mkdir()
    (notes_dir / "abc.md").write_text("# IPA notes")
    monkeypatch.chdir(tmp_path)
    assert _read_brew_notes("abc") == "# IPA notes"


def test_read_brew_notes_returns_placeholder_when_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _read_brew_notes("abc") == "*No brew notes yet.*"
