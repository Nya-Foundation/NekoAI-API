#!/usr/bin/env python3
"""Show subscription tier, Anlas balance and account data.

Usage: uvrun examples/requests/account_info.py
Requires the NAI_TOKEN environment variable (e.g. via .env).
"""

import asyncio
import json
import os

from nekoai import NovelAI


async def main():
    async with NovelAI(token=os.environ["NAI_TOKEN"]) as client:
        subscription = await client.get_subscription()
        print(json.dumps(subscription, indent=2))

        steps = subscription.get("trainingStepsLeft", {})
        if isinstance(steps, dict):
            anlas = steps.get("fixedTrainingStepsLeft", 0) + steps.get(
                "purchasedTrainingSteps", 0
            )
            print(f"\nAnlas balance: {anlas}")


if __name__ == "__main__":
    asyncio.run(main())
