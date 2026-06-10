import asyncio
import io
import zipfile
from asyncio import Task
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from httpx import AsyncClient, ReadTimeout
from loguru import logger
from pydantic import validate_call

from .types import (
    EmotionLevel,
    EmotionOptions,
    Image,
    Metadata,
    MsgpackEvent,
    User,
)

if TYPE_CHECKING:
    from .types.director import DirectorRequest

from .auth import encode_access_key, prep_headers
from .constant import HEADERS, Controlnet, Endpoint, Host, Model, is_v4_model
from .exceptions import TimeoutError
from .imaging import get_image_hash, parse_image
from .response import (
    StreamingMsgpackParser,
    handle_msgpack_content,
    handle_response_with_content,
    handle_zip_content,
)


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
    host: `str`, optional
        Base URL for image endpoints, defaults to the official https://image.novelai.net.
        Pass a custom base URL to use a reverse proxy or self-hosted gateway
    api_host: `str`, optional
        Base URL for account endpoints (login, subscription, user data),
        defaults to the official https://api.novelai.net
    proxy: `dict`, optional
        Proxy to use for the client

    Notes
    -----
    Either a username/password combination or a token must be provided.

    Examples
    --------
    # Context manager (recommended)
    async with NovelAI(token="your_token") as client:
        images = await client.generate_image(prompt="1girl, cute")

    # Manual usage
    client = NovelAI(token="your_token")
    images = await client.generate_image(prompt="1girl, cute")
    # Resources will be cleaned up automatically when client goes out of scope
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        token: str = None,
        host: str = Host.WEB.value,
        api_host: str = Host.API.value,
        proxy: dict | None = None,
        verbose: bool = False,
    ):
        self.user = User(username=username, password=password, token=token)
        if not self.user.validate_auth():
            raise ValueError("Either username/password or token must be provided")

        self.host = host.rstrip("/")
        self.api_host = api_host.rstrip("/")
        self.proxy = proxy
        self.client: AsyncClient | None = None

        self.verbose: bool = verbose
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
        headers = HEADERS.copy()
        # Host header must match the actual target, including custom base URLs
        headers["Host"] = urlparse(self.host).netloc
        self.client = AsyncClient(timeout=timeout, proxy=self.proxy, headers=headers)
        self.client.headers["Authorization"] = f"Bearer {await self.get_access_token()}"

        self.running = True
        self.auto_close = auto_close
        self.close_delay = close_delay

        if auto_close:
            await self.reset_close_task()

        logger.success("NovelAI client initialized successfully.")

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

        # Don't cancel ourselves when invoked via the auto-close task
        if self.close_task and self.close_task is not asyncio.current_task():
            self.close_task.cancel()
        self.close_task = None

        if self.client:
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

    async def _ensure_initialized(self) -> None:
        """Ensure the client is initialized before making requests."""
        if not self.running:
            await self.init(auto_close=self.auto_close, close_delay=self.close_delay)

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
        if self.user.token:
            return self.user.token

        access_key = encode_access_key(self.user)

        response = await self.client.post(
            url=f"{self.api_host}{Endpoint.LOGIN.value}",
            json={"key": access_key},
            headers=self._api_headers(),
        )

        handle_response_with_content(response, response.content)
        return response.json()["accessToken"]

    def _api_headers(self) -> dict[str, str]:
        """Build per-request headers targeting the account API host."""
        headers = prep_headers(self.client.headers)
        headers["Host"] = urlparse(self.api_host).netloc
        return headers

    @validate_call
    async def generate_image(
        self,
        metadata: Metadata | None = None,
        stream: bool = False,
        is_opus: bool = False,
        **kwargs,
    ) -> list[Image] | AsyncGenerator[MsgpackEvent, None]:
        """
        Send post request to /ai/generate-image-stream endpoint for image generation.

        Parameters
        ----------
        metadata: `novelai.Metadata`
            Metadata object containing parameters required for image generation
        stream: `bool`, optional
            If `True`, the request will be sent to the streaming endpoint for V4 models and return intermediate steps as they are generated
        is_opus: `bool`, optional
            Use with `verbose` to calculate the cost based on your subscription tier
        **kwargs: `Any`
            If `metadata` is not provided, these parameters are used to create a `novelai.Metadata` object

        Returns
        -------
        `list[novelai.Image]` | `Iterator[novelai.MsgpackEvent]`
            List of `Image` objects or Iterator of `MsgpackEvent` objects

        Raises
        ------
        `novelai.exceptions.TimeoutError`
            If the request time exceeds the client's timeout value
        `novelai.exceptions.AuthError`
            If the access token is incorrect or expired
        """
        await self._ensure_initialized()

        if metadata is None:
            metadata = Metadata(**kwargs)

        if self.verbose:
            logger.info(
                f"Generating image... estimated Anlas cost: {metadata.calculate_cost(is_opus)}"
            )

        if self.auto_close:
            await self.reset_close_task()

        # V4 curated vibe transfer handling
        await self.encode_vibe(metadata)

        try:
            payload = metadata.model_dump_for_api()
            headers = prep_headers(self.client.headers)

            if self.verbose:
                logger.info(f"[Headers] for image generation: {headers}")
                logger.info(f"[Payload] for image generation: {payload}")

            if is_v4_model(metadata.model):
                if stream:
                    return self._stream_v4_events(payload, headers)
                else:
                    content = await self._handle_v4_request(payload, headers)
                    return handle_msgpack_content(content)
            else:
                content = await self._handle_v3_request(payload, headers)
                return handle_zip_content(content)

        except ReadTimeout as e:
            raise TimeoutError(
                "Request timed out, please try again. If the problem persists, consider setting a higher `timeout` value when initiating NAIClient."
            ) from e

    async def _handle_v3_request(self, payload: dict, headers: dict) -> bytes:
        """
        Handle V3 requests by sending a post request to the /ai/generate-image endpoint.

        Parameters
        ----------
        payload: `dict`
            The request payload containing parameters for image generation
        headers: `dict`
            The headers to include in the request, including authorization

        Returns
        -------
        `bytes`
            The response content from the server, expected to be a zip file with images
        """
        response = await self.client.post(
            url=f"{self.host}{Endpoint.IMAGE.value}",
            headers=headers,
            json=payload,
        )

        handle_response_with_content(response, response.content)
        return response.content

    async def _handle_v4_request(self, payload: dict, headers: dict) -> bytes:
        """
        Handle V4 requests by sending a post request to the /ai/generate-image-stream endpoint.

        Parameters
        ----------
        payload: `dict`
            The request payload containing parameters for image generation
        headers: `dict`
            The headers to include in the request, including authorization

        Returns
        -------
        `bytes`
            The response content from the server, expected to be msgpack data
        """
        async with self.client.stream(
            "POST",
            url=f"{self.host}{Endpoint.IMAGE_STREAM.value}",
            headers=headers,
            json=payload,
        ) as response:
            # Check response status first
            if response.status_code != 200:
                content = await response.aread()
                handle_response_with_content(response, content)

            raw_data = bytearray()
            # Collect all chunks
            async for chunk in response.aiter_bytes():
                raw_data.extend(chunk)

            return bytes(raw_data)

    async def _stream_v4_events(
        self, payload: dict, headers: dict
    ) -> AsyncGenerator[MsgpackEvent, None]:
        """
        Stream V4 events in real-time as they arrive from the server.

        Parameters
        ----------
        payload: `dict`
            The request payload containing parameters for image generation
        headers: `dict`
            The headers to include in the request, including authorization

        Yields
        ------
        `MsgpackEvent`
            Individual msgpack events as they are received and parsed
        """
        async with self.client.stream(
            "POST",
            url=f"{self.host}{Endpoint.IMAGE_STREAM.value}",
            headers=headers,
            json=payload,
        ) as response:
            # Check response status first
            if response.status_code != 200:
                content = await response.aread()
                handle_response_with_content(response, content)

            # Create parser for real-time msgpack parsing
            parser = StreamingMsgpackParser()

            # Process chunks as they arrive
            async for chunk in response.aiter_bytes():
                # Feed chunk to parser and yield any complete events
                async for event in parser.feed_chunk(chunk):
                    yield event

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
        await self._ensure_initialized()

        if self.auto_close:
            await self.reset_close_task()

        try:
            payload = request.model_dump(mode="json", exclude_none=True)
            response = await self.client.post(
                url=f"{self.host}{Endpoint.DIRECTOR.value}",
                headers=prep_headers(self.client.headers),
                json=payload,
            )
        except ReadTimeout as e:
            raise TimeoutError(
                "Request timed out, please try again. If the problem persists, consider setting a higher `timeout` value when initiating NAIClient."
            ) from e

        handle_response_with_content(response, response.content)

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
        # V3 models take raw base64 reference images; V4/V4.5 models require vibe tokens
        if not is_v4_model(metadata.model) or not metadata.reference_image_multiple:
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

                response = await self.client.post(
                    url=f"{self.host}{Endpoint.ENCODE_VIBE.value}",
                    headers=prep_headers(self.client.headers),
                    json=payload,
                )

                # Raise an exception if the response is not valid
                handle_response_with_content(response, response.content)

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
        compressed_data: `bytes`
            The response content to decompress

        Returns
        -------
        `bytes`
            The decompressed response content. If the content is not a zip
            archive, it is returned as-is (some endpoints return raw images).
        """
        if not compressed_data.startswith(b"PK"):
            return compressed_data

        with zipfile.ZipFile(io.BytesIO(compressed_data)) as zf:
            file_names = zf.namelist()
            return zf.read(file_names[0])

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

    async def colorize(
        self, image, prompt: str | None = "", defry: int | None = 0
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

    async def change_emotion(
        self,
        image,
        emotion: "EmotionOptions",
        prompt: str | None = "",
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

    async def upscale(self, image, scale: int = 4) -> "Image":
        """
        Upscale an image using the /ai/upscale endpoint.

        Parameters
        ----------
        image: Various types accepted:
            - `str`: Path to an image file or base64-encoded image
            - `pathlib.Path`: Path object pointing to an image file
            - `bytes`: Raw image bytes
            - `io.BytesIO`: BytesIO object containing image data
        scale: `int`, optional
            Upscaling factor, either 2 or 4 (default)

        Returns
        -------
        `Image`
            The upscaled image
        """
        await self._ensure_initialized()

        if self.auto_close:
            await self.reset_close_task()

        width, height, base64_image = parse_image(image)
        payload = {
            "image": base64_image,
            "width": width,
            "height": height,
            "scale": scale,
        }

        try:
            response = await self.client.post(
                url=f"{self.host}{Endpoint.UPSCALE.value}",
                headers=prep_headers(self.client.headers),
                json=payload,
            )
        except ReadTimeout as e:
            raise TimeoutError(
                "Request timed out, please try again. If the problem persists, consider setting a higher `timeout` value when initiating NAIClient."
            ) from e

        handle_response_with_content(response, response.content)

        image_data = self.handle_decompression(response.content)
        return Image(
            filename=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_upscaled.png",
            data=image_data,
        )

    async def annotate_image(self, image, model: Controlnet) -> "Image":
        """
        Generate a ControlNet condition mask from an image using the /ai/annotate-image endpoint.

        The returned mask can be passed as `controlnet_condition` to `generate_image`.

        Parameters
        ----------
        image: Various types accepted:
            - `str`: Path to an image file or base64-encoded image
            - `pathlib.Path`: Path object pointing to an image file
            - `bytes`: Raw image bytes
            - `io.BytesIO`: BytesIO object containing image data
        model: `Controlnet`
            ControlNet annotator to use, refer to `nekoai.constant.Controlnet`

        Returns
        -------
        `Image`
            The annotated condition image
        """
        await self._ensure_initialized()

        if self.auto_close:
            await self.reset_close_task()

        if not isinstance(model, Controlnet):
            model = Controlnet(model)

        _, _, base64_image = parse_image(image)
        payload = {
            "model": model.value,
            "parameters": {"image": base64_image},
        }

        try:
            response = await self.client.post(
                url=f"{self.host}{Endpoint.ANNOTATE.value}",
                headers=prep_headers(self.client.headers),
                json=payload,
            )
        except ReadTimeout as e:
            raise TimeoutError(
                "Request timed out, please try again. If the problem persists, consider setting a higher `timeout` value when initiating NAIClient."
            ) from e

        handle_response_with_content(response, response.content)

        image_data = self.handle_decompression(response.content)
        return Image(
            filename=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{model.value}.png",
            data=image_data,
        )

    async def suggest_tags(
        self, prompt: str, model: Model = Model.V4_5, lang: str = "en"
    ) -> list[dict]:
        """
        Get tag suggestions for an incomplete tag via /ai/generate-image/suggest-tags.

        Parameters
        ----------
        prompt: `str`
            Incomplete tag to get suggestions for
        model: `Model`, optional
            Model to get suggestions for, defaults to V4.5 full
        lang: `str`, optional
            Language of the tag, "en" (default) or "jp"

        Returns
        -------
        `list[dict]`
            Suggested tags, each with `tag`, `count` and `confidence` keys
        """
        await self._ensure_initialized()

        if self.auto_close:
            await self.reset_close_task()

        response = await self.client.get(
            url=f"{self.host}{Endpoint.SUGGEST_TAGS.value}",
            headers=prep_headers(self.client.headers),
            params={"model": model.value, "prompt": prompt, "lang": lang},
        )

        handle_response_with_content(response, response.content)
        return response.json().get("tags", [])

    async def get_subscription(self) -> dict:
        """
        Get subscription information from the /user/subscription endpoint.

        Useful to check the subscription tier (e.g. Opus for free generations)
        and the remaining Anlas balance (`trainingStepsLeft`).

        Returns
        -------
        `dict`
            Subscription information as returned by the API
        """
        await self._ensure_initialized()

        response = await self.client.get(
            url=f"{self.api_host}{Endpoint.SUBSCRIPTION.value}",
            headers=self._api_headers(),
        )

        handle_response_with_content(response, response.content)
        return response.json()

    async def get_user_data(self) -> dict:
        """
        Get account data (priority, subscription, keystore info) from the /user/data endpoint.

        Returns
        -------
        `dict`
            User data as returned by the API
        """
        await self._ensure_initialized()

        response = await self.client.get(
            url=f"{self.api_host}{Endpoint.USER_DATA.value}",
            headers=self._api_headers(),
        )

        handle_response_with_content(response, response.content)
        return response.json()

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_initialized()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - automatically clean up resources."""
        await self.close()

    def __del__(self):
        """Cleanup resources when object is garbage collected."""
        if self.client and not self.client.is_closed:
            # Schedule cleanup in the event loop if one exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except RuntimeError:
                pass
