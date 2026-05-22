---
name: screenshot-markup
description: >-
  Draw on, annotate, and mark up screenshots — circles, rectangles, arrows,
  spotlights, blur effects, macOS cursors, and zoomed insets. Use this skill
  whenever the user asks to draw, annotate, mark up, highlight, point out,
  emphasize, circle, box, or call attention to anything in a screenshot or
  image. Trigger especially aggressively right after a Playwright MCP
  screenshot — that's the killer flow; browse → screenshot → "draw a circle
  on the Send button", "highlight the pricing table", "point an arrow at the
  error", "show where to click". Also triggers for any local image the user
  wants to annotate. Do not skip this skill just because the user used a
  casual verb like "draw" or "circle" instead of "annotate". IMPORTANT — do
  NOT pass --caption unless the user explicitly asked for a text label on the
  image; the description usually goes under the image, not on it.
---

# screenshot-markup

Draw on a screenshot — circles, rectangles, arrows, captions, spotlights, blur, cursors, zoomed insets — to mark up exactly what the user asked about. Most commonly used right after a Playwright MCP screenshot, but works on any local image.

This skill is **deterministic rendering only**. The *intelligence* — interpreting the user's prompt, locating the focus region in the screenshot, and choosing the right style — lives in you, the calling model. This script just turns your decisions into pixels.

## ⚠️ Do NOT add captions by default

The `--caption` flag writes a text label onto the image itself. **Only pass `--caption` when the user explicitly asks for a text label on the image** — phrases like "label it X", "add the text Y", "write 'Z' on it", or "make it a tutorial card with a caption".

For pure pointing requests like "highlight the Send button", "circle the headline", "point at the dropdown", or "draw on the toggle" — **omit `--caption` entirely**. The image will be shown to the user with a description underneath it (in chat, in a viewer, in a doc); duplicating that as text *on* the image is visual noise. Trust the surrounding context to label what you've highlighted.

## When to use this skill

Trigger when the user wants visual emphasis on part of a screenshot. Examples:

- "Highlight the Subscribe button in this screenshot."
- "Make the pricing table stand out, blur the rest."
- "Point out the error banner with an arrow."
- "Circle the timezone dropdown — it's tiny, also zoom in on it."
- "Make a tutorial-style image showing where to click next."
- After Playwright MCP returns a screenshot, when the user references a specific UI element they want to draw attention to.

Do NOT use this skill for: cropping, OCR, generic image editing, or composing multiple screenshots together.

## The four styles

Pick the style that best fits the user's intent. If they didn't specify, infer from these heuristics:

| Style | Best for | Heuristic |
|---|---|---|
| `spotlight` | Drawing strong focus on one area, tutorial feel | User says "focus on", "make X stand out", or wants a clean teaching image |
| `blur` | Softer focus, preserves layout context | User says "blur the rest" or wants the surrounding UI still legible-ish |
| `shape` | Pointing at a specific element with explanation | User wants a caption, arrow, or Skitch-style call-out |
| `cursor-zoom` | Tiny UI (checkbox, icon) or "click here" instruction | Target is small, or user says "click", "tap", "show where to press" |

You can also chain styles by running the script multiple times (e.g., spotlight then add a caption with `shape`).

## Locating the focus region

You have two ways to tell the script *where* to focus:

- **Area** — `--region "x,y,w,h"` (pixel coordinates, top-left origin). Best for buttons, tables, panels, banners.
- **Point** — `--point "x,y"` plus optional `--radius N`. Best for "click here" or pinpointing an icon.

How to obtain coordinates:

1. **From Playwright MCP**: if the user identified the element by selector, ask Playwright to return the element's bounding box (`element.boundingBox()`), then pass it as `--region`. This is the most reliable path — prefer it.
2. **By visual reasoning**: if no bbox is available, open the screenshot, identify the element visually, and estimate its bounding box. Coordinates are in image pixels (not CSS pixels — they match the rendered PNG).
3. **Ask the user** if you're unsure and the screenshot is dense.

## CLI reference

Script path: `scripts/annotate.py` (run with `python3`). Always pass absolute paths for `--input` and `--output`.

```
python3 scripts/annotate.py \
  --input  /abs/path/to/shot.png \
  --output /abs/path/to/out.png \
  --style  {spotlight|blur|shape|cursor-zoom} \
  [--region "x,y,w,h"  | --point "x,y" [--radius 80]] \
  [--caption "Text label"] \
  [--color "#E53935"]
```

Style-specific flags:

- `spotlight`:
  - `--dim-opacity 0.65` — how dark the outside gets (0.0–1.0). Default 0.65.
- `blur`:
  - `--blur-radius 8` — Gaussian radius. 6–12 is typical.
- `shape`:
  - `--shape {rect|circle}` — default `rect` for areas; circle is auto-used for points.
  - `--stroke 4` — outline width in pixels.
  - `--arrow-from {tl|tr|bl|br}` — optional arrow pointing AT the shape from the given
    direction. The arrow originates ~140px from the shape edge in that direction (NOT
    from the page corner) and terminates at the shape edge with the arrowhead just
    outside the box.
  - `--arrow-length 140` — distance in pixels from the shape edge to the arrow tail.
- `cursor-zoom`:
  - `--zoom-factor 2.0` — magnification of the inset.
  - `--zoom-corner {tl|tr|bl|br}` — *optional* override. By default the inset is
    placed adjacent to the target on the side with the most free space, which
    keeps the visual connection tight. Pass `--zoom-corner` only when the
    surrounding UI is crowded and pinning to a page corner reads cleaner.
  - `--no-cursor` — skip the macOS cursor overlay (zoom only).
  - `--no-zoom` — skip the inset (cursor only).
  - `--cursor-color {auto|dark|light}` — cursor color. Default `auto` samples the
    background around the target and picks the variant with better contrast
    (dark cursor on light UIs, light cursor on dark UIs). Override with `dark`
    (also accepts `black`) or `light` (also accepts `white`).
  - `--cursor-size 56` — cursor size in pixels (square). Default 56. The script
    auto-shrinks when the target is smaller than the cursor so the cursor
    doesn't swallow the UI element it's pointing at.

## Worked examples

**Area highlight with spotlight + caption:**
```
python3 scripts/annotate.py \
  --input  /tmp/shot.png --output /tmp/out.png \
  --style spotlight \
  --region "120,300,420,180" \
  --caption "Pricing tiers"
```

**Click target with cursor + zoomed inset (auto cursor color):**
```
python3 scripts/annotate.py \
  --input  /tmp/shot.png --output /tmp/out.png \
  --style cursor-zoom \
  --point "640,512" --radius 30 \
  --zoom-corner br --zoom-factor 2.5 \
  --caption "Click 'Subscribe'"
```

**Forcing white cursor on a dark UI screenshot:**
```
python3 scripts/annotate.py \
  --input  /tmp/dark-shot.png --output /tmp/out.png \
  --style cursor-zoom \
  --region "1015,715,90,45" \
  --cursor-color white
```

**Zoom inset only (no cursor) — magnify a tiny element:**
```
python3 scripts/annotate.py \
  --input  /tmp/shot.png --output /tmp/out.png \
  --style cursor-zoom \
  --region "1180,40,32,32" --zoom-factor 3.5 \
  --no-cursor
```

**Cursor only (no inset) — "click here" pointer without magnification:**
```
python3 scripts/annotate.py \
  --input  /tmp/shot.png --output /tmp/out.png \
  --style cursor-zoom \
  --region "1015,715,90,45" \
  --no-zoom
```

**Tutorial-style red rectangle with arrow and caption:**
```
python3 scripts/annotate.py \
  --input  /tmp/shot.png --output /tmp/out.png \
  --style shape \
  --region "200,200,300,80" \
  --shape rect --color "#E53935" \
  --arrow-from tr \
  --caption "Enter your email here"
```

**Soft-focus blur on a panel:**
```
python3 scripts/annotate.py \
  --input  /tmp/shot.png --output /tmp/out.png \
  --style blur \
  --region "60,80,520,300" \
  --blur-radius 10
```

## Decision flow you should follow

1. Confirm the user has a screenshot and a focus target (ask if either is unclear).
2. Get the region or point coordinates — prefer Playwright `boundingBox()` over visual estimation.
3. Choose a style using the heuristic table above, or honor the user's explicit choice.
4. Run the script. Show the output path to the user.
5. If the user wants a different style or a tweak (e.g., different color, more dim), re-run — it's cheap and deterministic.

## Notes

- The script writes PNG and accepts most common input formats (PNG/JPEG/WebP).
- All coordinates are clamped to the image; out-of-bounds regions won't crash.
- Cursor assets live in `assets/`. SVG files are the canonical source of truth
  (versioned for the repo); PNG files are pre-rendered at 4× supersampling and
  are what the script actually loads at runtime. Two variants are bundled:
  `macos-cursor.png` (dark cursor, used on light UIs) and
  `macos-cursor-white.png` (light cursor, used on dark UIs). The variant is
  auto-selected based on background brightness; if neither asset is present,
  the script falls back to a generated arrow cursor in the chosen color.
- Pillow ≥ 9 is required (uses `rounded_rectangle`, `textbbox`).
