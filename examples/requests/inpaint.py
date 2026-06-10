#!/usr/bin/env python3
"""Inpaint: regenerate the masked region of an image (V4.5 inpainting model).

The mask is a black and white image: white areas are repainted, black is kept.

Usage: uvrun examples/requests/inpaint.py <path/to/image> <path/to/mask>
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os
import sys

from nekoai import Action, Model, NovelAI
from nekoai.utils import parse_image

if len(sys.argv) < 3:
    sys.exit("usage: inpaint.py <image> <mask>")

IMAGE, MASK = sys.argv[1], sys.argv[2]


async def main():
    width, height, base64_image = parse_image(IMAGE)
    _, _, base64_mask = parse_image(MASK)

    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        images = await client.generate_image(
            prompt="1girl, silver hair, blue eyes, white dress",
            model=Model.V4_5_INP,
            action=Action.INPAINT,
            width=width,
            height=height,
            image=base64_image,
            mask=base64_mask,
            add_original_image=True,  # overlay untouched pixels from the original
            seed=424242,
        )

        for image in images:
            image.save("output", "inpaint.png")
            print(f"Saved output/{image.filename}")


if __name__ == "__main__":
    asyncio.run(main())
