# NovelAI API Request Examples

This directory contains example Python scripts demonstrating how to use the NekoAI API to interact with NovelAI's services. Each script is a standalone example that can be run independently.

## Authentication

All examples use token-based authentication. Replace `"your_token_here"` with your actual NovelAI access token.

For enhanced security in production environments, consider using environment variables or a secure secret management solution.

## Image Generation Examples

### Model Variations
- **generate_v3.py**: Generate an image using V3 model
- **generate_v4.py**: Generate an image using V4 curated model
- **generate_v4_5.py**: Generate an image using V4.5 curated model
- **generate_v4_5_multi_char.py**: Generate an image with multiple characters using V4.5 curated model

## Director Tool Examples

### Image Manipulation
- **line_art.py**: Convert an image to line art
- **background_removal.py**: Remove background from an image
- **colorize.py**: Colorize a line art image
- **declutter.py**: Clean up and declutter an image
- **change_emotion.py**: Change a character's emotion in an image

## How to Run

1. Ensure you have installed the NekoAI package
2. Replace the token and image paths in the examples with your own
3. Run with Python 3:

```bash
python generate_v3.py
```

## Image Requirements

For director tool examples, you'll need to provide input images. Place your images in the `examples/input/` directory or update the image paths in the scripts.

## Output

All examples save their output to the `output/` directory, which will be created if it doesn't exist.