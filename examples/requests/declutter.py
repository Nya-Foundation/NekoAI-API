#!/usr/bin/env python3
"""
Example script for using the declutter director tool with NovelAI API.
Authentication is done with a direct access token.
"""

import asyncio
import os

from nekoai import NovelAI


async def main():
    # Use your NAI token (replace with your actual token)
    token = os.environ.get("NAI_TOKEN")

    # Initialize client with token authentication
    client = NovelAI(token=token)

    try:
        # Load an image file and encode it as base64
        image_path = "../input/cluttered_image.png"  # Replace with your image path

        # Declutter the image
        result = await client.declutter(image=image_path)

        # Save the result
        os.makedirs("../output", exist_ok=True)
        result.save("../output", "decluttered_result.png")
        print("Decluttered image saved as ../output/decluttered_result.png")

    finally:
        # Close the client
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
