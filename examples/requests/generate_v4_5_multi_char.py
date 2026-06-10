#!/usr/bin/env python3
"""Generate an image with multiple positioned characters (V4.5).

Usage: uvrun examples/requests/generate_v4_5_multi_char.py
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os

from nekoai import CharacterPrompt, Model, NovelAI, PositionCoords, Resolution


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        images = await client.generate_image(
            prompt="two people standing in a park, sunny day",
            model=Model.V4_5,
            res_preset=Resolution.NORMAL_LANDSCAPE,
            seed=424242,
            characterPrompts=[
                CharacterPrompt(
                    prompt="girl, red hair, red dress",
                    uc="bad hands, bad anatomy",
                    center=PositionCoords(x=0.3, y=0.5),
                ),
                CharacterPrompt(
                    prompt="boy, blue hair, blue suit",
                    uc="bad hands, bad anatomy",
                    center=PositionCoords(x=0.7, y=0.5),
                ),
            ],
        )

        for image in images:
            image.save("output", "multi_character.png")
            print(f"Saved output/{image.filename}")


if __name__ == "__main__":
    asyncio.run(main())
