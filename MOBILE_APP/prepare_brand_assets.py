"""Prepare the approved VST artwork as a Buildozer-compatible launcher icon.

Requires Pillow. Keeps the full artwork visible by fitting it inside a square
rather than cropping important details off the edges.
"""
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "vst-approved-artwork.jpg"
OUTPUT = HERE / "vst-launcher-icon.png"
SIZE = (512, 512)
BACKGROUND = (3, 9, 20, 255)


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Approved VST artwork is missing: {SOURCE}")

    with Image.open(SOURCE) as original:
        artwork = ImageOps.exif_transpose(original).convert("RGBA")
        artwork.thumbnail((SIZE[0] - 24, SIZE[1] - 24), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", SIZE, BACKGROUND)
        x = (SIZE[0] - artwork.width) // 2
        y = (SIZE[1] - artwork.height) // 2
        canvas.alpha_composite(artwork, (x, y))
        canvas.convert("RGB").save(OUTPUT, format="PNG", optimize=True)

    with Image.open(OUTPUT) as generated:
        if generated.size != SIZE or generated.format != "PNG":
            raise SystemExit("Generated launcher icon failed validation.")
    print(f"Prepared {OUTPUT.name} ({SIZE[0]}x{SIZE[1]} PNG)")


if __name__ == "__main__":
    main()
