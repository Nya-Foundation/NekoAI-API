#!/usr/bin/env python3
"""Generate an image with the legacy V3 model (zip response path).

Usage: uvrun examples/requests/generate_v3.py
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os

from nekoai import Model, Noise, NovelAI, Resolution, Sampler


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        images = await client.generate_image(
            prompt="1girl, cute, red eyes, white hair, cat ears, smiling",
            model=Model.V3,
            res_preset=Resolution.NORMAL_PORTRAIT,
            steps=28,
            scale=6.3,
            sampler=Sampler.DPM2S_ANC,
            noise_schedule=Noise.KARRAS,
            seed=424242,
        )

        for image in images:
            image.save("output", "generate_v3.png")
            print(f"Saved output/{image.filename}")


if __name__ == "__main__":
    asyncio.run(main())
