import asyncio
import io
import zipfile
from asyncio import Task
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from httpx import AsyncClient, ReadTimeout
from loguru import logger
from pydantic import validate_call

from .types import (
    EmotionLevel,
    EmotionOptions,
    Image,
    Metadata,
    User,
)

if TYPE_CHECKING:
    from .types.director import DirectorRequest

from .constant import HEADERS, Endpoint, Host, Model
from .exceptions import AuthError, TimeoutError
from .types.host import HostInstance
from .utils import ResponseParser, encode_access_key, get_image_hash, parse_image


def running(func) -> callable:
    """
    Decorator to check if client is running before making a request.
    """

    async def wrapper(self: "NovelAI", *args, **kwargs):
        if not self.running:
            await self.init(auto_close=self.auto_close, close_delay=self.close_delay)
            if self.running:
                return await func(self, *args, **kwargs)

            raise Exception(
                f"Invalid function call: NAIClient.{func.__name__}. Client initialization failed."
            )
        else:
            return await func(self, *args, **kwargs)

    return wrapper


class NovelAI:
    """
    Async httpx client interface to interact with NovelAI's service.

    Parameters
    ----------
    username: `str`, optional
        NovelAI username, usually an email address (required if token is not provided)
    password: `str`, optional
        NovelAI password (required if token is not provided)
    token: `str`, optional
        NovelAI access token (required if username/password is not provided)
    proxy: `dict`, optional
        Proxy to use for the client

    Notes
    -----
    Either a username/password combination or a token must be provided.
    """

    __slots__ = [
        "user",
        "proxy",
        "client",
        "running",
        "auto_close",
        "close_delay",
        "close_task",
        "vibe_cache",
    ]

    def __init__(
        self,
        username: str = None,
        password: str = None,
        token: str = None,
        proxy: dict | None = None,
    ):
        self.user = User(username=username, password=password, token=token)
        if not self.user.validate_auth():
            raise ValueError("Either username/password or token must be provided")

        self.proxy = proxy
        self.client: AsyncClient | None = None
        self.running: bool = False
        self.auto_close: bool = False
        self.close_delay: float = 300
        self.close_task: Task | None = None

        self.vibe_cache: dict = {}  # Cache for storing vibe tokens

    async def init(
        self, timeout: float = 30, auto_close: bool = False, close_delay: float = 300
    ) -> None:
        """
        Get access token and implement Authorization header.

        Parameters
        ----------
        timeout: `float`, optional
            Request timeout of the client in seconds. Used to limit the max waiting time when sending a request
        auto_close: `bool`, optional
            If `True`, the client will close connections and clear resource usage after a certain period
            of inactivity. Useful for keep-alive services
        close_delay: `float`, optional
            Time to wait before auto-closing the client in seconds. Effective only if `auto_close` is `True`
        """
        try:
            self.client = AsyncClient(
                timeout=timeout, proxy=self.proxy, headers=HEADERS
            )
            self.client.headers["Authorization"] = (
                f"Bearer {await self.get_access_token()}"
            )

            self.running = True
            logger.success("NovelAI client initialized successfully.")

            self.auto_close = auto_close
            self.close_delay = close_delay
            if self.auto_close:
                await self.reset_close_task()
        except Exception:
            await self.close()
            raise

    async def close(self, delay: float = 0) -> None:
        """
        Close the client after a certain period of inactivity, or call manually to close immediately.

        Parameters
        ----------
        delay: `float`, optional
            Time to wait before closing the client in seconds
        """
        if delay:
            await asyncio.sleep(delay)

        if self.close_task:
            self.close_task.cancel()
            self.close_task = None

        await self.client.aclose()
        self.running = False

    async def reset_close_task(self) -> None:
        """
        Reset the timer for closing the client when a new request is made.
        """
        if self.close_task:
            self.close_task.cancel()
            self.close_task = None
        self.close_task = asyncio.create_task(self.close(self.close_delay))

    async def get_access_token(self) -> str:
        """
        Get access token for NovelAI API authorization.

        If a token is directly provided, it will be used.
        Otherwise, send post request to /user/login endpoint to get user's access token.

        Returns
        -------
        `str`
            NovelAI access token which is used in the Authorization header with the Bearer scheme

        Raises
        ------
        `novelai.exceptions.AuthError`
            If the account credentials are incorrect
        """
        # Use token directly if provided
        if self.user.token:
            return self.user.token

        # Otherwise authenticate with username/password
        access_key = encode_access_key(self.user)

        response = await self.client.post(
            url=f"{Host.API.value.url}{Endpoint.LOGIN.value}",
            json={
                "key": access_key,
            },
        )

        # Exceptions are handled in self.init
        ResponseParser(response).handle_status_code()

        return response.json()["accessToken"]

    @running
    @validate_call
    async def generate_image(
        self,
        metadata: Metadata | None = None,
        host: Host | HostInstance = Host.WEB,
        verbose: bool = False,
        is_opus: bool = False,
        **kwargs,
    ) -> list[Image]:
        """
        Send post request to /ai/generate-image endpoint for image generation.

        Parameters
        ----------
        metadata: `novelai.Metadata`
            Metadata object containing parameters required for image generation
        host: `Host` or `HostInstance`, optional
            Host to send the request. Can be:
            - A predefined host from `novelai.constant.Host` (API or WEB)
            - A custom host created with `Host.custom(url, accept)`
            - A direct `HostInstance` object
        verbose: `bool`, optional
            If `True`, will log the estimated Anlas cost before sending the request
        is_opus: `bool`, optional
            Use with `verbose` to calculate the cost based on your subscription tier
        **kwargs: `Any`
            If `metadata` is not provided, these parameters are used to create a `novelai.Metadata` object

        Returns
        -------
        `list[novelai.Image]`
            List of `Image` objects containing the generated image and its metadata

        Raises
        ------
        `novelai.exceptions.TimeoutError`
            If the request time exceeds the client's timeout value
        `novelai.exceptions.AuthError`
            If the access token is incorrect or expired
        """
        if metadata is None:
            metadata = Metadata(**kwargs)

        if verbose:
            logger.info(
                f"Generating image... estimated Anlas cost: {metadata.calculate_cost(is_opus)}"
            )

        if self.auto_close:
            await self.reset_close_task()

        # Get the actual host instance (whether from enum or direct HostInstance)
        host_instance = host.value if isinstance(host, Host) else host

        # V4 vibe transfer handling
        await self.encode_vibe(metadata)

        try:
            # Use model_dump_for_api which properly formats the request for different model versions
            payload = metadata.model_dump_for_api()

            print(f"Payload: {payload}")

            response = await self.client.post(
                url=f"{host_instance.url}{Endpoint.IMAGE.value}",
                json=payload,
            )
        except ReadTimeout:
            raise TimeoutError(
                "Request timed out, please try again. If the problem persists, consider setting a higher `timeout` value when initiating NAIClient."
            )

        try:
            ResponseParser(response).handle_status_code()
        except AuthError:
            await self.close()
            raise

        assert (
            response.headers["Content-Type"] == host_instance.accept
        ), f"Invalid response content type. Expected '{host_instance.accept}', got '{response.headers['Content-Type']}'."

        # Use the host name or 'custom' for the filename
        host_name = host_instance.name.lower()

        return [
            Image(
                filename=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{host_name}_p{i}.png",
                data=data,
                metadata=metadata,
            )
            for i, data in enumerate(ResponseParser(response).parse_zip_content())
        ]

    @running
    async def use_director_tool(self, request: "DirectorRequest") -> "Image":
        """
        Send request to /ai/augment-image endpoint for using NovelAI's Director tools.

        Parameters
        ----------
        request: `DirectorRequest`
            The director tool request containing the necessary parameters

        Returns
        -------
        `Image`
            An image object containing the generated image

        Raises
        ------
        `novelai.exceptions.TimeoutError`
            If the request time exceeds the client's timeout value
        `novelai.exceptions.AuthError`
            If the access token is incorrect or expired
        """
        if self.auto_close:
            await self.reset_close_task()

        host_instance = Host.WEB.value
        try:
            json_data = request.model_dump(mode="json", exclude_none=True)
            response = await self.client.post(
                url=f"{host_instance.url}{Endpoint.DIRECTOR.value}",
                json=json_data,
            )
        except ReadTimeout:
            raise TimeoutError(
                "Request timed out, please try again. If the problem persists, consider setting a higher `timeout` value when initiating NAIClient."
            )

        try:
            ResponseParser(response).handle_status_code()
        except AuthError:
            await self.close()
            raise

        if not response.content:
            logger.error("Received empty response from the server.")
            return None

        image_data = self.handle_decompression(response.content)

        # Director tool responses are not zipped, but directly return a single image
        return Image(
            filename=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.req_type}.png",
            data=image_data,
            metadata=None,
        )

    async def encode_vibe(self, metadata: Metadata) -> None:
        """
        Encode images to vibe tokens using the /ai/encode-vibe endpoint.
        Implements caching to avoid unnecessary API calls for previously processed images.

        Parameters
        ----------
        metadata: `Metadata`
            Metadata object containing parameters required for image generation

        Returns
        -------
        `None`
            The function modifies the metadata object in place, adding the encoded vibe tokens
        """
        if metadata.model not in [Model.V4, Model.V4_CUR]:
            return

        if not metadata.reference_image_multiple:
            return

        reference_image_multiple = []

        # Process each reference image
        for i, ref_image in enumerate(metadata.reference_image_multiple):
            ref_info_extracted = (
                metadata.reference_information_extracted_multiple[i]
                if metadata.reference_information_extracted_multiple
                else 1.0
            )

            # Create a unique hash from the image data for caching
            image_hash = get_image_hash(ref_image)
            cache_key = f"{image_hash}:{ref_info_extracted}:{metadata.model.value}"

            # Check if we have this image in cache
            if cache_key in self.vibe_cache:
                logger.debug("Using cached vibe token")
                vibe_token = self.vibe_cache[cache_key]
            else:
                logger.debug("Encoding new vibe token")
                # We need to make an API call to encode the vibe
                payload = {
                    "image": ref_image,
                    "information_extracted": ref_info_extracted,
                    "model": metadata.model.value,
                }

                # Use the async client properly
                response = await self.client.post(
                    url=f"{Host.WEB.value.url}{Endpoint.ENCODE_VIBE.value}",
                    json=payload,
                )

                # Raise an exception if the response is not valid
                ResponseParser(response).handle_status_code()

                # Get and cache the vibe token
                vibe_token = response.content
                self.vibe_cache[cache_key] = vibe_token

            # Add both the original image and its vibe token
            reference_image_multiple.append(vibe_token)

        # Update metadata with both reference images and their vibe tokens
        metadata.reference_image_multiple = reference_image_multiple

        # Clean up legacy fields
        metadata.reference_information_extracted_multiple = None

    def handle_decompression(self, compressed_data: bytes) -> bytes:
        """
        Handle decompression of the response content.

        Parameters
        ----------
        response: `bytes`
            The response content to decompress

        Returns
        -------
        `bytes`
            The decompressed response content
        """
        with zipfile.ZipFile(io.BytesIO(compressed_data)) as zf:

            # List the contents to see what files are inside
            file_names = zf.namelist()
            return zf.read(file_names[0])

    @running
    async def lineart(self, image) -> "Image":
        """
        Convert an image to line art using the Director tool.

        Parameters
        ----------
        image: Various types accepted:
            - `str`: Path to an image file or base64-encoded image
            - `pathlib.Path`: Path object pointing to an image file
            - `bytes`: Raw image bytes
            - `io.BytesIO`: BytesIO object containing image data
            - Any file-like object with read() method

        Returns
        -------
        `Image`
            The processed image
        """
        from .types.director import LineArtRequest

        width, height, base64_image = parse_image(image)

        request = LineArtRequest(width=width, height=height, image=base64_image)
        return await self.use_director_tool(request)

    @running
    async def sketch(self, image) -> "Image":
        """
        Convert an image to sketch using the Director tool.
        Parameters
        ----------
        image: Various types accepted:
            - `str`: Path to an image file or base64-encoded image
            - `pathlib.Path`: Path object pointing to an image file
            - `bytes`: Raw image bytes
            - `io.BytesIO`: BytesIO object containing image data
            - Any file-like object with read() method

        Returns
        -------
        `Image`
            The processed image
        """
        from .types.director import SketchRequest

        width, height, base64_image = parse_image(image)

        request = SketchRequest(width=width, height=height, image=base64_image)
        return await self.use_director_tool(request)

    @running
    async def background_removal(self, image) -> "Image":
        """
        Remove background from an image using the Director tool.

        Parameters
        ----------
        image: Various types accepted:
            - `str`: Path to an image file or base64-encoded image
            - `pathlib.Path`: Path object pointing to an image file
            - `bytes`: Raw image bytes
            - `io.BytesIO`: BytesIO object containing image data
            - Any file-like object with read() method

        Returns
        -------
        `Image`
            The processed image with background removed
        """
        from .types.director import BackgroundRemovalRequest

        width, height, base64_image = parse_image(image)

        request = BackgroundRemovalRequest(
            width=width, height=height, image=base64_image
        )
        return await self.use_director_tool(request)

    @running
    async def declutter(self, image) -> "Image":
        """
        Declutter an image using the Director tool.

        Parameters
        ----------
        image: Various types accepted:
            - `str`: Path to an image file or base64-encoded image
            - `pathlib.Path`: Path object pointing to an image file
            - `bytes`: Raw image bytes
            - `io.BytesIO`: BytesIO object containing image data
            - Any file-like object with read() method

        Returns
        -------
        `Image`
            The processed image
        """
        from .types.director import DeclutterRequest

        width, height, base64_image = parse_image(image)

        request = DeclutterRequest(width=width, height=height, image=base64_image)
        return await self.use_director_tool(request)

    @running
    async def colorize(
        self, image, prompt: Optional[str] = "", defry: Optional[int] = 0
    ) -> "Image":
        """
        Colorize a line art or sketch using the Director tool.

        Parameters
        ----------
        image: Various types accepted:
            - `str`: Path to an image file or base64-encoded image
            - `pathlib.Path`: Path object pointing to an image file
            - `bytes`: Raw image bytes
            - `io.BytesIO`: BytesIO object containing image data
            - Any file-like object with read() method
        prompt: str
            Additional prompt for the request
        defry: int, optional
            Strength level of the colorize, defaults to 0

        Returns
        -------
        `Image`
            The colorized image
        """
        from .types.director import ColorizeRequest

        width, height, base64_image = parse_image(image)

        request = ColorizeRequest(
            width=width, height=height, image=base64_image, prompt=prompt, defry=defry
        )
        return await self.use_director_tool(request)

    @running
    async def change_emotion(
        self,
        image,
        emotion: "EmotionOptions",
        prompt: Optional[str] = "",
        emotion_level: "EmotionLevel" = EmotionLevel.NORMAL,
    ) -> "Image":
        """
        Change the emotion of a character in an image using the Director tool.

        Parameters
        ----------
        image: Various types accepted:
            - `str`: Path to an image file or base64-encoded image
            - `pathlib.Path`: Path object pointing to an image file
            - `bytes`: Raw image bytes
            - `io.BytesIO`: BytesIO object containing image data
            - Any file-like object with read() method
        emotion: EmotionOptions
            The target emotion to apply
        prompt: str
            Additional prompt for the request
        emotion_level: EmotionLevel, optional
            Strength level of the emotion, defaults to NORMAL

        Returns
        -------
        `Image`
            The image with modified emotion
        """
        from .types.director import EmotionRequest

        # Validate inputs are proper enums
        if not isinstance(emotion, EmotionOptions):
            emotion = EmotionOptions(emotion)

        if not isinstance(emotion_level, EmotionLevel):
            emotion_level = EmotionLevel(emotion_level)

        width, height, base64_image = parse_image(image)

        request = EmotionRequest.create(
            width=width,
            height=height,
            image=base64_image,
            emotion=emotion,
            prompt=prompt,
            emotion_level=emotion_level,
        )
        return await self.use_director_tool(request)
