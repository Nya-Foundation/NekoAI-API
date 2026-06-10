#!/usr/bin/env python3
"""Get tag completions for a partial tag.

Usage: uvrun examples/requests/suggest_tags.py [partial tag]
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import os
import sys

from nekoai import Model, NovelAI

QUERY = sys.argv[1] if len(sys.argv) > 1 else "blue hai"


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        tags = await client.suggest_tags(QUERY, model=Model.V4_5)
        for tag in tags:
            print(f"{tag.get('tag'):30} count={tag.get('count')}")


if __name__ == "__main__":
    asyncio.run(main())
