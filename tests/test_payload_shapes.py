"""Compare generated payloads against real payloads captured from the NovelAI web UI.

Captures live in examples/payloads/. Some predate API changes (e.g. the img2img
capture lacks the stream field), so the assertions are:
- we send every field the web client sends (no missing keys), and
- any extra fields we send are in a known-tolerated set (verified live).
"""

import json
from pathlib import Path

import pytest

from nekoai import Action, Metadata, Model

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
