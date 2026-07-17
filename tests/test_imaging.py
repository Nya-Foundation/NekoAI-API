"""Image input parsing and dimension extraction."""

import base64
import io
import struct

import pytest

from nekoai import parse_image
from nekoai.exceptions import ImageProcessingError


def make_png(width: int, height: int) -> bytes:
    ihdr = struct.pack(">II", width, height) + b"\x08\x02\x00\x00\x00"
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", len(ihdr))
        + b"IHDR"
        + ihdr
        + b"\x00\x00\x00\x00"
    )


def make_jpeg(width: int, height: int) -> bytes:
    # SOF0 segment directly after the SOI marker
    return (
        b"\xff\xd8"
        + b"\xff\xc0"
        + struct.pack(">H", 17)
        + b"\x08"
        + struct.pack(">HH", height, width)
    )


def test_png_dimensions_from_bytes():
    width, height, b64 = parse_image(make_png(832, 1216))
    assert (width, height) == (832, 1216)
    assert base64.b64decode(b64) == make_png(832, 1216)


def test_jpeg_dimensions_from_bytes():
    width, height, _ = parse_image(make_jpeg(640, 480))
    assert (width, height) == (640, 480)


def test_parse_image_from_bytesio_and_base64():
    png = make_png(64, 64)
    assert parse_image(io.BytesIO(png))[:2] == (64, 64)
    # bare base64 strings are only treated as such above 100 chars
    b64 = base64.b64encode(png + b"\x00" * 100).decode()
    assert parse_image(b64)[:2] == (64, 64)


def test_parse_image_from_path(tmp_path):
    file = tmp_path / "img.png"
    file.write_bytes(make_png(128, 256))
    assert parse_image(str(file))[:2] == (128, 256)
    assert parse_image(file)[:2] == (128, 256)


def test_unsupported_format_raises():
    with pytest.raises(ImageProcessingError):
        parse_image(b"GIF89a not supported")


def test_missing_file_raises():
    with pytest.raises(ImageProcessingError):
        parse_image("no/such/file.png")
