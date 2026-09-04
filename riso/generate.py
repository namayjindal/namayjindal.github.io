"""
Risograph softboard generator for namay.xyz.

    python generate.py composite   -> out/board.png        one flat print, for previews
    python generate.py layers      -> out/layers/*.png     one PNG per element + manifest.json
    python generate.py all         -> both

------------------------------------------------------------------------------
HOW THE RISO LOOK IS FAKED  (read this before changing anything)

1. SPOT INKS, NOT RGB. Every colour is one of the real Risograph inks in INK.
   Nothing is a gradient and nothing is a CSS colour. Ink is laid down as a
   coverage map (0..1) and composited MULTIPLY over cream paper, which is how
   translucent ink actually behaves.

2. GRAIN. Three noise fields multiply into every layer's coverage: per-pixel
   speckle, a ~1px mottle, and a ~6px blurred field for uneven roller pressure.
   Pixels above 0.985 on the fine field drop to 25%, faking ink skips.

3. MISREGISTRATION. Every ink pass is shifted 2-5px in its own direction. On a
   note, the coloured ink is shifted INSIDE its paper silhouette, which leaves
   the cream sliver along one edge. That sliver is the most riso thing here.
   Do not align things.

4. HALFTONE. Tonal areas (cork tooth, shadows, the prints) are printed as a
   rotated dot screen rather than a flat fill.

------------------------------------------------------------------------------
PAPER OBJECTS vs INK LAYERS

A note is a piece of paper sitting ON the board, not ink printed onto it. So
elements come in two kinds:

  substrate elements  (notes, prints, cards, badges, the board itself)
      opaque. Built as cream paper + ink passes, exported with alpha = the
      paper silhouette. Blend mode "normal". Lifting one on hover reveals the
      cork underneath, which is what you want.

  ink layers  (shadows, the left-hand type)
      transparent. Exported as RGB = ink colour, alpha = coverage, blend mode
      "multiply" so the browser reproduces the same maths as this file.

manifest.json records id, position, size, blend and hover target for each.
------------------------------------------------------------------------------
"""
import json
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
OUT = HERE / "out"
CONTENT = json.loads((HERE / "content.json").read_text())

W, H = 1800, 1150
PAPER = (245, 237, 221)          # cream stock, the page background

# Real Risograph ink colours (stencil duplicator inks, not CMYK process colours)
INK = {
    "yellow":    (255, 232, 0),
    "sunflower": (255, 181, 17),
    "orange":    (255, 108, 47),
    "red":       (241, 80, 96),
    "pink":      (255, 72, 176),
    "purple":    (118, 91, 167),
    "blue":      (0, 120, 191),
    "lake":      (35, 91, 168),
    "aqua":      (94, 200, 229),
    "teal":      (0, 131, 138),
    "green":     (0, 169, 92),
    "mint":      (130, 216, 213),
    "brown":     (146, 95, 82),
    "black":     (30, 30, 35),
    "cream":     (245, 237, 221),
}

F_HAND = str(HERE / "fonts/Caveat.ttf")          # Namay's handwriting stand-in
F_CLEAN = str(HERE / "fonts/InterTight.ttf")     # left column, berd.xyz register
F_COND = str(HERE / "fonts/PathwayGothicOne.ttf")

rng = np.random.default_rng(11)                  # fixed seed: renders are reproducible


# --------------------------------------------------------------------- helpers
def noise(shape, blur=0.0):
    im = Image.fromarray((rng.random(shape) * 255).astype(np.uint8), "L")
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im, float) / 255


def blank():
    return Image.new("L", (W, H), 0)


def coverage(mask_img, opacity=1.0, grain=0.42, shift=(0, 0)):
    """Clean mask -> inked coverage with grain, dropouts and misregistration."""
    m = np.asarray(mask_img, float) / 255
    if shift != (0, 0):
        m = np.roll(m, shift, axis=(0, 1))
    fine = noise(m.shape)
    mid = noise(m.shape, blur=1.2)
    coarse = noise(m.shape, blur=6)
    cov = m * (1 - grain * fine) * (0.86 + 0.28 * mid) * (0.74 + 0.54 * coarse)
    cov[fine > 0.985] *= 0.25
    return np.clip(cov * opacity, 0, 1)


def halftone(mask_img, pitch=7, angle=22.5, density=0.55, wobble=10.0):
    """Rotated dot screen clipped to a mask. Dot size wobbles across the sheet."""
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    a = np.deg2rad(angle)
    u = xx * np.cos(a) + yy * np.sin(a)
    v = -xx * np.sin(a) + yy * np.cos(a)
    cell = (np.sin(u * 2 * np.pi / pitch) * np.sin(v * 2 * np.pi / pitch) + 1) / 2
    m = np.asarray(mask_img, float) / 255
    dens = density * (0.75 + 0.5 * noise((H, W), blur=wobble))
    return Image.fromarray((((cell < dens) & (m > 0.5)) * 255).astype(np.uint8), "L")


def multiply(canvas, cov, color):
    return canvas * (1 - cov[..., None] * (1 - np.array(color, float) / 255))


def rough_edge(mask_img, amount=2.0, scale=2.5):
    """Perturb a silhouette so the paper edge is torn/cut rather than laser-straight."""
    n = noise((H, W), blur=scale)
    m = np.asarray(mask_img, float) / 255
    soft = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6)), float) / 255
    return Image.fromarray((np.clip((soft + (n - 0.5) * amount * 0.14 - 0.42) * 6, 0, 1) * 255).astype(np.uint8))


def subtract(a, b):
    """a minus b. Riso knockout: the shape shows as bare paper instead of ink."""
    return Image.fromarray(np.where(np.asarray(b) > 100, 0, np.asarray(a)).astype(np.uint8))


def rect(x, y, w, h, rot=0.0, radius=0):
    m = blank()
    tile = Image.new("L", (w, h), 0)
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
    tile = tile.rotate(rot, expand=True, resample=Image.BICUBIC)
    m.paste(tile, (x - (tile.width - w) // 2, y - (tile.height - h) // 2))
    return m


def stamp(draw_fn, x, y, w, h, rot=0.0):
    """Draw into a w*h tile with draw_fn(ImageDraw, w, h), rotate it, place at x,y."""
    tile = Image.new("L", (w, h), 0)
    draw_fn(ImageDraw.Draw(tile), w, h)
    tile = tile.rotate(rot, expand=True, resample=Image.BICUBIC)
    m = blank()
    m.paste(tile, (x - (tile.width - w) // 2, y - (tile.height - h) // 2), tile)
    return m


def font(path, size):
    return ImageFont.truetype(path, size)


# --------------------------------------------------------------------- elements
class El:
    """One thing on the page."""
    def __init__(self, eid, inks, substrate=None, blend="normal", hover=None, z=0):
        self.id, self.inks, self.substrate, self.blend, self.hover, self.z = eid, inks, substrate, blend, hover, z


BOARD = (556, 62, 1748, 1092)          # x0, y0, x1, y1
CORK = (578, 84, 1726, 1070)


def build():
    els = []

    # ---- board: wood frame + mustard cork ---------------------------------
    frame_m = blank()
    ImageDraw.Draw(frame_m).rounded_rectangle(BOARD, 10, fill=255)
    cork_m = blank()
    ImageDraw.Draw(cork_m).rectangle(CORK, fill=255)
    border_m = subtract(frame_m, cork_m)            # wood shows only outside the cork
    wood_grain = subtract(stamp(lambda d, w, h: [d.line((0, i, w, i + rng.integers(-8, 8)), fill=255,
                                                        width=int(rng.integers(1, 4)))
                                                 for i in range(0, h, 7)],
                                BOARD[0], BOARD[1], BOARD[2] - BOARD[0], BOARD[3] - BOARD[1]), cork_m)
    els.append(El("board", [
        (border_m, "brown", 0.95, 0.35, (0, 0)),
        (wood_grain, "black", 0.45, 0.5, (2, -2)),
        # cork: sunflower base, olive-ing green pass, black tooth. Matches the photo.
        (cork_m, "sunflower", 0.92, 0.40, (-2, 2)),
        (halftone(cork_m, pitch=5, angle=15, density=0.42), "green", 0.55, 0.5, (2, 1)),
        (halftone(cork_m, pitch=3, angle=61, density=0.30), "brown", 0.40, 0.6, (-1, -2)),
    ], substrate=frame_m, z=0))

    # ---- decorative pinned artwork (mirrors the real board) ----------------
    els += decor()

    # ---- notes ------------------------------------------------------------
    for n in CONTENT["notes"]:
        els += (manifesto(n) if n["kind"] == "manifesto" else note(n))

    # ---- badge cluster ----------------------------------------------------
    els += badges()

    # ---- left column ------------------------------------------------------
    els += left_column()
    return els


def shadow_for(sil, dx=10, dy=12):
    """Halftoned drop shadow, printed in blue like the papaya reference."""
    m = np.roll(np.asarray(sil, float), (dy, dx), axis=(0, 1))
    return halftone(Image.fromarray(m.astype(np.uint8)), pitch=4, angle=45, density=0.72)


def paper(x, y, w, h, rot, radius=2, tear=2.0):
    return rough_edge(rect(x, y, w, h, rot, radius), amount=tear)


def note(n):
    """A pinned post-it: cream paper, coloured ink shifted inside it, rules, handwriting."""
    x, y, w, h, rot = n["x"], n["y"], n["w"], n["h"], n["rot"]
    sil = paper(x, y, w, h, rot)
    ink = n["ink"]
    body = ImageDraw.Draw  # noqa - readability

    def rules(d, ww, hh):
        for i in range(int(hh * 0.34), hh - 14, 26):
            d.line((16, i, ww - 16, i), fill=255, width=2)

    def text(d, ww, hh):
        # shrink the title until it fits the note, so a long room name never clips
        size = 46
        while size > 22 and d.textlength(n["title"], font=font(F_HAND, size)) > ww - 36:
            size -= 1
        f = font(F_HAND, size)
        d.text((18, 16), n["title"], font=f, fill=255)
        rule = 16 + size + 8
        d.line((18, rule, 18 + int(d.textlength(n["title"], font=f)), rule),
               fill=255, width=3)
        for i, ln in enumerate(n["lines"]):
            d.text((20, 86 + i * 34), ln, font=font(F_HAND, 32), fill=255)

    inks = [
        (sil, ink, 0.95, 0.36, {"yellow": (-3, 3), "aqua": (3, -3), "mint": (-2, -3),
                                "sunflower": (3, 3), "pink": (2, -4)}.get(ink, (2, 2))),
        (stamp(rules, x, y, w, h, rot), "blue", 0.30, 0.5, (1, 1)),
        (stamp(text, x, y, w, h, rot), "black", 0.92, 0.32, (-2, 1)),
    ]
    out = [El(f"{n['id']}-shadow", [(shadow_for(sil), "lake", 0.62, 0.45, (0, 0))],
              blend="multiply", z=1),
           El(n["id"], inks, substrate=sil, hover=n["id"], z=2)]
    out.append(pin(x + w // 2 + int(rng.integers(-40, 40)), y + 14,
                   ["red", "blue", "green", "orange"][zlib.crc32(n["id"].encode()) % 4], n["id"]))
    return out


def manifesto(n):
    """The hand-lettered roadtrip page. Each capitalised word gets its own ink."""
    x, y, w, h, rot = n["x"], n["y"], n["w"], n["h"], n["rot"]
    sil = paper(x, y, w, h, rot, tear=3.2)
    lines = CONTENT["manifesto_words"]
    accent = ["red", "orange", "green", "blue", "pink", "purple", "teal"]

    fit = 27
    probe = ImageDraw.Draw(Image.new("L", (10, 10)))
    while fit > 15 and max(probe.textlength(l, font=font(F_HAND, fit)) for l in lines) > w - 42:
        fit -= 1

    def plain(d, ww, hh):
        f = font(F_HAND, fit)
        for i, ln in enumerate(lines):
            xx = 20
            for word in ln.split(" "):
                if not (word.strip(".,").isupper() and len(word.strip(".,")) > 1):
                    d.text((xx, 18 + i * (fit - 5)), word, font=f, fill=255)
                xx += d.textlength(word + " ", font=f)

    def accented(idx):
        def draw(d, ww, hh):
            f = font(F_HAND, fit)
            for i, ln in enumerate(lines):
                xx = 20
                for j, word in enumerate(ln.split(" ")):
                    core = word.strip(".,")
                    if core.isupper() and len(core) > 1 and (i + j) % len(accent) == idx:
                        d.text((xx, 18 + i * (fit - 5)), word, font=f, fill=255)
                    xx += d.textlength(word + " ", font=f)
        return draw

    inks = [(sil, "cream", 1.0, 0.30, (0, 0)),
            (stamp(plain, x, y, w, h, rot), "black", 0.88, 0.34, (-2, 2))]
    for i, a in enumerate(accent):
        inks.append((stamp(accented(i), x, y, w, h, rot), a, 0.95, 0.34,
                     ((i % 3) - 1, (i % 2) * 3 - 1)))
    return [El(f"{n['id']}-shadow", [(shadow_for(sil), "lake", 0.62, 0.45, (0, 0))], blend="multiply", z=1),
            El(n["id"], inks, substrate=sil, hover=n["id"], z=2),
            pin(x + 34, y + 12, "red", n["id"] + "a"),
            pin(x + w - 40, y + 16, "blue", n["id"] + "b")]


def pin(cx, cy, color, key):
    """Two-ink push pin: body plus a highlight sliver, deliberately off-register."""
    body = stamp(lambda d, w, h: d.ellipse((0, 0, w - 1, h - 1), fill=255), cx - 12, cy - 12, 24, 24)
    hi = stamp(lambda d, w, h: d.ellipse((0, 0, w - 1, h - 1), fill=255), cx - 8, cy - 9, 10, 10)
    return El(f"pin-{key}", [(body, color, 1.0, 0.28, (1, -2)),
                             (hi, "cream", 0.75, 0.3, (-1, 1))], substrate=body, z=3)


def decor():
    """The prints, cards and paintings that make it a board and not a kanban."""
    out = []

    # -- Paris print (top left): sky wash, river, bridge arches, tower, autumn tree
    px, py, pw, ph = 604, 128, 306, 218

    def paris_sky(d, w, h):
        d.rectangle((10, 10, w - 10, int(h * 0.55)), fill=255)

    def paris_water(d, w, h):
        d.rectangle((10, int(h * 0.62), w - 10, h - 10), fill=255)

    def paris_ink(d, w, h):
        d.line((10, int(h * 0.62), w - 10, int(h * 0.62)), fill=255, width=3)
        for i in range(3):                                    # bridge arches
            cx = 40 + i * 62
            d.arc((cx, int(h * 0.5), cx + 54, int(h * 0.74)), 180, 360, fill=255, width=4)
        d.rectangle((16, int(h * 0.55), w - 16, int(h * 0.63)), outline=255, width=3)
        tx = int(w * 0.24)                                     # eiffel tower
        d.line((tx - 16, int(h * 0.55), tx, int(h * 0.13)), fill=255, width=3)
        d.line((tx + 16, int(h * 0.55), tx, int(h * 0.13)), fill=255, width=3)
        d.line((tx - 9, int(h * 0.38), tx + 9, int(h * 0.38)), fill=255, width=2)
        d.line((tx - 5, int(h * 0.27), tx + 5, int(h * 0.27)), fill=255, width=2)

    def paris_trees(d, w, h):
        for i in range(8):
            cx = int(w * 0.60) + (i % 4) * 26
            cy = int(h * 0.22) + (i // 4) * 30
            d.ellipse((cx, cy, cx + 40, cy + 38), fill=255)

    sil = paper(px, py, pw, ph, -1.4)
    out.append(El("art-paris-shadow", [(shadow_for(sil), "lake", 0.60, 0.45, (0, 0))], blend="multiply", z=1))
    out.append(El("art-paris", [
        (sil, "cream", 1.0, 0.3, (0, 0)),
        (halftone(stamp(paris_sky, px, py, pw, ph, -1.4), pitch=4, density=0.5), "aqua", 0.85, 0.4, (3, -2)),
        (halftone(stamp(paris_water, px, py, pw, ph, -1.4), pitch=4, angle=70, density=0.6), "lake", 0.8, 0.4, (-2, 3)),
        (stamp(paris_trees, px, py, pw, ph, -1.4), "orange", 0.85, 0.45, (2, 2)),
        (stamp(paris_ink, px, py, pw, ph, -1.4), "black", 0.75, 0.35, (-2, -1)),
    ], substrate=sil, z=2))
    out.append(pin(px + pw - 30, py + 12, "orange", "paris"))

    # -- Rings watercolour (top middle): three hanging rings, red/blue wash
    rx, ry, rw, rh = 968, 116, 268, 190

    def rings_wash(d, w, h):
        d.rectangle((0, 0, w, h), fill=255)

    def rings_ink(d, w, h):
        for i in range(3):
            cx = 44 + i * 82
            d.line((cx + 22, 6, cx + 22, 74), fill=255, width=4)
            d.ellipse((cx, 74, cx + 46, 122), outline=255, width=7)

    sil = paper(rx, ry, rw, rh, 2.0, tear=3.0)
    rings_mask = stamp(rings_ink, rx, ry, rw, rh, 2.0)
    top = subtract(stamp(rings_wash, rx, ry, rw, rh, 2.0), rings_mask)
    bot = subtract(stamp(lambda d, w, h: d.rectangle((0, int(h * 0.52), w, h), fill=255), rx, ry, rw, rh, 2.0),
                   rings_mask)
    out.append(El("art-rings-shadow", [(shadow_for(sil), "lake", 0.58, 0.45, (0, 0))], blend="multiply", z=1))
    out.append(El("art-rings", [
        (sil, "cream", 1.0, 0.3, (0, 0)),
        (halftone(top, pitch=5, density=0.62), "lake", 0.85, 0.5, (3, 2)),
        (halftone(bot, pitch=5, angle=70, density=0.55), "red", 0.75, 0.5, (-3, 1)),
    ], substrate=sil, z=2))
    out.append(pin(rx + rw // 2, ry + 10, "orange", "rings"))

    # -- Abstract shapes piece (top right), signed. Mirrors the big painting.
    ax, ay, aw, ah = 1318, 108, 356, 330
    shapes = [
        ("sunflower", lambda d, w, h: (d.rectangle((28, 26, 44, 92), fill=255),
                                       d.rectangle((54, 26, 70, 92), fill=255),
                                       d.ellipse((92, 22, 148, 78), fill=255))),
        ("red", lambda d, w, h: [d.polygon([(178 + i * 26, 96), (196 + i * 26, 22),
                                            (212 + i * 26, 22), (194 + i * 26, 96)], fill=255) for i in range(3)]),
        ("black", lambda d, w, h: (d.line((300, 24, 336, 24), fill=255, width=9),
                                   d.line((300, 24, 300, 76), fill=255, width=9),
                                   d.line((300, 76, 336, 76), fill=255, width=9),
                                   [d.ellipse((36 + (i % 6) * 13, 118 + (i // 6) * 13,
                                               42 + (i % 6) * 13, 124 + (i // 6) * 13), fill=255)
                                    for i in range(18)])),
        ("teal", lambda d, w, h: (d.rectangle((150, 150, 292, 168), fill=255),
                                  d.arc((60, 232, 152, 324), 180, 360, fill=255, width=13),
                                  d.rectangle((196, 250, 214, 316), fill=255))),
        ("orange", lambda d, w, h: (d.rectangle((36, 196, 128, 214), fill=255),
                                    d.rectangle((238, 196, 320, 214), fill=255),
                                    d.rectangle((240, 250, 320, 268), fill=255),
                                    [d.rectangle((36 + i * 30, 286, 60 + i * 30, 316), fill=255) for i in range(2)])),
        ("green", lambda d, w, h: d.polygon([(36, 108), (92, 108), (36, 164)], fill=255)),
        ("pink", lambda d, w, h: [d.rectangle((150 + i * 26, 250, 168 + i * 26, 320), fill=255) for i in range(2)]),
    ]
    sil = paper(ax, ay, aw, ah, -1.0, tear=2.6)
    out.append(El("art-abstract-shadow", [(shadow_for(sil), "lake", 0.58, 0.45, (0, 0))], blend="multiply", z=1))
    inks = [(sil, "cream", 1.0, 0.28, (0, 0))]
    for i, (col, fn) in enumerate(shapes):
        inks.append((stamp(fn, ax, ay, aw, ah, -1.0), col, 0.9, 0.42, ((i % 3) - 1, ((i + 1) % 3) - 1)))
    inks.append((stamp(lambda d, w, h: d.text((w - 96, h - 34), "NAMAY", font=font(F_HAND, 26), fill=255),
                       ax, ay, aw, ah, -1.0), "black", 0.85, 0.3, (-1, 1)))
    out.append(El("art-abstract", inks, substrate=sil, z=2))
    out += [pin(ax + 24, ay + 12, "orange", "abs1"), pin(ax + aw - 26, ay + 14, "green", "abs2")]

    # -- "NEW YORK IS ALWAYS A GOOD IDEA" card
    nx, ny, nw, nh = 1462, 470, 224, 172

    def sky(d, w, h):
        d.rectangle((0, 0, w, int(h * 0.62)), fill=255)

    def skyline(d, w, h):
        base = int(h * 0.66)
        for i, (bw, bh) in enumerate([(20, 46), (16, 70), (26, 34), (14, 88), (22, 52),
                                      (18, 64), (28, 40), (16, 76), (20, 50)]):
            x0 = 14 + i * 24
            d.rectangle((x0, base - bh, x0 + bw, base), fill=255)
        d.polygon([(96, base - 96), (104, base - 128), (112, base - 96)], fill=255)
        d.rectangle((0, base, w, base + 5), fill=255)

    def caption(d, w, h):
        f = font(F_HAND, 24)
        d.text((22, h - 46), "NEW YORK IS ALWAYS", font=f, fill=255)
        d.text((40, h - 24), "A GOOD IDEA.", font=f, fill=255)

    sil = paper(nx, ny, nw, nh, -2.2)
    out.append(El("art-nyc-shadow", [(shadow_for(sil), "lake", 0.58, 0.45, (0, 0))], blend="multiply", z=1))
    out.append(El("art-nyc", [
        (sil, "cream", 1.0, 0.3, (0, 0)),
        (halftone(stamp(sky, nx, ny, nw, nh, -2.2), pitch=4, density=0.42), "aqua", 0.8, 0.45, (3, -3)),
        (stamp(skyline, nx, ny, nw, nh, -2.2), "black", 0.9, 0.35, (-2, 2)),
        (stamp(caption, nx, ny, nw, nh, -2.2), "black", 0.9, 0.3, (1, -1)),
    ], substrate=sil, z=2))
    out.append(pin(nx + 18, ny + 10, "blue", "nyc"))

    # -- small framed photo
    fx, fy, fw, fh = 998, 618, 152, 194
    sil = paper(fx, fy, fw, fh, 3.0, radius=3)
    out.append(El("art-photo-shadow", [(shadow_for(sil), "lake", 0.60, 0.45, (0, 0))], blend="multiply", z=1))
    out.append(El("art-photo", [
        (sil, "brown", 0.95, 0.35, (2, -2)),
        (stamp(lambda d, w, h: d.rectangle((12, 12, w - 12, h - 12), fill=255), fx, fy, fw, fh, 3.0),
         "cream", 1.0, 0.3, (0, 0)),
        (halftone(stamp(lambda d, w, h: d.rectangle((12, 12, w - 12, h - 12), fill=255), fx, fy, fw, fh, 3.0),
                  pitch=4, density=0.45), "lake", 0.75, 0.5, (2, 2)),
        (halftone(stamp(lambda d, w, h: (d.ellipse((44, 44, 84, 84), fill=255),
                                         d.polygon([(38, 156), (52, 92), (78, 92), (92, 156)], fill=255),
                                         d.ellipse((86, 92, 108, 114), fill=255),
                                         d.polygon([(84, 156), (92, 112), (110, 112), (116, 156)], fill=255)),
                        fx, fy, fw, fh, 3.0), pitch=4, angle=52, density=0.72),
         "black", 0.72, 0.4, (-2, 1)),
    ], substrate=sil, z=2))

    # -- washi tape + a pink notepad, for the corners that need noise
    tape = paper(1132, 604, 96, 34, 18.0)
    out.append(El("tape-1", [(tape, "aqua", 0.62, 0.4, (2, -2)),
                             (halftone(tape, pitch=3, density=0.4), "cream", 0.5, 0.4, (-1, 1))],
                  substrate=tape, z=3))
    padsil = paper(1128, 846, 152, 206, -4.0)
    out.append(El("art-pad-shadow", [(shadow_for(padsil), "lake", 0.7, 0.4, (0, 0))], blend="multiply", z=1))
    out.append(El("art-pad", [
        (padsil, "pink", 0.85, 0.38, (3, -3)),
        (stamp(lambda d, w, h: [d.line((14, 40 + i * 24, w - 14, 40 + i * 24), fill=255, width=2)
                                for i in range((h - 60) // 24)], 1128, 846, 152, 206, -4.0),
         "red", 0.4, 0.5, (1, 1)),
    ], substrate=padsil, z=2))
    return out


def badges():
    """The button-badge cluster in the bottom right. Two inks each, no text detail."""
    spec = [
        (1352, 700, 62, "red", "blue"), (1432, 686, 74, "blue", "cream"),
        (1524, 694, 58, "black", "orange"), (1602, 704, 68, "blue", "aqua"),
        (1344, 792, 66, "cream", "red"), (1428, 802, 56, "aqua", "lake"),
        (1500, 786, 72, "cream", "black"), (1596, 796, 62, "lake", "yellow"),
        (1366, 884, 58, "yellow", "red"), (1444, 890, 66, "red", "cream"),
        (1532, 878, 60, "green", "black"), (1614, 886, 54, "purple", "cream"),
    ]
    out = []
    for i, (x, y, d_, c1, c2) in enumerate(spec):
        sil = rough_edge(stamp(lambda dr, w, h: dr.ellipse((0, 0, w - 1, h - 1), fill=255), x, y, d_, d_), amount=1.2)
        inner = stamp(lambda dr, w, h: dr.ellipse((int(w * .22), int(h * .22), int(w * .78), int(h * .78)), fill=255),
                      x, y, d_, d_)
        arc = stamp(lambda dr, w, h: dr.arc((6, 6, w - 6, h - 6), 200, 340, fill=255, width=max(4, d_ // 10)),
                    x, y, d_, d_)
        out.append(El(f"badge-{i}-shadow", [(shadow_for(sil, 6, 7), "lake", 0.5, 0.45, (0, 0))], blend="multiply", z=1))
        out.append(El(f"badge-{i}", [
            (sil, c1, 0.95, 0.35, ((i % 3) - 1, ((i + 1) % 3) - 1)),
            (inner, c2, 0.8, 0.4, (2, -2)),
            (arc, "cream" if c2 != "cream" else "black", 0.7, 0.4, (-2, 1)),
        ], substrate=sil, z=2))
    return out


def posterise(img_path, x, y, size, inks, alpha_from_image=True):
    """Map a PNG onto a small set of riso inks. Returns (silhouette, [(mask, ink), ...])."""
    im = Image.open(img_path).convert("RGBA").resize((size, size), Image.LANCZOS)
    arr = np.asarray(im, float)
    rgb, a = arr[..., :3], arr[..., 3] / 255
    pal = np.array([INK[i] for i in inks], float)
    d = ((rgb[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(-1)
    nearest = d.argmin(-1)
    sil = blank()
    sil.paste(Image.fromarray(((a > 0.4) * 255).astype(np.uint8), "L"), (x, y))
    masks = []
    for i, ink in enumerate(inks):
        layer = ((nearest == i) & (a > 0.4)) * 255
        m = blank()
        m.paste(Image.fromarray(layer.astype(np.uint8), "L"), (x, y))
        if np.asarray(m).max() > 0:
            masks.append((m, ink))
    return sil, masks


def logo_element(x, y, size):
    inks = ["black", "sunflower", "aqua", "red", "yellow", "green", "cream"]
    sil, masks = posterise(HERE.parent / "assets/logo.png", x, y, size, inks)
    passes = [(m, ink, 0.95, 0.30, ((i % 3) - 1, ((i + 1) % 3) - 1)) for i, (m, ink) in enumerate(masks)]
    return El("logo", passes, substrate=sil, z=4)


def left_column():
    """Logo, wordmark, tagline, contacts. Printed in ink straight onto the page."""
    out = []
    lx, ly, ls = 74, 92, 96

    # Namay's real logo, posterised into riso inks. Keeping his mark, not redrawing it.
    out.append(logo_element(lx, ly, ls))

    def wordmark(d, w, h):
        d.text((0, 0), CONTENT["name"], font=font(F_CLEAN, 150), fill=255)

    def small(d, w, h):
        d.text((0, 0), CONTENT["tagline"], font=font(F_CLEAN, 30), fill=255)
        d.text((0, 44), CONTENT["blurb"], font=font(F_CLEAN, 30), fill=255)

    def hint(d, w, h):
        d.text((0, 0), CONTENT["hint"], font=font(F_CLEAN, 26), fill=255)
        d.text((0, 58), "  ".join(c["label"] for c in CONTENT["contacts"]),
               font=font(F_CLEAN, 26), fill=255)

    blob = stamp(lambda d, w, h: d.ellipse((0, 0, w, h), fill=255), 62, 316, 420, 76)
    out.append(El("type-accent", [(halftone(blob, pitch=4, density=0.55), "sunflower", 0.55, 0.45, (3, -2))],
                  blend="multiply", z=4))
    out.append(El("type", [
        (stamp(wordmark, 70, 260, 560, 190), "black", 0.95, 0.24, (0, 0)),
        (stamp(wordmark, 70, 260, 560, 190), "red", 0.22, 0.4, (3, -4)),   # off-register ghost
        (stamp(small, 76, 452, 620, 110), "black", 0.9, 0.26, (-1, 1)),
        (stamp(hint, 76, 900, 620, 110), "black", 0.85, 0.28, (1, -1)),
    ], blend="multiply", z=4))
    return out


# --------------------------------------------------------------------- output
def paper_canvas():
    c = np.ones((H, W, 3)) * np.array(PAPER) / 255
    c *= (0.972 + 0.028 * noise((H, W), blur=0.7))[..., None]
    return c


def render_composite(els, path):
    canvas = paper_canvas()
    for el in sorted(els, key=lambda e: e.z):
        if el.substrate is not None:
            patch = np.ones((H, W, 3))
            for m, ink, op, g, sh in el.inks:
                patch = multiply(patch, coverage(m, op, g, sh), INK[ink])
            patch = patch * np.array(PAPER) / 255            # ink sits on cream stock
            a = coverage(el.substrate, 1.0, 0.10, (0, 0))[..., None]
            canvas = canvas * (1 - a) + patch * a
        else:
            for m, ink, op, g, sh in el.inks:
                canvas = multiply(canvas, coverage(m, op, g, sh), INK[ink])
    canvas *= (0.95 + 0.05 * noise((H, W), blur=70))[..., None]     # uneven press
    Image.fromarray((np.clip(canvas, 0, 1) * 255).astype(np.uint8)).save(path)


def export_layers(els, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    for f in outdir.glob("*.png"):
        f.unlink()
    manifest = {"canvas": [W, H], "paper": list(PAPER), "elements": []}
    for el in sorted(els, key=lambda e: e.z):
        if el.substrate is not None:
            patch = np.ones((H, W, 3))
            for m, ink, op, g, sh in el.inks:
                patch = multiply(patch, coverage(m, op, g, sh), INK[ink])
            rgb = patch * np.array(PAPER) / 255
            alpha = coverage(el.substrate, 1.0, 0.10, (0, 0))
            blend = "normal"
        else:
            over_white = np.ones((H, W, 3))
            alpha = np.zeros((H, W))
            for m, ink, op, g, sh in el.inks:
                cov = coverage(m, op, g, sh)
                over_white = multiply(over_white, cov, INK[ink])
                alpha = 1 - (1 - alpha) * (1 - cov)
            a = np.clip(alpha, 1e-6, 1)
            rgb = 1 - (1 - over_white) / a[..., None]   # un-premultiply so multiply blending works
            blend = "multiply"
        ys, xs = np.where(alpha > 0.02)
        if len(ys) == 0:
            continue
        y0, y1, x0, x1 = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
        rgba = np.dstack([np.clip(rgb, 0, 1), np.clip(alpha, 0, 1)])[y0:y1, x0:x1]
        Image.fromarray((rgba * 255).astype(np.uint8), "RGBA").save(outdir / f"{el.id}.png")
        manifest["elements"].append({"id": el.id, "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0,
                                     "blend": blend, "hover": el.hover, "z": el.z})
    # paper tooth as its own multiply layer so the browser matches the composite
    tooth = (np.clip(0.972 + 0.028 * noise((H, W), blur=0.7), 0, 1) * 255).astype(np.uint8)
    Image.fromarray(np.dstack([tooth] * 3 + [np.full((H, W), 255, np.uint8)]), "RGBA").save(outdir / "_tooth.png")
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(manifest['elements'])} elements -> {outdir}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    OUT.mkdir(exist_ok=True)
    els = build()
    if mode in ("composite", "all"):
        render_composite(els, OUT / "board.png")
        print("wrote", OUT / "board.png")
    if mode in ("layers", "all"):
        export_layers(els, OUT / "layers")
