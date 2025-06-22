#!/usr/bin/env python3
"""
Example script for generating an image with NovelAI API using the V4.5 curated model.
Authentication is done with a direct access token.
"""
import asyncio
import os

from nekoai import NovelAI
from nekoai.constant import Model, Resolution, Sampler
from nekoai.types import EventType, MsgpackEvent


async def main():
    # Use your NAI token (replace with your actual token)
    token = os.environ.get("NAI_TOKEN")

    # Initialize client with token authentication
    client = NovelAI(token=token, verbose=True)

    try:
        async for event in await client.generate_image(
            prompt="1girl, cute",
            negative_prompt="1234",
            ucPreset=3,
            scale=5,
            seed="3417044607",
            steps=30,
            n_samples=1,
            model=Model.V4_5,
            height=936,
            width=1400,
            sampler=Sampler.EULER_ANC,
            stream=True,
        ):
            event: MsgpackEvent
            os.makedirs("../output", exist_ok=True)

            if event.event_type == EventType.INTERMEDIATE:
                event.image.save(
                    "../output", f"image_{event.samp_ix}_step_{event.step_ix:02d}.jpg"
                )
            elif event.event_type == EventType.FINAL:
                event.image.save("../output", f"image_{event.samp_ix}_result.png")

    finally:
        # Close the client
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
