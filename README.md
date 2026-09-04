# namay.xyz — riso softboard revamp

Personal site for Namay Jindal, hosted on GitHub Pages from this repo (`CNAME` → namay.xyz).
This branch (`riso-revamp`) is a **handoff**: the visual direction and the texture pipeline are
set, the actual site has not been built yet. Whoever picks this up (human or agent) should read
this whole file first.

The old site (typing animation, Roboto, hamburger nav) is still in `index.html`, `html/`, `styles/`,
`scripts/`. It is being replaced, not extended. Keep `assets/` (logos, resume, photo) — they get
re-used as pins/photos on the board.

---

## 1. The vision (in Namay's words, paraphrased)

- A **Risograph-print** version of the softboard in his room back home.
- **Clean typography to the left**, the **board big on the right**, same colour palette as the
  papaya reference: cream paper, riso green, fluorescent pink, yellow, blue, red.
- The board is **his own space**, not a résumé. Post-its and pinned scraps each represent a part of
  his life: work, media he's into, side projects, an about note, maybe a "now" note.
- **Hovering a post-it plays a nice little animation**, and each post-it opens into a section.
- It should feel **artsy and hand-made**, not vibe-coded. Colour and texture are the two things he
  cares about most. If a change makes it look "cleaner" but less like a print, it's wrong.

References (look at both before touching anything):

| file | what it is |
|---|---|
| `riso/reference/riso_papaya_vibe.png` | the target texture + palette: flat spot inks, grain, dot halftone, misregistered edges, blue drop-shadows |
| `riso/reference/softboard_home.jpg` | **not in repo yet** — Namay's actual board photo (mustard cork, wood panelling, post-its titled PMC / NETWORKING / UPSKILLING / PROJECTS, a Paris print, a NYC skyline card, watercolour abstracts, a photo, ~12 badge pins, a hand-lettered "I wanna go on a roadtrip" page). Namay: drop the photo here. |
| https://berd.xyz/ | typography reference. Clean, confident sans, generous spacing. |

`riso/out/board_v0.png` is the current best render. It is the vibe. It is not the final layout.

---

## 2. What's already built

```
riso/
  generate.py        the whole texture pipeline (read its docstring)
  requirements.txt   pillow + numpy
  preview.html       proof that exported layers composite correctly in a browser, with hover lift
  reference/         see above
  out/board_v0.png   flat composite render
  out/layers/        one RGBA PNG per element + manifest.json  (generated, safe to delete/regen)
```

Run it:

```sh
cd riso
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python generate.py composite   # -> out/board_v0.png
.venv/bin/python generate.py layers      # -> out/layers/*.png + manifest.json
python3 -m http.server 8765 && open http://localhost:8765/preview.html
```

Verified 2026-09-03 with Python 3.14, Pillow 12.3, NumPy 2.5. Headless Chrome screenshot of
`preview.html` matched `board_v0.png` pixel-for-pixel in colour (minus paper tooth, see §3.5).

### How the riso texture is faked

This is the part to internalise. Four mechanisms, all in `generate.py`:

1. **Separate ink layers, multiplied.** Every colour is its own coverage map (0..1) paired with one
   of the real Risograph ink colours in `INK`. Layers are multiply-blended onto cream paper, the way
   translucent ink behaves. Consequence: yellow printed over green goes muddy, so the board and the
   shadows are **knocked out** under each note (`subtract(mask, knock)`), exactly like a real riso
   print file. The first render skipped this and every note came out olive. Don't remove knockouts.
2. **Grain.** Three noise fields multiplied into each layer's coverage: per-pixel speckle, a
   ~1px-blurred mottle, and a ~6px-blurred field for uneven roller pressure. Pixels where the fine
   noise is > 0.985 drop to 25% to fake ink skips. `grain=` per layer controls the speckle amount.
3. **Misregistration.** Every layer gets its own `(dy, dx)` shift of 2–4 px in a different
   direction. This produces the cream slivers along note edges and pins that sit slightly off. It
   is the single most "riso" cue in the image. Don't align things.
4. **Halftone.** Tonal areas (cork tooth, note shadows) are printed as a rotated dot screen
   (`halftone()`), not a flat fill. The board is a yellow underprint + green + teal dots, which is
   what moved it from "flat green" to "cork".

### How the layers reach the browser

`generate.py layers` writes each element as an RGBA PNG where **RGB = ink colour, alpha = coverage**,
cropped to its bounding box, plus `manifest.json` with `{id, x, y, w, h}` on a 1600×1000 canvas
in paint order. Put them over a `rgb(246,238,222)` background with `mix-blend-mode: multiply`
and the browser reproduces the Python multiply math. Elements with two inks (note + handwriting)
are pre-composited over white and un-premultiplied so the trick still holds.

Element naming: `board`, then per note `{id}-shadow`, `{id}`, `{id}-pin`, then `type-accent`, `type`.
Shadow is a separate layer specifically so hover can move the note and shadow independently.
`preview.html` shows the lift: note translates up-left and scales 1.03, shadow translates down-right
and fades to 55%. That's the seed of the hover animation, not the final one.

---

## 3. What to build (in order)

### 3.1 Content first
Namay hasn't finalised the sections. Current placeholders: WORK, MEDIA, PROJECTS, ABOUT, NOW, NOTES.
Get the real list from him before laying out the board. Likely shape: about, work (Corner and
earlier), projects, media (books / albums / films), now, and a "scraps" category for things that
are just pinned because he likes them (a print, a photo, badges). Each post-it needs a title, 2–4
handwritten lines, and a destination (a section on the page or a sub-page).

### 3.2 Board elements beyond post-its
The real board has more than post-its. Add generators in `build_elements()` for:
- **ruled post-it lines** (faint blue rules, like the real ones), a **curled corner**, torn edges
  (perturb the mask edge with low-freq noise before `riso_coverage`)
- **pinned photo / print** frames: a cream paper rect with a 3-ink "riso illustration" inside
  (e.g. the NYC skyline as a 2-colour block print, a Paris scene as 4 inks)
- **round badge pins** (~12 on the real board): circle with 1–2 inks and a tiny word, use the
  existing logos in `assets/` posterised to 2 inks as a starting point
- **washi tape** strips at 15–30° in pink/teal at 60% opacity
- **push pins** that are 2-ink (highlight sliver + body), not flat dots
- a **hand-lettered page** like the "roadtrip" note: multi-colour lettering, one ink per word

### 3.3 Fonts
Both current fonts are macOS placeholders (`MarkerFelt`, `HelveticaNeue`).
- **Clean type (left column, live HTML):** something in the berd.xyz family — a tight grotesk
  with real weight. Try Inter Tight, Söhne-alike (e.g. "Instrument Sans"), or "Geist". Ask Namay
  to pick one from 2–3 rendered options; he cares about this.
- **Handwriting (baked into note PNGs):** replace MarkerFelt with something that looks like
  *his* hand: caps, slightly narrow, marker-ish. "Caveat Brush", "Permanent Marker" (too heavy),
  "Reenie Beanie", or scan his actual handwriting from the board photo into a font.

### 3.4 Site architecture
Keep it a **static site, no framework, no build step** beyond `generate.py`. GitHub Pages serves
the repo root. Proposed layout:

```
index.html                    the board page
styles/board.css
scripts/board.js              loads manifest.json, positions layers, hover + click
assets/riso/                  copy of riso/out/layers/* (the committed, served version)
html/<section>.html           one per post-it (or in-page panels; decide with Namay)
riso/                         generator, never served
```

- Position layers in a 1600×1000 "stage" scaled with `transform: scale()` to the viewport
  (`preview.html` already does this). Below ~900px width, stack: type on top, board below,
  board scaled to width.
- `mix-blend-mode: multiply` on every ink layer. Background is the paper colour, add a faint
  CSS noise or the paper-tooth PNG on top at low opacity (see 3.5).
- Hover: lift note + shift shadow + tiny pin wobble. Consider a 200ms "peel" using a rotateX on
  the top edge as transform-origin. Keep it under 400ms and eased with slight overshoot.
- Click: either scroll to a section on the same page (board shrinks to a sidebar) or navigate to
  `html/<section>.html` rendered as a single big sheet of the same paper with one ink for
  headings. Decide with Namay. Either way the section pages must use the same paper + inks.
- `prefers-reduced-motion`: disable the lift, keep a colour change.
- Preload the board and note PNGs; total layer payload right now is ~2 MB at 1600px, which is
  fine but export at 2× for retina and serve as WebP if it grows.

### 3.5 Known rough edges in v0
- Paper tooth and the "uneven press" vignette are applied in `render_composite` only, so the
  browser version is slightly cleaner than `board_v0.png`. Export the tooth as one more
  multiply layer (`paper-tooth.png`, full canvas, very low alpha) so both match.
- Pin colour alternates red/blue by index. Make it per-note config.
- Note text is hardcoded in `NOTES`. Move content to `riso/content.json` so the section pages and
  the generator read the same source.
- Green is still a touch more saturated than the mustard board in the photo. Try bumping the
  yellow underprint to 0.55 and dropping green to 0.72, or add a thin `orange` pass at 0.15.
- Board corners are a rounded rect; the real one has a wood frame. A 2-ink wood texture
  (orange + black, long-axis noise) around the board would sell it.

---

## 4. Rules for whoever builds this

- **Colour and texture are non-negotiable.** Every visual element goes through `generate.py` or
  reproduces the same four mechanisms. No CSS box-shadows, no gradients, no flat vector colour,
  no anti-riso "polish".
- Only real Risograph ink colours (the `INK` dict). Add inks from a real riso chart
  (e.g. Stencil's or Risotto Studio's swatches) if you need more, and name them properly.
- Misregistration stays. Grain stays. Knockouts stay.
- No frameworks, no bundlers. Python generator + static HTML/CSS/JS.
- Namay wants to be able to **explain the design to someone else**, so: keep `generate.py`
  readable, comment the *why*, and keep this README current as decisions get made.
- Show him renders early. Two or three variants of a thing, not one polished guess.
