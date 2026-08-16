#!/usr/bin/env python3
"""
recolor_assets.py

Batch-recolors PNG (or other Pillow-supported) images in a folder by shifting
a source color to a target color, while preserving anti-aliasing, shading,
and transparency.

How it works:
- Converts each pixel to HSV.
- For pixels whose hue is close to the SOURCE color's hue (weighted by how
  saturated/colorful the pixel is), it rotates the hue toward the TARGET
  color's hue and rescales saturation/value accordingly.
- Grayscale / low-saturation pixels (outlines, white highlights, shadows)
  are left alone, so anti-aliased edges blend naturally.
- Alpha channel is always preserved untouched.

Usage:
    python3 recolor_assets.py <input_folder> <output_folder> \
        --from 91,123,249 --to 249,91,91

    # or omit --from to auto-detect the dominant color in each image
    python3 recolor_assets.py <input_folder> <output_folder> --to 249,91,91

Output files are saved as "<original_stem>_1<original_ext>" inside the
output folder (output folder can be the same as input folder if you want).
"""

import argparse
import colorsys
from pathlib import Path

from PIL import Image

IMAGE_EXTS = {".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def parse_color(s: str):
    parts = [int(p.strip()) for p in s.split(",")]
    if len(parts) != 3:
        raise ValueError(f"Color must be R,G,B — got: {s}")
    return tuple(parts)


def dominant_color(img: Image.Image):
    """Find the most common fully-opaque, saturated color in the image."""
    rgba = img.convert("RGBA")
    colors = rgba.getcolors(maxcolors=1_000_000) or []
    best = None
    best_count = -1
    for count, (r, g, b, a) in colors:
        if a < 200:
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.25:  # skip near-white/gray/black pixels
            continue
        if count > best_count:
            best_count = count
            best = (r, g, b)
    return best


def recolor_image(img: Image.Image, src_rgb, dst_rgb, hue_tolerance=0.12,
                   sat_floor=0.12):
    """Return a new image with src_rgb's hue family shifted toward dst_rgb."""
    img = img.convert("RGBA")
    src_h, src_s, src_v = colorsys.rgb_to_hsv(*[c / 255 for c in src_rgb])
    dst_h, dst_s, dst_v = colorsys.rgb_to_hsv(*[c / 255 for c in dst_rgb])

    pixels = img.load()
    w, h_img = img.size

    # Precompute an LUT-free per-pixel pass (fast enough for icon-sized assets)
    for y in range(h_img):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue

            ph, ps, pv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

            if ps < sat_floor:
                # Grayscale-ish pixel (white/black/outline) — leave as-is
                continue

            # How close is this pixel's hue to the source hue?
            diff = abs(ph - src_h)
            diff = min(diff, 1 - diff)  # hue wraps around 0/1
            if diff > hue_tolerance:
                continue

            weight = 1 - (diff / hue_tolerance)  # 1.0 = exact match, 0 at edge

            new_h = (ph + (dst_h - src_h) * weight) % 1.0
            # scale saturation/value proportionally to how far src is from dst,
            # blended by weight so only close-hue pixels shift
            sat_ratio = (dst_s / src_s) if src_s > 0.0001 else 1.0
            val_ratio = (dst_v / src_v) if src_v > 0.0001 else 1.0
            new_s = min(1.0, ps * (1 + (sat_ratio - 1) * weight))
            new_v = min(1.0, pv * (1 + (val_ratio - 1) * weight))

            nr, ng, nb = colorsys.hsv_to_rgb(new_h, new_s, new_v)
            pixels[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)

    return img


def process_folder(in_dir: Path, out_dir: Path, src_rgb, dst_rgb,
                    hue_tolerance, sat_floor):
    out_dir.mkdir(parents=True, exist_ok=True)
    files = [p for p in sorted(in_dir.iterdir())
             if p.is_file() and p.suffix.lower() in IMAGE_EXTS]

    if not files:
        print(f"No supported image files found in {in_dir}")
        return

    for path in files:
        img = Image.open(path)
        this_src = src_rgb or dominant_color(img)
        if this_src is None:
            print(f"  [skip] {path.name}: couldn't detect a source color")
            continue

        result = recolor_image(img, this_src, dst_rgb, hue_tolerance, sat_floor)
        out_path = out_dir / f"{path.stem}_2{path.suffix}"
        result.save(out_path)
        print(f"  [ok]   {path.name} -> {out_path.name}  "
              f"(source color used: {this_src})")


def main():
    ap = argparse.ArgumentParser(description="Batch recolor images in a folder.")
    ap.add_argument("input_folder", type=Path)
    ap.add_argument("output_folder", type=Path)
    ap.add_argument("--from", dest="from_color", type=parse_color, default=None,
                     help="Source R,G,B to replace, e.g. 91,123,249. "
                          "If omitted, auto-detected per image.")
    ap.add_argument("--to", dest="to_color", type=parse_color, required=True,
                     help="Target R,G,B, e.g. 249,91,91")
    ap.add_argument("--tolerance", type=float, default=0.12,
                     help="Hue matching tolerance, 0-0.5 (default 0.12)")
    ap.add_argument("--sat-floor", type=float, default=0.12,
                     help="Ignore pixels with saturation below this (default 0.12)")
    args = ap.parse_args()

    process_folder(args.input_folder, args.output_folder,
                    args.from_color, args.to_color,
                    args.tolerance, args.sat_floor)


if __name__ == "__main__":
    main()
