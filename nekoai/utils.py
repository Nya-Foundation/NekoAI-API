import io
import json
import zipfile
from base64 import urlsafe_b64encode
from hashlib import blake2b
from typing import Generator

import argon2

from .exceptions import APIError, AuthError, ConcurrentError, NovelAIError
from .types import User


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


def parse_image(file_path: str) -> tuple[int, int, str]:
    """
    Read a PNG image and return its dimensions and Base64 encoded raw data
    without using PIL.

    Args:
        file_path (str): Path to the PNG image file

    Returns:
        tuple: (width, height, base64_string)
    """
    import base64
    import struct

    try:
        # Read the file
        with open(file_path, "rb") as f:
            img_bytes = f.read()

        # Verify PNG signature (first 8 bytes should be 89 50 4E 47 0D 0A 1A 0A)
        if img_bytes[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Not a valid PNG file")

        # PNG stores dimensions in the IHDR chunk, which comes after the signature
        # The IHDR chunk should start at byte 8 with length (4 bytes) + "IHDR" (4 bytes)
        # Width and height are each 4 bytes, starting at offset 16
        width = struct.unpack(">I", img_bytes[16:20])[0]
        height = struct.unpack(">I", img_bytes[20:24])[0]

        # Encode to Base64
        base64_encoded = base64.b64encode(img_bytes).decode("utf-8")

        return width, height, base64_encoded

    except Exception as e:
        print(f"Error processing image: {e}")
        return None, None, None


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
