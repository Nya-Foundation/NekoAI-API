"""Msgpack stream parsing and zip/raw content unwrapping."""

import io
import struct
import zipfile

import msgpack
import pytest
from test_imaging import make_jpeg, make_png

from nekoai.exceptions import NovelAIError
from nekoai.response import (
    StreamingMsgpackParser,
    handle_msgpack_content,
    unwrap_content,
)


def frame(obj: dict) -> bytes:
    msg = msgpack.packb(obj)
    return struct.pack(">I", len(msg)) + msg


def final_event(samp_ix: int) -> dict:
    return {
        "event_type": "final",
        "samp_ix": samp_ix,
        "gen_id": 42,
        "image": make_png(64, 64),
    }


def intermediate_event(samp_ix: int, step_ix: int) -> dict:
    return {
        "event_type": "intermediate",
        "samp_ix": samp_ix,
        "step_ix": step_ix,
        "gen_id": 42,
        "sigma": 1.5,
        "image": make_jpeg(64, 64),
    }


async def collect(parser: StreamingMsgpackParser, data: bytes, chunk_size: int):
    events = []
    for i in range(0, len(data), chunk_size):
        async for event in parser.feed_chunk(data[i : i + chunk_size]):
            events.append(event)
    return events


async def test_streaming_parser_handles_chunk_boundaries():
    data = frame(intermediate_event(0, 3)) + frame(final_event(0))
    # A chunk size of 7 splits both the length prefix and the messages
    events = await collect(StreamingMsgpackParser(), data, chunk_size=7)
    assert [e.event_type.value for e in events] == ["intermediate", "final"]
    assert events[0].step_ix == 3
    assert events[0].image.filename.endswith(".jpg")
    assert events[1].image.filename.endswith(".png")


async def test_multi_sample_finals_get_distinct_filenames():
    data = frame(final_event(0)) + frame(final_event(1))
    events = await collect(StreamingMsgpackParser(), data, chunk_size=4096)
    names = [e.image.filename for e in events]
    assert len(set(names)) == 2
    assert "_p0_" in names[0] and "_p1_" in names[1]


async def test_error_event_raises():
    data = frame({"event_type": "error", "code": 500, "message": "boom"})
    with pytest.raises(NovelAIError, match="boom"):
        await collect(StreamingMsgpackParser(), data, chunk_size=4096)


def test_handle_msgpack_content_returns_finals_only():
    data = frame(intermediate_event(0, 1)) + frame(final_event(0))
    images = handle_msgpack_content(data)
    assert len(images) == 1
    assert images[0].data == make_png(64, 64)


def test_unwrap_content_zip_and_raw():
    png = make_png(64, 64)
    assert unwrap_content(png) == png

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("image.png", png)
    assert unwrap_content(buffer.getvalue()) == png
