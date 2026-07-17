"""Enhance builds a scaled img2img request without network access."""

from test_imaging import make_png

from nekoai import Action, Model, NovelAI


async def test_enhance_builds_scaled_img2img_metadata(monkeypatch):
    client = NovelAI(token="x")
    captured = {}

    async def fake_generate(metadata=None, **kwargs):
        captured["metadata"] = metadata
        return []

    monkeypatch.setattr(client, "generate_image", fake_generate)
    await client.enhance(make_png(832, 1216), "1girl, detailed", scale=1.5)

    meta = captured["metadata"]
    assert meta.action == Action.IMG2IMG
    assert meta.model == Model.V4_5
    assert meta.strength == 0.4 and meta.noise == 0
    # 832*1.5=1248 and 1216*1.5=1824, rounded up to multiples of 64
    assert (meta.width, meta.height) == (1280, 1856)
    assert meta.image  # base64 of the source image


async def test_enhance_defaults_keep_original_resolution(monkeypatch):
    client = NovelAI(token="x")
    captured = {}

    async def fake_generate(metadata=None, **kwargs):
        captured["metadata"] = metadata
        return []

    monkeypatch.setattr(client, "generate_image", fake_generate)
    await client.enhance(make_png(1024, 1024), "1girl", seed=7)

    meta = captured["metadata"]
    assert (meta.width, meta.height) == (1024, 1024)
    assert meta.seed == 7
