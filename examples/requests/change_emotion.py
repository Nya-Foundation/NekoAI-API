#!/usr/bin/env python3
"""Change a character's emotion with NovelAI's Director tool.

Usage: uvrun examples/requests/change_emotion.py [path/to/image]
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os
import sys

from nekoai import EmotionLevel, EmotionOptions, NovelAI

IMAGE = sys.argv[1] if len(sys.argv) > 1 else "examples/input/example_image.png"


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        result = await client.change_emotion(
            IMAGE,
            emotion=EmotionOptions.HAPPY,
            emotion_level=EmotionLevel.NORMAL,
        )
        result.save("output", "emotion_happy.png")
        print("Saved output/emotion_happy.png")


if __name__ == "__main__":
    asyncio.run(main())
