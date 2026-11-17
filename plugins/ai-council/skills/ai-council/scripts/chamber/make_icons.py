"""Draws the Council hub's app icons: a gold ring and a gold "C" on a deep disc. Needs Pillow (pip install pillow).
Writes icon-512.png, icon-192.png, favicon.png and council.ico beside this file. Edit LETTER or the colours, then rerun."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
LETTER = "C"
FONTS = [r"C:\Windows\Fonts\georgiab.ttf", r"C:\Windows\Fonts\georgia.ttf", "/Library/Fonts/Georgia.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]


def font(size):
    for f in FONTS:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def draw(size):
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(s // 2, 0, -1):
        t = i / (s / 2)
        c = tuple(int(a + (b - a) * (1 - t)) for a, b in zip((21, 11, 56), (59, 31, 139)))
        d.ellipse([s / 2 - i, s / 2 - i, s / 2 + i, s / 2 + i], fill=c + (255,))
    ring = max(2, s // 40)
    d.ellipse([ring, ring, s - ring, s - ring], outline=(232, 200, 74, 255), width=ring)
    f = font(int(s * 0.58))
    box = d.textbbox((0, 0), LETTER, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((s - w) / 2 - box[0], (s - h) / 2 - box[1]), LETTER, font=f, fill=(232, 200, 74, 255))
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    big = draw(512)
    big.save(HERE / "icon-512.png")
    draw(192).save(HERE / "icon-192.png")
    draw(64).save(HERE / "favicon.png")
    big.save(HERE / "council.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icons written")
