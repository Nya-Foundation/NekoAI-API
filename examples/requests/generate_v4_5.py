#!/usr/bin/env python3
"""Generate an image with the V4.5 full model.

Usage: uvrun examples/requests/generate_v4_5.py
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os

from nekoai import Model, NovelAI, Resolution


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"], verbose=True) as client:
        images = await client.generate_image(
            prompt="1girl, silver hair, blue eyes, white dress, flower garden",
            model=Model.V4_5,
            res_preset=Resolution.NORMAL_PORTRAIT,
            seed=424242,
        )

        for image in images:
            image.save("output", "generate_v4_5.png")
            print(f"Saved output/{image.filename}")


if __name__ == "__main__":
    asyncio.run(main())
