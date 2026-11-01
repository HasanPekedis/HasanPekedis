#!/usr/bin/env python3
"""Recolor the git-koi GIF to an orange/black/white koi.

git-koi paints its color patches from the account's language pigments, and GitHub
language colors most often land on the "ai" (blue) pigment, which draws a blue-and-white
koi. This pass shifts only strongly saturated blue hues to the koi's orange (orenji)
hue; the pale blue-white body shading, the black sumi patches, and the transparent
background are left untouched. Pure palette math, no account data involved.
"""
import colorsys
import sys

from PIL import Image, ImageSequence

ORANGE_HUE = 24.0 / 360.0   # koi ORANGE_RAMP mid: #F77622
HUE_LO, HUE_HI = 0.50, 0.75  # blue .. indigo/violet
MIN_SAT = 0.45              # below: body shading / whites -> leave alone
MIN_VAL = 0.22              # below: black sumi -> leave alone


def recolor_frame(rgb):
    px = rgb.load()
    w, h = rgb.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            hh, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if s < MIN_SAT or v < MIN_VAL or not (HUE_LO <= hh <= HUE_HI):
                continue
            nr, ng, nb = colorsys.hsv_to_rgb(ORANGE_HUE, s, v)
            px[x, y] = (int(nr * 255 + 0.5), int(ng * 255 + 0.5), int(nb * 255 + 0.5))
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
    print(f"{dst}: {len(frames)} frames recolored to orange")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
