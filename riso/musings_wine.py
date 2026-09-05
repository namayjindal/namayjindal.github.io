"""
Doodles for musings/wine.

Five drawings, each its own transparent multiply layer, sized to sit in the
article's flow. Run:

    riso/.venv/bin/python riso/musings_wine.py

-> assets/wine/*.webp

Every drawing here is trying to carry one idea. If a drawing needs a paragraph
to explain it, it is the wrong drawing.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))

from doodle import (Sheet, arrow, blob, hand_ellipse, hand_poly, hand_rect,  # noqa: E402
                    hatch, stroke, write)
from generate import F_HAND, rng  # noqa: E402

OUT = Path(__file__).parent.parent / "assets/wine"
HAND = F_HAND


def label(sheet, mask, xy, text, size=30, anchor="la"):
    return write(mask, xy, text, size, HAND, anchor=anchor)


def leaf_pts(cx, cy, length, width, ang):
    """A leaf: fat near the stem, pointed at the tip. A polygon of it is a pentagon."""
    u = np.linspace(-1, 1, 18)
    bulge = (1 - u ** 2) * (0.62 - 0.30 * u)
    p = np.vstack([np.stack([u * length, bulge * width], 1),
                   np.stack([u[::-1] * length, -bulge[::-1] * width], 1)])
    a = np.deg2rad(ang)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return (p @ rot.T) + [cx, cy]


# ------------------------------------------------------------------ 1. soil
def soil():
    """Why poor soil makes better wine: a comfortable vine has no reason to dig."""
    s = Sheet(760, 700)
    ground_y = 232

    # rocks first, so roots read as going *between* them
    rocks = s.mask()
    caption = (40, ground_y + 40, 300, 410)          # keep the ground clear under the label
    for _ in range(11):
        for _try in range(24):
            cx = rng.uniform(80, 680)
            cy = rng.uniform(ground_y + 60, 640)
            r = rng.uniform(20, 44)
            if not (caption[0] - r < cx < caption[2] + r and caption[1] - r < cy < caption[3] + r):
                break
        pts = [(cx + r * np.cos(t) * rng.uniform(.7, 1.3), cy + r * np.sin(t) * rng.uniform(.7, 1.3))
               for t in np.linspace(0, 2 * np.pi, 7, endpoint=False)]
        blob(rocks, pts, wob=3.0)
    s.ink(rocks, "brown", 0.52, 0.42, (2, -2))
    s.ink(hatch(s.mask(), rocks, angle=52, pitch=9, width=1.8), "brown", 0.78, 0.4, (-2, 1))

    line = s.mask()
    stroke(line, [(40, ground_y + 6), (250, ground_y - 4), (520, ground_y + 5), (720, ground_y - 3)],
           width=4.0, amp=3.0, taper=False)

    # the vine above ground: one stem, two leaves, one small bunch
    plant = s.mask()
    stroke(plant, [(360, ground_y), (356, 186), (368, 140), (352, 96), (358, 58)], width=5.0, amp=2.6)
    stroke(plant, [(357, 150), (410, 132), (452, 104)], width=3.4, amp=2.2)
    stroke(plant, [(360, 176), (312, 158), (276, 128)], width=3.4, amp=2.2)
    s.ink(plant, "black", 0.88, 0.34, (-2, 1))

    leaves = s.mask()
    blob(leaves, leaf_pts(258, 118, 48, 34, 202), wob=2.6)
    blob(leaves, leaf_pts(470, 92, 42, 30, -18), wob=2.6)
    s.ink(leaves, "green", 0.7, 0.36, (2, 2))

    veins = s.mask()
    stroke(veins, [(300, 132), (222, 106)], width=2.0, amp=1.4, passes=1, taper=False)
    stroke(veins, [(434, 100), (504, 84)], width=2.0, amp=1.4, passes=1, taper=False)
    s.ink(veins, "black", 0.5, 0.36, (1, 1))

    bunch = s.mask()
    for dx, dy in ((0, 0), (-25, 5), (25, 7), (-12, 28), (12, 30), (0, 54)):
        ImageDraw.Draw(bunch).ellipse([352 + dx - 13, 34 + dy - 13, 352 + dx + 13, 34 + dy + 13], fill=255)
        hand_ellipse(bunch, 352 + dx, 34 + dy, 15, 15, width=2.6, amp=1.2)
    s.ink(bunch, "purple", 0.74, 0.36, (-2, 2))

    # the roots. this is the whole point of the drawing, so they get the deepest ink
    roots = s.mask()
    stroke(roots, [(360, ground_y), (352, 300), (330, 396), (300, 500), (286, 622)], width=4.6, amp=3.2)
    stroke(roots, [(352, 300), (268, 352), (214, 430), (196, 528)], width=3.2, amp=3.0)
    stroke(roots, [(340, 350), (430, 402), (486, 486), (498, 578)], width=3.2, amp=3.0)
    stroke(roots, [(330, 396), (392, 470), (404, 552)], width=2.4, amp=2.6)
    stroke(roots, [(214, 430), (150, 486)], width=2.0, amp=2.4)
    stroke(roots, [(300, 500), (322, 596), (318, 668)], width=2.2, amp=2.6)
    s.ink(roots, "black", 0.9, 0.34, (2, -1))
    s.ink(line, "brown", 0.85, 0.36, (1, 2))

    txt = s.mask()
    label(s, txt, (556, 150), "one bunch,", 31)
    label(s, txt, (556, 182), "not ten.", 31)
    label(s, txt, (60, 292), "poor soil,", 36)
    label(s, txt, (60, 334), "so it digs.", 36)
    s.ink(txt, "black", 0.9, 0.3, (-1, 2))

    acc = s.mask()
    stroke(acc, [(58, 392), (212, 387)], width=3.0, amp=2.2, passes=1, taper=False)
    s.ink(acc, "red", 0.8, 0.32, (2, 1))
    return s


# ----------------------------------------------------------------- 2. grape
def grape():
    """The one fact that reorganises everything else: the juice is clear."""
    s = Sheet(800, 620)
    cx, cy, R, r = 286, 292, 196, 158

    skin = s.mask()
    d = ImageDraw.Draw(skin)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)          # knockout: flesh is bare paper
    s.ink(skin, "purple", 0.82, 0.4, (-3, 3))
    s.ink(skin, "red", 0.34, 0.45, (3, -2))

    edge = s.mask()
    hand_ellipse(edge, cx, cy, R, R, width=3.4, amp=2.6)
    hand_ellipse(edge, cx, cy, r, r, width=2.8, amp=2.4)
    s.ink(edge, "black", 0.86, 0.32, (2, 1))

    pips = s.mask()
    for px, py, rot in ((272, 300, -18), (330, 268, 24), (306, 340, 6)):
        pts = [(px, py - 20), (px + 13, py), (px, py + 20), (px - 13, py)]
        blob(pips, pts, wob=2.0)
    s.ink(pips, "brown", 0.72, 0.34, (1, -2))

    txt = s.mask()
    label(s, txt, (516, 112), "skin.", 38)
    label(s, txt, (516, 152), "all the colour", 27)
    label(s, txt, (516, 182), "is in here.", 27)
    label(s, txt, (18, 470), "flesh — clear.", 34)
    label(s, txt, (18, 508), "almost every grape,", 26)
    label(s, txt, (18, 536), "red or white.", 26)
    s.ink(txt, "black", 0.9, 0.3, (-2, 1))

    acc = s.mask()
    arrow(acc, [(508, 152), (462, 160), (418, 174)], width=2.6, amp=1.8, head=13)
    arrow(acc, [(176, 466), (218, 402), (252, 358)], width=2.6, amp=1.8, head=13)
    s.ink(acc, "red", 0.82, 0.32, (2, 2))
    return s


# ---------------------------------------------------------- 3. skin contact
def glass(mask, cx, top, scale=1.0, fill=0.0):
    """A wine glass outline. fill is 0..1 of the bowl, drawn as a level, not a gradient."""
    bw, bh = 62 * scale, 84 * scale
    stem, foot = 74 * scale, 34 * scale
    bowl = [(cx - bw, top), (cx - bw * .99, top + bh * .42), (cx - bw * .80, top + bh * .74),
            (cx - bw * .44, top + bh * .95), (cx, top + bh), (cx + bw * .44, top + bh * .95),
            (cx + bw * .80, top + bh * .74), (cx + bw * .99, top + bh * .42), (cx + bw, top)]
    stroke(mask, bowl, width=3.0, amp=1.8, taper=False)
    stroke(mask, [(cx, top + bh), (cx, top + bh + stem)], width=3.0, amp=1.6, taper=False)
    stroke(mask, [(cx - foot, top + bh + stem), (cx + foot, top + bh + stem)], width=3.2, amp=1.6, taper=False)
    if fill <= 0:
        return None
    lvl = top + bh * (1 - fill)
    poly = [(p[0], max(p[1], lvl)) for p in bowl]
    wine = Image.new("L", mask.size, 0)
    ImageDraw.Draw(wine).polygon([(cx - bw, lvl)] + poly + [(cx + bw, lvl)], fill=255)
    return wine


def skin_contact():
    """Three ways to combine a grape and its skin. Same fruit, three colours."""
    s = Sheet(1000, 470)
    outline, txt = s.mask(), s.mask()
    fills = []
    panels = [
        (168, "purple", 0.86, "dark grape", "skins left in", "red"),
        (500, "yellow", 0.72, "dark grape", "skins pulled fast", "white / champagne"),
        (832, "orange", 0.80, "pale grape", "skins left in", "orange"),
    ]
    for cx, ink, amt, a, b, name in panels:
        w = glass(outline, cx, 96, 1.15, fill=amt)
        fills.append((w, ink))
        label(s, txt, (cx, 300), a, 28, anchor="ma")
        label(s, txt, (cx, 332), b, 28, anchor="ma")
        label(s, txt, (cx, 382), name, 36, anchor="ma")

    for w, ink in fills:
        s.ink(w, ink, 0.78, 0.42, (-3, 3))
    s.ink(outline, "black", 0.88, 0.32, (2, 1))
    s.ink(txt, "black", 0.9, 0.3, (-1, 2))

    rules = s.mask()
    stroke(rules, [(334, 92), (334, 400)], width=2.0, amp=2.2, passes=1, taper=False)
    stroke(rules, [(666, 92), (666, 400)], width=2.0, amp=2.2, passes=1, taper=False)
    s.ink(rules, "blue", 0.3, 0.4, (1, 1))
    return s


# -------------------------------------------------------------- 4. spectrum
def spectrum():
    """Where the four reds sit relative to each other. The only chart on the page."""
    s = Sheet(1120, 530)
    axis_y = 306
    outline, txt = s.mask(), s.mask()
    fills = []
    wines = [(150, "pinot noir", 0.34, "red", 0.80),
             (398, "merlot", 0.52, "red", 0.94),
             (660, "sangiovese", 0.62, "purple", 0.80),
             (930, "cabernet", 0.86, "purple", 0.98)]
    for cx, name, body, ink, op in wines:
        w = glass(outline, cx, 96, 1.0, fill=body)
        fills.append((w, ink, op))
        label(s, txt, (cx, axis_y + 26), name, 34, anchor="ma")

    for w, ink, op in fills:
        s.ink(w, ink, op * 0.8, 0.42, (-3, 2))
    s.ink(outline, "black", 0.88, 0.32, (2, 1))

    ax = s.mask()
    arrow(ax, [(70, axis_y), (420, axis_y - 4), (760, axis_y + 3), (1050, axis_y)],
          width=3.4, amp=2.4, head=16)
    s.ink(ax, "black", 0.9, 0.34, (1, 2))

    ends = s.mask()
    label(s, ends, (60, axis_y + 96), "light, high acid,", 28)
    label(s, ends, (60, axis_y + 126), "you could chill it", 28)
    label(s, ends, (1060, axis_y + 96), "big, tannic,", 28, anchor="ra")
    label(s, ends, (1060, axis_y + 126), "dries your mouth", 28, anchor="ra")
    s.ink(ends, "red", 0.82, 0.3, (-2, 1))
    s.ink(txt, "black", 0.9, 0.3, (-1, 2))
    return s


# --------------------------------------------------------------- 5. bubbles
def bubbles():
    """Second fermentation. The bottle is the pressure vessel, that is the trick."""
    s = Sheet(800, 880)
    # champagne, not a jar: a long sloping shoulder is most of the silhouette
    left = [(256, 122), (252, 214), (212, 272), (180, 342), (174, 470), (172, 660),
            (178, 754), (194, 778)]
    right = [(344, 122), (348, 214), (388, 272), (420, 342), (426, 470), (428, 660),
             (422, 754), (406, 778)]

    body = s.mask()
    stroke(body, left, width=4.0, amp=2.2, taper=False)
    stroke(body, right, width=4.0, amp=2.2, taper=False)
    stroke(body, [(194, 778), (300, 790), (406, 778)], width=4.0, amp=1.8, taper=False)
    stroke(body, [(256, 122), (300, 116), (344, 122)], width=3.4, amp=1.4, taper=False)
    s.ink(body, "black", 0.88, 0.34, (2, -1))

    wine = s.mask()
    ImageDraw.Draw(wine).polygon(
        [(182, 362), (418, 362)] + right[3:] + [(300, 790)] + left[:2:-1], fill=255)
    s.ink(wine, "yellow", 0.52, 0.44, (-3, 3))
    s.ink(wine, "sunflower", 0.20, 0.46, (3, -2))

    fizz = s.mask()
    for _ in range(52):
        by = rng.uniform(382, 762)
        half = 118 + 8 * (by - 382) / 380          # bottle widens slightly going down
        bx = rng.uniform(300 - half, 300 + half)
        r = rng.uniform(4, 13)
        hand_ellipse(fizz, bx, by, r, r, width=2.0, amp=1.0, overshoot=0.5)
    s.ink(fizz, "black", 0.66, 0.36, (-2, 2))

    cap = s.mask()
    ImageDraw.Draw(cap).rectangle([248, 86, 352, 132], fill=255)
    s.ink(cap, "red", 0.8, 0.4, (2, 2))

    txt = s.mask()
    label(s, txt, (30, 158), "yeast + sugar,", 33)
    label(s, txt, (30, 194), "then sealed.", 33)
    label(s, txt, (470, 468), "the CO2 has", 30)
    label(s, txt, (470, 500), "nowhere to go,", 30)
    label(s, txt, (470, 532), "so it dissolves.", 30)
    label(s, txt, (30, 812), "that is the bubble.", 34)
    s.ink(txt, "black", 0.9, 0.3, (-1, 2))

    acc = s.mask()
    arrow(acc, [(206, 180), (250, 158), (280, 138)], width=2.6, amp=1.8, head=13)
    arrow(acc, [(462, 464), (424, 434), (400, 412)], width=2.6, amp=1.8, head=13)
    s.ink(acc, "red", 0.82, 0.32, (2, 1))
    return s


# -------------------------------------------------------------------- render
DOODLES = {"soil": soil, "grape": grape, "skin-contact": skin_contact,
           "spectrum": spectrum, "bubbles": bubbles}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:] or list(DOODLES)
    for name in only:
        img = DOODLES[name]().render()
        img.save(OUT / f"{name}.webp", "WEBP", quality=88, method=6)
        print(f"{name:14} {img.width}x{img.height}  {(OUT / f'{name}.webp').stat().st_size // 1024} KB")
