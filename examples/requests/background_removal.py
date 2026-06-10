#!/usr/bin/env python3
"""Remove the background from an image with NovelAI's Director tool.

Usage: uvrun examples/requests/background_removal.py [path/to/image]
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os
import sys

from nekoai import NovelAI

IMAGE = sys.argv[1] if len(sys.argv) > 1 else "examples/input/example_image.png"


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        result = await client.background_removal(IMAGE)
        result.save("output", "bg_removal.png")
        print("Saved output/bg_removal.png")


if __name__ == "__main__":
    asyncio.run(main())
