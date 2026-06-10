"""Response validation and zip/msgpack payload parsing."""

import io
import json
import struct
import zipfile
from collections.abc import Generator
from datetime import datetime

import msgpack

from .exceptions import (
    APIError,
    AuthError,
    ConcurrentError,
    ImageProcessingError,
    NovelAIError,
)
from .types import EventType, Image, MsgpackEvent


def handle_response_with_content(response, content: bytes) -> None:
    """
    Validate a response, raising a descriptive exception for error status codes.

    Parameters
    ----------
    response : `httpx.Response`
        Response object from the API
    content : `bytes`
        The response content (already read from stream if applicable)
    """
    status_code = response.status_code
    if status_code < 400:
        return

    try:
        error_data = json.loads(content.decode("utf-8"))
        error_message = json.dumps(error_data, indent=2)
    except (json.JSONDecodeError, UnicodeDecodeError):
        error_message = f"Unable to parse error response. Raw content: {content[:500]}"

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


def handle_zip_content(zip_data: bytes) -> list[Image]:
    """
    Handle binary data of a zip file and return the contained images.

    Parameters
    ----------
    zip_data : `bytes`
        Binary data of a zip file

    Returns
    -------
    `list[Image]`
        Image objects for each file in the zip
    """

    return [
        Image(
            filename=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_p{i}.png",
            data=data,
        )
        for i, data in enumerate(parse_zip_content(zip_data))
    ]


def parse_zip_content(zip_data: bytes) -> Generator[bytes, None, None]:
    """Yield the binary content of each file in a zip archive."""

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_file:
        for filename in zip_file.namelist():
            yield zip_file.read(filename)


def handle_msgpack_content(msgpack_data: bytes) -> list[Image]:
    """
    Parse msgpack stream data and return the final images.

    Parameters
    ----------
    msgpack_data : bytes
        Raw msgpack stream data from NovelAI API

    Returns
    -------
    list[Image]
        List of final images
    """

    final_images = []
    for event in _parse_msgpack_events(msgpack_data):
        if event.event_type == EventType.FINAL:
            final_images.append(event.image)
    return final_images


def _create_msgpack_event(obj: dict) -> MsgpackEvent:
    """Create a MsgpackEvent from a parsed msgpack object."""
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

    event_type = obj["event_type"]
    if event_type == "final":
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_final.{extension}"
    else:
        step_ix = obj.get("step_ix", "unknown")
        filename = (
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_step_{step_ix:02d}.{extension}"
        )

    image = Image(filename=filename, data=image_data)

    return MsgpackEvent(
        event_type=EventType(event_type),
        samp_ix=obj["samp_ix"],
        step_ix=obj.get("step_ix", 0),  # Final events don't have step_ix
        gen_id=str(obj["gen_id"]),
        sigma=obj.get("sigma", 0.0),  # Final events don't have sigma
        image=image,
    )


def _parse_msgpack_message(message_data: bytes) -> MsgpackEvent | None:
    """Parse a single msgpack message, returning None if it is not an event."""
    try:
        unpacker = msgpack.Unpacker(raw=False)
        unpacker.feed(message_data)
        obj = next(unpacker)

        if isinstance(obj, dict) and "event_type" in obj:
            return _create_msgpack_event(obj)

    except Exception:
        pass

    return None


def _parse_msgpack_events(msgpack_data: bytes) -> Generator[MsgpackEvent, None, None]:
    """Parse length-prefixed msgpack stream data into individual events."""
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
        self.buffer = bytearray()
        self.expected_message_length = None

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
        self.buffer.extend(chunk)

        while True:
            # If we don't have a message length yet, try to read it
            if self.expected_message_length is None:
                if len(self.buffer) < 4:
                    break  # Need more data for length prefix

                # Read length prefix (big-endian 32-bit)
                self.expected_message_length = struct.unpack(">I", self.buffer[:4])[0]
                del self.buffer[:4]  # Remove length prefix

            # Check if we have enough data for the complete message
            if len(self.buffer) < self.expected_message_length:
                break  # Need more data

            # Extract the complete message
            message_data = bytes(self.buffer[: self.expected_message_length])
            del self.buffer[: self.expected_message_length]
            # Reset for next message
            self.expected_message_length = None

            # Parse the message using shared logic
            event = _parse_msgpack_message(message_data)
            if event:
                yield event
