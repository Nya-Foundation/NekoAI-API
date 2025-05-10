import asyncio
import sys
from argparse import ArgumentParser

from .client import NovelAI


async def async_main():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    # Login command
    login_parser = subparsers.add_parser(
        "login", help="Login to NovelAI to get your access token"
    )
    login_parser.add_argument("username", help="NovelAI username")
    login_parser.add_argument("password", help="NovelAI password")

    args = parser.parse_args()

    if args.command == "login":
        client = NovelAI(username=args.username, password=args.password)
        await client.init()

        access_token = await client.get_access_token()
        print(access_token)
    else:
        parser.print_help()


def main():
    """
    Synchronous entry point for the package.
    This function is used when the package is run as a script through the entry point.
    """
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
