#!/usr/bin/env python3
"""Generate a ControlNet condition mask, then use it to guide a generation.

Usage: uvrun examples/requests/annotate_image.py [path/to/image]
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import base64
import os
import sys

from nekoai import Controlnet, Model, NovelAI, Resolution

IMAGE = sys.argv[1] if len(sys.argv) > 1 else "examples/input/example_image.png"


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        # Step 1: annotate the source image into a condition mask
        mask = await client.annotate_image(IMAGE, model=Controlnet.SCRIBBLER)
        mask.save("output", "annotate_scribbler.png")
        print("Saved output/annotate_scribbler.png")

        # Step 2: generate guided by the condition mask
        images = await client.generate_image(
            prompt="1girl, cute, watercolor style",
            model=Model.V3,  # ControlNet is a V3 feature
            res_preset=Resolution.NORMAL_PORTRAIT,
            controlnet_model=Controlnet.SCRIBBLER,
            controlnet_condition=base64.b64encode(mask.data).decode("utf-8"),
        )
        for image in images:
            image.save("output", "controlnet_result.png")
            print(f"Saved output/{image.filename}")


if __name__ == "__main__":
    asyncio.run(main())
