#!/usr/bin/env python3
"""
Example script for generating an image with NovelAI API using the V3 model.
Authentication is done with a direct access token.
"""

import asyncio
import base64
import os

from nekoai import NovelAI
from nekoai.constant import Model, Noise, Resolution, Sampler


async def main():
    # Use your NAI token (replace with your actual token)
    token = os.environ.get("NAI_TOKEN")

    # Initialize client with token authentication
    client = NovelAI(token=token)

    try:
        # Generate an image
        images = await client.generate_image(
            prompt="1 girl, cute, red eyes, white hair, cat ears, smiling",
            model=Model.V3,
            res_preset=Resolution.NORMAL_PORTRAIT,
            steps=28,
            scale=6.3,
            sampler=Sampler.DPM2S_ANC,
            noise_schedule=Noise.KARRAS,
        )

        # Save the generated image(s)
        for i, image in enumerate(images):
            # Create output directory if it doesn't exist
            os.makedirs("../output", exist_ok=True)
            # Save the image
            image.save("../output", f"v3_result_{i}.png")
            print(f"Image saved as ../output/v3_result_{i}.png")

    finally:
        # Close the client
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
