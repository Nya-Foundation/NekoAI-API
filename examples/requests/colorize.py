#!/usr/bin/env python3
"""
Example script for using the colorize director tool with NovelAI API.
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
        # Load a line art image file and encode it as base64
        image_path = "../input/lineart.png"  # Replace with your line art image path

        # Colorize the line art
        result = await client.colorize(image=image_path)

        # Save the result
        os.makedirs("../output", exist_ok=True)
        result.save("../output", "colorized_result.png")
        print("Colorized image saved as ../output/colorized_result.png")

    finally:
        # Close the client
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
