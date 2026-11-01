#!/usr/bin/env python3
"""Recolor the git-koi GIF to an orange/black/white koi.

git-koi paints its color patches from the account's language pigments, and GitHub
language colors most often land on the "ai" (blue) pigment, which draws a blue-and-white
koi. This pass rewrites only the pigment pixels:

  * strongly saturated blue at normal brightness -> the koi's orange (orenji) hue
  * dark blue (the sumi/black pigment, and its shading) -> a neutral dark gray-black
  * pale blue-white body shading, whites and the transparent background -> untouched

The palette math is deterministic and idempotent: running it again on an already
recolored GIF changes nothing.
"""
import colorsys
import sys

from PIL import Image, ImageSequence

ORANGE_HUE = 24.0 / 360.0     # koi ORANGE_RAMP mid tone: #F77622
HUE_LO, HUE_HI = 0.50, 0.75   # blue .. indigo
MIN_SAT = 0.40                # below this the pixel is body shading / white: leave
SUMI_VAL = 0.38               # below this value a blue pixel is the black pigment
SUMI_SCALE = 0.55             # how dark the neutral sumi ends up


def recolor_pixel(rgb):
    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    if not (HUE_LO <= h <= HUE_HI) or s < MIN_SAT:
        return rgb
    if v < SUMI_VAL:
        gray = int(v * 255.0 * SUMI_SCALE + 8)
        gray = min(gray, 255)
        return (gray, gray, gray)
    nr, ng, nb = colorsys.hsv_to_rgb(ORANGE_HUE, s, v)
    return (int(nr * 255 + 0.5), int(ng * 255 + 0.5), int(nb * 255 + 0.5))


def recolor_frame(rgb):
    px = rgb.load()
    w, h = rgb.size
    for y in range(h):
        for x in range(w):
            px[x, y] = recolor_pixel(px[x, y])
    return rgb


def main(src, dst):
    im = Image.open(src)
    frames, durations = [], []
    for frame in ImageSequence.Iterator(im):
        frames.append(recolor_frame(frame.convert("RGB")))
        durations.append(frame.info.get("duration", 80))
    first, *rest = frames
    first.save(dst, save_all=True, append_images=rest, duration=durations, loop=0,
               disposal=2, optimize=False)
    print(f"{dst}: {len(frames)} frames recolored to orange/black/white")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
