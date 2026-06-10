#!/usr/bin/env python3
"""Upscale an image 2x or 4x via the /ai/upscale endpoint (costs Anlas).

Usage: uvrun examples/requests/upscale.py [path/to/image]
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os
import sys

from nekoai import NovelAI

IMAGE = sys.argv[1] if len(sys.argv) > 1 else "examples/input/example_image.png"


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        result = await client.upscale(IMAGE, scale=2)
        result.save("output", "upscaled.png")
        print("Saved output/upscaled.png")


if __name__ == "__main__":
    asyncio.run(main())
