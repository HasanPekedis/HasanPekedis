#!/usr/bin/env python3
"""Recolor a git-koi GIF to orange / black / white and size it for any screen.

Three passes, all deterministic:

1. **Recolor** — git-koi colors the coat from the account's language pigments, and
   GitHub language colors most often land on the "ai" (blue) pigment. Saturated blue at
   normal brightness becomes the koi's orange (orenji) hue; dark blue (the sumi pigment
   and its shading) becomes neutral black. Pale body shading, whites and the transparent
   ground are left alone, and alpha is preserved, so the README shows a fish on the page
   background instead of in a black box.
2. **Trim** — crop every frame to the union of all frames' alpha bounding boxes (never
   frame 0's, or fins get clipped mid-cycle). The koi then fills the frame instead of
   swimming in dead space, which is what makes it read at phone width.
3. **Upscale** — nearest-neighbour by an integer factor, so the asset is bigger than the
   README column and the browser *downscales* it. Downscaling pixel art stays clean;
   upscaling blurs it. A 2x asset looks crisp on a wide desktop and sharp on a phone.

    python3 tools/recolor.py IN.gif OUT.gif [--scale 2] [--no-trim]
"""
import argparse
import colorsys

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


def union_bbox(frames):
    """Union of the alpha boxes: cropping to frame 0 alone clips fins mid-cycle."""
    x0 = y0 = 10**9
    x1 = y1 = -1
    for f in frames:
        bb = f.getchannel("A").getbbox()
        if bb is None:
            continue
        x0, y0 = min(x0, bb[0]), min(y0, bb[1])
        x1, y1 = max(x1, bb[2]), max(y1, bb[3])
    return x0, y0, x1, y1


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
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--scale", type=int, default=2,
                    help="nearest-neighbour factor; the README column downscales it")
    ap.add_argument("--no-trim", action="store_true")
    ap.add_argument("--no-recolor", action="store_true")
    args = ap.parse_args()

    image = Image.open(args.src)
    frames, durations = [], []
    for frame in ImageSequence.Iterator(image):
        frames.append(frame.convert("RGBA"))
        durations.append(frame.info.get("duration", 70))

    if not args.no_recolor:
        frames = [recolor_frame(f) for f in frames]

    if not args.no_trim:
        box = union_bbox(frames)
        if box[0] < 10**9:
            frames = [f.crop(box) for f in frames]

    if args.scale > 1:
        size = (frames[0].width * args.scale, frames[0].height * args.scale)
        frames = [f.resize(size, Image.Resampling.NEAREST) for f in frames]

    save_gif(frames, durations, args.dst)
    w, h = frames[0].size
    print(f"{args.dst}: {len(frames)} frames at {w}x{h} (x{args.scale})")


if __name__ == "__main__":
    main()
