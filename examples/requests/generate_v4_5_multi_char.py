#!/usr/bin/env python3
"""
Example script for generating an image with NovelAI API using the V4.5 curated model
with multiple characters. Authentication is done with a direct access token.
"""

import asyncio
import os

from nekoai import NovelAI
from nekoai.constant import Model, Resolution, Sampler
from nekoai.types import CharacterPrompt, PositionCoords


async def main():
    # Use your NAI token (replace with your actual token)
    token = os.environ.get("NAI_TOKEN")

    # Initialize client with token authentication
    client = NovelAI(token=token)

    try:
        # Create character prompts for multiple characters
        character_prompts = [
            CharacterPrompt(
                prompt="girl, klee_(genshin_impact)",
                uc="lowres, aliasing,",
                center=PositionCoords(x=0.3, y=0.3),
                enabled=True,
            ),
            CharacterPrompt(
                prompt="girl, qiqi_(genshin_impact)",
                uc="lowres, aliasing,",
                center=PositionCoords(x=0.7, y=0.7),
                enabled=True,
            ),
        ]

        # Generate an image with V4.5 curated model and multiple characters
        images = await client.generate_image(
            prompt="2 girls, 2 girls, playing together",
            model=Model.V4_5_CUR,
            res_preset=Resolution.NORMAL_PORTRAIT,
            steps=23,
            scale=5,
            sampler=Sampler.EULER_ANC,
            characterPrompts=character_prompts,
        )

        # Save the generated image(s)
        for i, image in enumerate(images):
            # Create output directory if it doesn't exist
            os.makedirs("../output", exist_ok=True)
            # Save the image
            image.save("../output", f"v4_5_multi_char_result_{i}.png")
            print(f"Image saved as output/v4_5_multi_char_result_{i}.png")

    finally:
        # Close the client
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
