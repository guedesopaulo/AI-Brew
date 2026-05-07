"""Tests for src/ui/app.py pure helper functions."""

from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import patch

import httpx
import pytest

from src.ui.app import _REPO_ROOT
from src.ui.app import _fetch_recipe
from src.ui.app import _read_brew_notes


@pytest.mark.anyio
async def test_fetch_recipe_returns_dict_on_200() -> None:
    payload = b'{"id":"abc","name":"IPA"}'
    mock_response = httpx.Response(200, content=payload)
    with patch("src.ui.app.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client.return_value
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.get = AsyncMock(return_value=mock_response)
        result = await _fetch_recipe("abc")
    assert result == {"id": "abc", "name": "IPA"}


@pytest.mark.anyio
async def test_fetch_recipe_returns_none_on_404() -> None:
    mock_response = httpx.Response(404, content=b'{"detail":"not found"}')
    with patch("src.ui.app.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client.return_value
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.get = AsyncMock(return_value=mock_response)
        result = await _fetch_recipe("missing")
    assert result is None


@pytest.mark.anyio
async def test_fetch_recipe_returns_none_on_request_error() -> None:
    with patch("src.ui.app.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client.return_value
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.get = AsyncMock(
            side_effect=httpx.RequestError("connection refused")
        )
        result = await _fetch_recipe("abc")
    assert result is None


@pytest.mark.anyio
async def test_fetch_recipe_returns_none_for_empty_id() -> None:
    assert await _fetch_recipe("") is None


def test_read_brew_notes_returns_content_when_file_exists(tmp_path: Path) -> None:
    notes_dir = tmp_path / "brew_notes"
    notes_dir.mkdir()
    (notes_dir / "abc.md").write_text("# IPA notes")
    with patch("src.ui.app._REPO_ROOT", tmp_path):
        assert _read_brew_notes("abc") == "# IPA notes"


def test_read_brew_notes_returns_placeholder_when_missing(tmp_path: Path) -> None:
    with patch("src.ui.app._REPO_ROOT", tmp_path):
        assert _read_brew_notes("abc") == "*No brew notes yet.*"


def test_repo_root_is_absolute() -> None:
    assert _REPO_ROOT.is_absolute()
