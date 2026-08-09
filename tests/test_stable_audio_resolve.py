"""Stable Audio model alias resolution."""

from app.services.ai_sound_designer import resolve_stability_audio_model


def test_stable_audio_aliases():
    assert resolve_stability_audio_model("stable-audio-2.5") == "stable-audio-2.5"
    assert resolve_stability_audio_model("2.5") == "stable-audio-2.5"
    assert resolve_stability_audio_model("stable-audio-2") == "stable-audio-2"
    assert resolve_stability_audio_model("3") == "stable-audio-3"
    assert resolve_stability_audio_model("unknown") == "stable-audio-2"
    assert resolve_stability_audio_model("") == "stable-audio-2"
