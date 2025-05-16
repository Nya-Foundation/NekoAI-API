import base64
import os

import requests

url = "https://image.novelai.net/ai/encode-vibe"

HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://novelai.net",
    "Referer": "https://novelai.net",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxxxxx",
}

image_path = "../input/example_image.png"  # Replace with your line art image path


# read and image then convert to base64
def read_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string


image_base64 = read_image(image_path)
data = {
    "image": image_base64,
    "information_extracted": 0.34,
    "model": "nai-diffusion-4-full",
}


result = requests.post(url, headers=HEADERS, json=data)

print(result.status_code)
print(result.headers)
print(result.content)
