#!/usr/bin/env python3
"""Finish the git-koi GIF: orange/black/white coat, then room to swim.

git-koi draws the koi from the account's language pigments and paints it in place in a
512x512 frame. This script does two deterministic palette/pixel passes so the README
koi reads as a classic orange-black-white koi that actually travels:

1. ``recolor`` — saturated blue pigment pixels become the koi's orange (orenji) hue and
   dark blue (the sumi pigment) becomes neutral black. Pale blue-white body shading,
   whites and the transparent background are left alone, so an already recolored frame
   passes through unchanged.
2. ``swim`` — the koi is cropped to its own bounding box and re-placed, frame by frame,
   along a closed figure-eight path on a wider canvas, mirrored when it turns around.
   Integer offsets only, so the pixel art stays crisp, and every path term completes a
   whole number of cycles per loop so the GIF still loops seamlessly.

Usage: koi_extras.py SRC.gif DST.gif [--canvas 768x384] [--margin 30] [--y-swing 60]
"""
import argparse
import colorsys
import math

from PIL import Image, ImageSequence

# --- recolor -----------------------------------------------------------------

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
        gray = min(int(v * 255.0 * SUMI_SCALE + 8), 255)
        return (gray, gray, gray)
    nr, ng, nb = colorsys.hsv_to_rgb(ORANGE_HUE, s, v)
    return (int(nr * 255 + 0.5), int(ng * 255 + 0.5), int(nb * 255 + 0.5))


def recolor(frame):
    """RGBA in, RGBA out; fully transparent pixels are never touched."""
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


# --- swim --------------------------------------------------------------------


def fish_bbox(frames):
    """Union of the alpha bounding boxes, so no fin gets clipped mid-swim."""
    x0 = y0 = 10**9
    x1 = y1 = -1
    for f in frames:
        bb = f.getchannel("A").getbbox()
        if bb is None:
            continue
        x0, y0 = min(x0, bb[0]), min(y0, bb[1])
        x1, y1 = max(x1, bb[2]), max(y1, bb[3])
    return x0, y0, x1, y1


def swim(frames, canvas, margin, y_swing, flip=True):
    x0, y0, x1, y1 = fish_bbox(frames)
    fw, fh = x1 - x0, y1 - y0
    cw, ch = canvas
    if fw > cw - 2 * margin or fh > ch - 2 * margin:
        raise SystemExit(f"canvas {cw}x{ch} is too small for a {fw}x{fh} koi")

    cropped = [f.crop((x0, y0, x1, y1)) for f in frames]

    cx, cy = (cw - fw) / 2.0, (ch - fh) / 2.0
    ax = (cw - fw) / 2.0 - margin
    ay = min(y_swing, (ch - fh) / 2.0 - margin)

    out = []
    facing_right = True  # the git-koi art points right at rest (snout and whiskers right)
    n = len(cropped)
    for i, frame in enumerate(cropped):
        t = i / float(n)
        x = cx + ax * math.sin(2 * math.pi * t)
        y = cy + ay * math.sin(4 * math.pi * t + math.pi / 2) + 4 * math.sin(6 * math.pi * t)

        body = frame
        if flip:
            vx = math.cos(2 * math.pi * t)  # sign of horizontal velocity
            if vx > 0.25:
                facing_right = True
            elif vx < -0.25:
                facing_right = False
            if not facing_right:
                body = frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

        canvas_frame = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        canvas_frame.paste(body, (int(round(x)), int(round(y))), body)
        out.append(canvas_frame)
    return out


# --- write -------------------------------------------------------------------


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
        p.paste(0, mask=f.getchannel("A").point(lambda v: 255 if v < 128 else 0))
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
    ap.add_argument("--canvas", default="768x384")
    ap.add_argument("--margin", type=int, default=30)
    ap.add_argument("--y-swing", type=float, default=60.0)
    ap.add_argument("--no-flip", action="store_true")
    ap.add_argument("--no-recolor", action="store_true")
    ap.add_argument("--no-swim", action="store_true")
    args = ap.parse_args()

    src = Image.open(args.src)
    frames, durations = [], []
    for frame in ImageSequence.Iterator(src):
        frames.append(frame.convert("RGBA"))
        durations.append(frame.info.get("duration", 70))

    if not args.no_recolor:
        frames = [recolor(f) for f in frames]

    if not args.no_swim:
        cw, ch = (int(v) for v in args.canvas.lower().split("x"))
        frames = swim(frames, (cw, ch), args.margin, args.y_swing, flip=not args.no_flip)

    save_gif(frames, durations, args.dst)
    print(f"{args.dst}: {len(frames)} frames on {frames[0].size[0]}x{frames[0].size[1]}")


if __name__ == "__main__":
    main()
