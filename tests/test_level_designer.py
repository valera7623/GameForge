"""Unit tests for Level Designer mock styles + difficulty."""

from __future__ import annotations

from app.services.ai_level_designer import LEVEL_STYLES, _mock_level, _normalize_style


def test_mock_styles_and_difficulty():
    for style in LEVEL_STYLES:
        easy = _mock_level("test dungeon with traps", 24, 24, style, "easy")
        hard = _mock_level("test dungeon with traps", 24, 24, style, "hard")
        assert easy["style"] == style
        assert easy["difficulty"] == "easy"
        assert hard["difficulty"] == "hard"
        assert len(easy["tiles"]) == 24
        assert len(easy["tiles"][0]) == 24
        assert len(hard["enemies"]) >= len(easy["enemies"])


def test_normalize_scifi_alias():
    assert _normalize_style("Sci-Fi") == "sci_fi"
    assert _normalize_style("scifi") == "sci_fi"
