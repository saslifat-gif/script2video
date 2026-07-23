from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    output = Path(__file__).with_name("script2video.ico")
    scale = 4
    size = 256 * scale
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (40 * scale, 40 * scale, 216 * scale, 216 * scale),
        radius=48 * scale,
        fill="#171817",
    )
    bars = (
        (82, 112, 94, 144),
        (103, 91, 115, 165),
        (124, 72, 136, 184),
        (145, 96, 157, 160),
        (166, 117, 178, 139),
    )
    for left, top, right, bottom in bars:
        draw.rounded_rectangle(
            (
                left * scale,
                top * scale,
                right * scale,
                bottom * scale,
            ),
            radius=6 * scale,
            fill="#D9F06C",
        )

    image = image.resize((256, 256), Image.Resampling.LANCZOS)
    image.save(
        output,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)],
    )
    print(f"Created {output}")


if __name__ == "__main__":
    main()
