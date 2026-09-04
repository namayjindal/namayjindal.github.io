"""
Risograph softboard generator for namay.xyz.

Two modes:
  python generate.py composite   -> out/board_v0.png   (one flat "print", for previews)
  python generate.py layers      -> out/layers/*.png + out/layers/manifest.json
                                    (one transparent PNG per element, for the live site)

How the riso look is faked (read this before touching anything):
  1. Every colour is a separate INK LAYER. A layer is a coverage map (0..1) plus one of
     the real Risograph ink colours in INK below. Layers are MULTIPLIED onto cream paper,
     which is how translucent ink actually behaves. Yellow over green goes dark, so we
     KNOCK OUT the board under each note, exactly like a real riso print file.
  2. GRAIN: three noise fields are multiplied into each layer's coverage. Per-pixel
     speckle, a mid-frequency mottle, and a blurred low-frequency field for uneven roller
     pressure. A handful of pixels drop to ~25% to fake spots the ink skipped.
  3. MISREGISTRATION: every layer is shifted a few px in its own direction. This is what
     makes the cream slivers at note edges and the offset pins. Do not "fix" it.
  4. HALFTONE: tonal areas (cork, shadows) are printed as a dot grid rather than flat fill.

For the live site, `layers` mode writes RGBA PNGs where RGB = the ink colour and
alpha = coverage. Put them over the paper background with `mix-blend-mode: multiply`
and the browser reproduces the multiply math exactly.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).parent / "out"
W, H = 1600, 1000
PAPER = (246, 238, 222)            # warm cream stock, matches the papaya reference

# Real Risograph ink colours (stencil-duplicator inks, not CMYK)
INK = {
    "green":  (0, 169, 92),
    "teal":   (0, 131, 138),
    "yellow": (255, 232, 0),
    "pink":   (255, 72, 176),
    "red":    (241, 80, 96),
    "blue":   (0, 120, 191),
    "orange": (255, 108, 47),
    "black":  (30, 30, 35),
}

FONT_HAND = "/System/Library/Fonts/MarkerFelt.ttc"       # placeholder; swap for a real handwriting font
FONT_CLEAN = "/System/Library/Fonts/HelveticaNeue.ttc"   # placeholder; see README for the intended face

rng = np.random.default_rng(7)     # fixed seed so re-renders are stable


# ----------------------------------------------------------------- texture helpers
def noise(shape, blur=0.0):
    im = Image.fromarray((rng.random(shape) * 255).astype(np.uint8), "L")
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im, float) / 255


def riso_coverage(mask_img, opacity=1.0, grain=0.45, shift=(0, 0)):
    """Turn a clean 'L' mask into ink coverage with grain, dropouts and misregistration."""
    m = np.asarray(mask_img, float) / 255
    m = np.roll(m, shift, axis=(0, 1))
    fine = noise(m.shape)
    mid = noise(m.shape, blur=1.2)
    coarse = noise(m.shape, blur=6)
    cov = m * (1 - grain * fine) * (0.85 + 0.30 * mid) * (0.72 + 0.56 * coarse)
    cov[fine > 0.985] *= 0.25
    return np.clip(cov * opacity, 0, 1)


def halftone(mask_img, pitch=7, angle=22.5, density=0.55):
    """Dot-screen version of a mask: returns an 'L' image of dots whose size follows density."""
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    a = np.deg2rad(angle)
    u = xx * np.cos(a) + yy * np.sin(a)
    v = -xx * np.sin(a) + yy * np.cos(a)
    cell = (np.sin(u * 2 * np.pi / pitch) * np.sin(v * 2 * np.pi / pitch) + 1) / 2
    m = np.asarray(mask_img, float) / 255
    dens = density * (0.75 + 0.5 * noise((H, W), blur=10))   # wobble dot size across the sheet
    dots = (cell < dens) & (m > 0.5)
    return Image.fromarray((dots * 255).astype(np.uint8), "L")


def multiply(canvas, cov, color):
    ink = np.array(color, float) / 255
    return canvas * (1 - cov[..., None] * (1 - ink))


def blank():
    return Image.new("L", (W, H), 0)


def rot_rect(x, y, w, h, deg):
    m = blank()
    tile = Image.new("L", (w, h), 255).rotate(deg, expand=True, resample=Image.BICUBIC)
    m.paste(tile, (x - (tile.width - w) // 2, y - (tile.height - h) // 2))
    return m


def subtract(a, b):
    return Image.fromarray(np.where(np.asarray(b) > 128, 0, np.asarray(a)).astype(np.uint8))


# ----------------------------------------------------------------- the design
BOARD = (560, 80, 1520, 920)

# id, x, y, w, h, rotation, ink, title, body lines  (content is placeholder; see README)
NOTES = [
    ("work",     620, 140, 250, 250,  3, "yellow", "WORK",     ["- corner", "- product", "- shipping"]),
    ("media",    930, 130, 250, 250, -2, "pink",   "MEDIA",    ["- reading", "- albums", "- films"]),
    ("projects", 1230, 160, 240, 240, 4, "blue",   "PROJECTS", ["- riso site", "- era agent", "- robinhood"]),
    ("about",    660, 470, 250, 250, -4, "blue",   "ABOUT",    ["- nyc", "- from india", "- builds stuff"]),
    ("now",      1000, 520, 260, 260, 2, "yellow", "NOW",      ["- learning design", "- gym", "- roadtrip?"]),
    ("notes",    1290, 480, 200, 300, -3, "pink",  "NOTES",    ["- meet 3 ppl", "  a week", "- coffee chat"]),
]
NOTE_INK_OPACITY = {"yellow": 1.0, "pink": 0.7, "blue": 0.42}


def note_text_mask(x, y, w, h, r, title, lines):
    hand = ImageFont.truetype(FONT_HAND, 34)
    hand_small = ImageFont.truetype(FONT_HAND, 24)
    tile = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(tile)
    d.text((22, 30), title, font=hand, fill=255)
    d.line((22, 72, 22 + len(title) * 19, 72), fill=255, width=3)
    for i, ln in enumerate(lines):
        d.text((24, 95 + i * 34), ln, font=hand_small, fill=255)
    tile = tile.rotate(r, expand=True, resample=Image.BICUBIC)
    m = blank()
    m.paste(tile, (x - (tile.width - w) // 2, y - (tile.height - h) // 2), tile)
    return m


def build_elements():
    """Returns an ordered list of elements. Each element = (id, [(mask, ink, opacity, grain, shift), ...])."""
    knock = blank()
    for (_, x, y, w, h, r, *_rest) in NOTES:
        rr = rot_rect(x, y, w, h, r)
        knock.paste(rr, (0, 0), rr)

    # Board: yellow underprint + green + teal halftone for cork tooth, all knocked out under notes
    board_fill = blank()
    ImageDraw.Draw(board_fill).rounded_rectangle(BOARD, 18, fill=255)
    board_fill = subtract(board_fill, knock)
    frame = blank()
    ImageDraw.Draw(frame).rounded_rectangle(BOARD, 18, outline=255, width=14)
    elements = [("board", [
        (board_fill, "yellow", 0.45, 0.4, (2, -2)),
        (board_fill, "green", 0.80, 0.55, (0, 0)),
        (halftone(board_fill, pitch=6, density=0.35), "teal", 0.55, 0.6, (-2, 1)),
        (frame, "teal", 0.9, 0.4, (2, 3)),
    ])]

    for i, (nid, x, y, w, h, r, ink, title, lines) in enumerate(NOTES):
        shadow = subtract(rot_rect(x + 14, y + 16, w, h, r), knock)
        elements.append((f"{nid}-shadow", [(halftone(shadow, pitch=5, density=0.7), "blue", 0.8, 0.4, (0, 0))]))
        elements.append((nid, [
            (rot_rect(x, y, w, h, r), ink, NOTE_INK_OPACITY[ink], 0.38, {"yellow": (-3, 2), "pink": (4, -3), "blue": (2, 4)}[ink]),
            (note_text_mask(x, y, w, h, r, title, lines), "black", 0.9, 0.35, (-2, 1)),
        ]))
        pin = blank()
        cx, cy = x + w // 2 + int(rng.integers(-30, 30)), y + 16
        ImageDraw.Draw(pin).ellipse((cx - 11, cy - 11, cx + 11, cy + 11), fill=255)
        pink = "red" if i % 2 == 0 else "blue"
        elements.append((f"{nid}-pin", [(pin, pink, 1.0, 0.3, (1, -2) if pink == "red" else (-2, 2))]))

    # Left column typography, black ink. (In the real site this is live HTML text, not an image.)
    clean = ImageFont.truetype(FONT_CLEAN, 120, index=1)
    clean_sm = ImageFont.truetype(FONT_CLEAN, 26)
    typ = blank()
    d = ImageDraw.Draw(typ)
    d.text((70, 300), "namay", font=clean, fill=255)
    d.text((74, 440), "product · code · nyc", font=clean_sm, fill=255)
    d.text((74, 480), "a softboard of the things i care about.", font=clean_sm, fill=255)
    d.text((74, 860), "hover a note  ->", font=clean_sm, fill=255)
    blob = blank()
    ImageDraw.Draw(blob).ellipse((40, 250, 470, 330), fill=255)
    elements.append(("type-accent", [(blob, "teal", 0.35, 0.5, (3, -2))]))
    elements.append(("type", [(typ, "black", 0.95, 0.25, (0, 0))]))
    return elements


# ----------------------------------------------------------------- outputs
def render_composite(elements, path):
    canvas = np.ones((H, W, 3)) * np.array(PAPER) / 255
    canvas *= (0.97 + 0.03 * noise((H, W), blur=0.8))[..., None]      # paper tooth
    for _, inks in elements:
        for mask, ink, op, grain, shift in inks:
            canvas = multiply(canvas, riso_coverage(mask, op, grain, shift), INK[ink])
    canvas *= (0.94 + 0.06 * noise((H, W), blur=60))[..., None]        # uneven press
    Image.fromarray((np.clip(canvas, 0, 1) * 255).astype(np.uint8)).save(path)


def export_layers(elements, outdir):
    """Each element -> RGBA PNG cropped to its bbox. RGB is the un-premultiplied ink colour so that
    `mix-blend-mode: multiply` over the paper colour reproduces the composite exactly."""
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {"canvas": [W, H], "paper": PAPER, "elements": []}
    for eid, inks in elements:
        over_white = np.ones((H, W, 3))
        alpha = np.zeros((H, W))
        for mask, ink, op, grain, shift in inks:
            cov = riso_coverage(mask, op, grain, shift)
            over_white = multiply(over_white, cov, INK[ink])
            alpha = 1 - (1 - alpha) * (1 - cov)
        a = np.clip(alpha, 1e-6, 1)
        rgb = 1 - (1 - over_white) / a[..., None]          # solve multiply-over-white for the ink colour
        rgba = np.dstack([np.clip(rgb, 0, 1), alpha])
        ys, xs = np.where(alpha > 0.02)
        if len(ys) == 0:
            continue
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        crop = (rgba[y0:y1, x0:x1] * 255).astype(np.uint8)
        Image.fromarray(crop, "RGBA").save(outdir / f"{eid}.png")
        manifest["elements"].append({"id": eid, "x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)})
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "composite"
    OUT.mkdir(exist_ok=True)
    els = build_elements()
    if mode == "composite":
        render_composite(els, OUT / "board_v0.png")
        print("wrote", OUT / "board_v0.png")
    elif mode == "layers":
        export_layers(els, OUT / "layers")
        print("wrote", OUT / "layers")
    else:
        sys.exit("mode must be composite|layers")
