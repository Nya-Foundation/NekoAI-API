#!/usr/bin/env python3
"""Generate a text continuation with Erato, then stream one token by token.

Usage: uv run examples/requests/generate_text.py
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os

from nekoai import NovelAI, TextModel


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        prompt = "The dragon circled the tower once more,"
        output = await client.generate_text(
            prompt, model=TextModel.ERATO, max_length=60
        )
        print(f"{prompt}{output}\n")

        async for token in client.generate_text_stream(
            "Once upon a time,", model=TextModel.KAYRA, max_length=40
        ):
            print(token, end="", flush=True)
        print()


if __name__ == "__main__":
    asyncio.run(main())
