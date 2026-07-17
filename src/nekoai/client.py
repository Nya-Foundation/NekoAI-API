import asyncio
import base64
import logging
import os
from asyncio import Task
from collections.abc import AsyncGenerator
from datetime import datetime
from json import JSONDecodeError, loads

from httpx import AsyncClient, ReadTimeout, Response

from .auth import encode_access_key, prep_headers
from .constant import (
    HEADERS,
    Controlnet,
    EmotionLevel,
    EmotionOptions,
    Endpoint,
    Host,
    Model,
    TextModel,
    is_v4_model,
)
from .exceptions import NovelAIError, TimeoutError
from .imaging import get_image_hash, parse_image
from .response import (
    StreamingMsgpackParser,
    handle_msgpack_content,
    handle_response_with_content,
    handle_zip_content,
    unwrap_content,
)
from .types import Image, Metadata, MsgpackEvent, TextParams, User
from .types.director import (
    BackgroundRemovalRequest,
    ColorizeRequest,
    DeclutterRequest,
    DirectorRequest,
    EmotionRequest,
    LineArtRequest,
    SketchRequest,
)

logger = logging.getLogger(__name__)

TOKEN_ENV = "NAI_TOKEN"

TIMEOUT_MESSAGE = (
    "Request timed out, please try again. If the problem persists, "
    "consider setting a higher `timeout` value when initiating NovelAI."
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
        NovelAI access token. Falls back to the `NAI_TOKEN` environment variable
    host: `str`, optional
        Base URL for image and account endpoints, defaults to the official
        https://image.novelai.net. Pass a custom base URL to use a reverse
        proxy or self-hosted gateway
    api_host: `str`, optional
        Base URL for the few endpoints still served only by the legacy API host
        (upscale, ControlNet annotation), defaults to https://api.novelai.net
    text_host: `str`, optional
        Base URL for text generation endpoints, defaults to https://text.novelai.net
    proxy: `dict`, optional
        Proxy to use for the client
    rate_limit: `float`, optional
        Minimum number of seconds between requests to NovelAI. Defaults to 0
        (no client-side throttling). Useful to space out batch generations
    max_retries: `int`, optional
        Number of times to retry a request that hit the rate limit (HTTP 429),
        with exponential backoff. Defaults to 2

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
    await client.close()
    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        host: str = Host.WEB.value,
        api_host: str = Host.API.value,
        text_host: str = Host.TEXT.value,
        proxy: dict | None = None,
        rate_limit: float = 0,
        max_retries: int = 2,
        verbose: bool = False,
    ):
        self.user = User(
            username=username, password=password, token=token or os.getenv(TOKEN_ENV)
        )
        if not self.user.validate_auth():
            raise ValueError(
                "Either username/password or token must be provided "
                f"(or set the ${TOKEN_ENV} environment variable)"
            )

        self.host = host.rstrip("/")
        self.api_host = api_host.rstrip("/")
        self.text_host = text_host.rstrip("/")
        self.proxy = proxy
        self.client: AsyncClient | None = None

        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self._throttle_lock = asyncio.Lock()
        self._last_request_at = 0.0

        self.verbose: bool = verbose
        if verbose:
            # Make verbose output visible even if the app never configures logging
            pkg_logger = logging.getLogger(__package__)
            if not pkg_logger.handlers:
                pkg_logger.addHandler(logging.StreamHandler())
                pkg_logger.setLevel(logging.INFO)

        self.running: bool = False
        self.auto_close: bool = False
        self.close_delay: float = 300
        self.close_task: Task | None = None

        self.vibe_cache: dict[str, str] = {}  # Cache for storing vibe tokens

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
        self.client = AsyncClient(timeout=timeout, proxy=self.proxy, headers=HEADERS)
        self.client.headers["Authorization"] = f"Bearer {await self.get_access_token()}"

        self.running = True
        self.auto_close = auto_close
        self.close_delay = close_delay

        if auto_close:
            await self.reset_close_task()

        logger.info("NovelAI client initialized successfully.")

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
        """Ensure the client is initialized and reset the idle-close timer."""
        if not self.running:
            await self.init(auto_close=self.auto_close, close_delay=self.close_delay)
        if self.auto_close:
            await self.reset_close_task()

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
            url=f"{self.host}{Endpoint.LOGIN.value}",
            json={"key": access_key},
            headers=prep_headers(self.client.headers),
        )

        handle_response_with_content(response, response.content)
        return response.json()["accessToken"]

    async def _throttle(self) -> None:
        """Enforce `rate_limit` seconds between requests, if configured."""
        if self.rate_limit <= 0:
            return
        async with self._throttle_lock:
            loop = asyncio.get_running_loop()
            wait = self._last_request_at + self.rate_limit - loop.time()
            if wait > 0:
                logger.debug(f"Throttling request for {wait:.1f}s")
                await asyncio.sleep(wait)
            self._last_request_at = loop.time()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> Response:
        """
        Send a request with throttling, 429 retry with backoff, and error handling.
        """
        await self._ensure_initialized()

        for attempt in range(self.max_retries + 1):
            await self._throttle()
            try:
                response = await self.client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=prep_headers(self.client.headers),
                )
            except ReadTimeout as e:
                raise TimeoutError(TIMEOUT_MESSAGE) from e

            if response.status_code == 429 and attempt < self.max_retries:
                backoff = 2 ** (attempt + 1)
                logger.warning(f"Rate limited (429), retrying in {backoff}s...")
                await asyncio.sleep(backoff)
                continue

            handle_response_with_content(response, response.content)
            return response

    async def generate_image(
        self,
        metadata: Metadata | None = None,
        is_opus: bool = False,
        **kwargs,
    ) -> list[Image]:
        """
        Generate images and return them once complete.

        For V4/V4.5 models the request goes through the msgpack streaming
        endpoint and the final images are collected; use `generate_image_stream`
        to receive intermediate steps instead.

        Parameters
        ----------
        metadata: `novelai.Metadata`
            Metadata object containing parameters required for image generation
        is_opus: `bool`, optional
            Use with `verbose` to calculate the cost based on your subscription tier
        **kwargs: `Any`
            If `metadata` is not provided, these parameters are used to create a `novelai.Metadata` object

        Returns
        -------
        `list[novelai.Image]`
            List of `Image` objects

        Raises
        ------
        `novelai.exceptions.TimeoutError`
            If the request time exceeds the client's timeout value
        `novelai.exceptions.AuthError`
            If the access token is incorrect or expired
        """
        payload = await self._prepare_image_payload(
            metadata or Metadata(**kwargs), is_opus
        )

        if is_v4_model(Model(payload["model"])):
            response = await self._request(
                "POST", f"{self.host}{Endpoint.IMAGE_STREAM.value}", json=payload
            )
            return handle_msgpack_content(response.content)

        response = await self._request(
            "POST", f"{self.host}{Endpoint.IMAGE.value}", json=payload
        )
        return handle_zip_content(response.content)

    async def generate_image_stream(
        self,
        metadata: Metadata | None = None,
        is_opus: bool = False,
        **kwargs,
    ) -> AsyncGenerator[MsgpackEvent, None]:
        """
        Generate images with a V4/V4.5 model, yielding msgpack events
        (intermediate denoising steps and final images) as they arrive.

        Parameters
        ----------
        metadata: `novelai.Metadata`
            Metadata object containing parameters required for image generation
        is_opus: `bool`, optional
            Use with `verbose` to calculate the cost based on your subscription tier
        **kwargs: `Any`
            If `metadata` is not provided, these parameters are used to create a `novelai.Metadata` object

        Yields
        ------
        `novelai.MsgpackEvent`
            Individual msgpack events as they are received and parsed
        """
        metadata = metadata or Metadata(**kwargs)
        if not is_v4_model(metadata.model):
            raise ValueError(
                "Streaming generation requires a V4/V4.5 model; "
                "use generate_image() for V3 models."
            )

        payload = await self._prepare_image_payload(metadata, is_opus)
        await self._throttle()

        try:
            async with self.client.stream(
                "POST",
                url=f"{self.host}{Endpoint.IMAGE_STREAM.value}",
                headers=prep_headers(self.client.headers),
                json=payload,
            ) as response:
                if response.status_code != 200:
                    content = await response.aread()
                    handle_response_with_content(response, content)

                parser = StreamingMsgpackParser()
                async for chunk in response.aiter_bytes():
                    async for event in parser.feed_chunk(chunk):
                        yield event
        except ReadTimeout as e:
            raise TimeoutError(TIMEOUT_MESSAGE) from e

    async def _prepare_image_payload(
        self, metadata: Metadata, is_opus: bool = False
    ) -> dict:
        """
        Build the request payload for image generation, encoding vibe reference
        images into vibe tokens for V4/V4.5 models without mutating `metadata`.
        """
        await self._ensure_initialized()

        if self.verbose:
            logger.info(
                f"Generating image... estimated Anlas cost: {metadata.calculate_cost(is_opus)}"
            )

        payload = metadata.model_dump_for_api()

        # V4/V4.5 models take vibe tokens from /ai/encode-vibe instead of raw
        # base64 reference images (which is what V3 models expect)
        if is_v4_model(metadata.model) and metadata.reference_image_multiple:
            tokens = []
            for i, ref_image in enumerate(metadata.reference_image_multiple):
                ref_info_extracted = (
                    metadata.reference_information_extracted_multiple[i]
                    if metadata.reference_information_extracted_multiple
                    else 1.0
                )
                tokens.append(
                    await self._encode_vibe_token(
                        ref_image, ref_info_extracted, metadata.model
                    )
                )
            payload["parameters"]["reference_image_multiple"] = tokens
            payload["parameters"].pop("reference_information_extracted_multiple", None)

        if self.verbose:
            logger.info(f"[Payload] for image generation: {payload}")

        return payload

    async def _encode_vibe_token(
        self, ref_image: str, information_extracted: float, model: Model
    ) -> str:
        """
        Encode a base64 reference image into a vibe token via /ai/encode-vibe,
        caching results to avoid repeated Anlas-costing calls.
        """
        cache_key = f"{get_image_hash(ref_image)}:{information_extracted}:{model.value}"
        if cache_key in self.vibe_cache:
            logger.debug("Using cached vibe token")
            return self.vibe_cache[cache_key]

        logger.debug("Encoding new vibe token")
        response = await self._request(
            "POST",
            f"{self.host}{Endpoint.ENCODE_VIBE.value}",
            json={
                "image": ref_image,
                "information_extracted": information_extracted,
                "model": model.value,
            },
        )

        # The endpoint returns the vibe token as raw bytes; the
        # generate payload expects it base64-encoded
        token = base64.b64encode(response.content).decode("utf-8")
        self.vibe_cache[cache_key] = token
        return token

    async def generate_text(
        self,
        prompt: str,
        model: TextModel | str = TextModel.ERATO,
        params: TextParams | None = None,
        **kwargs,
    ) -> str:
        """
        Generate a text continuation via the /ai/generate endpoint.

        Parameters
        ----------
        prompt: `str`
            Input text for the model to continue
        model: `TextModel` | `str`, optional
            Text model to use, defaults to Erato (`llama-3-erato-v1`).
            An arbitrary string is passed through for models not in the enum
        params: `TextParams`, optional
            Generation parameters; created from `**kwargs` if not provided

        Returns
        -------
        `str`
            The generated continuation
        """
        payload = self._text_payload(prompt, model, params, kwargs)
        response = await self._request(
            "POST", f"{self.text_host}{Endpoint.TEXT.value}", json=payload
        )

        data = response.json()
        if data.get("error"):
            raise NovelAIError(f"Text generation failed: {data['error']}")
        return data.get("output", "")

    async def generate_text_stream(
        self,
        prompt: str,
        model: TextModel | str = TextModel.ERATO,
        params: TextParams | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a text continuation via /ai/generate-stream, yielding tokens
        as they arrive (SSE `newToken` events).

        Parameters are the same as `generate_text`.

        Yields
        ------
        `str`
            Generated text fragments, in order
        """
        payload = self._text_payload(prompt, model, params, kwargs)
        await self._ensure_initialized()
        await self._throttle()

        try:
            async with self.client.stream(
                "POST",
                url=f"{self.text_host}{Endpoint.TEXT_STREAM.value}",
                headers=prep_headers(self.client.headers),
                json=payload,
            ) as response:
                if response.status_code != 200:
                    content = await response.aread()
                    handle_response_with_content(response, content)

                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    try:
                        data = loads(line[5:].strip())
                    except JSONDecodeError:
                        continue
                    if "token" in data:
                        yield data["token"]
        except ReadTimeout as e:
            raise TimeoutError(TIMEOUT_MESSAGE) from e

    @staticmethod
    def _text_payload(
        prompt: str,
        model: TextModel | str,
        params: TextParams | None,
        kwargs: dict,
    ) -> dict:
        return {
            "input": prompt,
            "model": model.value if isinstance(model, TextModel) else model,
            "parameters": (params or TextParams(**kwargs)).to_payload(),
        }

    async def use_director_tool(self, request: DirectorRequest) -> Image:
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
        response = await self._request(
            "POST",
            f"{self.host}{Endpoint.DIRECTOR.value}",
            json=request.model_dump(mode="json", exclude_none=True),
        )

        # Director tool responses are a single image, zipped or raw
        return Image(
            filename=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.req_type}.png",
            data=unwrap_content(response.content),
        )

    async def _run_director_tool(self, request_cls, image, **kwargs) -> Image:
        """Parse the image input and run a Director tool with its dimensions filled in."""
        width, height, base64_image = parse_image(image)
        request = request_cls(width=width, height=height, image=base64_image, **kwargs)
        return await self.use_director_tool(request)

    async def lineart(self, image) -> Image:
        """
        Convert an image to line art using the Director tool.

        `image` accepts a file path (`str`/`Path`), base64 string, raw `bytes`,
        or a binary file-like object.
        """
        return await self._run_director_tool(LineArtRequest, image)

    async def sketch(self, image) -> Image:
        """
        Convert an image to sketch using the Director tool.

        `image` accepts a file path (`str`/`Path`), base64 string, raw `bytes`,
        or a binary file-like object.
        """
        return await self._run_director_tool(SketchRequest, image)

    async def background_removal(self, image) -> Image:
        """
        Remove background from an image using the Director tool.

        `image` accepts a file path (`str`/`Path`), base64 string, raw `bytes`,
        or a binary file-like object.
        """
        return await self._run_director_tool(BackgroundRemovalRequest, image)

    async def declutter(self, image) -> Image:
        """
        Declutter an image using the Director tool.

        `image` accepts a file path (`str`/`Path`), base64 string, raw `bytes`,
        or a binary file-like object.
        """
        return await self._run_director_tool(DeclutterRequest, image)

    async def colorize(self, image, prompt: str | None = "", defry: int = 0) -> Image:
        """
        Colorize a line art or sketch using the Director tool.

        Parameters
        ----------
        image: file path (`str`/`Path`), base64 string, raw `bytes`,
            or a binary file-like object
        prompt: str
            Additional prompt for the request
        defry: int, optional
            Strength level of the colorize, defaults to 0

        Returns
        -------
        `Image`
            The colorized image
        """
        return await self._run_director_tool(
            ColorizeRequest, image, prompt=prompt, defry=defry
        )

    async def change_emotion(
        self,
        image,
        emotion: EmotionOptions | str,
        prompt: str | None = "",
        emotion_level: EmotionLevel | int = EmotionLevel.NORMAL,
    ) -> Image:
        """
        Change the emotion of a character in an image using the Director tool.

        Parameters
        ----------
        image: file path (`str`/`Path`), base64 string, raw `bytes`,
            or a binary file-like object
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
        emotion = EmotionOptions(emotion)
        emotion_level = EmotionLevel(emotion_level)

        # The emotion tool encodes its options in the prompt and defry fields
        final_prompt = f"{emotion.value};;"
        if prompt:
            final_prompt += f"{prompt},"

        return await self._run_director_tool(
            EmotionRequest, image, prompt=final_prompt, defry=emotion_level.value
        )

    async def upscale(self, image, scale: int = 4) -> Image:
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
        width, height, base64_image = parse_image(image)

        # Upscale is still served only by the legacy API host
        response = await self._request(
            "POST",
            f"{self.api_host}{Endpoint.UPSCALE.value}",
            json={
                "image": base64_image,
                "width": width,
                "height": height,
                "scale": scale,
            },
        )

        return Image(
            filename=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_upscaled.png",
            data=unwrap_content(response.content),
        )

    async def annotate_image(self, image, model: Controlnet | str) -> Image:
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
        model = Controlnet(model)
        _, _, base64_image = parse_image(image)

        # Annotate is still served only by the legacy API host
        response = await self._request(
            "POST",
            f"{self.api_host}{Endpoint.ANNOTATE.value}",
            json={"model": model.value, "parameters": {"image": base64_image}},
        )

        return Image(
            filename=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{model.value}.png",
            data=unwrap_content(response.content),
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
        response = await self._request(
            "GET",
            f"{self.host}{Endpoint.SUGGEST_TAGS.value}",
            params={"model": model.value, "prompt": prompt, "lang": lang},
        )
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
        response = await self._request(
            "GET", f"{self.host}{Endpoint.SUBSCRIPTION.value}"
        )
        return response.json()

    async def get_user_data(self) -> dict:
        """
        Get account data (priority, subscription, keystore info) from the /user/data endpoint.

        Returns
        -------
        `dict`
            User data as returned by the API
        """
        response = await self._request("GET", f"{self.host}{Endpoint.USER_DATA.value}")
        return response.json()

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_initialized()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - automatically clean up resources."""
        await self.close()
