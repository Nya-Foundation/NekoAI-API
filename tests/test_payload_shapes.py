"""Compare generated payloads against real payloads captured from the NovelAI web UI.

Captures live in examples/payloads/. Some predate API changes (e.g. the img2img
capture lacks the stream field), so the assertions are:
- we send every field the web client sends (no missing keys), and
- any extra fields we send are in a known-tolerated set (verified live).
"""

import json
from pathlib import Path

import pytest

from nekoai import Action, CharacterPrompt, Metadata, Model, PositionCoords

PAYLOADS = Path(__file__).parent.parent / "examples" / "payloads"

# Fields we may send that a (possibly stale) capture lacks; all verified
# tolerated by the live API.
ALLOWED_EXTRA = {
    "stream",
    "legacy",
    "legacy_uc",
    "legacy_v3_extend",
    "inpaintImg2ImgStrength",
    "extra_noise_seed",
    "deliberate_euler_ancestral_bug",
    "prefer_brownian",
    "negative_prompt",
    "characterPrompts",
    "v4_prompt",
    "v4_negative_prompt",
    "add_original_image",
    "strength",
    "noise",
}

CASES = {
    "nai3.json": dict(model=Model.V3),
    "nai4.json": dict(model=Model.V4),
    "nai4_cur.json": dict(model=Model.V4_CUR),
    "nai4_mult_char_w_pos.json": dict(model=Model.V4),
    "nai4.5.json": dict(model=Model.V4_5),
    "nai4.5_cur.json": dict(model=Model.V4_5_CUR),
    "nai4.5_cur_multi_char.json": dict(model=Model.V4_5_CUR),
    "nai4.5_img2img.json": dict(
        model=Model.V4_5, action=Action.IMG2IMG, image="x", strength=0.5, noise=0.1
    ),
    "inpaint.json": dict(
        model=Model.V4_5_INP, action=Action.INPAINT, image="x", mask="y"
    ),
}


@pytest.mark.parametrize("capture_name", sorted(CASES))
def test_payload_covers_captured_fields(capture_name):
    captured = json.loads((PAYLOADS / capture_name).read_text())
    meta = Metadata(prompt="1girl", width=832, height=1216, **CASES[capture_name])
    payload = meta.model_dump_for_api()

    assert payload["model"] == captured["model"]
    assert payload["action"] == captured["action"]

    ours = set(payload["parameters"])
    theirs = set(captured["parameters"])
    binary_inputs = {
        "image",
        "mask",
        "reference_image_multiple",
        "reference_strength_multiple",
        "reference_information_extracted_multiple",
    }

    missing = theirs - ours - binary_inputs
    assert not missing, f"missing fields the web client sends: {missing}"

    extra = ours - theirs - binary_inputs
    assert extra <= ALLOWED_EXTRA, f"unexpected extra fields: {extra - ALLOWED_EXTRA}"


def test_v3_payload_shape():
    params = Metadata(prompt="x", model=Model.V3).model_dump_for_api()["parameters"]
    assert params["sm"] is False and params["sm_dyn"] is False
    for v4_field in (
        "autoSmea",
        "use_coords",
        "legacy_uc",
        "prefer_brownian",
        "deliberate_euler_ancestral_bug",
        "normalize_reference_strength_multiple",
        "inpaintImg2ImgStrength",
        "v4_prompt",
        "stream",
    ):
        assert v4_field not in params, v4_field


def test_v4_actions_use_stream_and_v4_prompt():
    # Verified live: all V4 actions need the stream endpoint and v4_prompt
    for kwargs in (
        dict(model=Model.V4_5),
        dict(model=Model.V4_5, action=Action.IMG2IMG, image="i", strength=0.5),
        dict(model=Model.V4_5_INP, action=Action.INPAINT, image="i", mask="m"),
    ):
        params = Metadata(prompt="x", width=832, height=1216, **kwargs)
        dumped = params.model_dump_for_api()["parameters"]
        assert dumped["stream"] == "msgpack", kwargs
        assert "v4_prompt" in dumped and "v4_negative_prompt" in dumped, kwargs
        assert "sm" not in dumped, kwargs


@pytest.mark.parametrize(
    "model,steps",
    [(Model.V5, 32), (Model.V5_MEDIUM, 14), (Model.V5_CUR, 32), (Model.V5_INP, 32)],
)
def test_v5_payload_shape(model, steps):
    payload = Metadata(prompt="1girl", model=model).model_dump_for_api()
    params = payload["parameters"]
    assert payload["model"] == model.value
    assert params["params_version"] == 4
    assert params["steps"] == steps
    assert params["scale"] == 7
    assert params["stream"] == "msgpack"
    assert params["image_format"] == "png"
    assert params["straight_alpha"] is True
    assert params["qualityPresetId"] == "standard"
    assert params["ucPresetId"] == "heavy"
    if model != Model.V5_CUR:
        assert params["inpaintImg2ImgStrength"] == 1
    assert params["v4_prompt"]["caption"]["base_caption"] == payload["input"]
    assert (
        params["v4_negative_prompt"]["caption"]["base_caption"]
        == params["negative_prompt"]
    )


def test_v5_medium_rejects_unsupported_settings():
    with pytest.raises(ValueError, match="V5 Medium requires steps=14"):
        Metadata(prompt="x", model=Model.V5_MEDIUM, steps=23)
    with pytest.raises(ValueError, match="V5 does not support vibe transfer"):
        Metadata(prompt="x", model=Model.V5, reference_image_multiple=["x"])
    with pytest.raises(ValueError, match="Karras"):
        Metadata(prompt="x", model=Model.V5, noise_schedule="native")


def test_v5_light_quality_tags():
    meta = Metadata(prompt="1girl", model=Model.V5, qualityPresetId="light")
    assert meta.prompt.endswith("very aesthetic, amazing quality, no text")


def test_v5_webp_can_be_selected_explicitly():
    params = Metadata(
        prompt="x", model=Model.V5, image_format="webp"
    ).model_dump_for_api()["parameters"]
    assert params["image_format"] == "webp"


def test_v5_character_and_img2img_request_shapes():
    characters = Metadata(
        prompt="2girls",
        model=Model.V5,
        characterPrompts=[
            CharacterPrompt(prompt="girl, red hair", center=PositionCoords(x=0.28)),
            CharacterPrompt(prompt="girl, blue hair", center=PositionCoords(x=0.72)),
        ],
    ).model_dump_for_api()["parameters"]
    assert characters["use_coords"] is True
    assert [
        caption["char_caption"]
        for caption in characters["v4_prompt"]["caption"]["char_captions"]
    ] == ["girl, red hair", "girl, blue hair"]

    img2img = Metadata(
        prompt="2girls",
        model=Model.V5,
        action=Action.IMG2IMG,
        image="base64-image",
        strength=0.35,
        noise=0.05,
    ).model_dump_for_api()
    assert img2img["action"] == "img2img"
    assert img2img["parameters"]["strength"] == 0.35
    assert img2img["parameters"]["inpaintImg2ImgStrength"] == 1
