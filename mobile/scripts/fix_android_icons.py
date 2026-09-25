"""Regenerate PriceWise Android launcher icons from logo-mark.png."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
RES = ROOT / "android" / "app" / "src" / "main" / "res"
MAROON = (92, 18, 40, 255)  # #5C1228


def strip_near_black(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r < 18 and g < 18 and b < 18:
                pixels[x, y] = (0, 0, 0, 0)
    return img


def make_fg(logo: Image.Image, size: int = 1024) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    target = int(size * 0.72)
    src = strip_near_black(logo.copy()).resize((target, target), Image.Resampling.LANCZOS)
    ox = (size - target) // 2
    oy = (size - target) // 2
    canvas.paste(src, (ox, oy), src)
    return canvas


def save_webp(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGBA").save(path, "WEBP", quality=95)


def main() -> None:
    logo = Image.open(ASSETS / "logo-mark.png").convert("RGBA")
    bg = Image.new("RGBA", (1024, 1024), MAROON)
    bg.save(ASSETS / "android-icon-background.png")

    fg = make_fg(logo, 1024)
    fg.save(ASSETS / "android-icon-foreground.png")

    alpha = fg.split()[-1]
    white = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
    mono = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    mono.paste(white, (0, 0), alpha)
    mono.save(ASSETS / "android-icon-monochrome.png")

    classic = Image.alpha_composite(Image.new("RGBA", (1024, 1024), MAROON), fg)
    for name in ("icon.png", "favicon.png", "adaptive-icon.png", "splash-icon.png"):
        classic.save(ASSETS / name)

    densities = {
        "mdpi": (48, 108),
        "hdpi": (72, 162),
        "xhdpi": (96, 216),
        "xxhdpi": (144, 324),
        "xxxhdpi": (192, 432),
    }
    for dens, (launcher, adaptive) in densities.items():
        folder = RES / f"mipmap-{dens}"
        save_webp(classic.resize((launcher, launcher), Image.Resampling.LANCZOS), folder / "ic_launcher.webp")
        save_webp(classic.resize((launcher, launcher), Image.Resampling.LANCZOS), folder / "ic_launcher_round.webp")
        save_webp(bg.resize((adaptive, adaptive), Image.Resampling.LANCZOS), folder / "ic_launcher_background.webp")
        save_webp(fg.resize((adaptive, adaptive), Image.Resampling.LANCZOS), folder / "ic_launcher_foreground.webp")
        save_webp(mono.resize((adaptive, adaptive), Image.Resampling.LANCZOS), folder / "ic_launcher_monochrome.webp")
        print(f"mipmap-{dens} ok")

    for dens, size in [
        ("mdpi", 200),
        ("hdpi", 300),
        ("xhdpi", 400),
        ("xxhdpi", 600),
        ("xxxhdpi", 800),
    ]:
        folder = RES / f"drawable-{dens}"
        folder.mkdir(parents=True, exist_ok=True)
        classic.resize((size, size), Image.Resampling.LANCZOS).save(folder / "splashscreen_logo.png")
        print(f"splash {dens} ok")

    print("DONE")


if __name__ == "__main__":
    main()
