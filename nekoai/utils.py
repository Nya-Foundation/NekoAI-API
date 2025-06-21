import base64
import io
import json
import random
import string
import struct
import zipfile
from datetime import datetime, timezone
from hashlib import blake2b, sha256
from pathlib import Path
from typing import Generator

import argon2
import msgpack

from .exceptions import (
    APIError,
    AuthError,
    ConcurrentError,
    ImageProcessingError,
    NovelAIError,
)
from .types import EventType, Image, MsgpackEvent, User


def get_image_hash(ref_image_b64: str) -> str:
    image_bytes = base64.b64decode(ref_image_b64)
    return sha256(image_bytes).hexdigest()


def encode_access_key(user: User) -> str:
    """
    Generate hashed access key from the user's username and password using the blake2 and argon2 algorithms.

    Parameters
    ----------
    user : `novelai.types.User`
        User object containing username and password

    Returns
    -------
    `str`
        Hashed access key
    """
    pre_salt = f"{user.password[:6]}{user.username}novelai_data_access_key"

    blake = blake2b(digest_size=16)
    blake.update(pre_salt.encode())
    salt = blake.digest()

    raw = argon2.low_level.hash_secret_raw(
        secret=user.password.encode(),
        salt=salt,
        time_cost=2,
        memory_cost=int(2000000 / 1024),
        parallelism=1,
        hash_len=64,
        type=argon2.low_level.Type.ID,
    )
    hashed = base64.urlsafe_b64encode(raw).decode()

    return hashed[:64]


def generate_x_correlation_id():
    chars = string.ascii_letters + string.digits  # A–Z a–z 0–9
    return "".join(random.choices(chars, k=6))


def generate_x_initiated_at():
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(now.microsecond / 1000):03d}Z"


def prep_headers(headers: dict[str, str]) -> dict[str, str]:

    headers["x-correlation-id"] = generate_x_correlation_id()
    headers["x-initiated-at"] = generate_x_initiated_at()
    return headers


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
        FileNotFoundError: If a file path is provided but doesn't exist
        TypeError: If the input type is not supported
        ValueError: If the image format is invalid
    """

    try:
        # Get image bytes from input
        img_bytes = _get_image_bytes(image_input)

        # Validate the image format and extract dimensions
        width, height = _extract_image_dimensions(img_bytes)

        # Encode to Base64
        base64_encoded = base64.b64encode(img_bytes).decode("utf-8")

        return width, height, base64_encoded

    except (FileNotFoundError, TypeError, ValueError) as e:
        # Re-raise specific exceptions with more context
        raise ImageProcessingError(f"Failed to process image: {str(e)}")
    except Exception as e:
        # Catch-all for unexpected errors
        raise ImageProcessingError(f"Unexpected error processing image: {str(e)}")


def _get_image_bytes(image_input: str | Path | bytes | io.BytesIO) -> bytes:
    """
    Extract image bytes from various input types.

    Args:
        image_input: Various input formats (str, Path, bytes, BytesIO, file-like object)

    Returns:
        bytes: Raw image bytes

    Raises:
        FileNotFoundError: If a file path is provided but doesn't exist
        TypeError: If the input type is not supported
    """

    if isinstance(image_input, str):
        return _get_bytes_from_string(image_input)
    elif isinstance(image_input, Path):
        return _get_bytes_from_file(image_input)
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
    import os

    # Check if it's already a base64 string
    if string_input.startswith("data:image/"):
        # Extract the base64 part after the comma
        base64_encoded = string_input.split(",", 1)[1]
        return base64.b64decode(base64_encoded)

    # Check if it looks like a base64 string
    if len(string_input) > 100 and set(string_input).issubset(
        set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
    ):
        try:
            return base64.b64decode(string_input)
        except Exception:
            # Not a valid base64 string, proceed to file path handling
            pass

    # Treat as file path
    if not os.path.exists(string_input):
        raise FileNotFoundError(f"File not found: {string_input}")

    return _get_bytes_from_file(string_input)


def _get_bytes_from_file(file_path) -> bytes:
    """Read bytes from a file path."""
    with open(file_path, "rb") as f:
        return f.read()


def _get_bytes_from_file_like(file_object) -> bytes:
    """Read bytes from a file-like object."""
    try:
        file_object.seek(0)
    except (AttributeError, IOError):
        # Some file-like objects might not support seek
        pass
    return file_object.read()


def _extract_image_dimensions(img_bytes) -> tuple[int, int]:
    """
    Extract image dimensions based on the image format.
    This function detects the image format and delegates to the appropriate handler.

    Args:
        img_bytes: Raw image bytes

    Returns:
        tuple: (width, height)

    Raises:
        ValueError: If the image format is not supported or invalid
    """
    # Check for PNG signature
    if img_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return _extract_png_dimensions(img_bytes)

    # Check for JPEG signature (starts with FF D8 FF)
    elif img_bytes[:3] == b"\xff\xd8\xff":
        return _extract_jpeg_dimensions(img_bytes)

    else:
        raise ValueError("Unsupported or invalid image format")


def _extract_png_dimensions(img_bytes) -> tuple[int, int]:
    """
    Extract dimensions from PNG format.

    Args:
        img_bytes: Raw PNG image bytes

    Returns:
        tuple: (width, height)
    """
    import struct

    # PNG stores dimensions in the IHDR chunk, which comes after the signature
    # Width and height are each 4 bytes, starting at offset 16
    width = struct.unpack(">I", img_bytes[16:20])[0]
    height = struct.unpack(">I", img_bytes[20:24])[0]

    return width, height


def _extract_jpeg_dimensions(img_bytes) -> tuple[int, int]:
    """
    Extract dimensions from JPEG format.

    Args:
        img_bytes: Raw JPEG image bytes

    Returns:
        tuple: (width, height)

    Raises:
        ValueError: If JPEG headers cannot be parsed correctly
    """
    import struct
    from io import BytesIO

    # JPEG is more complex as dimensions are stored in SOF markers
    # Use BytesIO to navigate through the file
    stream = BytesIO(img_bytes)
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


def handle_response_with_content(response, content: bytes):
    """
    Handle response status and content type validation with detailed error messages.

    Parameters
    ----------
    response : `httpx.Response`
        Response object from the API
    content : `bytes`
        The response content (already read from stream if applicable)

    Raises
    ------
    Various exceptions based on status code and content
    """
    content_type = response.headers.get("content-type", "").lower()

    # Check if we have an error based on content-type
    if content_type == "application/json":
        # Parse error message from JSON
        try:
            error_data = json.loads(content.decode("utf-8"))
            error_message = json.dumps(error_data, indent=2)
        except (json.JSONDecodeError, UnicodeDecodeError):
            error_message = (
                f"Unable to parse error response. Raw content: {content[:500]}"
            )

        # Raise appropriate exception based on status code
        status_code = response.status_code
        if status_code == 400:
            raise APIError(f"A validation error occurred.\nResponse: {error_message}")
        elif status_code == 401:
            raise AuthError(f"Access token is incorrect.\nResponse: {error_message}")
        elif status_code == 402:
            raise AuthError(
                f"An active subscription is required.\nResponse: {error_message}"
            )
        elif status_code == 409:
            raise NovelAIError(f"A conflict error occurred.\nResponse: {error_message}")
        elif status_code == 429:
            raise ConcurrentError(f"Rate limit exceeded.\nResponse: {error_message}")
        else:
            raise NovelAIError(
                f"Unknown error (Status: {status_code}).\nResponse: {error_message}"
            )


def handle_zip_content(zip_data: bytes) -> dict[str, bytes]:
    """
    Handle binary data of a zip file and return a dictionary of file names and their contents.

    Parameters
    ----------
    zip_data : `bytes`
        Binary data of a zip file

    Returns
    -------
    `dict`
        A dictionary where keys are file names and values are binary data of the files
    """

    return [
        Image(
            filename=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_p{i}.png",
            data=data,
        )
        for i, data in enumerate(parse_zip_content(zip_data))
    ]


def parse_zip_content(zip_data: bytes) -> Generator[bytes, None, None]:
    """
    Parse binary data of a zip file into a dictionary.

    Parameters
    ----------
    zip_data : `bytes`
        Binary data of a zip file

    Returns
    -------
    `Generator`
        A generator of binary data of all files in the zip
    """

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_file:
        for filename in zip_file.namelist():
            yield zip_file.read(filename)


def handle_msgpack_content(msgpack_data: bytes) -> list[Image]:
    """
    Parse msgpack stream data and return either final images or all events.

    Parameters
    ----------
    msgpack_data : bytes
        Raw msgpack stream data from NovelAI API

    Returns
    -------
    list[Image]
        List of final images or iterator of all msgpack events
    """

    # Extract only final images
    final_images = []
    for event in _parse_msgpack_events(msgpack_data):
        if event.event_type == EventType.FINAL:
            final_images.append(event.image)
    return final_images


def _create_msgpack_event(obj: dict) -> "MsgpackEvent":
    """
    Create a MsgpackEvent from a parsed msgpack object.

    Parameters
    ----------
    obj : dict
        Parsed msgpack object containing event data

    Returns
    -------
    MsgpackEvent
        Created event object
    """
    from .types import MsgpackEvent

    # Create Image object from raw image data
    image_data = obj["image"]

    # Determine file extension based on image format
    if image_data.startswith(b"\xff\xd8"):
        extension = "jpg"
    elif image_data.startswith(b"\x89PNG\r\n\x1a\n"):
        extension = "png"
    else:
        raise ImageProcessingError(
            f"Unsupported image format in msgpack data: {image_data[:16].hex()}"
        )

    # Generate filename
    event_type = obj["event_type"]
    if event_type == "final":
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_final.{extension}"
    else:
        step_ix = obj.get("step_ix", "unknown")
        filename = (
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_step_{step_ix:02d}.{extension}"
        )

    image = Image(filename=filename, data=image_data)

    # Create MsgpackEvent
    return MsgpackEvent(
        event_type=EventType(event_type),
        samp_ix=obj["samp_ix"],
        step_ix=obj.get("step_ix", 0),  # Final events don't have step_ix
        gen_id=str(obj["gen_id"]),
        sigma=obj.get("sigma", 0.0),  # Final events don't have sigma
        image=image,
    )


def _parse_msgpack_message(message_data: bytes) -> MsgpackEvent | None:
    """
    Parse a single msgpack message and return the event.

    Parameters
    ----------
    message_data : bytes
        Raw msgpack message data

    Returns
    -------
    MsgpackEvent | None
        Parsed event or None if parsing failed
    """
    try:
        unpacker = msgpack.Unpacker(raw=False)
        unpacker.feed(message_data)
        obj = next(unpacker)

        if isinstance(obj, dict) and "event_type" in obj:
            return _create_msgpack_event(obj)

    except Exception:
        pass

    return None


def _parse_msgpack_events(msgpack_data: bytes) -> Generator["MsgpackEvent", None, None]:
    """
    Parse msgpack stream data into individual events.

    Parameters
    ----------
    msgpack_data : bytes
        Raw msgpack stream data

    Yields
    ------
    MsgpackEvent
        Individual msgpack events containing image data and metadata
    """
    offset = 0

    while offset < len(msgpack_data):
        try:
            # Check if we have at least 4 bytes for length prefix
            if offset + 4 > len(msgpack_data):
                break

            # Read length prefix (big-endian 32-bit)
            length_bytes = msgpack_data[offset : offset + 4]
            message_length = struct.unpack(">I", length_bytes)[0]

            # Extract message data
            msg_start = offset + 4
            msg_end = min(msg_start + message_length, len(msgpack_data))

            if msg_start >= len(msgpack_data):
                break

            # Parse the message
            message_data = msgpack_data[msg_start:msg_end]
            event = _parse_msgpack_message(message_data)

            if event:
                yield event

            # Move to next message
            offset = msg_start + message_length

        except Exception:
            # Skip corrupted data and try next byte
            offset += 1


class StreamingMsgpackParser:
    """
    Real-time msgpack parser that processes streaming data chunk by chunk.
    Handles the length-prefixed msgpack format used by NovelAI's V4 API.
    """

    def __init__(self):
        self.buffer = b""
        self.expected_message_length = None
        self.length_bytes_needed = 4

    async def feed_chunk(self, chunk: bytes):
        """
        Feed a chunk of data to the parser and yield any complete events.

        Parameters
        ----------
        chunk : bytes
            Raw chunk of data from the stream

        Yields
        ------
        MsgpackEvent
            Complete msgpack events as they become available
        """
        self.buffer += chunk

        while True:
            # If we don't have a message length yet, try to read it
            if self.expected_message_length is None:
                if len(self.buffer) < 4:
                    break  # Need more data for length prefix

                # Read length prefix (big-endian 32-bit)
                length_bytes = self.buffer[:4]
                self.expected_message_length = struct.unpack(">I", length_bytes)[0]
                self.buffer = self.buffer[4:]  # Remove length prefix

            # Check if we have enough data for the complete message
            if len(self.buffer) < self.expected_message_length:
                break  # Need more data

            # Extract the complete message
            message_data = self.buffer[: self.expected_message_length]
            self.buffer = self.buffer[self.expected_message_length :]
            # Reset for next message
            self.expected_message_length = None

            # Parse the message using shared logic
            event = _parse_msgpack_message(message_data)
            if event:
                yield event
