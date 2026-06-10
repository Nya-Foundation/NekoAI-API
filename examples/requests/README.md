# NekoAI-API Examples

One standalone script per core functionality. Every example reads your access
token from the `NAI_TOKEN` environment variable — the easiest way to run them
is with a `.env` file at the repo root:

```sh
# .env
NAI_TOKEN=your_access_token
```

```sh
uv run examples/requests/generate_v4_5.py
# or, if you load .env via a helper (e.g. `uvrun` = load-env .env uv run):
uvrun examples/requests/generate_v4_5.py
```

Outputs are saved to `output/`. Scripts that take an input image accept a path
as the first argument and default to `examples/input/example_image.png`.

> [!NOTE]
> Each run is a real API call. NovelAI allows one concurrent generation per
> account — run examples one at a time and avoid rapid-fire requests.

## Image Generation

| Script | What it shows | Cost |
|---|---|---|
| `generate_v3.py` | V3 model (zip response path) | Anlas* |
| `generate_v4.py` | V4 full model | Anlas* |
| `generate_v4_5.py` | V4.5 full model | Anlas* |
| `generate_v4_5_stream.py` | Real-time step-by-step streaming | Anlas* |
| `generate_v4_5_multi_char.py` | Multiple positioned characters | Anlas* |
| `img2img.py` | Image-to-image with strength/noise | Anlas* |
| `inpaint.py` | Masked inpainting (`inpaint.py <image> <mask>`) | Anlas* |
| `vibe_transfer.py` | Style transfer from a reference image | Anlas* + 2 per vibe encode |

\* Standard generations (≤1024×1024, ≤28 steps, 1 sample) are free on Opus.

## Director Tools

| Script | What it shows | Cost |
|---|---|---|
| `lineart.py` | Image → line art | free |
| `sketch.py` | Image → sketch | free |
| `background_removal.py` | Background removal | Anlas |
| `declutter.py` | Remove text/artifacts | free |
| `colorize.py` | Colorize line art (defaults to `examples/input/lineart.png`) | free |
| `change_emotion.py` | Change a character's emotion | free |

## Other Endpoints

| Script | What it shows | Cost |
|---|---|---|
| `upscale.py` | 2x/4x upscaling | Anlas |
| `annotate_image.py` | ControlNet mask generation + guided V3 generation | Anlas* |
| `suggest_tags.py` | Tag autocomplete | free |
| `account_info.py` | Subscription tier and Anlas balance | free |
