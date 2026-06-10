# CHANGELOG


## v0.4.0 (2026-06-10)

### Bug Fixes

- Correct endpoint routing and response handling found by live API testing
  ([`5a0c233`](https://github.com/Nya-Foundation/NekoAI-API/commit/5a0c233c4647dec382cc1b981ed1c32ecda6a128))

Verified against the live API (10/19 tests passed before fixes; failures were diagnosed and fixed,
  remainder blocked only by Anlas balance):

- account endpoints (login/subscription/user-data) sent duplicate Host headers because httpx
  lowercases header names; replace in place - /ai/upscale and /ai/annotate-image are served by
  api.novelai.net, not the image host (were returning 404) - add brotli support to httpx: JSON
  endpoints (suggest-tags) respond br-encoded per our Accept-Encoding and failed to decode - V4
  img2img answers with a zip on the stream endpoint; detect zip vs msgpack by magic bytes instead of
  assuming - encode-vibe tokens are raw bytes; base64-encode them for the generate payload instead
  of injecting bytes into a str field - map 402 to NotEnoughCreditsError with an accurate message
  (was AuthError "subscription required" even for insufficient Anlas) and export it

Examples: rewrite examples/requests with one up-to-date standalone script per core feature
  (generation V3/V4/V4.5, streaming, multi-character, img2img, inpaint, vibe transfer, all director
  tools, upscale, ControlNet annotate, tag suggestions, account info), all reading NAI_TOKEN from
  the environment; drop the obsolete raw-requests vibe-encode script.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

- Model-aware payload shapes verified against captured web payloads
  ([`54cc79c`](https://github.com/Nya-Foundation/NekoAI-API/commit/54cc79cddd17d02bf21a9c9577d46efcbb3d87e5))

Diffed generated payloads against every capture in examples/payloads/ and ran every example in
  examples/requests/ live (15 pass; vibe transfer, bg-removal, upscale correctly raise
  NotEnoughCreditsError on a 0-Anlas account):

- V3/Furry payloads now carry sm/sm_dyn and drop all V4-only fields (autoSmea, use_coords,
  legacy_uc, normalize_reference_strength_multiple, deliberate_euler_ancestral_bug, prefer_brownian,
  inpaintImg2ImgStrength) - always send skip_cfg_above_sigma (null when unset) like the web client -
  prefer_brownian/deliberate_euler_ancestral_bug now set for all V4 actions with k_euler_ancestral,
  not just generate (matches the inpaint capture) - annotate_image example: drop the
  ControlNet-guided generation step — V3+ models do not support ControlNet generation; annotators
  verified live

Add tests/test_payload_shapes.py comparing generated payloads against the captured web payloads per
  model/action.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

- V4 img2img requires v4_prompt on the stream endpoint; surface in-stream errors
  ([`cda5f6c`](https://github.com/Nya-Foundation/NekoAI-API/commit/cda5f6c6fbc659b1d7444aeb6e4ab3e356f20433))

Live testing on an Opus account showed V4/V4.5 img2img failing with a server 500 delivered as
  in-stream retry/error msgpack events:

- remove the IMG2IMG carve-outs in handle_v4_prompt/handle_v4_negative_prompt: the server 500s when
  v4_prompt is missing; img2img works exactly like generate (stream endpoint, msgpack framing, v4
  prompt formats) — verified end-to-end - raise NovelAIError for in-stream "error" events and log
  "retry" events instead of silently dropping them (previously surfaced as an empty image list with
  no diagnostics)

Verified live this round: subscription/user-data (Host fix), ControlNet annotate (api host fix),
  img2img. Upscale and bg-removal now return proper NotEnoughCreditsError (cost 7 and 65 Anlas;
  account balance is 0).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

### Documentation

- Restructure README around the V4.5 models
  ([`9c338a5`](https://github.com/Nya-Foundation/NekoAI-API/commit/9c338a5870f4c61f26a5e7207545246f8945a1af))

Professional rewrite: overview with verified-payload note, supported-models table, V4.5-first quick
  start and usage sections, consolidated director tools and utilities, CLI reference, and links to
  the runnable examples. Fixes stale content: missing await in the streaming example, vibe transfer
  marked V4-curated-only (works on all V4/V4.5), inpainting demoed on V3.

### Features

- Add upscale, annotate-image, suggest-tags and account endpoints, custom api_host support
  ([`fbe3449`](https://github.com/Nya-Foundation/NekoAI-API/commit/fbe344960d11f446b47ccf53883b7f1200ad9bad))

New endpoints: - /ai/upscale via client.upscale() - /ai/annotate-image via client.annotate_image()
  for ControlNet condition masks - /ai/generate-image/suggest-tags via client.suggest_tags() -
  /user/subscription and /user/data via client.get_subscription() / client.get_user_data()

Custom base URL support: - new api_host parameter for account endpoints alongside host for image
  endpoints - Host header now derived from the configured base URL instead of being hardcoded

Bug fixes: - vibe encoding now applies to all V4/V4.5 models (was V4 curated only) and respects
  custom host - V4/V4.5 inpaint no longer crashes when character prompts are absent - character
  prompts with enabled=False are no longer force-enabled - response error handling is status-based;
  JSON success bodies (login 201, tag suggestions) no longer raise - prep_headers no longer mutates
  the shared client headers - auto-close task no longer cancels itself, leaving stale running state
  - seed=0 (server-side random) allowed again - types: fix DirectorTools.EMOTION typo, remove
  phantom HostInstance export, export SketchRequest and V4NegativePromptFormat - stream chunks
  accumulated via bytearray to avoid quadratic copies

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

- Major update
  ([`2753f40`](https://github.com/Nya-Foundation/NekoAI-API/commit/2753f40edc45afc1cb632f5233358e7253e7e54e))

### Refactoring

- Restructure package for better DX, modernize packaging, expand CLI
  ([`f75ff84`](https://github.com/Nya-Foundation/NekoAI-API/commit/f75ff84ba6262ae8bf4345f2246ed4db6ba064a5))

Structure: - move to src/ layout (src/nekoai) - split utils.py into focused modules: auth.py,
  imaging.py, response.py (nekoai.utils kept as a backwards-compatible re-export shim) - unify
  exception hierarchy under NovelAIError so `except NovelAIError` catches everything - explicit
  public API in nekoai.__init__ with __all__ and __version__ - replace StrEnum (3.11+) with str+Enum
  to honor the declared Python 3.10 floor - migrate deprecated pydantic class-based Config to
  ConfigDict; package now imports warning-free

Packaging: - switch build backend from setuptools to uv_build with PEP 735 dev dependency group -
  fix deprecated SPDX license id (AGPL-3.0 -> AGPL-3.0-only) - add ruff and pytest config; drop
  requirements.txt in favor of pyproject + committed uv.lock - update semantic-release
  version_variables for the src layout

CLI: - new nekoai.cli with subcommands: login, generate (incl. --stream progress), upscale, tool
  (lineart/sketch/bg-removal/declutter/colorize/emotion/annotate), tags, subscription - auth via
  --token, NOVELAI_TOKEN env var, or username/password; --host for custom base URLs

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

- Restructure package for better DX, modernize packaging, expand CLI
  ([`8929e4b`](https://github.com/Nya-Foundation/NekoAI-API/commit/8929e4b6baaa2342a4081866b0722d6e13df13bf))

Structure: - move to src/ layout (src/nekoai) - split utils.py into focused modules: auth.py,
  imaging.py, response.py (nekoai.utils kept as a backwards-compatible re-export shim) - unify
  exception hierarchy under NovelAIError so `except NovelAIError` catches everything - explicit
  public API in nekoai.__init__ with __all__ and __version__ - replace StrEnum (3.11+) with str+Enum
  to honor the declared Python 3.10 floor - migrate deprecated pydantic class-based Config to
  ConfigDict; package now imports warning-free

Packaging: - switch build backend from setuptools to uv_build with PEP 735 dev dependency group -
  fix deprecated SPDX license id (AGPL-3.0 -> AGPL-3.0-only) - add ruff and pytest config; drop
  requirements.txt in favor of pyproject + committed uv.lock - update semantic-release
  version_variables for the src layout

CLI: - new nekoai.cli with subcommands: login, generate (incl. --stream progress), upscale, tool
  (lineart/sketch/bg-removal/declutter/colorize/emotion/annotate), tags, subscription - auth via
  --token, NOVELAI_TOKEN env var, or username/password; --host for custom base URLs

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>


## v0.3.1 (2025-06-22)

### Bug Fixes

- Round width and height is non-valid
  ([`9921604`](https://github.com/Nya-Foundation/NekoAI-API/commit/99216042e9598d79cea07b2392815f02b7400fcf))


## v0.3.0 (2025-06-21)

### Bug Fixes

- Lisence change from MIT to AGPL-3.0
  ([`c88a44a`](https://github.com/Nya-Foundation/NekoAI-API/commit/c88a44adf31ebea52aab70dd5427058188cbea40))

### Features

- Add support for generate-image-stream endpoint and stream mode, better bot detection evasion
  ([`8651501`](https://github.com/Nya-Foundation/NekoAI-API/commit/86515011b031e2449d2de4b9dae88066d11d2789))


## v0.2.1 (2025-05-31)


## v0.2.0 (2025-05-16)


## v0.1.3 (2025-05-11)


## v0.1.2 (2025-05-10)


## v0.1.1 (2025-05-10)

### Bug Fixes

- Add support for nai4.5 full
  ([`7bf3754`](https://github.com/Nya-Foundation/NekoAI-API/commit/7bf375492bf90967a117476b0b592b6aa7a5df5b))

- Enhanced parse_image and director tools for various input types for image
  ([`ba380de`](https://github.com/Nya-Foundation/NekoAI-API/commit/ba380de8adb2bc9384e831f7a825d5754fba3ddc))

- Fix circular import issue
  ([`d911010`](https://github.com/Nya-Foundation/NekoAI-API/commit/d9110107fe92a6e4f10d240399b5d2f4c40f9a37))

- Fix vibe transfer issue
  ([`5a4e5e0`](https://github.com/Nya-Foundation/NekoAI-API/commit/5a4e5e0c83bfe7a74369fcb0a5e361c5055bf5e8))

- Minor comments update just to trigger a pipeline run...
  ([`2b9e159`](https://github.com/Nya-Foundation/NekoAI-API/commit/2b9e1591cd73c6e356cc0f1ae1d28edc6443ad2c))

### Chores

- Fix uc_preset for nai4
  ([`defffd9`](https://github.com/Nya-Foundation/NekoAI-API/commit/defffd9c4c535e29e7f686cef55deb2cddda6c87))

- **format**: Apply automatic formatting [skip ci]
  ([`aaa5ded`](https://github.com/Nya-Foundation/NekoAI-API/commit/aaa5ded109f94dd592d7b92bca96c2b957e973c4))

- **format**: Apply automatic formatting [skip ci]
  ([`ec0f1d2`](https://github.com/Nya-Foundation/NekoAI-API/commit/ec0f1d2d3e60437ce4ef6881acd3af5d552d72f4))

- **format**: Apply automatic formatting [skip ci]
  ([`920ec28`](https://github.com/Nya-Foundation/NekoAI-API/commit/920ec28555ca1490e750ef6fcb770c7de46607dd))

- **format**: Apply automatic formatting [skip ci]
  ([`6a466cc`](https://github.com/Nya-Foundation/NekoAI-API/commit/6a466ccd577acd78aedc2c087d95238b806ba6fc))

### Features

- Add better vibe transfer support for v4 model... refine metadata processing logic with better
  default
  ([`b36505b`](https://github.com/Nya-Foundation/NekoAI-API/commit/b36505bb27cdc57c37a98fc27fcaec4cf2812a8e))


## v0.1.0 (2025-05-10)

### Chores

- Fix package name
  ([`f4c33b2`](https://github.com/Nya-Foundation/NekoAI-API/commit/f4c33b22ad682055fda2cfe977b6b509469be047))

### Features

- Nekoai-api Public Preview
  ([`9b86f1b`](https://github.com/Nya-Foundation/NekoAI-API/commit/9b86f1be7b4a58bcf616ce6c59a7a5ce53dd4ec5))
