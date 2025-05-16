import base64
import io
import json
import os
import zipfile
from base64 import urlsafe_b64encode
from hashlib import blake2b, sha256
from typing import Generator

import argon2

from .exceptions import APIError, AuthError, ConcurrentError, NovelAIError
from .types import User


def get_image_hash(ref_image_b64: str) -> str:
    image_bytes = base64.b64decode(ref_image_b64)
    return sha256(image_bytes).hexdigest()


# https://github.com/Aedial/novelai-api/blob/main/novelai_api/utils.py
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
    hashed = urlsafe_b64encode(raw).decode()

    return hashed[:64]


class ImageProcessingError(Exception):
    """Custom exception for image processing errors."""

    pass


def parse_image(image_input) -> tuple[int, int, str]:
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
    import base64
    from pathlib import Path

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


def _get_image_bytes(image_input) -> bytes:
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
    import base64
    from pathlib import Path

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


def _get_bytes_from_string(string_input) -> bytes:
    """Extract bytes from a string input (base64 or file path)."""
    import base64
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


class ResponseParser:
    """
    A helper class to parse the response from NovelAI's API.

    Parameters
    ----------
    response : `httpx.Response`
        Response object from the API
    """

    def __init__(self, response):
        self.response = response

    def handle_status_code(self):
        """
        Handle the status code of the response.

        Raises
        ------
        `novelai.exceptions.APIError`
            If the status code is 400
        `novelai.exceptions.AuthError`
            If the status code is 401 or 402
        `novelai.exceptions.ConcurrentError`
            If the status code is 429
        `novelai.exceptions.NovelAIError`
            If the status code is 409 or any other unknown status code
        """
        if self.response.status_code in (200, 201):
            return

        # Try to get detailed error response
        try:
            error_data = self.response.json()
            error_details = json.dumps(error_data, indent=4)
        except (json.JSONDecodeError, ValueError):
            error_details = self.response.text or "No error details available"

        if self.response.status_code == 400:
            raise APIError(
                f"A validation error occurred. Response from NovelAI:\n{error_details}"
            )
        elif self.response.status_code == 401:
            self.running = False
            raise AuthError(
                f"Access token is incorrect. Response from NovelAI:\n{error_details}"
            )
        elif self.response.status_code == 402:
            self.running = False
            raise AuthError(
                f"An active subscription is required to access this endpoint. Response from NovelAI:\n{error_details}"
            )
        elif self.response.status_code == 409:
            raise NovelAIError(
                f"A conflict error occurred. Response from NovelAI:\n{error_details}"
            )
        elif self.response.status_code == 429:
            raise ConcurrentError(
                f"A concurrent error occurred. Response from NovelAI:\n{error_details}"
            )
        else:
            raise NovelAIError(
                f"An unknown error occurred. Status code: {self.response.status_code} {self.response.reason_phrase}\n"
                f"Response details:\n{error_details}"
            )

    def parse_zip_content(self) -> Generator[bytes, None, None]:
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
        with zipfile.ZipFile(io.BytesIO(self.response.content)) as zip_file:
            for filename in zip_file.namelist():
                yield zip_file.read(filename)
