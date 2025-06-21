#!/usr/bin/env python3
"""
Example script for using the background removal director tool with NovelAI API.
Authentication is done with a direct access token.
"""

import asyncio
import base64
import os

from nekoai import NovelAI


async def main():
    # Use your NAI token (replace with your actual token)
    token = os.environ.get("NAI_TOKEN")

    # Initialize client with token authentication
    client = NovelAI(token=token)

    try:
        # Load an image file and encode it as base64
        image_path = "../input/example_image.png"  # Replace with your image path

        # Remove the background from the image
        result = await client.background_removal(image_path)

        # Save the result
        os.makedirs("../output", exist_ok=True)
        result.save("../output", "bg_removed_result.png")
        print("Background removed image saved as output/bg_removed_result.png")

    finally:
        # Close the client
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
