# 🐾 NekoAI-API

<div align="center">
  <img src="https://raw.githubusercontent.com/Nya-Foundation/NekoAI-API/main/assets/banner.png" alt="NekoAI-API Banner" width="800" />

  <h3>A lightweight async Python client for NovelAI image generation, with first-class support for the V4.5 models.</h3>

  <div>
    <a href="https://github.com/Nya-Foundation/NekoAI-API/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Nya-Foundation/nekoai-api.svg" alt="License"/></a>
    <a href="https://pypi.org/project/nekoai-api/"><img src="https://img.shields.io/pypi/v/nekoai-api.svg" alt="PyPI version"/></a>
    <a href="https://pypi.org/project/nekoai-api/"><img src="https://img.shields.io/pypi/pyversions/nekoai-api.svg" alt="Python versions"/></a>
  </div>

  <div>
    <a href="https://github.com/nya-foundation/nekoai-api/actions/workflows/scan.yml"><img src="https://github.com/nya-foundation/nekoai-api/actions/workflows/scan.yml/badge.svg" alt="CodeQL & Dependencies Scan"/></a>
    <a href="https://github.com/Nya-Foundation/nekoai-api/actions/workflows/publish.yml"><img src="https://github.com/Nya-Foundation/nekoai-api/actions/workflows/publish.yml/badge.svg" alt="CI/CD Builds"/></a>
    <a href="https://pepy.tech/projects/nekoai-api"><img src="https://static.pepy.tech/badge/nekoai-api" alt="PyPI Downloads"/></a>
    <a href="https://deepwiki.com/Nya-Foundation/NekoAI-API"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"/></a>
  </div>
</div>

## Overview

**NekoAI-API** wraps NovelAI's image generation API in a clean, typed, asyncio-based
Python interface. It centers on the **V4.5 model family** — multi-character prompts
with positioning, real-time generation streaming, vibe transfer with automatic
encoding — while remaining fully compatible with V4 and V3.

Request payloads are validated with pydantic and verified field-by-field against
payloads captured from the NovelAI web client, so what this library sends is what
the website sends.

| | |
|---|---|
| ✨ **V4.5 first** | Full/Curated models, multi-character prompts with coordinates, character-level undesired content |
| 🎬 **Real-time streaming** | Watch every denoising step as an async event stream |
| 🖌️ **All actions** | Text-to-image, img2img, inpainting, vibe transfer (auto vibe encoding with caching) |
| 🛠️ **Director tools** | Line art, sketch, background removal, declutter, colorize, emotion change |
| 🔧 **Utilities** | Upscaling, tag suggestions, ControlNet annotation, subscription/Anlas info |
| 🖥️ **CLI** | `nekoai` command covering generation, tools, and account queries |
| 🌐 **Custom hosts** | Point image and account endpoints at your own reverse proxy or gateway |

> [!NOTE]
> This project is licensed under **AGPL-3.0**. It was originally inspired by
> [HanaokaYuzu/NovelAI-API](https://github.com/HanaokaYuzu/NovelAI-API) and adopts a
> copyleft license accordingly.

## Supported Models

| Model | Enum | Inpainting variant |
|---|---|---|
| **NAI Diffusion V4.5 Full** (recommended) | `Model.V4_5` | `Model.V4_5_INP` |
| NAI Diffusion V4.5 Curated | `Model.V4_5_CUR` | `Model.V4_5_CUR_INP` |
| NAI Diffusion V4 Full | `Model.V4` | `Model.V4_INP` |
| NAI Diffusion V4 Curated | `Model.V4_CUR` | `Model.V4_CUR_INP` |
| NAI Diffusion V3 | `Model.V3` | `Model.V3_INP` |
| NAI Diffusion Furry V3 | `Model.FURRY` | `Model.FURRY_INP` |

## Installation

Requires **Python 3.10+**.

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

Authentication accepts a direct **access token** (recommended — generate one with
`nekoai login <username> <password>`) or a **username/password** pair. The client
initializes itself on first use; call `client.init(...)` only if you need a custom
timeout or auto-close behavior. Pass `verbose=True` to log the estimated Anlas cost
of each generation.

## Image Generation

`generate_image` accepts parameters directly or a prepared `Metadata` object.
Quality tags and undesired-content presets are applied automatically per model
(disable with `qualityToggle=False` / `ucPreset=3`).

```python
from nekoai import Metadata, Model, NovelAI, Resolution, Sampler

metadata = Metadata(
    prompt="1girl, cute, anime style, detailed",
    negative_prompt="lowres, blurry",
    model=Model.V4_5,
    res_preset=Resolution.NORMAL_PORTRAIT,
    sampler=Sampler.EULER_ANC,
    steps=28,
    scale=6.0,
    seed=1234567890,
)

images = await client.generate_image(metadata)
```

### Multi-Character Prompts (V4/V4.5)

Each character gets its own prompt, undesired content, and canvas position:

```python
from nekoai import CharacterPrompt, Model, PositionCoords, Resolution

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

### Real-time Streaming (V4/V4.5)

With `stream=True`, `generate_image` returns an async event stream so you can watch
each denoising step — useful for progress UIs and timelapses:

```python
from nekoai import EventType

async for event in await client.generate_image(
    prompt="1girl, cute, anime style",
    model=Model.V4_5,
    res_preset=Resolution.NORMAL_PORTRAIT,
    stream=True,
):
    if event.event_type == EventType.INTERMEDIATE:
        print(f"step {event.step_ix} (sigma={event.sigma:.2f})")
    elif event.event_type == EventType.FINAL:
        event.image.save("output", "final.png")
```

In batch mode (`stream=False`, the default) the same call returns `list[Image]`
once generation completes. V3 models always return final images directly.

### Image to Image

```python
from nekoai import Action, Model
from nekoai.utils import parse_image

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

Provide a base image and a black/white mask (white areas are repainted) and use an
inpainting model:

```python
from nekoai import Action, Model
from nekoai.utils import parse_image

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

### Vibe Transfer

Borrow the style and mood of reference images. For V4/V4.5 models the client
encodes references through `/ai/encode-vibe` automatically (2 Anlas per new image;
results are cached for the client's lifetime):

```python
from nekoai import Model, Resolution
from nekoai.utils import parse_image

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

## Director Tools

Every Director tool is a single method call. Image inputs accept a file path,
`pathlib.Path`, raw `bytes`, a file-like object, or a base64 string.

```python
from nekoai import EmotionLevel, EmotionOptions

result = await client.lineart("image.png")            # image -> line art
result = await client.sketch("image.png")             # image -> sketch
result = await client.background_removal("image.png") # remove background (costs Anlas)
result = await client.declutter("image.png")          # remove text/artifacts
result = await client.colorize("lineart.png", prompt="silver hair, blue eyes")

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

# Tag autocomplete
tags = await client.suggest_tags("blue hai")  # [{"tag": "blue hair", "count": ...}, ...]

# ControlNet condition masks (edge/depth preprocessing).
# Note: ControlNet-guided generation is a V1/V2-era feature not supported by V3+.
from nekoai import Controlnet
mask = await client.annotate_image("image.png", model=Controlnet.SCRIBBLER)

# Subscription tier and Anlas balance
subscription = await client.get_subscription()
user_data = await client.get_user_data()
```

## Command Line Interface

The `nekoai` command covers generation, tools, and account queries. Authentication
comes from `--token`, the `NOVELAI_TOKEN` environment variable, or
`--username`/`--password`.

```sh
nekoai login <username> <password>          # exchange credentials for a token

export NOVELAI_TOKEN="your_access_token"
nekoai generate "1girl, cute" -m v4_5 -s 832x1216 --steps 28 -n 2
nekoai generate "1girl, cute" --stream      # live step progress (V4/V4.5)

nekoai tool lineart image.png               # also: sketch, bg-removal, declutter,
nekoai tool emotion image.png --emotion happy  # colorize, emotion, annotate
nekoai upscale image.png --scale 4
nekoai tags "blue hai"
nekoai subscription
```

## Custom Hosts

Both the image host and the account host can point at a custom base URL (reverse
proxy, self-hosted gateway). The `Host` header is derived from the URL automatically.

```python
client = NovelAI(
    token="your_access_token",
    host="https://your-image-proxy.example.com",   # default: https://image.novelai.net
    api_host="https://your-api-proxy.example.com", # default: https://api.novelai.net
)
```

## Examples

One runnable script per feature lives in [`examples/requests/`](examples/requests/),
each reading `NAI_TOKEN` from the environment — see its
[README](examples/requests/README.md) for the full index and per-feature Anlas costs.

## References

- [NovelAI Documentation](https://docs.novelai.net/)
- [NovelAI Backend API](https://api.novelai.net/docs)
- [NovelAI Unofficial Knowledgebase](https://naidb.miraheze.org/wiki/Using_the_API)
- [Aedial/novelai-api](https://github.com/Aedial/novelai-api)
- [HanaokaYuzu/NovelAI-API](https://github.com/HanaokaYuzu/NovelAI-API)
