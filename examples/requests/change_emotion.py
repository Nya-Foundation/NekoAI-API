#!/usr/bin/env python3
"""
Example script for using the emotion change director tool with NovelAI API.
Authentication is done with a direct access token.
"""

import asyncio
import os

from nekoai import NovelAI
from nekoai.types import EmotionLevel, EmotionOptions


async def main():
    # Use your NAI token (replace with your actual token)
    token = os.environ.get("NAI_TOKEN")

    # Initialize client with token authentication
    client = NovelAI(token=token)

    try:
        # Load an image file and encode it as base64
        image_path = "../input/example_image.png"  # Replace with your image path

        # Declutter the image
        result = await client.declutter(image=image_path)

        # Change the emotion in the image
        # Going from NEUTRAL to HAPPY emotion with NORMAL emotion level
        result = await client.change_emotion(
            image=image_path,
            emotion=EmotionOptions.ANGRY,
            prompt="happy",
            emotion_level=EmotionLevel.NORMAL,
        )

        # Save the result
        os.makedirs("../output", exist_ok=True)
        result.save("../output", "angry_emotion_result.png")
        print("Emotion changed image saved as ../output/angry_emotion_result.png")

    finally:
        # Close the client
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
