#!/usr/bin/env python3
"""Generate a ControlNet condition mask from an image via /ai/annotate-image.

Note: generating images guided by these masks (`controlnet_condition` /
`controlnet_model`) was a V1/V2-era feature — V3 and later models do not
support ControlNet. The annotators themselves still work and are useful as
preprocessing (edge maps, depth maps, etc.).

Usage: uvrun examples/requests/annotate_image.py [path/to/image]
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os
import sys

from nekoai import Controlnet, NovelAI

IMAGE = sys.argv[1] if len(sys.argv) > 1 else "examples/input/example_image.png"


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        for annotator in (Controlnet.SCRIBBLER, Controlnet.FORMLOCK):
            mask = await client.annotate_image(IMAGE, model=annotator)
            name = f"annotate_{annotator.name.lower()}.png"
            mask.save("output", name)
            print(f"Saved output/{name}")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
