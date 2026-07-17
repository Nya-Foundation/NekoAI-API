from enum import Enum

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Origin": "https://novelai.net",
    "Referer": "https://novelai.net",
    "DHT": "1",
    "Sec-GPC": "1",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Priority": "u=0",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "TE": "trailers",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0",
}


class Host(Enum):
    WEB = "https://image.novelai.net"
    API = "https://api.novelai.net"
    TEXT = "https://text.novelai.net"


class Endpoint(Enum):
    # Account endpoints. NovelAI blocks third-party requests to /user/* on
    # api.novelai.net ("update to the image URL"); they are served by the
    # image host instead (verified live 2026-07).
    LOGIN = "/user/login"
    USER_DATA = "/user/data"
    SUBSCRIPTION = "/user/subscription"
    # Image endpoints (image host)
    IMAGE = "/ai/generate-image"
    IMAGE_STREAM = "/ai/generate-image-stream"
    DIRECTOR = "/ai/augment-image"
    ENCODE_VIBE = "/ai/encode-vibe"
    SUGGEST_TAGS = "/ai/generate-image/suggest-tags"
    # Endpoints still served only by api.novelai.net (404 on the image host)
    UPSCALE = "/ai/upscale"
    ANNOTATE = "/ai/annotate-image"
    # Text endpoints (text host)
    TEXT = "/ai/generate"
    TEXT_STREAM = "/ai/generate-stream"


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


def is_v4_model(model: Model) -> bool:
    """Check if the model is a V4 model."""
    return model in (
        Model.V4,
        Model.V4_INP,
        Model.V4_CUR,
        Model.V4_CUR_INP,
        Model.V4_5,
        Model.V4_5_INP,
        Model.V4_5_CUR,
        Model.V4_5_CUR_INP,
    )


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
    DPM2MSDE = "k_dpmpp_2m_sde"
    DPMSDE = "k_dpmpp_sde"
    DDIM = "ddim_v3"


# NATIVE was deprecated on NAIv4_Curated and later models
class Noise(Enum):
    NATIVE = "native"
    KARRAS = "karras"
    EXPONENTIAL = "exponential"
    POLYEXPONENTIAL = "polyexponential"


class TextModel(Enum):
    ERATO = "llama-3-erato-v1"
    KAYRA = "kayra-v1"
    CLIO = "clio-v1"


class EmotionOptions(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SCARED = "scared"
    SURPRISED = "surprised"
    TIRED = "tired"
    EXCITED = "excited"
    NERVOUS = "nervous"
    THINKING = "thinking"
    CONFUSED = "confused"
    SHY = "shy"
    DISGUSTED = "disgusted"
    SMUG = "smug"
    BORED = "bored"
    LAUGHING = "laughing"
    IRRITATED = "irritated"
    AROUSED = "aroused"
    EMBARRASSED = "embarrassed"
    WORRIED = "worried"
    LOVE = "love"
    DETERMINED = "determined"
    HURT = "hurt"
    PLAYFUL = "playful"


class EmotionLevel(Enum):
    NORMAL = 0
    SLIGHTLY_WEAK = 1
    WEAK = 2
    EVEN_WEAKER = 3
    VERY_WEAK = 4
    WEAKEST = 5
