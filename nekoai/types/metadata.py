import math
import random
from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from nekoai.constant import Action, Controlnet, Model, Noise, Resolution, Sampler
from nekoai.types.parameters import (
    CharacterCaption,
    CharacterPrompt,
    V4CaptionFormat,
    V4NegativePromptFormat,
    V4PromptFormat,
)


class Metadata(BaseModel):
    """
    Serve as `input` and `parameters` in the request body of the /ai/generate-image endpoint.

    Except for the provided fields, other arbitrary fields can also be added into parameters,
    which will be present in the metadata of the image, like qualityToggle or ucPreset.
    These fields are mainly for the website to remember some key information when importing the image.

    Parameters
    ----------
    | General
    prompt: `str`
        Text prompt to generate image from. Serve as `input` in the request body.
        Refer to https://docs.novelai.net/image/tags.html, https://docs.novelai.net/image/strengthening-weakening.html
    model: `nekoai.Model`, optional
        Model to use for the generation. Serve as `model` in the request body. Refer to `nekoai.constant.Model`
    action: `nekoai.Action`, optional
        Action to perform. Serve as `action` in the request body. Refer to `nekoai.consts.Action`
    res_preset: `nekoai.Resolution`, optional
        Resolution preset to use for the image. Will be overridden by `width` and `height`, and won't be included in the request

    | Note: all fields below that are not in "General" section will together serve as `parameters` in the request body

    | Prompt
    negative_prompt: `str`, optional
        Refer to https://docs.novelai.net/image/undesiredcontent.html
    qualityToggle: `bool`, optional
        Whether to automatically append quality tags to the prompt. Refer to https://docs.novelai.net/image/qualitytags.html
    ucPreset: `int`, optional
        Preset value of undisired content. Refer to https://docs.novelai.net/image/undesiredcontent.html
        Range: 0-3, 0: Heavy, 1: Light, 2: Human Focus, 3: None

    | Image settings
    width: `int`, optional
        Width of the image to generate in pixels, will override `res_preset` if provided
    height: `int`, optional
        Height of the image to generate in pixels, will override `res_preset` if provided
    n_samples: `int`, optional
        Number of images to return. The maximum value is 8 up to 360,448 px, 6 up to 409,600 px,
        4 up to 1,310,720 px, 2 up to 1,572,864 px, and 1 up to the max size

    | AI settings
    steps: `int`, optional
        Refer to https://docs.novelai.net/image/stepsguidance.html
    scale: `float`, optional
        Value of prompt guidance. Refer to https://docs.novelai.net/image/stepsguidance.html
    dynamic_thresholding: `bool`, optional
        Whether to enable descrisper. Refer to https://docs.novelai.net/image/stepsguidance.html#decrisper
    seed: `int`, optional
        Random seed to use for the image (between 0 and 4294967295), defaults to 0
        Seed 0 means that a random seed will be chosen, but not set in the metadata (so giving a seed yourself is important)
        Note: When generating multiple images, each consecutive image adds 1 to the seed parameter.
        This means it can go beyond the limit of 4294967295, making it unreproducible with a single generation
    extra_noise_seed: `int`, optional
        Unknown, but seems to be fulfill the same role as seed
    sampler: `nekoai.Sampler`, optional
        Refer to https://docs.novelai.net/image/sampling.html.
        The full list of samplers is (some may not work due to being deprecated): "k_lms", "k_euler",
        "k_euler_ancestral", "k_heun", "plms", "ddim", "nai_smea", "nai_smea_dyn", "k_dpmpp_2m",
        "k_dpmpp_2s_ancestral", "k_dpmpp_sde", "k_dpm_2", "k_dpm_2_ancestral", "k_dpm_adaptive", "k_dpm_fast"
    sm: `bool`, optional, legacy
        Whether to enable SMEA. Refer to https://docs.novelai.net/image/sampling.html#special-samplers-smea--smea-dyn
        Must set false when inpainting. For img2img, setting to true will not cause error but generated image will be blurry
    sm_dyn: `bool`, optional, legacy
        Whether to enable SMEA DYN (SMEA needs to be enabled to enable SMEA DYN).
        Refer to https://docs.novelai.net/image/sampling.html#special-samplers-smea--smea-dyn
    cfg_rescale: `float`, optional
        Range: 0-1, Prompt guidance rescale, refer to https://docs.novelai.net/image/stepsguidance.html#prompt-guidance-rescale
    noise_schedule: `Noise`, optional
        Noise schedule, choose from "native", "karras", "exponential", and "polyexponential"

    | img2img
    image: `str`, optional
        Base64-encoded image for Image to Image
    strength: `float`, optional
        Range: 0.01-0.99, refer to https://docs.novelai.net/image/strengthnoise.html
    noise: `float`, optional
        Range: 0-0.99, refer to https://docs.novelai.net/image/strengthnoise.html
    controlnet_strength: `float`, optional
        Range: 0.1-2, controls how much influence the ControlNet has on the image
    controlnet_condition: `str`, optional
        Base64-encoded PNG ControlNet mask retrieved from the /ai/annotate-image endpoint
    controlnet_model: `nekoai.Controlnet`, optional
        Control tool to use for the ControlNet. Note: V3 model does not support control tools
        Palette Swap is "hed", Form Lock is "depth", Scribbler is "scribble", Building Control is "mlsd", is Landscaper is "seg"

    | Inpaint
    add_original_image: `bool`, optional
        Refer to https://docs.novelai.net/image/inpaint.html#overlay-original-image
    mask: `str`, optional
        Base64-encoded black and white image to use as a mask for inpainting
        White is the area to inpaint and black is the rest

    | Vibe Transfer
    reference_image_multiple: `list[str]`, optional
        List of base64-encoded images to use as base images for Vibe Transfer
    reference_information_extracted_multiple: `list[float]`, optional
        List of floats from range 0-1, should be the same length as `reference_image_multiple` and follow the same order
        Refer to https://docs.novelai.net/.image/vibetransfer.html#information-extracted
    reference_strength_multiple: `list[float]`, optional
        List of floats from range 0-1, should be the same length as `reference_image_multiple` and follow the same order
        Refer to https://docs.novelai.net/.image/vibetransfer.html#reference-strength
        The strength AI uses to emulate visual cues, such as stylistic aspects, colors etc., from the given input image

    | V4/V4.5 specific fields
    params_version: `int`, optional
        Version of the parameters, defaults to 1 for V3 models, 3 for V4/V4.5 models
    autoSmea: `bool`, optional
        Automatically enable SMEA for V4/V4.5 models (replaces sm and sm_dyn)
    characterPrompts: `List[CharacterPrompt]`, optional
        List of character prompts for multi-character generation in V4.5
    v4_prompt: `V4PromptFormat`, optional
        V4/V4.5 format for base and character prompts
    v4_negative_prompt: `V4NegativePromptFormat`, optional
        V4/V4.5 format for negative prompts
    skip_cfg_above_sigma: `int|None`, optional
        Parameter for V4/V4.5 models
    use_coords: `bool`, optional
        Whether to use coordinates for character placement in V4/V4.5
    legacy_uc: `bool`, optional
        Legacy undesired content setting for V4/V4.5
    normalize_reference_strength_multiple: `bool`, optional
        Whether to normalize reference strengths for vibe transfer in V4/V4.5
    deliberate_euler_ancestral_bug: `bool`, optional
        Enables the deliberate bug in euler ancestral sampler for V4.5, default to False
    prefer_brownian: `bool`, optional
        Prefer brownian noise for V4.5, set when the sampler is k_euler_ancestral

    | Misc
    legacy: `bool`, optional
        Defaults to False
    legacy_v3_extend: `bool`, optional
        Defaults to False
    """

    # General
    # Fields in this section will be excluded from the output of model_dump during serialization
    prompt: str = Field(exclude=True)
    model: Model = Field(default=Model.V3, exclude=True)
    action: Action = Field(default=Action.GENERATE, exclude=True)
    res_preset: Resolution = Field(default=Resolution.NORMAL_SQUARE, exclude=True)

    # Prompt
    negative_prompt: str = ""
    qualityToggle: bool = True
    ucPreset: Literal[0, 1, 2, 3] = 0

    # Image settings
    width: Annotated[int, Field(ge=64, le=49152)] | None = None
    height: Annotated[int, Field(ge=64, le=49152)] | None = None
    n_samples: Annotated[int, Field(ge=1, le=8)] = 1

    # AI settings
    steps: int = Field(default=28, ge=1, le=50)
    scale: float = Field(default=6.0, ge=0, le=10, multiple_of=0.1)
    dynamic_thresholding: bool = False
    seed: int = Field(
        default_factory=lambda: random.randint(0, 4294967295 - 7),
        gt=0,
        le=4294967295 - 7,
    )
    extra_noise_seed: Annotated[int, Field(gt=0, le=4294967295 - 7)] | None = None
    sampler: Sampler = Sampler.EULER
    sm: bool = True
    sm_dyn: bool = False
    cfg_rescale: float = Field(default=0, ge=0, le=1, multiple_of=0.02)
    noise_schedule: Noise = Noise.KARRAS

    # img2img
    image: str | None = None
    strength: Annotated[float, Field(ge=0.01, le=0.99, multiple_of=0.01)] | None = None
    noise: Annotated[float, Field(ge=0, le=0.99, multiple_of=0.01)] | None = None
    controlnet_strength: float = Field(default=1, ge=0.1, le=2, multiple_of=0.1)
    controlnet_condition: str | None = None
    controlnet_model: Controlnet | None = None

    # Inpaint
    add_original_image: bool = True
    mask: str | None = None

    # Vibe Transfer
    reference_image_multiple: list[str] = None
    reference_information_extracted_multiple: list[
        Annotated[float, Field(default=1, ge=0.01, le=1, multiple_of=0.01)]
    ] = None
    reference_strength_multiple: list[
        Annotated[float, Field(default=0.6, ge=0.01, le=1, multiple_of=0.01)]
    ] = None

    # V4/V4.5 specific fields
    params_version: Literal[1, 2, 3] = 3
    autoSmea: bool = Field(default=False)
    characterPrompts: List[CharacterPrompt] = None
    v4_prompt: Optional[V4PromptFormat] = None
    v4_negative_prompt: Optional[V4NegativePromptFormat] = None
    skip_cfg_above_sigma: Optional[int] = None
    use_coords: bool = Field(default=False)
    legacy_uc: bool = Field(default=False)
    normalize_reference_strength_multiple: bool = Field(default=True)
    deliberate_euler_ancestral_bug: bool = Field(default=False)
    prefer_brownian: bool = Field(default=False)

    # Misc
    legacy: bool = False
    legacy_v3_extend: bool = False

    @model_validator(mode="after")
    def use_coords_validator(self) -> "Metadata":
        """
        Validate the use_coords field. If characterPrompts is not empty or coords are not the default (0.5, 0.5),
        set use_coords to True.
        """
        if self.characterPrompts and any(
            cp.center.x != 0.5 or cp.center.y != 0.5 for cp in self.characterPrompts
        ):
            self.use_coords = True
        return self

    @model_validator(mode="after")
    def n_samples_validator(self) -> "Metadata":
        """
        Validate the following:

        - If length of `reference_information_extracted_multiple` and `reference_strength_multiple` matches `reference_image_multiple`.
            If not, fill the missing values with default or truncate the extra values.
        - If value of `n_samples` exceeds the maximum allowed value based on resolution.
        """

        if self.reference_image_multiple:
            if len(self.reference_information_extracted_multiple) > len(
                self.reference_image_multiple
            ):
                self.reference_information_extracted_multiple = (
                    self.reference_information_extracted_multiple[
                        : len(self.reference_image_multiple)
                    ]
                )
            elif len(self.reference_information_extracted_multiple) < len(
                self.reference_image_multiple
            ):
                self.reference_information_extracted_multiple += [
                    1
                    for _ in range(
                        len(self.reference_image_multiple)
                        - len(self.reference_information_extracted_multiple)
                    )
                ]

            if len(self.reference_strength_multiple) > len(
                self.reference_image_multiple
            ):
                self.reference_strength_multiple = self.reference_strength_multiple[
                    : len(self.reference_image_multiple)
                ]
            elif len(self.reference_strength_multiple) < len(
                self.reference_image_multiple
            ):
                self.reference_strength_multiple += [
                    0.6
                    for _ in range(
                        len(self.reference_image_multiple)
                        - len(self.reference_strength_multiple)
                    )
                ]

        max_n_samples = self.get_max_n_samples()
        if self.n_samples > max_n_samples:
            raise ValueError(
                f"Max value of n_samples is {max_n_samples} under current resolution ({self.width}x{self.height}). Got {self.n_samples}."
            )
        return self

    @model_validator(mode="after")
    def setup_v4_format(self) -> "Metadata":
        """
        Set up V4/V4.5 format parameters based on model version
        """
        # V4 and V4.5 models need params_version=3
        if self.model in [Model.V4, Model.V4_CUR, Model.V4_5_CUR]:
            self.params_version = 3

            # Create V4 prompt format if not provided
            if not self.v4_prompt:
                char_captions = []

                # Convert character prompts to V4 format if they exist
                if self.characterPrompts:
                    for cp in self.characterPrompts:
                        if cp.enabled:
                            # Deduplicate character prompts
                            deduped_prompt = self.deduplicate_tags(cp.prompt)
                            char_captions.append(
                                CharacterCaption(
                                    char_caption=deduped_prompt, centers=[cp.center]
                                )
                            )

                self.v4_prompt = V4PromptFormat(
                    caption=V4CaptionFormat(
                        # Use already deduplicated base prompt
                        base_caption=self.prompt,
                        char_captions=char_captions,
                    ),
                    use_coords=self.use_coords,
                    use_order=True,
                )

            # Create V4 negative prompt format if not provided
            if not self.v4_negative_prompt and self.negative_prompt:
                char_captions = []

                # Convert character prompts negative UCs to V4 format if they exist
                if self.characterPrompts:
                    for cp in self.characterPrompts:
                        if cp.enabled and cp.uc:
                            # Deduplicate character negative prompts
                            deduped_uc = self.deduplicate_tags(cp.uc)
                            char_captions.append(
                                CharacterCaption(
                                    char_caption=deduped_uc, centers=[cp.center]
                                )
                            )

                self.v4_negative_prompt = V4NegativePromptFormat(
                    caption=V4CaptionFormat(
                        # Use already deduplicated negative prompt
                        base_caption=self.negative_prompt,
                        char_captions=char_captions,
                    ),
                    legacy_uc=self.legacy_uc,
                )

        return self

    # override
    def model_post_init(self, *args) -> None:
        """
        Post-initialization hook. Inherit from `pydantic.BaseModel`.
        Implement this method to add custom initialization logic.
        """
        # Fall back to resolution preset if width and height are not provided
        self.width = self.width or self.res_preset.value[0]
        self.height = self.height or self.res_preset.value[1]

        # Append undesired content tags to negative prompt
        if self.ucPreset == 0:  # Heavy
            self.negative_prompt += ", lowres, {bad}, error, fewer, extra, missing, worst quality, jpeg artifacts, bad quality, watermark, unfinished, displeasing, chromatic aberration, signature, extra digits, artistic error, username, scan, [abstract]"
        elif self.ucPreset == 1:  # Light
            self.negative_prompt += ", lowres, jpeg artifacts, worst quality, watermark, blurry, very displeasing"
        elif self.ucPreset == 2:  # Human Focus
            self.negative_prompt += ", lowres, {bad}, error, fewer, extra, missing, worst quality, jpeg artifacts, bad quality, watermark, unfinished, displeasing, chromatic aberration, signature, extra digits, artistic error, username, scan, [abstract], bad anatomy, bad hands, @_@, mismatched pupils, heart-shaped pupils, glowing eyes"

        # Append quality tags to prompt
        if self.qualityToggle:
            self.prompt += ", best quality, amazing quality, very aesthetic, absurdres"

        # Deduplicate tags after appending quality tags
        self.prompt = self.deduplicate_tags(self.prompt)
        self.negative_prompt = self.deduplicate_tags(self.negative_prompt)

        # Disable SMEA and SMEA DYN and fill default extra param values for img2img/inpaint
        if self.action == Action.IMG2IMG or self.action == Action.INPAINT:
            self.sm = False
            self.sm_dyn = False
            self.strength = self.strength or 0.3
            self.noise = self.noise or 0
            self.extra_noise_seed = self.extra_noise_seed or random.randint(
                0, 4294967295 - 7
            )

        # Vibe Transfer handling
        # If reference_image_multiple is empty, drop unrelated fields
        if not self.reference_image_multiple:
            self.reference_image_multiple = None
            self.reference_information_extracted_multiple = None
            self.reference_strength_multiple = None

        # V4/V4.5 model SMEA handling
        # drop sm and sm_dyn
        if self.model in [Model.V4, Model.V4_CUR, Model.V4_5_CUR]:
            self.sm = None
            self.sm_dyn = None

        # Sampler handling
        # If sampler is k_euler_ancestral, set deliberate_euler_ancestral_bug and prefer_brownian
        if self.sampler == Sampler.EULER_ANC:
            self.deliberate_euler_ancestral_bug = False
            self.prefer_brownian = True

    def get_max_n_samples(self) -> int:
        """
        Get the max allowed number of images to generate in a single request by resolution.

        Returns
        -------
        `int`
            Maximum value of `ImageParams.n_samples`
        """

        w, h = self.width, self.height

        if w * h <= 512 * 704:
            return 8

        if w * h <= 640 * 640:
            return 6

        if w * h <= 1024 * 3072:
            return 4

        return 0

    def calculate_cost(self, is_opus: bool = False):
        """
        Calculate the Anlas cost of current parameters.

        Parameters
        ----------
        is_opus: `bool`, optional
            If the subscription tier is Opus. Opus accounts have access to free generations.
        """

        steps: int = self.steps
        n_samples: int = self.n_samples
        strength: float = self.action == Action.IMG2IMG and self.strength or 1.0

        # Handle SMEA factor for both V3 and V4+ models
        smea_factor = 1.0
        if self.model in [Model.V4, Model.V4_CUR, Model.V4_5_CUR]:
            # V4/V4.5 uses autoSmea
            if self.autoSmea:
                smea_factor = 1.2
        else:
            # V3 uses sm/sm_dyn
            if self.sm_dyn:
                smea_factor = 1.4
            elif self.sm:
                smea_factor = 1.2

        resolution = max(self.width * self.height, 65536)

        # For normal resolutions, square is adjusted to the same price as portrait/landscape
        if resolution > math.prod(
            Resolution.NORMAL_PORTRAIT.value
        ) and resolution <= math.prod(Resolution.NORMAL_SQUARE.value):
            resolution = math.prod(Resolution.NORMAL_PORTRAIT.value)

        per_sample = (
            math.ceil(
                2951823174884865e-21 * resolution
                + 5.753298233447344e-7 * resolution * steps
            )
            * smea_factor
        )
        per_sample = max(math.ceil(per_sample * strength), 2)

        opus_discount = (
            is_opus
            and steps <= 28
            and (resolution <= math.prod(Resolution.NORMAL_SQUARE.value))
        )

        return per_sample * (n_samples - int(opus_discount))

    def deduplicate_tags(self, prompt: str) -> str:
        """
        Deduplicate tags in a prompt string.

        Parameters
        ----------
        prompt : str
            The prompt string containing potentially duplicate tags

        Returns
        -------
        str
            The prompt with duplicate tags removed
        """
        if not prompt:
            return prompt

        # Split by commas, strip whitespace
        tags = [tag.strip() for tag in prompt.split(",")]

        # Remove empty tags
        tags = [tag for tag in tags if tag]

        # Convert to lowercase for case-insensitive comparison
        # But keep original case for the final output
        lowercase_to_original = {}
        for tag in tags:
            lowercase = tag.lower()
            # If we have multiple versions of the same tag, keep the first one
            if lowercase not in lowercase_to_original:
                lowercase_to_original[lowercase] = tag

        # Reconstruct deduplicated prompt with original case
        deduplicated_tags = list(lowercase_to_original.values())
        return ", ".join(deduplicated_tags)

    def model_dump_for_api(self) -> Dict[str, Any]:
        """
        Generate a request payload suitable for the NovelAI API.

        Returns
        -------
        Dict[str, Any]
            Dictionary formatted as API expects
        """
        # Get standard parameters
        params = self.model_dump(mode="json", exclude_none=True)

        # Create the full request payload
        payload = {
            "input": self.prompt,
            "model": self.model.value,
            "action": self.action.value,
            "parameters": params,
        }

        # Handle V4/V4.5 specific formats
        if self.model in [Model.V4, Model.V4_CUR, Model.V4_5_CUR]:
            if self.v4_prompt:
                payload["parameters"]["v4_prompt"] = self.v4_prompt.model_dump(
                    exclude_none=True
                )

            if self.v4_negative_prompt:
                payload["parameters"]["v4_negative_prompt"] = (
                    self.v4_negative_prompt.model_dump(exclude_none=True)
                )

        return payload
