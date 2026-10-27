"""Generate Windows ICO resources from the approved VST raster artwork."""
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "branding" / "vst-approved-artwork.jpg"
OUTPUT = ROOT / "assets" / "branding" / "vst-approved-artwork.ico"
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Approved VST artwork is missing: {SOURCE}")
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.save(OUTPUT, format="ICO", sizes=SIZES)
    with Image.open(OUTPUT) as icon:
        if icon.format != "ICO":
            raise SystemExit("Windows icon validation failed: output is not ICO.")
    print(f"Prepared Windows icon: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
