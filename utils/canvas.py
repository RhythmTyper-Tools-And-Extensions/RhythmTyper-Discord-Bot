from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import aiohttp
from typing import Tuple, Union

FONT_PATH = "arial.ttf"
FONT_SIZE = 24

Position = Union[Tuple[int, int], Tuple[int, int, int, int]]

async def load_image(url: str) -> Image.Image:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.read()
                return Image.open(BytesIO(data)).convert("RGBA")
    return None

def create_canvas(width=800, height=300, color=(30, 30, 30)) -> Image.Image:
    return Image.new("RGBA", (width, height), color=color)

def add_text(img: Image.Image, text: str, position: Position, color=(255,255,255), font_size=FONT_SIZE):
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, font_size)
    draw.text(position, text, fill=color, font=font)

def add_image(img: Image.Image, overlay: Image.Image, position: Position):
    img.paste(overlay, position, overlay)

def save_to_bytes(img: Image.Image, fmt="PNG") -> BytesIO:
    buffer = BytesIO()
    img.save(buffer, format=fmt)
    buffer.seek(0)
    return buffer