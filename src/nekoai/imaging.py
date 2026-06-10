"""Image input parsing and dimension extraction (no Pillow dependency)."""

import base64
import io
import struct
from hashlib import sha256
from pathlib import Path

from .exceptions import ImageProcessingError

_BASE64_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")


def get_image_hash(ref_image_b64: str) -> str:
    image_bytes = base64.b64decode(ref_image_b64)
    return sha256(image_bytes).hexdigest()


def parse_image(image_input: str | Path | bytes | io.BytesIO) -> tuple[int, int, str]:
    """
    Read an image from various input types and return its dimensions and Base64 encoded raw data.

    Args:
        image_input: Can be one of:
            - str: Path to an image file
            - pathlib.Path: Path object pointing to an image file
            - bytes: Raw image bytes
            - io.BytesIO: BytesIO object containing image data
            - Any file-like object with read() method (must be in binary mode)
            - base64 encoded string (must start with 'data:image/' or be a valid base64 string)

    Returns:
        tuple: (width, height, base64_string)

    Raises:
        ImageProcessingError: If image processing fails
    """

    try:
        img_bytes = _get_image_bytes(image_input)

        # Validate the image format and extract dimensions
        width, height = _extract_image_dimensions(img_bytes)

        base64_encoded = base64.b64encode(img_bytes).decode("utf-8")

        return width, height, base64_encoded

    except (FileNotFoundError, TypeError, ValueError) as e:
        raise ImageProcessingError(f"Failed to process image: {str(e)}") from e
    except Exception as e:
        raise ImageProcessingError(
            f"Unexpected error processing image: {str(e)}"
        ) from e


def _get_image_bytes(image_input: str | Path | bytes | io.BytesIO) -> bytes:
    """Extract image bytes from various input types."""

    if isinstance(image_input, str):
        return _get_bytes_from_string(image_input)
    elif isinstance(image_input, Path):
        return image_input.read_bytes()
    elif isinstance(image_input, bytes):
        return image_input
    elif isinstance(image_input, io.BytesIO):
        image_input.seek(0)
        return image_input.read()
    elif hasattr(image_input, "read"):
        return _get_bytes_from_file_like(image_input)
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")


def _get_bytes_from_string(string_input: str) -> bytes:
    """Extract bytes from a string input (base64 or file path)."""
    # Check if it's a base64 string with data URL prefix
    if string_input.startswith("data:image/"):
        base64_encoded = string_input.split(",", 1)[1]
        return base64.b64decode(base64_encoded)

    # Check if it looks like a bare base64 string
    if len(string_input) > 100 and set(string_input).issubset(_BASE64_CHARS):
        try:
            return base64.b64decode(string_input)
        except Exception:
            # Not a valid base64 string, proceed to file path handling
            pass

    path = Path(string_input)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {string_input}")

    return path.read_bytes()


def _get_bytes_from_file_like(file_object) -> bytes:
    """Read bytes from a file-like object."""
    try:
        file_object.seek(0)
    except (OSError, AttributeError):
        # Some file-like objects might not support seek
        pass
    return file_object.read()


def _extract_image_dimensions(img_bytes: bytes) -> tuple[int, int]:
    """Detect the image format and extract (width, height)."""
    # Check for PNG signature
    if img_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return _extract_png_dimensions(img_bytes)

    # Check for JPEG signature (starts with FF D8 FF)
    elif img_bytes[:3] == b"\xff\xd8\xff":
        return _extract_jpeg_dimensions(img_bytes)

    else:
        raise ValueError("Unsupported or invalid image format")


def _extract_png_dimensions(img_bytes: bytes) -> tuple[int, int]:
    """Extract dimensions from PNG format."""
    # PNG stores dimensions in the IHDR chunk, which comes after the signature
    # Width and height are each 4 bytes, starting at offset 16
    width = struct.unpack(">I", img_bytes[16:20])[0]
    height = struct.unpack(">I", img_bytes[20:24])[0]

    return width, height


def _extract_jpeg_dimensions(img_bytes: bytes) -> tuple[int, int]:
    """Extract dimensions from JPEG format by walking SOF markers."""
    stream = io.BytesIO(img_bytes)
    stream.seek(2)  # Skip the first two bytes (JPEG marker)

    while True:
        marker = struct.unpack(">H", stream.read(2))[0]
        size = struct.unpack(">H", stream.read(2))[0]

        # SOF markers contain the dimensions (0xFFC0 - 0xFFC3, 0xFFC5 - 0xFFC7, 0xFFC9 - 0xFFCB)
        if (
            (0xFFC0 <= marker <= 0xFFC3)
            or (0xFFC5 <= marker <= 0xFFC7)
            or (0xFFC9 <= marker <= 0xFFCB)
        ):
            stream.seek(1, 1)  # Skip 1 byte
            height = struct.unpack(">H", stream.read(2))[0]
            width = struct.unpack(">H", stream.read(2))[0]
            return width, height

        # If it's not an SOF marker, skip to the next marker
        stream.seek(size - 2, 1)

        # Failsafe to prevent infinite loop
        if stream.tell() >= len(img_bytes):
            break

    raise ValueError("Could not extract dimensions from JPEG image")
