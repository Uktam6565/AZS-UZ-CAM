from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICONS = ROOT / "icons"
ICONS.mkdir(exist_ok=True)

def _text_wh(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    # Pillow >= 10: используем textbbox
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    return w, h

def make_icon(size, filename, maskable=False):
    img = Image.new("RGBA", (size, size), (11, 18, 32, 255))
    d = ImageDraw.Draw(img)

    pad = int(size * (0.12 if maskable else 0.18))
    d.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=int(size * 0.12),
        fill=(32, 201, 151, 255),
    )

    # шрифт
    try:
        font = ImageFont.truetype("arial.ttf", int(size * 0.18))
    except:
        font = ImageFont.load_default()

    text = "GasQ"
    tw, th = _text_wh(d, text, font)
    d.text(((size - tw) / 2, (size - th) / 2), text, font=font, fill=(11, 18, 32, 255))

    img.save(ICONS / filename, "PNG")

def make_screenshot(w, h, filename, title):
    img = Image.new("RGBA", (w, h), (11, 18, 32, 255))
    d = ImageDraw.Draw(img)

    try:
        font1 = ImageFont.truetype("arial.ttf", int(min(w, h) * 0.06))
        font2 = ImageFont.truetype("arial.ttf", int(min(w, h) * 0.035))
    except:
        font1 = ImageFont.load_default()
        font2 = ImageFont.load_default()

    d.text((40, 40), title, font=font1, fill=(232, 237, 247, 255))
    d.text((40, 140), "PWA screenshots placeholder", font=font2, fill=(167, 178, 198, 255))

    img.save(ICONS / filename, "PNG")

make_icon(192, "icon-192.png", maskable=False)
make_icon(512, "icon-512.png", maskable=False)
make_icon(192, "maskable-192.png", maskable=True)
make_icon(512, "maskable-512.png", maskable=True)

make_screenshot(1280, 720, "screenshot-1.png", "GasQ — Driver")
make_screenshot(720, 1280, "screenshot-2.png", "GasQ — Operator")

print("OK: icons created in", ICONS)
