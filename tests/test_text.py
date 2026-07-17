"""Text generation payload shapes."""

from nekoai import TextModel
from nekoai.client import NovelAI
from nekoai.types import TextParams


def test_text_params_defaults():
    payload = TextParams().to_payload()
    assert payload["use_string"] is True
    assert payload["max_length"] == 100
    assert "top_p" not in payload  # None fields are excluded


def test_text_params_passthrough_extras():
    payload = TextParams(mirostat_tau=5.0, top_p=0.9).to_payload()
    assert payload["mirostat_tau"] == 5.0
    assert payload["top_p"] == 0.9


def test_text_payload_shape():
    payload = NovelAI._text_payload("Once upon a time", TextModel.ERATO, None, {})
    assert payload["input"] == "Once upon a time"
    assert payload["model"] == "llama-3-erato-v1"
    assert payload["parameters"]["use_string"] is True

    # arbitrary model strings pass through for models not in the enum
    payload = NovelAI._text_payload("x", "genji-jp-6b-v2", TextParams(max_length=5), {})
    assert payload["model"] == "genji-jp-6b-v2"
    assert payload["parameters"]["max_length"] == 5
