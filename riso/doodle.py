"""
Hand-drawn strokes for the musings pages.

generate.py makes the softboard: flat shapes, halftones, paper. This makes the
other half — the doodles in the margin of a notebook. Same ink model, different
mark. Nothing here is a vector shape; every line is a hand that wobbled.

HOW A LINE IS FAKED

1. WOBBLE, NOT JITTER. A hand does not shake per-pixel, it drifts. Every path is
   resampled to even spacing and pushed sideways by *smoothed* noise, so the line
   wanders over ~40px rather than buzzing. Per-point jitter reads as noise; a slow
   wander reads as a person.

2. TWO PASSES. Pens go over their own line. Each stroke is drawn 2x with its own
   wobble and a sub-pixel offset, so edges double up and darken unevenly the way
   real ink does.

3. BREATHING WIDTH. The stroke is stamped as overlapping dots whose radius rides
   its own noise, and tapers at both ends. That gives pressure without a brush
   engine.

4. OVERSHOOT. Hand-drawn circles do not close cleanly, they run past the start.
   hand_ellipse deliberately overshoots.

Everything returns an "L" mask. Colour, grain and misregistration are applied
later by Sheet.ink(), which reuses generate.coverage() so a doodle prints with
exactly the same ink physics as the board.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from generate import INK, PAPER, coverage, font, multiply, noise, rng  # noqa: F401


# --------------------------------------------------------------------- paths
def _wander(n, scale=0.32):
    """Smoothed noise in about [-1, 1]. The drift of a hand, not a tremor."""
    k = max(3, int(n * scale))
    raw = rng.standard_normal(n + 2 * k)
    s = np.convolve(raw, np.ones(k) / k, mode="same")[k:k + n]
    peak = np.abs(s).max()
    return s / peak if peak else s


def resample(pts, step=2.0):
    """Walk a polyline at fixed spacing, so wobble is even however the path was typed."""
    p = np.asarray(pts, float)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    dist = np.concatenate([[0], np.cumsum(seg)])
    total = dist[-1]
    if total < step:
        return p
    want = np.arange(0, total, step)
    return np.stack([np.interp(want, dist, p[:, 0]), np.interp(want, dist, p[:, 1])], 1)


def wobble(pts, amp=2.4, step=2.0):
    """Push a path sideways along its own normal by a slow wander."""
    p = resample(pts, step)
    if len(p) < 3:
        return p
    d = np.gradient(p, axis=0)
    nrm = np.stack([-d[:, 1], d[:, 0]], 1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
    return p + nrm * (_wander(len(p))[:, None] * amp)


# -------------------------------------------------------------------- strokes
def stroke(mask, pts, width=3.0, amp=2.4, passes=2, taper=True):
    """Ink a path. Stamped as overlapping dots so the width can breathe."""
    d = ImageDraw.Draw(mask)
    for _ in range(passes):
        p = wobble(pts, amp) + rng.normal(0, 0.6, 2)
        n = len(p)
        if n < 2:
            continue
        press = 0.78 + 0.42 * (_wander(n, 0.22) * 0.5 + 0.5)
        if taper:
            t = np.minimum(np.arange(n), np.arange(n)[::-1]) / max(1, n * 0.06)
            press *= np.clip(t, 0.35, 1.0)
        for (x, y), pr in zip(p, press):
            r = width * 0.5 * pr
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    return mask


def hand_ellipse(mask, cx, cy, rx, ry, width=3.0, amp=2.2, overshoot=0.22, rot=0.0):
    """A circle drawn by hand: it starts early, ends late, and never quite meets."""
    t = np.linspace(-overshoot, 2 * np.pi + overshoot, 240)
    x, y = rx * np.cos(t), ry * np.sin(t)
    if rot:
        a = np.deg2rad(rot)
        x, y = x * np.cos(a) - y * np.sin(a), x * np.sin(a) + y * np.cos(a)
    return stroke(mask, np.stack([cx + x, cy + y], 1), width, amp, taper=False)


def hand_poly(mask, pts, width=3.0, amp=2.2, close=True):
    p = list(pts) + ([pts[0]] if close else [])
    return stroke(mask, p, width, amp, taper=False)


def hand_rect(mask, x, y, w, h, width=3.0, amp=2.0):
    return hand_poly(mask, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], width, amp)


def arrow(mask, pts, width=3.0, amp=2.0, head=13):
    """A stroke with two flicks at the end. The flicks are drawn like a tick, fast."""
    stroke(mask, pts, width, amp, taper=False)
    p = resample(pts, 2.0)
    tip, back = p[-1], p[-6] if len(p) > 6 else p[0]
    v = tip - back
    v /= np.linalg.norm(v) + 1e-9
    for sign in (+1, -1):
        a = np.deg2rad(150 * sign)
        r = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]) @ v
        stroke(mask, [tuple(tip), tuple(tip + r * head)], width * 0.9, 1.0, passes=1, taper=False)
    return mask


def hatch(mask, region, angle=38, pitch=9, width=1.8, amp=1.4):
    """Shade a region with wobbly parallel lines, clipped to it. Hand shading, not a screen."""
    w, h = region.size
    lines = Image.new("L", (w, h), 0)
    a = np.deg2rad(angle)
    dx, dy = np.cos(a), np.sin(a)
    span = int(np.hypot(w, h))
    for off in range(-span, span, pitch):
        cx, cy = w / 2 - dy * off, h / 2 + dx * off
        stroke(lines, [(cx - dx * span, cy - dy * span), (cx + dx * span, cy + dy * span)],
               width, amp, passes=1, taper=False)
    clipped = np.minimum(np.asarray(lines, float), np.asarray(region, float))
    out = np.maximum(np.asarray(mask, float), clipped)
    return Image.fromarray(out.astype(np.uint8), "L")


def blob(mask, pts, wob=4.0):
    """A filled organic shape — a leaf, a rock, a splash of skin."""
    p = wobble(list(pts) + [pts[0]], wob, step=3.0)
    ImageDraw.Draw(mask).polygon([tuple(q) for q in p], fill=255)
    return mask


def write(mask, xy, text, size, font_path, anchor="la", spacing=4):
    d = ImageDraw.Draw(mask)
    d.multiline_text(xy, text, font=font(font_path, size), fill=255,
                     anchor=anchor if "\n" not in text else None, spacing=spacing)
    return mask


# ---------------------------------------------------------------------- sheet
class Sheet:
    """One doodle. Collect ink passes, then render an un-premultiplied RGBA
    exactly the way generate.export_layers() does, so the browser's
    mix-blend-mode:multiply reproduces the Python compositing."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.passes = []

    def mask(self):
        return Image.new("L", (self.w, self.h), 0)

    def ink(self, mask, color, opacity=0.95, grain=0.30, shift=(0, 0)):
        self.passes.append((mask, color, opacity, grain, shift))
        return mask

    def render(self):
        over_white = np.ones((self.h, self.w, 3))
        alpha = np.zeros((self.h, self.w))
        for m, ink, op, g, sh in self.passes:
            cov = coverage(m, op, g, sh)
            over_white = multiply(over_white, cov, INK[ink])
            alpha = 1 - (1 - alpha) * (1 - cov)
        a = np.clip(alpha, 1e-6, 1)
        rgb = 1 - (1 - over_white) / a[..., None]      # un-premultiply for multiply blending
        rgba = np.dstack([np.clip(rgb, 0, 1), np.clip(alpha, 0, 1)])
        return Image.fromarray((rgba * 255).astype(np.uint8), "RGBA")
