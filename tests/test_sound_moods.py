"""Sound Designer mood prompts."""

from app.services.ai_sound_designer import (
    MOOD_GUIDES,
    SOUND_MOODS,
    build_sound_prompt,
    normalize_mood,
)


def test_all_moods_have_guides():
    assert len(SOUND_MOODS) >= 14
    for mood in SOUND_MOODS:
        assert mood in MOOD_GUIDES
        assert len(MOOD_GUIDES[mood]) > 20


def test_normalize_mood_fallback():
    assert normalize_mood("battle") == "battle"
    assert normalize_mood("UNKNOWN") == "dark"
    assert normalize_mood("") == "dark"


def test_build_sound_prompt_music_includes_mood_and_scene():
    prompt = build_sound_prompt("throne room victory", "music", "heroic")
    assert "loopable" in prompt.lower() or "loop" in prompt.lower()
    assert "instrumental" in prompt.lower()
    assert "throne room victory" in prompt
    assert "heroic" in prompt.lower() or "brass" in prompt.lower()
    assert "no vocals" in prompt.lower()


def test_build_sound_prompt_sfx_excludes_music_bed():
    prompt = build_sound_prompt("iron gate slam", "sfx", "industrial")
    assert "sound effect" in prompt.lower() or "sfx" in prompt.lower()
    assert "iron gate slam" in prompt
    assert "metal" in prompt.lower() or "industrial" in prompt.lower()
    assert "no full music bed" in prompt.lower()
