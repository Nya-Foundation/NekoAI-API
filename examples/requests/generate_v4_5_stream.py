#!/usr/bin/env python3
"""Stream a V4.5 generation in real time, watching each denoising step.

Usage: uvrun examples/requests/generate_v4_5_stream.py
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os

from nekoai import EventType, Model, NovelAI, Resolution


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        async for event in client.generate_image_stream(
            prompt="1girl, silver hair, blue eyes, white dress, flower garden",
            model=Model.V4_5,
            res_preset=Resolution.NORMAL_PORTRAIT,
            seed=424242,
        ):
            if event.event_type == EventType.FINAL:
                event.image.save("output", "stream_final.png")
                print("Saved output/stream_final.png")
            else:
                print(f"step {event.step_ix} (sigma={event.sigma:.2f})", end="\r")
                # Uncomment to keep every intermediate step:
                # event.image.save("output", f"stream_step_{event.step_ix:02d}.jpg")


if __name__ == "__main__":
    asyncio.run(main())
