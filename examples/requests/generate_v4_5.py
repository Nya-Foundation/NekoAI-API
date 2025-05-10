#!/usr/bin/env python3
"""
Example script for generating an image with NovelAI API using the V4.5 curated model.
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

    # Initialize with a timeout of 60 seconds
    await client.init(timeout=60)

    try:
        # Generate an image with V4.5 curated model
        images = await client.generate_image(
            prompt="1 girl, cute",
            model=Model.V4_5_CUR,
            res_preset=Resolution.NORMAL_PORTRAIT,
            steps=23,
            scale=5,
            sampler=Sampler.EULER_ANC,
            autoSmea=False,
            verbose=True,  # Show Anlas cost
        )

        # Save the generated image(s)
        for i, image in enumerate(images):
            # Create output directory if it doesn't exist
            os.makedirs("../output", exist_ok=True)
            # Save the image
            image.save("../output", f"v4_5_result_{i}.png")
            print(f"Image saved as output/v4_5_result_{i}.png")

    finally:
        # Close the client
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
