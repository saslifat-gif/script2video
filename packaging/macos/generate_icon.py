from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


def _artwork(size: int) -> Image.Image:
    scale = size / 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        tuple(round(value * scale) for value in (40, 40, 216, 216)),
        radius=round(48 * scale),
        fill="#171817",
    )
    for bounds in (
        (82, 112, 94, 144),
        (103, 91, 115, 165),
        (124, 72, 136, 184),
        (145, 96, 157, 160),
        (166, 117, 178, 139),
    ):
        draw.rounded_rectangle(
            tuple(round(value * scale) for value in bounds),
            radius=max(1, round(6 * scale)),
            fill="#D9F06C",
        )
    return image


def main() -> None:
    iconset = Path(__file__).with_name("script2video.iconset")
    output = Path(__file__).with_name("script2video.icns")
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir()
    for points in (16, 32, 128, 256, 512):
        _artwork(points).save(iconset / f"icon_{points}x{points}.png")
        _artwork(points * 2).save(iconset / f"icon_{points}x{points}@2x.png")
    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(output)],
        check=True,
    )
    shutil.rmtree(iconset)
    print(f"Created {output}")


if __name__ == "__main__":
    main()
