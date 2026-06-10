#!/usr/bin/env python3
"""Image-to-image: re-imagine an existing image with a new prompt (V4.5).

Usage: uvrun examples/requests/img2img.py [path/to/image]
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os
import sys

from nekoai import Action, Model, NovelAI
from nekoai.utils import parse_image

IMAGE = sys.argv[1] if len(sys.argv) > 1 else "examples/input/example_image.png"


async def main():
    width, height, base64_image = parse_image(IMAGE)

    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        images = await client.generate_image(
            prompt="1girl, silver hair, red eyes, black dress, night, moonlight",
            model=Model.V4_5,
            action=Action.IMG2IMG,
            width=width,
            height=height,
            image=base64_image,
            strength=0.5,  # lower = closer to the original
            noise=0.1,
            seed=424242,
        )

        for image in images:
            image.save("output", "img2img.png")
            print(f"Saved output/{image.filename}")


if __name__ == "__main__":
    asyncio.run(main())
