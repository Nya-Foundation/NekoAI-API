#!/usr/bin/env python3
"""Vibe transfer: borrow style/mood from a reference image (V4/V4.5).

The client automatically encodes reference images into vibe tokens via the
/ai/encode-vibe endpoint (costs 2 Anlas per new image; results are cached).

Usage: uvrun examples/requests/vibe_transfer.py [path/to/reference]
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os
import sys

from nekoai import Model, NovelAI, Resolution
from nekoai.utils import parse_image

REFERENCE = sys.argv[1] if len(sys.argv) > 1 else "examples/input/example_image.png"


async def main():
    _, _, base64_image = parse_image(REFERENCE)

    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        images = await client.generate_image(
            prompt="landscape, mountains, sunset, scenic",
            model=Model.V4_5,
            res_preset=Resolution.NORMAL_LANDSCAPE,
            seed=424242,
            reference_image_multiple=[base64_image],
            reference_information_extracted_multiple=[1.0],
            reference_strength_multiple=[0.6],
        )

        for image in images:
            image.save("output", "vibe_transfer.png")
            print(f"Saved output/{image.filename}")


if __name__ == "__main__":
    asyncio.run(main())
