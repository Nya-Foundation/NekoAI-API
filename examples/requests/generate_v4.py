#!/usr/bin/env python3
"""
Example script for generating an image with NovelAI API using the V4 curated model.
Authentication is done with a direct access token.
"""

import asyncio
import os

from nekoai import NovelAI
from nekoai.constant import Model, Noise, Resolution, Sampler


async def main():
    # Use your NAI token (replace with your actual token)
    token = os.environ.get("NAI_TOKEN")

    # Initialize client with token authentication
    client = NovelAI(token=token)

    try:
        # Generate an image with V4 curated model
        images = await client.generate_image(
            prompt="1 girl, cute",
            model=Model.V4,
            res_preset=Resolution.NORMAL_PORTRAIT,
            steps=28,
            scale=6.0,
            sampler=Sampler.EULER_ANC,
            params_version=3,  # V4 models need params_version=3
            noise_schedule=Noise.KARRAS,
            uc_preset=2,
        )

        # Save the generated image(s)
        for i, image in enumerate(images):
            # Create output directory if it doesn't exist
            os.makedirs("../output", exist_ok=True)
            # Save the image
            image.save("../output", f"v4_result_{i}.png")
            print(f"Image saved as ../output/v4_result_{i}.png")

    finally:
        # Close the client
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
