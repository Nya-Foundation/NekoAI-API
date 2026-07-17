"""Command-line interface for NekoAI-API.

Authentication is resolved in this order:
1. --token flag
2. NAI_TOKEN environment variable
3. --username / --password flags
"""

import argparse
import asyncio
import json
import sys

from ._version import __version__
from .client import TOKEN_ENV, NovelAI
from .constant import Action, Controlnet, Model, Resolution, Sampler, TextModel
from .exceptions import NovelAIError
from .imaging import parse_image
from .types import EmotionLevel, EmotionOptions, EventType

# generate/inpaint model ids differ; map each base model to its inpainting variant
INPAINT_VARIANTS = {
    Model.V4_5: Model.V4_5_INP,
    Model.V4_5_CUR: Model.V4_5_CUR_INP,
    Model.V4: Model.V4_INP,
    Model.V4_CUR: Model.V4_CUR_INP,
    Model.V3: Model.V3_INP,
    Model.FURRY: Model.FURRY_INP,
}


def _resolve_enum(enum_cls, value: str):
    """Resolve an enum from its member name (e.g. 'v4_5') or value (e.g. 'nai-diffusion-4-5-full')."""
    try:
        return enum_cls[value.upper().replace("-", "_")]
    except KeyError:
        pass
    try:
        return enum_cls(value)
    except ValueError:
        choices = ", ".join(m.name.lower() for m in enum_cls)
        raise SystemExit(
            f"error: invalid {enum_cls.__name__} {value!r} (choose from: {choices})"
        ) from None


def _make_client(args: argparse.Namespace) -> NovelAI:
    kwargs = {"host": args.host} if args.host else {}
    try:
        if args.username and args.password:
            return NovelAI(username=args.username, password=args.password, **kwargs)
        # NovelAI falls back to $NAI_TOKEN when token is None
        return NovelAI(token=args.token, **kwargs)
    except ValueError:
        raise SystemExit(
            f"error: no credentials. Pass --token, set ${TOKEN_ENV}, or pass --username/--password"
        ) from None


def _add_auth_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("authentication")
    group.add_argument("--token", "-t", help=f"access token (or set ${TOKEN_ENV})")
    group.add_argument("--username", "-u", help="NovelAI username")
    group.add_argument("--password", "-p", help="NovelAI password")
    group.add_argument("--host", help="custom base URL for image endpoints")


def _add_output_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output", "-o", default="output", help="output directory (default: output)"
    )


async def _cmd_login(args) -> None:
    async with NovelAI(username=args.username, password=args.password) as client:
        print(await client.get_access_token())


async def _cmd_generate(args) -> None:
    params = {
        "prompt": args.prompt,
        "model": _resolve_enum(Model, args.model),
        "n_samples": args.count,
    }
    if args.size:
        try:
            width, height = (int(v) for v in args.size.lower().split("x"))
            params["width"], params["height"] = width, height
        except ValueError:
            params["res_preset"] = _resolve_enum(Resolution, args.size)
    if args.negative_prompt:
        params["negative_prompt"] = args.negative_prompt
    if args.seed is not None:
        params["seed"] = args.seed
    if args.steps is not None:
        params["steps"] = args.steps
    if args.sampler:
        params["sampler"] = _resolve_enum(Sampler, args.sampler)

    if args.image:
        params["image"] = parse_image(args.image)[2]
        params["action"] = Action.IMG2IMG
        if args.strength is not None:
            params["strength"] = args.strength
        if args.noise is not None:
            params["noise"] = args.noise
    if args.mask:
        if not args.image:
            raise SystemExit("error: --mask requires --image")
        params["mask"] = parse_image(args.mask)[2]
        params["action"] = Action.INPAINT
        params["model"] = INPAINT_VARIANTS.get(params["model"], params["model"])
    if args.reference_image:
        params["reference_image_multiple"] = [
            parse_image(ref)[2] for ref in args.reference_image
        ]

    async with _make_client(args) as client:
        if args.stream:
            async for event in client.generate_image_stream(**params):
                if event.event_type == EventType.FINAL:
                    event.image.save(args.output)
                    print(f"saved {args.output}/{event.image.filename}")
                else:
                    print(f"step {event.step_ix}", end="\r", flush=True)
        else:
            for image in await client.generate_image(**params):
                image.save(args.output)
                print(f"saved {args.output}/{image.filename}")


async def _cmd_text(args) -> None:
    params = {"max_length": args.max_length, "temperature": args.temperature}
    model = _resolve_enum(TextModel, args.model)
    async with _make_client(args) as client:
        if args.stream:
            async for token in client.generate_text_stream(
                args.prompt, model=model, **params
            ):
                print(token, end="", flush=True)
            print()
        else:
            print(await client.generate_text(args.prompt, model=model, **params))


async def _cmd_upscale(args) -> None:
    async with _make_client(args) as client:
        image = await client.upscale(args.image, scale=args.scale)
        image.save(args.output)
        print(f"saved {args.output}/{image.filename}")


async def _cmd_tool(args) -> None:
    async with _make_client(args) as client:
        if args.tool == "colorize":
            image = await client.colorize(
                args.image, prompt=args.prompt or "", defry=args.defry
            )
        elif args.tool == "emotion":
            if not args.emotion:
                raise SystemExit("error: --emotion is required for the emotion tool")
            image = await client.change_emotion(
                args.image,
                emotion=_resolve_enum(EmotionOptions, args.emotion),
                prompt=args.prompt or "",
                emotion_level=EmotionLevel(args.emotion_level),
            )
        elif args.tool == "annotate":
            if not args.controlnet:
                raise SystemExit(
                    "error: --controlnet is required for the annotate tool"
                )
            image = await client.annotate_image(
                args.image, model=_resolve_enum(Controlnet, args.controlnet)
            )
        else:
            method = {
                "lineart": client.lineart,
                "sketch": client.sketch,
                "bg-removal": client.background_removal,
                "declutter": client.declutter,
            }[args.tool]
            image = await method(args.image)
        image.save(args.output)
        print(f"saved {args.output}/{image.filename}")


async def _cmd_tags(args) -> None:
    async with _make_client(args) as client:
        tags = await client.suggest_tags(
            args.prompt, model=_resolve_enum(Model, args.model)
        )
        for tag in tags:
            print(f"{tag.get('tag')}\t{tag.get('count', '')}")


async def _cmd_subscription(args) -> None:
    async with _make_client(args) as client:
        print(json.dumps(await client.get_subscription(), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nekoai", description="NovelAI image generation CLI"
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    login = subparsers.add_parser(
        "login", help="exchange credentials for an access token"
    )
    login.add_argument("username", help="NovelAI username")
    login.add_argument("password", help="NovelAI password")
    login.set_defaults(func=_cmd_login)

    generate = subparsers.add_parser("generate", help="generate images from a prompt")
    generate.add_argument("prompt", help="text prompt")
    generate.add_argument(
        "--model", "-m", default="v4_5", help="model name or id (default: v4_5)"
    )
    generate.add_argument(
        "--size",
        "-s",
        help="WxH (e.g. 832x1216) or a preset name (e.g. normal_portrait)",
    )
    generate.add_argument("--negative-prompt", "-N", help="undesired content")
    generate.add_argument("--seed", type=int, help="random seed")
    generate.add_argument("--steps", type=int, help="sampling steps")
    generate.add_argument("--sampler", help="sampler name (e.g. euler_anc)")
    generate.add_argument(
        "--count", "-n", type=int, default=1, help="number of images (default: 1)"
    )
    generate.add_argument("--image", "-i", help="base image for img2img/inpainting")
    generate.add_argument("--mask", help="inpainting mask (white = area to repaint)")
    generate.add_argument(
        "--strength", type=float, help="img2img strength 0.01-0.99 (default: 0.3)"
    )
    generate.add_argument("--noise", type=float, help="img2img noise 0-0.99")
    generate.add_argument(
        "--reference-image",
        action="append",
        help="vibe transfer reference image (repeatable)",
    )
    generate.add_argument(
        "--stream", action="store_true", help="show V4/V4.5 generation progress"
    )
    _add_output_arg(generate)
    _add_auth_args(generate)
    generate.set_defaults(func=_cmd_generate)

    upscale = subparsers.add_parser("upscale", help="upscale an image")
    upscale.add_argument("image", help="path to image file")
    upscale.add_argument(
        "--scale", type=int, default=4, choices=(2, 4), help="upscale factor"
    )
    _add_output_arg(upscale)
    _add_auth_args(upscale)
    upscale.set_defaults(func=_cmd_upscale)

    tool = subparsers.add_parser("tool", help="run a Director or annotation tool")
    tool.add_argument(
        "tool",
        choices=(
            "lineart",
            "sketch",
            "bg-removal",
            "declutter",
            "colorize",
            "emotion",
            "annotate",
        ),
        help="tool to run",
    )
    tool.add_argument("image", help="path to image file")
    tool.add_argument("--prompt", help="extra prompt (colorize/emotion)")
    tool.add_argument(
        "--defry", type=int, default=0, help="colorize strength (default: 0)"
    )
    tool.add_argument("--emotion", help="target emotion (e.g. happy)")
    tool.add_argument(
        "--emotion-level",
        type=int,
        default=0,
        choices=range(6),
        help="emotion strength, 0 (normal) to 5 (weakest)",
    )
    tool.add_argument("--controlnet", help="ControlNet annotator (e.g. scribbler)")
    _add_output_arg(tool)
    _add_auth_args(tool)
    tool.set_defaults(func=_cmd_tool)

    text = subparsers.add_parser("text", help="generate a text continuation")
    text.add_argument("prompt", help="input text to continue")
    text.add_argument(
        "--model", "-m", default="erato", help="text model (default: erato)"
    )
    text.add_argument(
        "--max-length", type=int, default=100, help="max tokens (default: 100)"
    )
    text.add_argument(
        "--temperature", type=float, default=1.0, help="sampling temperature"
    )
    text.add_argument("--stream", action="store_true", help="stream tokens as SSE")
    _add_auth_args(text)
    text.set_defaults(func=_cmd_text)

    tags = subparsers.add_parser("tags", help="suggest completions for a partial tag")
    tags.add_argument("prompt", help="partial tag")
    tags.add_argument("--model", "-m", default="v4_5", help="model (default: v4_5)")
    _add_auth_args(tags)
    tags.set_defaults(func=_cmd_tags)

    subscription = subparsers.add_parser(
        "subscription", help="show subscription info and Anlas balance"
    )
    _add_auth_args(subscription)
    subscription.set_defaults(func=_cmd_subscription)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        asyncio.run(args.func(args))
    except NovelAIError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
