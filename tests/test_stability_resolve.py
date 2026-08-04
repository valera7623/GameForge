"""Stability generate path / model alias resolution."""

from app.services.ai_character_creator import resolve_stability_generate


def test_core_and_ultra_have_no_sd3_model_field():
    assert resolve_stability_generate("core") == ("core", None)
    assert resolve_stability_generate("ultra") == ("ultra", None)
    assert resolve_stability_generate("") == ("core", None)
    assert resolve_stability_generate("unknown") == ("core", None)


def test_sd3_family_maps_to_endpoint_and_model():
    assert resolve_stability_generate("sd3") == ("sd3", "sd3.5-large")
    assert resolve_stability_generate("sd3.5-large") == ("sd3", "sd3.5-large")
    assert resolve_stability_generate("sd3.5-large-turbo") == ("sd3", "sd3.5-large-turbo")
    assert resolve_stability_generate("turbo") == ("sd3", "sd3.5-large-turbo")
    assert resolve_stability_generate("sd3.5-medium") == ("sd3", "sd3.5-medium")
    assert resolve_stability_generate("flash") == ("sd3", "sd3.5-flash")
