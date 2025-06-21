# 🐾 NekoAI-API

<div align="center">
  <img src="https://raw.githubusercontent.com/Nya-Foundation/NekoAI-API/main/assets/banner.png" alt="NekoAI-API Banner" width="800" />
  
  <h3>🎨 A lightweight async Python API for NovelAI image generation and director tools.</h3>
  
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

## 🌈 Introduction

> 🐾 **NekoAI-API** is a **lightweight** and **easy-to-use** Python wrapper for NovelAI's image generation capabilities. This project makes it simple to integrate NovelAI's powerful image generation and manipulation tools into your Python applications with minimal code overhead.
>
> Built with asyncio for efficient performance, it provides full access to NovelAI's latest models (V3, V4, V4.5) and Director tools while maintaining a clean, pythonic interface. This project was heavily inspired by [HanaokaYuzu's NovelAI-API](https://github.com/HanaokaYuzu/NovelAI-API), with a focus on providing more features support and enhanced usability.

### 📄 License Change Notice

> **Important**: This project has transitioned from MIT to **AGPL-3.0** license to ensure better compliance and alignment with our inspiration source. As this work builds significantly upon concepts and approaches from HanaokaYuzu's NovelAI-API, we've adopted a more appropriate license that better reflects the collaborative nature of open-source development and provides stronger copyleft protections for the community.

## 🌟 Core Capabilities

| Feature                      | Description                                                                                       |
|------------------------------|---------------------------------------------------------------------------------------------------|
| 🚀 **Lightweight**              | Focuses on image generation and Director tools, providing a simple and easy-to-use interface.     |
| ⚙️ **Parameterized**            | Provides a `Metadata` class to easily set up generation parameters with type validation.           |
| ⚡ **Asynchronous**             | Utilizes `asyncio` to run generating tasks and return outputs efficiently.                        |
| 🎬 **Real-time Streaming**      | Stream V4/V4.5 generation progress in real-time, watching each denoising step as it happens.      |
| 🔑 **Multiple Authentication Methods** | Supports both username/password and direct token authentication.                        |
| 🌐 **Custom Hosts**             | Allows specifying custom API hosts for flexibility.                                               |
| ✨ **Latest Models**            | Full support for V3, V4, and V4.5 models including multi-character generation.                    |
| 🛠️ **Director Tools**           | Complete support for all NovelAI Director tools like line art, background removal, and emotion change. |

## 📦 Installation

> [!IMPORTANT]
>
> This package requires **Python 3.10 or higher**.

Install/update with pip:

```sh
pip install -U nekoai-api
```

## 🚀 Usage

### 🔑 Initialization

Import required packages and initialize a client with your NovelAI credentials. You can use either **username/password** or a **direct token**.

```python
import asyncio
from nekoai import NovelAI

# Option 1: Username and password
async def main_with_credentials():
    client = NovelAI(username="your_username", password="your_password")
    # Client will auto-initialize when you make your first request
    
    images = await client.generate_image(prompt="1girl, cute")
    
# Option 2: Direct token authentication
async def main_with_token():
    client = NovelAI(token="your_access_token")
    # Client will auto-initialize when you make your first request
    
    images = await client.generate_image(prompt="1girl, cute")
    
# Option 3: Manual initialization (if you need custom settings)
async def main_with_manual_init():
    client = NovelAI(token="your_access_token")
    await client.init(timeout=60, auto_close=True)  # Custom timeout and auto-close
    
    images = await client.generate_image(prompt="1girl, cute")
    # Client will auto-close after 5 minutes of inactivity

asyncio.run(main_with_token())  # Or main_with_credentials()
```

> **Note**: The client now automatically initializes on first use, so calling `client.init()` is optional unless you need custom settings.

### 🖼️ Image Generation

After initializing successfully, you can generate images with the `generate_image` method. The method takes parameters **directly** or a `Metadata` object.

By passing `verbose=True`, the method will print the **estimated Anlas cost** each time a generating request is going to be made.

```python
from nekoai import NovelAI, Metadata
from nekoai.constant import Model, Resolution, Sampler, Noise

async def main():
    client = NovelAI(token="your_access_token", verbose=True)
    
    # Generate using Metadata object
    metadata = Metadata(
        prompt="1girl, cute, anime style, detailed",
        model=Model.V4_5_CUR,  # Use the latest V4.5 model
        res_preset=Resolution.NORMAL_PORTRAIT,
        n_samples=1,
    )

    # Alternative: pass parameters directly
    images = await client.generate_image(
        prompt="1girl, cute, anime style, detailed",
        model=Model.V4_5_CUR,
        res_preset=Resolution.NORMAL_PORTRAIT,
        seed=1234567890  # Fixed seed for reproducibility
    )

    for image in images:
        image.save(path="output")
        print(f"Image saved: {image.filename}")

asyncio.run(main())
```

### 🎬 Real-time Streaming (V4/V4.5 Models)

For V4 and V4.5 models, you can stream the generation process in real-time to see each denoising step as it happens. This is perfect for monitoring progress or creating timelapse videos of the generation process.

```python
import asyncio
from nekoai import NovelAI
from nekoai.constant import Model, Resolution
from nekoai.types import EventType

async def main():
    client = NovelAI(token="your_access_token", verbose=True)
    
    # Stream generation progress in real-time
    async for event in client.generate_image(
        prompt="1girl, cute, anime style, detailed",
        model=Model.V4_5_CUR,
        res_preset=Resolution.NORMAL_PORTRAIT,
        stream=True  # Enable streaming mode
    ):
        if event.event_type == EventType.INTERMEDIATE:
            print(f"📸 Step {event.step_ix}/28 - Sigma: {event.sigma:.2f}")
            # Optionally save intermediate steps
            event.image.save("output", f"step_{event.step_ix:02d}.jpg")
            
        elif event.event_type == EventType.FINAL:
            print("🎉 Final image ready!")
            event.image.save("output", "final_result.png")
            break
    
    
asyncio.run(main())
```

#### 🔄 Streaming vs Batch Mode

The library supports two modes for V4/V4.5 models:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Streaming** (`stream=True`) | Returns an async generator yielding events in real-time | Progress monitoring, UI updates, timelapse creation |
| **Batch** (`stream=False`) | Returns final images only after complete generation | Simple generation, batch processing |

```python
# Streaming mode - see progress in real-time
async for event in client.generate_image(..., stream=True):
    # Process each denoising step as it happens
    pass

# Batch mode - get final results only
images = await client.generate_image(..., stream=False)
for image in images:
    image.save("output")
```

> **Note**: Streaming is only available for V4/V4.5 models. V3 models will return final images directly.

### Multi-Character Generation (V4.5)

V4.5 models support generating multiple characters with character-specific prompts and positioning.

```python
from nekoai import NovelAI
from nekoai.constant import Model, Resolution
from nekoai.types import CharacterPrompt, PositionCoords

async def main():
    client = NovelAI(token="your_access_token")
    
    # Create character prompts with positioning
    character_prompts = [
        CharacterPrompt(
            prompt="girl, red hair, red dress",
            uc="bad hands, bad anatomy",
            center=PositionCoords(x=0.3, y=0.3),
        ),
        CharacterPrompt(
            prompt="boy, blue hair, blue uniform", 
            uc="bad hands, bad anatomy",
            center=PositionCoords(x=0.7, y=0.7),
        )
    ]
    
    # Generate image with multiple characters
    images = await client.generate_image(
        prompt="two people standing together, park background",
        model=Model.V4_5,
        res_preset=Resolution.NORMAL_LANDSCAPE,
        characterPrompts=character_prompts,
    )
    
    for image in images:
        image.save("output")
    
    
asyncio.run(main())
```

### Image to Image

To perform `img2img` action, set `action` parameter to `Action.IMG2IMG`, and provide a base64-encoded image.

```python
from nekoai import NovelAI
from nekoai.constant import Action
from nekoai.utils import parse_image

async def main():
    client = NovelAI(token="your_access_token")
    
    # Parse image automatically handles various input formats
    width, height, base64_image = parse_image('image.png')

    images = await client.generate_image(
        prompt="1girl, fantasy outfit",
        action=Action.IMG2IMG,
        width=width,
        height=height,
        image=base64_image,
        strength=0.5,  # Lower = more similar to original
        noise=0.1,
    )

    for image in images:
        image.save("output")
    
    
asyncio.run(main())
```

### Inpainting

To perform inpainting, set `action` to `Action.INPAINT`, and provide both a base image and a mask.

```python
import base64
from nekoai import NovelAI
from nekoai.constant import Model, Action, Resolution

async def main():
    client = NovelAI(token="your_access_token")
    
    with open("input/portrait.jpg", "rb") as f:
        base_image = base64.b64encode(f.read()).decode("utf-8")

    with open("input/mask.jpg", "rb") as f:
        mask = base64.b64encode(f.read()).decode("utf-8")

    images = await client.generate_image(
        prompt="1girl, detailed background",
        model=Model.V3_INP,  # Use inpainting model
        action=Action.INPAINT,
        res_preset=Resolution.NORMAL_PORTRAIT,
        image=base_image,
        mask=mask,
        add_original_image=True,  # Overlay original image
    )

    for image in images:
        image.save("output")
    
    
asyncio.run(main())
```

### Vibe Transfer

Vibe transfer allows using a reference image's style or mood in your generated image (V4_CUR only).

```python
import base64
from nekoai import NovelAI
from nekoai.constant import Model, Resolution

async def main():
    client = NovelAI(token="your_access_token")
    
    with open("input/style_reference.jpg", "rb") as f:
        ref_image = base64.b64encode(f.read()).decode("utf-8")

    images = await client.generate_image(
        prompt="landscape, mountains, sunset",
        model=Model.V4_CUR,
        res_preset=Resolution.NORMAL_LANDSCAPE,
        reference_image_multiple=[ref_image],
        reference_information_extracted_multiple=[1],  # Max information extracted
        reference_strength_multiple=[0.7],  # Strong style transfer
    )

    for image in images:
        image.save("output")
    
    
asyncio.run(main())
```

### Director Tools

NovelAI offers several Director tools for image manipulation, all accessible through dedicated methods.

#### Line Art

Convert an image to line art:

```python
import asyncio
from nekoai import NovelAI

async def main():
    client = NovelAI(token="your_access_token")
    
    result = await client.lineart('image.png')
    result.save("output")

    print(f"Line art saved as {result.filename}")
    
    
asyncio.run(main())
```

#### Background Removal

Remove the background from an image:

```python
import asyncio
from nekoai import NovelAI

async def main():
    client = NovelAI(token="your_access_token")
    
    result = await client.background_removal('image.png')
    result.save("output")

    print(f"Background has been removed and saved as {result.filename}")
    
    
asyncio.run(main())
```

#### Change Emotion

Change the emotion of a character in an image:

```python
import asyncio
from nekoai import NovelAI
from nekoai.types import EmotionOptions, EmotionLevel

async def main():
    client = NovelAI(token="your_access_token")
    
    result = await client.change_emotion(
        image="image.png",
        emotion=EmotionOptions.HAPPY,
        emotion_level=EmotionLevel.NORMAL
    )
    
    result.save("output")
    
    
asyncio.run(main())
```

#### Other Director Tools

Additional tools include:

```python
# Declutter an image, input can be str | pathlib.Path | bytes | io.BytesIO
result = await client.declutter(image='image.png')

# Colorize a sketch or line art
result = await client.colorize(image='image.png')
```

### Custom Hosts

You can specify custom API hosts for proxy support.

```python
from nekoai import NovelAI

async def main():
    # You can also initialize with a custom host or proxy service
    custom_client = NovelAI(
        token="your_access_token",
        host="https://your-custom-host.com"
    )
    
    # Generate with default host
    images = await client.generate_image(
        prompt="1girl, cute",
    )
    
    
    
        await custom_client.close()

asyncio.run(main())
```

### CLI Token Generation

You can generate an access token from the command line:

```sh
# Replace with your actual account credentials
nekoai login <username> <password>
```

## Example Scripts

The package includes several example scripts in the `examples/requests/` directory:

- Generation with different models (V3, V4, V4.5)
- Multi-character generation
- All director tools (line art, background removal, emotion change, etc.)

## References

[NovelAI Documentation](https://docs.novelai.net/)

[NovelAI Backend API](https://api.novelai.net/docs)

[NovelAI Unofficial Knowledgebase](https://naidb.miraheze.org/wiki/Using_the_API)

[Aedial's novelai-api](https://github.com/Aedial/novelai-api)

[HanaokaYuzu's NovelAI-API](https://github.com/HanaokaYuzu/NovelAI-API)
