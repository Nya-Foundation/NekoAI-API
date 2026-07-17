#!/usr/bin/env python3
"""Enhance an image: a prompt-guided img2img pass at 1.5x resolution.

Usage: uv run examples/requests/enhance.py [image]
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os
import sys

from nekoai import NovelAI


async def main():
    image = sys.argv[1] if len(sys.argv) > 1 else "examples/input/example_image.png"

    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        images = await client.enhance(
            image,
            prompt="1girl, intricate details, best quality",
            scale=1.5,
            strength=0.4,
        )
        for img in images:
            img.save("output", "enhanced.png")
            print("Saved output/enhanced.png")


if __name__ == "__main__":
    asyncio.run(main())
