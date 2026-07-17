from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DirectorRequest(BaseModel):
    """
    Request model for NovelAI's Director tools (/ai/augment-image).

    Parameters
    ----------
    req_type: `str`
        The type of director tool to use
    width: `int`
        Width of the image in pixels
    height: `int`
        Height of the image in pixels
    image: `str`
        Base64-encoded image
    prompt: `str`, optional
        Text prompt needed for certain tools like colorize and emotion
    defry: `int`, optional
        Strength option for certain tools, defaults to 0
    """

    req_type: str = Field(..., description="Director tool type")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    image: str = Field(..., description="Base64-encoded image")
    prompt: str | None = Field(
        default="", description="Optional text prompt for tools like emotion"
    )
    defry: int = Field(default=0, description="Optional strength parameter")

    model_config = ConfigDict(use_enum_values=True)


class LineArtRequest(DirectorRequest):
    """Director request for the line art tool."""

    req_type: Literal["lineart"] = "lineart"


class SketchRequest(DirectorRequest):
    """Director request for the sketch tool."""

    req_type: Literal["sketch"] = "sketch"


class BackgroundRemovalRequest(DirectorRequest):
    """Director request for the background removal tool."""

    req_type: Literal["bg-removal"] = "bg-removal"


class DeclutterRequest(DirectorRequest):
    """Director request for the declutter tool."""

    req_type: Literal["declutter"] = "declutter"


class ColorizeRequest(DirectorRequest):
    """Director request for the colorize tool."""

    req_type: Literal["colorize"] = "colorize"


class EmotionRequest(DirectorRequest):
    """
    Director request for the emotion tool.

    The prompt field must contain the target emotion and optional extra prompt
    in the format "{emotion};;{extra_prompt}," and defry holds the EmotionLevel.
    """

    req_type: Literal["emotion"] = "emotion"
