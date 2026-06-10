#!/usr/bin/env python3
"""Colorize a line art or sketch with NovelAI's Director tool.

Usage: uvrun examples/requests/colorize.py [path/to/image]
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os
import sys

from nekoai import NovelAI

IMAGE = sys.argv[1] if len(sys.argv) > 1 else "examples/input/lineart.png"


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        result = await client.colorize(
            IMAGE, prompt="silver hair, blue eyes, white dress"
        )
        result.save("output", "colorize.png")
        print("Saved output/colorize.png")


if __name__ == "__main__":
    asyncio.run(main())
