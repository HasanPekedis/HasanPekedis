#!/usr/bin/env python3
"""Recolor a git-koi GIF to orange / black / white, keeping the transparent ground.

git-koi colors the coat from the account's language pigments. GitHub language colors
most often land on the "ai" (blue) pigment, which draws a blue-and-white koi. This pass
rewrites only pigment pixels:

  * saturated blue at normal brightness -> the koi's orange (orenji) hue
  * dark blue (the sumi/black pigment and its shading) -> neutral black
  * pale blue-white body shading, whites and the transparent background -> untouched

Alpha is preserved, so the README shows the fish on the page background instead of in a
black box. The transform is idempotent: an already recolored frame passes through.

    python3 tools/recolor.py IN.gif OUT.gif
"""
import colorsys
import sys

from PIL import Image, ImageSequence

ORANGE_HUE = 24.0 / 360.0     # koi ORANGE_RAMP mid tone: #F77622
HUE_LO, HUE_HI = 0.50, 0.75   # blue .. indigo
MIN_SAT = 0.40                # below this the pixel is body shading / white: leave
SUMI_VAL = 0.38               # below this value a blue pixel is the black pigment
SUMI_SCALE = 0.55             # how dark the neutral sumi ends up
ALPHA_CUTOFF = 128


def recolor_pixel(rgb):
    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    if not (HUE_LO <= h <= HUE_HI) or s < MIN_SAT:
        return rgb
    if v < SUMI_VAL:
        gray = min(int(v * 255.0 * SUMI_SCALE + 8), 255)
        return (gray, gray, gray)
    nr, ng, nb = colorsys.hsv_to_rgb(ORANGE_HUE, s, v)
    return (int(nr * 255 + 0.5), int(ng * 255 + 0.5), int(nb * 255 + 0.5))


def recolor_frame(frame):
    px = frame.load()
    w, h = frame.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            nr, ng, nb = recolor_pixel((r, g, b))
            if (nr, ng, nb) != (r, g, b):
                px[x, y] = (nr, ng, nb, a)
    return frame


def save_gif(frames, durations, path, colors=64):
    """Quantize every frame against one palette and keep index 0 transparent."""
    flat = Image.new("RGB", frames[0].size, (0, 0, 0))
    for f in frames:
        flat.paste(f, mask=f.getchannel("A"))
    palette_img = flat.quantize(colors=colors - 1, method=Image.Quantize.MEDIANCUT)
    palette = [0, 0, 0] + palette_img.getpalette()[: 3 * (colors - 1)]

    p_frames = []
    for f in frames:
        p = f.convert("RGB").quantize(palette=palette_img, dither=Image.Dither.NONE)
        p = p.point(lambda v: v + 1)
        p.paste(0, mask=f.getchannel("A").point(
            lambda v: 255 if v < ALPHA_CUTOFF else 0))
        p.putpalette(palette)
        p_frames.append(p)

    p_frames[0].save(
        path,
        save_all=True,
        append_images=p_frames[1:],
        duration=durations,
        loop=0,
        transparency=0,
        disposal=2,
        optimize=False,
    )


def main():
    src, dst = sys.argv[1], sys.argv[2]
    image = Image.open(src)
    frames, durations = [], []
    for frame in ImageSequence.Iterator(image):
        frames.append(recolor_frame(frame.convert("RGBA")))
        durations.append(frame.info.get("duration", 70))
    save_gif(frames, durations, dst)
    print(f"{dst}: {len(frames)} frames recolored to orange/black/white")


if __name__ == "__main__":
    main()
