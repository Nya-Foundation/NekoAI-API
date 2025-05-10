from typing import List

from pydantic import BaseModel, Field, model_validator


class PositionCoords(BaseModel):
    """
    Represents the position coordinates for character placement.

    Parameters
    ----------
    x: float
        X coordinate [0.1-0.9], center position horizontally
    y: float
        Y coordinate [0.1-0.9], center position vertically
    """

    x: float = Field(0.5, ge=0.1, le=0.9)
    y: float = Field(0.5, ge=0.1, le=0.9)


class CharacterCaption(BaseModel):
    """
    Character caption information for V4 prompts.

    Parameters
    ----------
    char_caption: str
        The character description prompt
    centers: List[PositionCoords]
        List of coordinate positions for this character
    """

    char_caption: str
    centers: List[PositionCoords] = Field(default_factory=lambda: [PositionCoords()])


class CharacterPrompt(BaseModel):
    """
    Represents a character prompt used in NovelAI V4.5.

    Parameters
    ----------
    prompt: str
        Character-specific prompt
    uc: str
        Undesired content for this specific character
    center: PositionCoords
        Position coordinates for character placement
    enabled: bool
        Whether this character prompt is enabled
    """

    prompt: str
    uc: str = "lowres, aliasing,"
    center: PositionCoords = Field(default_factory=PositionCoords)
    enabled: bool = True

    @model_validator(mode="after")
    def deduplicate_tags(self) -> "CharacterPrompt":
        """
        Deduplicate tags in the prompt and uc fields
        """
        if self.prompt:
            self.prompt = self._deduplicate(self.prompt)
        if self.uc:
            self.uc = self._deduplicate(self.uc)
        return self

    def _deduplicate(self, text: str) -> str:
        """Helper method to deduplicate tags in a string"""
        if not text:
            return text

        tags = [tag.strip() for tag in text.split(",")]
        tags = [tag for tag in tags if tag]
        lowercase_to_original = {}

        for tag in tags:
            lowercase = tag.lower()
            if lowercase not in lowercase_to_original:
                lowercase_to_original[lowercase] = tag

        return ", ".join(lowercase_to_original.values())


class V4PromptFormat(BaseModel):
    """
    V4 format for prompts with multi-character support.

    Parameters
    ----------
    caption: V4CaptionFormat
        Caption object containing base and character captions
    use_coords: bool
        Whether to use coordinate positioning
    use_order: bool
        Whether the order of characters matters
    """

    caption: "V4CaptionFormat"
    use_coords: bool = False
    use_order: bool = True


class V4NegativePromptFormat(BaseModel):
    """
    V4 format for negative prompts.

    Parameters
    ----------
    caption: V4CaptionFormat
        Caption object containing base and character captions
    use_coords: bool
        Whether to use coordinate positioning
    legacy_uc: bool
        Whether to use legacy undesired content format
    """

    caption: "V4CaptionFormat"
    legacy_uc: bool = False


class V4CaptionFormat(BaseModel):
    """
    Caption format for V4 prompts.

    Parameters
    ----------
    base_caption: str
        The base prompt
    char_captions: List[CharacterCaption]
        List of character-specific captions
    """

    base_caption: str
    char_captions: List[CharacterCaption] = Field(default_factory=list)
