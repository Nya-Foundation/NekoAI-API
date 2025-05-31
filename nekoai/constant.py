from enum import Enum

from .types.host import HostInstance

HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://novelai.net",
    "Referer": "https://novelai.net",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0",
}


class Host(Enum):
    API = HostInstance(
        url="https://api.novelai.net", accept="application/x-zip-compressed", name="api"
    )
    WEB = HostInstance(
        url="https://image.novelai.net", accept="binary/octet-stream", name="web"
    )

    @staticmethod
    def custom(url: str, accept: str, name: str = "custom") -> HostInstance:
        """
        Create a custom host instance.

        Parameters
        ----------
        url: `str`
            URL of the host
        accept: `str`
            Expected Content-Type of the response
        name: `str`, optional
            Name of the host (used for image filenames), defaults to "custom"

        Returns
        -------
        `HostInstance`
            Custom host instance
        """
        return HostInstance(url=url, accept=accept, name=name)


class Endpoint(Enum):
    LOGIN = "/user/login"
    USERDATA = "/user/data"
    IMAGE = "/ai/generate-image"
    DIRECTOR = "/ai/augment-image"
    ENCODE_VIBE = "/ai/encode-vibe"


class Model(Enum):
    # NAI V3
    V3 = "nai-diffusion-3"
    V3_INP = "nai-diffusion-3-inpainting"
    # NAI V4 Full
    V4 = "nai-diffusion-4-full"
    V4_INP = "nai-diffusion-4-full-inpainting"
    # NAI V4 Curated
    V4_CUR = "nai-diffusion-4-curated-preview"
    V4_CUR_INP = "nai-diffusion-4-curated-inpainting"
    # NAI V4.5 Full
    V4_5 = "nai-diffusion-4-5-full"
    V4_5_INP = "nai-diffusion-4-5-full-inpainting"
    # NAI V4.5 Curated
    V4_5_CUR = "nai-diffusion-4-5-curated"
    V4_5_CUR_INP = "nai-diffusion-4-5-curated-inpainting"
    # Furry model beta v1.3
    FURRY = "nai-diffusion-furry-3"
    FURRY_INP = "nai-diffusion-furry-3-inpainting"


class Controlnet(Enum):
    PALETTESWAP = "hed"
    FORMLOCK = "midas"
    SCRIBBLER = "fake_scribble"
    BUILDINGCONTROL = "mlsd"
    LANDSCAPER = "uniformer"


class Action(Enum):
    GENERATE = "generate"
    INPAINT = "infill"
    IMG2IMG = "img2img"


class Resolution(Enum):
    SMALL_PORTRAIT = (512, 768)
    SMALL_LANDSCAPE = (768, 512)
    SMALL_SQUARE = (640, 640)
    NORMAL_PORTRAIT = (832, 1216)
    NORMAL_LANDSCAPE = (1216, 832)
    NORMAL_SQUARE = (1024, 1024)
    LARGE_PORTRAIT = (1024, 1536)
    LARGE_LANDSCAPE = (1536, 1024)
    LARGE_SQUARE = (1472, 1472)
    WALLPAPER_PORTRAIT = (1088, 1920)
    WALLPAPER_LANDSCAPE = (1920, 1088)


class Sampler(Enum):
    EULER = "k_euler"
    EULER_ANC = "k_euler_ancestral"
    DPM2S_ANC = "k_dpmpp_2s_ancestral"
    DPM2M = "k_dpmpp_2m"
    DPM2MSDE = 'k_dpmpp_2m_sde'
    DPMSDE = "k_dpmpp_sde"
    DDIM = "ddim_v3"


# NATIVE was deprecated on NAIv4_Curated and later models
class Noise(Enum):
    NATIVE = "native"
    KARRAS = "karras"
    EXPONENTIAL = "exponential"
    POLYEXPONENTIAL = "polyexponential"
