"""Prompt post-processing: quality tags, UC presets, tag deduplication."""

from nekoai import Metadata, Model


def test_quality_tags_appended_for_model_family():
    meta = Metadata(prompt="1girl", model=Model.V4_5)
    assert "very aesthetic" in meta.prompt and "masterpiece" in meta.prompt
    # inpainting variants share the base model's tags
    inp = Metadata(prompt="1girl", model=Model.V4_5_INP, action="infill")
    assert "masterpiece" in inp.prompt


def test_quality_toggle_off_leaves_prompt_alone():
    meta = Metadata(prompt="1girl", model=Model.V4_5, qualityToggle=False)
    assert meta.prompt == "1girl"


def test_uc_preset_prepended():
    meta = Metadata(prompt="x", model=Model.V4_5, ucPreset=1)
    assert meta.negative_prompt.startswith("nsfw, lowres")


def test_uc_preset_without_entry_leaves_negative_prompt_clean():
    # V4 has no preset 3; the negative prompt must not gain a dangling comma
    meta = Metadata(prompt="x", model=Model.V4, ucPreset=3, negative_prompt="blurry")
    assert meta.negative_prompt == "blurry"


def test_deduplicate_tags_case_insensitive_preserves_order():
    meta = Metadata(prompt="x", qualityToggle=False)
    result = meta.deduplicate_tags("1girl, Blue Eyes, blue eyes, smile, 1girl")
    assert result == "1girl, Blue Eyes, smile"


def test_deduplicate_tags_preserves_weight_syntax():
    meta = Metadata(prompt="x", qualityToggle=False)
    result = meta.deduplicate_tags("-0.8::feet::, rating:general, -0.8::feet::")
    assert result == "-0.8::feet::, rating:general"
