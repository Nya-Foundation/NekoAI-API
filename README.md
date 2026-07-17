# NekoAI-API

[![PyPI version](https://img.shields.io/pypi/v/nekoai-api.svg)](https://pypi.org/project/nekoai-api/)
[![Python versions](https://img.shields.io/pypi/pyversions/nekoai-api.svg)](https://pypi.org/project/nekoai-api/)
[![License](https://img.shields.io/github/license/Nya-Foundation/nekoai-api.svg)](https://github.com/Nya-Foundation/NekoAI-API/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/nekoai-api)](https://pepy.tech/projects/nekoai-api)
[![CI](https://github.com/Nya-Foundation/nekoai-api/actions/workflows/publish.yml/badge.svg)](https://github.com/Nya-Foundation/nekoai-api/actions/workflows/publish.yml)

An async, fully typed Python client for the NovelAI API, covering image
generation (with first-class support for the V4.5 model family), text
generation, Director image tools, and account utilities.

Request payloads are validated with pydantic and verified field-by-field against
payloads captured from the NovelAI web client, so what this library sends is
what the website sends.

## Features

- **Image generation** — text-to-image, img2img, inpainting, and vibe transfer
  (reference images are encoded through `/ai/encode-vibe` automatically, with
  caching) for every model from V3 to V4.5.
- **V4.5 support** — multi-character prompts with canvas positioning,
  character-level undesired content, and real-time streaming of denoising steps.
- **Text generation** — story continuation with Erato, Kayra, and Clio.
  Plain text in, plain text out, with optional token-by-token streaming.
- **Director tools** — line art, sketch, background removal, declutter,
  colorize, and emotion change, each as a single method call.
- **Utilities** — upscaling, tag autocompletion, ControlNet annotation, and
  subscription/Anlas queries.
- **Robust by default** — automatic retry with backoff on rate limits,
  optional client-side request throttling, and typed exceptions.
- **CLI** — the `nekoai` command exposes generation, tools, and account
  queries for shell usage and scripting.
- **Custom hosts** — every endpoint group can be pointed at a reverse proxy
  or self-hosted gateway.

## Installation

Requires Python 3.10 or later.

```sh
pip install -U nekoai-api
# or
uv add nekoai-api
```

## Quick Start

```python
import asyncio

from nekoai import Model, NovelAI, Resolution


async def main():
    # Reads the token from the NAI_TOKEN environment variable when omitted
    async with NovelAI(token="your_access_token") as client:
        images = await client.generate_image(
            prompt="1girl, silver hair, blue eyes, white dress, flower garden",
            model=Model.V4_5,
            res_preset=Resolution.NORMAL_PORTRAIT,
        )
        for image in images:
            image.save("output")


asyncio.run(main())
```

### Authentication

The client accepts either an access token or account credentials:

```python
NovelAI(token="...")                            # explicit token
NovelAI()                                       # token from $NAI_TOKEN
NovelAI(username="user@example.com", password="...")
```

To obtain a persistent token, log in once and store the result:

```sh
nekoai login <username> <password>
```

## Image Generation

`generate_image` accepts either a prepared `Metadata` object or keyword
arguments, and returns a list of `Image` objects. All parameters are validated
before the request is sent; see the `Metadata` docstring for the full set.

### Models

| Model | Enum | Inpainting variant |
|---|---|---|
| NAI Diffusion V4.5 Full (recommended) | `Model.V4_5` | `Model.V4_5_INP` |
| NAI Diffusion V4.5 Curated | `Model.V4_5_CUR` | `Model.V4_5_CUR_INP` |
| NAI Diffusion V4 Full | `Model.V4` | `Model.V4_INP` |
| NAI Diffusion V4 Curated | `Model.V4_CUR` | `Model.V4_CUR_INP` |
| NAI Diffusion V3 | `Model.V3` | `Model.V3_INP` |
| NAI Diffusion Furry V3 | `Model.FURRY` | `Model.FURRY_INP` |

### Common parameters

```python
images = await client.generate_image(
    prompt="1girl, cute",
    model=Model.V4_5,               # default: Model.V4_5
    res_preset=Resolution.NORMAL_SQUARE,  # or width=..., height=...
    steps=28,
    scale=6.0,                      # prompt guidance
    seed=1234567890,                # random when omitted
    n_samples=1,
    negative_prompt="lowres",
    qualityToggle=True,             # append model quality tags
    ucPreset=0,                     # undesired-content preset (varies by model)
)
```

### Multi-character prompts (V4/V4.5)

Each character gets its own prompt, undesired content, and canvas position:

```python
from nekoai import CharacterPrompt, PositionCoords

images = await client.generate_image(
    prompt="two people standing together, park background",
    model=Model.V4_5,
    res_preset=Resolution.NORMAL_LANDSCAPE,
    characterPrompts=[
        CharacterPrompt(
            prompt="girl, red hair, red dress",
            uc="bad hands, bad anatomy",
            center=PositionCoords(x=0.3, y=0.5),
        ),
        CharacterPrompt(
            prompt="boy, blue hair, blue uniform",
            uc="bad hands, bad anatomy",
            center=PositionCoords(x=0.7, y=0.5),
        ),
    ],
)
```

### Real-time streaming (V4/V4.5)

`generate_image_stream` yields events for every denoising step, which is useful
for progress UIs and timelapses:

```python
from nekoai import EventType

async for event in client.generate_image_stream(
    prompt="1girl, cute, anime style",
    model=Model.V4_5,
    res_preset=Resolution.NORMAL_PORTRAIT,
):
    if event.event_type == EventType.INTERMEDIATE:
        print(f"step {event.step_ix} (sigma={event.sigma:.2f})")
    elif event.event_type == EventType.FINAL:
        event.image.save("output", "final.png")
```

`generate_image` works with every model and returns the final images;
streaming requires a V4/V4.5 model.

### Image to image

```python
from nekoai import Action, parse_image

width, height, base64_image = parse_image("input/source.png")

images = await client.generate_image(
    prompt="1girl, fantasy outfit",
    model=Model.V4_5,
    action=Action.IMG2IMG,
    width=width,
    height=height,
    image=base64_image,
    strength=0.5,  # lower = closer to the original
    noise=0.1,
)
```

### Inpainting

Provide a base image and a black/white mask (white areas are repainted) and use
an inpainting model:

```python
from nekoai import Action, parse_image

width, height, base64_image = parse_image("input/portrait.png")
_, _, base64_mask = parse_image("input/mask.png")

images = await client.generate_image(
    prompt="1girl, detailed background",
    model=Model.V4_5_INP,
    action=Action.INPAINT,
    width=width,
    height=height,
    image=base64_image,
    mask=base64_mask,
    add_original_image=True,  # overlay untouched pixels from the original
)
```

### Vibe transfer

Borrow the style and mood of reference images. For V4/V4.5 models the client
encodes references through `/ai/encode-vibe` automatically (2 Anlas per new
image; results are cached for the client's lifetime, and the `Metadata` object
can be reused across calls):

```python
from nekoai import parse_image

_, _, reference = parse_image("input/style_reference.png")

images = await client.generate_image(
    prompt="landscape, mountains, sunset",
    model=Model.V4_5,
    res_preset=Resolution.NORMAL_LANDSCAPE,
    reference_image_multiple=[reference],
    reference_information_extracted_multiple=[1.0],
    reference_strength_multiple=[0.7],
)
```

## Text Generation

Continue a story with NovelAI's text models. Input and output are plain text —
no tokenizer required. Declared parameters are validated, and any additional
sampling parameter accepted by the API (mirostat, cfg, phrase repetition
penalty, ...) passes through unchanged:

```python
from nekoai import TextModel

output = await client.generate_text(
    "The dragon circled the tower once more,",
    model=TextModel.ERATO,          # llama-3-erato-v1 (default)
    max_length=150,
    temperature=1.0,
)

# Stream tokens as they are generated:
async for token in client.generate_text_stream("Once upon a time,", max_length=50):
    print(token, end="", flush=True)
```

| Model | Enum | Identifier |
|---|---|---|
| Erato (recommended) | `TextModel.ERATO` | `llama-3-erato-v1` |
| Kayra | `TextModel.KAYRA` | `kayra-v1` |
| Clio | `TextModel.CLIO` | `clio-v1` |

Other model identifiers can be passed as plain strings. Note that
`generate_until_sentence` (enabled by default) lets the model run slightly past
`max_length` to finish a sentence; disable it for hard caps.

## Director Tools

Every Director tool is a single method call. Image inputs accept a file path,
`pathlib.Path`, raw `bytes`, a file-like object, or a base64 string.

```python
from nekoai import EmotionLevel, EmotionOptions

result = await client.lineart("image.png")             # image to line art
result = await client.sketch("image.png")              # image to sketch
result = await client.background_removal("image.png")  # remove background (costs Anlas)
result = await client.declutter("image.png")           # remove text/artifacts
result = await client.colorize("lineart.png", prompt="silver hair", defry=0)

result = await client.change_emotion(
    "image.png",
    emotion=EmotionOptions.HAPPY,
    emotion_level=EmotionLevel.NORMAL,
)

result.save("output")
```

## Utilities

```python
# Upscale 2x or 4x (costs Anlas)
upscaled = await client.upscale("image.png", scale=4)

# Tag autocompletion
tags = await client.suggest_tags("blue hai")  # [{"tag": "blue hair", ...}, ...]

# ControlNet condition masks (edge/depth preprocessing).
# Note: ControlNet-guided generation is a V1/V2-era feature not supported by V3+.
from nekoai import Controlnet
mask = await client.annotate_image("image.png", model=Controlnet.SCRIBBLER)

# Subscription tier and Anlas balance
subscription = await client.get_subscription()
user_data = await client.get_user_data()
```

## Command Line Interface

Authentication comes from `--token`, the `NAI_TOKEN` environment variable, or
`--username`/`--password`.

| Command | Purpose |
|---|---|
| `nekoai login <user> <pass>` | Exchange credentials for an access token |
| `nekoai generate <prompt>` | Generate images (txt2img, img2img, inpaint, vibe) |
| `nekoai text <prompt>` | Generate a text continuation |
| `nekoai tool <name> <image>` | Run a Director or annotation tool |
| `nekoai upscale <image>` | Upscale an image 2x or 4x |
| `nekoai tags <partial>` | Suggest completions for a partial tag |
| `nekoai subscription` | Show subscription info and Anlas balance |

```sh
export NAI_TOKEN="your_access_token"

nekoai generate "1girl, cute" -m v4_5 -s 832x1216 --steps 28 -n 2
nekoai generate "1girl, cute" --stream                        # live step progress
nekoai generate "1girl, fantasy outfit" --image src.png --strength 0.5   # img2img
nekoai generate "detailed background" --image base.png --mask mask.png   # inpaint
nekoai generate "landscape, sunset" --reference-image style.png          # vibe

nekoai text "Once upon a time," --max-length 80 --stream

nekoai tool lineart image.png
nekoai tool emotion image.png --emotion happy
nekoai upscale image.png --scale 4
```

## Configuration

### Custom hosts

Every host can point at a custom base URL (reverse proxy, self-hosted gateway).
`host` serves image and account endpoints, `text_host` serves text generation,
and `api_host` covers the endpoints still served only by the legacy API host
(upscale, ControlNet annotation):

```python
client = NovelAI(
    token="...",
    host="https://your-image-proxy.example.com",      # default: https://image.novelai.net
    text_host="https://your-text-proxy.example.com",  # default: https://text.novelai.net
    api_host="https://your-api-proxy.example.com",    # default: https://api.novelai.net
)
```

### Rate limiting and retries

Requests that hit the rate limit (HTTP 429) are retried with exponential
backoff (`max_retries`, default 2). For batch workloads, `rate_limit` enforces
a minimum spacing between requests client-side:

```python
client = NovelAI(token="...", rate_limit=10)  # at least 10 seconds between requests
```

### Timeouts and connection lifetime

```python
client = NovelAI(token="...")
await client.init(timeout=60)                       # per-request timeout in seconds
await client.init(auto_close=True, close_delay=300) # close idle connections
```

## Error Handling

All exceptions derive from `nekoai.NovelAIError`:

| Exception | Raised on |
|---|---|
| `AuthError` | Invalid or expired credentials (HTTP 401) |
| `APIError` | Request validation failure (HTTP 400) |
| `NotEnoughCreditsError` | Insufficient Anlas or no active subscription (HTTP 402) |
| `ConcurrentError` | Rate limit exceeded after retries (HTTP 429) |
| `TimeoutError` | Request exceeded the client timeout |
| `ImageProcessingError` | Unreadable or unsupported input image |

```python
from nekoai import NovelAI, NovelAIError

try:
    images = await client.generate_image(prompt="1girl")
except NovelAIError as e:
    print(f"generation failed: {e}")
```

## Examples

One runnable script per feature lives in [`examples/requests/`](examples/requests/),
each reading `NAI_TOKEN` from the environment. See its
[README](examples/requests/README.md) for the full index and per-feature Anlas
costs. NovelAI allows one concurrent generation per account, so run examples
one at a time.

## Development

The project uses [uv](https://docs.astral.sh/uv/) for dependency management and
[ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```sh
uv sync                 # install dependencies (including the dev group)
uv run pytest           # run the test suite
uv run ruff check .     # lint
uv run ruff format .    # format
```

Payload-shape tests compare generated request bodies against real payloads
captured from the NovelAI web client (`examples/payloads/`); please keep them
green when touching `Metadata` serialization.

## License

Licensed under [AGPL-3.0](LICENSE). Originally inspired by
[HanaokaYuzu/NovelAI-API](https://github.com/HanaokaYuzu/NovelAI-API) and
adopts a copyleft license accordingly.

## References

- [NovelAI documentation](https://docs.novelai.net/)
- [NovelAI backend API reference](https://api.novelai.net/docs)
- [NovelAI unofficial knowledgebase](https://naidb.miraheze.org/wiki/Using_the_API)
- [Aedial/novelai-api](https://github.com/Aedial/novelai-api)
