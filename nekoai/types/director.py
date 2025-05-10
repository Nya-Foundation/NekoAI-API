from typing import Literal, Optional

from pydantic import BaseModel, Field

from .constant import EmotionLevel, EmotionOptions


class DirectorRequest(BaseModel):
    """
    Request model for NovelAI's Director tools.

    Parameters
    ----------
    req_type: `DirectorTools` or `str`
        The type of director tool to use
    width: `int`
        Width of the image in pixels
    height: `int`
        Height of the image in pixels
    image: `str`
        Base64-encoded image
    prompt: `str`, optional
        Text prompt needed for certain tools like emotion
    defry: `int`, optional
        Defry option for certain tools, defaults to 0
    """

    req_type: str = Field(..., description="Director tool type")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    image: str = Field(..., description="Base64-encoded image")
    prompt: Optional[str] = Field(
        default="", description="Optional text prompt for tools like emotion"
    )
    defry: int = Field(default=0, description="Optional defry parameter")

    class Config:
        use_enum_values = True


class LineArtRequest(DirectorRequest):
    """Director request for line art tool"""

    req_type: Literal["lineart"] = "lineart"


class SketchRequest(DirectorRequest):
    """Sketch request for line art tool"""

    req_type: Literal["sketch"] = "sketch"


class BackgroundRemovalRequest(DirectorRequest):
    """Director request for background removal tool"""

    req_type: Literal["bg-removal"] = "bg-removal"


class DeclutterRequest(DirectorRequest):
    """Director request for declutter tool"""

    req_type: Literal["declutter"] = "declutter"


class ColorizeRequest(DirectorRequest):
    """Director request for colorize tool"""

    req_type: Literal["colorize"] = "colorize"

    @classmethod
    def create(
        cls,
        width: int,
        height: int,
        image: str,
        prompt: Optional[str] = "",
        defry: int = 0,
    ) -> "ColorizeRequest":
        """
        Factory method to create an colorize request.

        Parameters
        ----------
        width: int
            Image width
        height: int
            Image height
        image: str
            Base64-encoded image
        prompt: str
            Addtional prompt for the request
        defry: Strength level
            Strength level of the colorize, defaults to 0

        Returns
        -------
        EmotionRequest
            Ready-to-use emotion request object
        """

        return cls(width=width, height=height, image=image, prompt=prompt, defry=defry)


class EmotionRequest(DirectorRequest):
    """
    Director request for emotion tool.

    The prompt field should contain emotion options in the format:
    "{target_emotion};;{original_emotion},"

    For example: "angry;;happy,"
    """

    req_type: Literal["emotion"] = "emotion"

    @classmethod
    def create(
        cls,
        width: int,
        height: int,
        image: str,
        emotion: EmotionOptions,
        prompt: Optional[str] = "",
        emotion_level: EmotionLevel = EmotionLevel.NORMAL,
    ) -> "EmotionRequest":
        """
        Factory method to create an emotion request.

        Parameters
        ----------
        width: int
            Image width
        height: int
            Image height
        image: str
            Base64-encoded image
        motion: EmotionOptions
            The target emotion to apply
        prompt: str
            Addtional prompt for the request
        emotion_level: EmotionLevel, optional
            Strength level of the emotion, defaults to NORMAL

        Returns
        -------
        EmotionRequest
            Ready-to-use emotion request object
        """
        final_prompt = f"{emotion.value};;"

        # Add addtional prompt if provided
        if prompt:
            final_prompt += f"{prompt},"

        defry = emotion_level.value

        return cls(
            width=width, height=height, image=image, prompt=final_prompt, defry=defry
        )
