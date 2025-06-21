#!/usr/bin/env python3
"""
Example script for using the line art director tool with NovelAI API.
Authentication is done with a direct access token.
"""
import asyncio
import os

from nekoai import Model, NovelAI, Resolution
from nekoai.utils import parse_image


async def main():
    # Use your NAI token (replace with your actual token)
    token = os.environ.get("NAI_TOKEN")

    # Initialize client with token authentication
    client = NovelAI(token=token)

    try:
        # Load an image file and encode it as base64
        image_path = "../input/example_image.png"  # Replace with your image path

        # Convert the image to line art
        width, height, ref_image = parse_image(image_path)

        results = await client.generate_image(
            prompt="landscape, mountains, sunset",
            model=Model.V4,
            res_preset=Resolution.NORMAL_LANDSCAPE,
            reference_image_multiple=[ref_image],
            reference_information_extracted_multiple=[1],  # Max information extracted
            reference_strength_multiple=[0.7],  # Strong style transfer
            verbose=True,
        )
        # Save the result
        os.makedirs("../output", exist_ok=True)

        results[0].save("../output", "vibe_transfer.png")
        print("Line art saved as ../output/vibe_transfer.png")

    finally:
        # Close the client
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
