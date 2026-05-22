#!/usr/bin/env python3
"""Annotate a screenshot to make a focus area visually prominent.

Usage examples:
  annotate.py --input shot.png --output out.png --style spotlight --region 120,300,400,180
  annotate.py --input shot.png --output out.png --style blur --point 640,420 --radius 90
  annotate.py --input shot.png --output out.png --style shape --region 200,200,300,80 \
              --shape rect --caption "Click Subscribe" --color "#E53935" --arrow-from tr
  annotate.py --input shot.png --output out.png --style cursor-zoom --point 500,300 \
              --zoom-corner br --zoom-factor 2.5
"""
import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


# ---------- helpers ----------

def parse_region(s):
    if not s:
        return None
    parts = [int(float(p)) for p in s.split(",")]
    if len(parts) != 4:
        raise ValueError(f"--region expects 'x,y,w,h', got {s!r}")
    return tuple(parts)  # (x, y, w, h)


def parse_point(s):
    if not s:
        return None
    parts = [int(float(p)) for p in s.split(",")]
    if len(parts) != 2:
        raise ValueError(f"--point expects 'x,y', got {s!r}")
    return tuple(parts)


def hex_to_rgb(h, default=(229, 57, 53)):
    if not h:
        return default
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_font(size):
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def region_from_point(point, radius):
    x, y = point
    return (x - radius, y - radius, radius * 2, radius * 2)


def normalize_target(region, point, radius, img_size):
    """Return ((x,y,w,h), is_point). One of region/point must be set."""
    if region is None and point is None:
        raise SystemExit("Must pass --region or --point")
    if point is not None:
        return region_from_point(point, radius), True
    return region, False


def clamp_box(box, img_size):
    x, y, w, h = box
    W, H = img_size
    x = max(0, min(x, W - 1))
    y = max(0, min(y, H - 1))
    w = max(1, min(w, W - x))
    h = max(1, min(h, H - y))
    return (x, y, w, h)


# ---------- caption ----------

def draw_caption(img, text, anchor_xy, color_rgb, max_width=None):
    """Draw a rounded-rect caption label near anchor_xy. Returns the label bbox."""
    if not text:
        return None
    draw = ImageDraw.Draw(img, "RGBA")
    font = load_font(22)
    pad_x, pad_y = 14, 8
    # Measure
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        tw, th = font.getsize(text) if hasattr(font, "getsize") else (len(text) * 10, 20)
    box_w, box_h = tw + pad_x * 2, th + pad_y * 2
    ax, ay = anchor_xy
    # Keep label on-canvas
    W, H = img.size
    bx = max(8, min(ax, W - box_w - 8))
    by = max(8, min(ay, H - box_h - 8))
    radius = box_h // 2
    # Rounded rect background
    draw.rounded_rectangle(
        [bx, by, bx + box_w, by + box_h], radius=radius,
        fill=color_rgb + (235,), outline=(255, 255, 255, 220), width=2,
    )
    draw.text((bx + pad_x, by + pad_y - 2), text, fill=(255, 255, 255, 255), font=font)
    return (bx, by, bx + box_w, by + box_h)


# ---------- mask building ----------

def build_focus_mask(img_size, target, is_point, feather=24):
    """White (255) inside focus, black (0) outside, with feathered edges."""
    W, H = img_size
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    x, y, w, h = target
    if is_point:
        d.ellipse([x, y, x + w, y + h], fill=255)
    else:
        # Rounded rect for softer feel
        r = min(20, min(w, h) // 4)
        d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=255)
    if feather > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    return mask


# ---------- styles ----------

def style_spotlight(img, target, is_point, dim_opacity, color_rgb, caption):
    W, H = img.size
    base = img.convert("RGBA")
    mask = build_focus_mask((W, H), target, is_point, feather=28)
    # Dim layer: black with alpha = dim_opacity * (1 - mask)
    alpha = Image.eval(mask, lambda v: int((1 - v / 255.0) * 255 * dim_opacity))
    dim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dim.putalpha(alpha)
    out = Image.alpha_composite(base, dim)
    if caption:
        x, y, w, h = target
        draw_caption(out, caption, (x, max(8, y - 50)), color_rgb)
    return out


def style_blur(img, target, is_point, blur_radius, color_rgb, caption):
    W, H = img.size
    base = img.convert("RGBA")
    blurred = base.filter(ImageFilter.GaussianBlur(blur_radius))
    mask = build_focus_mask((W, H), target, is_point, feather=24)
    # Where mask=255, show base; where mask=0, show blurred.
    out = Image.composite(base, blurred, mask)
    if caption:
        x, y, w, h = target
        draw_caption(out, caption, (x, max(8, y - 50)), color_rgb)
    return out


def style_shape(img, target, is_point, shape_kind, color_rgb, stroke, caption,
                arrow_from, arrow_length=140):
    base = img.convert("RGBA")
    W, H = base.size
    x, y, w, h = target

    # Render the shape outlines at 2x scale then downsample so circle/rect
    # outlines are anti-aliased instead of pixel-jagged.
    SS = 2
    overlay_hi = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay_hi)
    if is_point or shape_kind == "circle":
        pad = 12
        sx0, sy0 = (x - pad) * SS, (y - pad) * SS
        sx1, sy1 = (x + w + pad) * SS, (y + h + pad) * SS
        d.ellipse([sx0, sy0, sx1, sy1],
                  outline=color_rgb + (255,), width=stroke * SS)
        shape_box = (x - pad, y - pad, x + w + pad, y + h + pad)
    else:
        pad = 8
        sx0, sy0 = (x - pad) * SS, (y - pad) * SS
        sx1, sy1 = (x + w + pad) * SS, (y + h + pad) * SS
        d.rounded_rectangle([sx0, sy0, sx1, sy1],
                            radius=12 * SS, outline=color_rgb + (255,),
                            width=stroke * SS)
        shape_box = (x - pad, y - pad, x + w + pad, y + h + pad)

    # Render the arrow into the same supersampled overlay so the line and
    # arrowhead are anti-aliased when we downsample.
    arrow_tail = None  # remember where the arrow starts, so the caption can
                      # anchor near it instead of at a page corner.
    if arrow_from:
        sx0, sy0, sx1, sy1 = shape_box
        cx, cy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
        diag = 0.70710678  # sqrt(2)/2
        dirs = {
            "tl": (-diag, -diag), "tr": (diag, -diag),
            "bl": (-diag, diag),  "br": (diag, diag),
        }
        ux, uy = dirs.get(arrow_from, (diag, -diag))
        start = (int(cx + ux * arrow_length), int(cy + uy * arrow_length))
        margin = 12
        start = (max(margin, min(W - margin, start[0])),
                 max(margin, min(H - margin, start[1])))
        end = clip_line_to_box_edge(start, shape_box, gap=10)
        # Scale endpoints into the 2x overlay coordinate space.
        start_hi = (start[0] * SS, start[1] * SS)
        end_hi = (end[0] * SS, end[1] * SS)
        draw_arrow(overlay_hi, start_hi, end_hi, color_rgb, stroke * SS)
        arrow_tail = start

    overlay = overlay_hi.resize((W, H), Image.LANCZOS)
    out = Image.alpha_composite(base, overlay)

    if caption:
        if arrow_tail is not None:
            # Anchor caption at the arrow tail, nudged outward along the same
            # direction so it sits past the tail rather than on top of it.
            ax, ay = arrow_tail
            anchor = (ax + int(ux * 8), ay + int(uy * 8) - 18)
        else:
            anchor = (shape_box[0], max(8, shape_box[1] - 50))
        draw_caption(out, caption, anchor, color_rgb)
    return out


def clip_line_to_box_edge(start, box, gap=8):
    """Return the point on the rounded outside of `box` along the segment
    from `start` toward the box center, offset outward by `gap` pixels so
    arrowheads don't visually crash into the box outline."""
    import math
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    sx, sy = start
    dx, dy = cx - sx, cy - sy
    if dx == 0 and dy == 0:
        return (int(cx), int(cy))
    # Parametric line from start toward center. Find smallest t in (0,1]
    # such that the point hits the box boundary.
    ts = []
    if dx != 0:
        for bx in (x0, x1):
            t = (bx - sx) / dx
            y = sy + t * dy
            if 0 < t <= 1 and y0 <= y <= y1:
                ts.append(t)
    if dy != 0:
        for by in (y0, y1):
            t = (by - sy) / dy
            x = sx + t * dx
            if 0 < t <= 1 and x0 <= x <= x1:
                ts.append(t)
    t = min(ts) if ts else 1.0
    ex, ey = sx + t * dx, sy + t * dy
    # Pull back along the direction by `gap` pixels.
    length = math.hypot(dx, dy)
    if length > 0:
        ex -= (dx / length) * gap
        ey -= (dy / length) * gap
    return (int(ex), int(ey))


def place_inset_adjacent(target, inset_size, img_size, gap=36, margin=24):
    """Pick (ix, iy) so the inset sits next to the target on the side with the
    most free space, clamped to stay in the image. Order tried: right, left,
    below, above. Falls back to bottom-right page corner if nothing fits."""
    tx, ty, tw, th = target
    iw, ih = inset_size
    W, H = img_size

    candidates = []  # (preference_score, ix, iy, side)
    # Right of target
    ix = tx + tw + gap
    iy = ty + th // 2 - ih // 2
    if ix + iw <= W - margin:
        iy = max(margin, min(H - ih - margin, iy))
        free = W - (tx + tw)  # free space on this side
        candidates.append((free, ix, iy, "right"))
    # Left of target
    ix = tx - gap - iw
    iy = ty + th // 2 - ih // 2
    if ix >= margin:
        iy = max(margin, min(H - ih - margin, iy))
        free = tx
        candidates.append((free, ix, iy, "left"))
    # Below target
    iy = ty + th + gap
    ix = tx + tw // 2 - iw // 2
    if iy + ih <= H - margin:
        ix = max(margin, min(W - iw - margin, ix))
        free = H - (ty + th)
        candidates.append((free, ix, iy, "below"))
    # Above target
    iy = ty - gap - ih
    ix = tx + tw // 2 - iw // 2
    if iy >= margin:
        ix = max(margin, min(W - iw - margin, ix))
        free = ty
        candidates.append((free, ix, iy, "above"))

    if candidates:
        candidates.sort(reverse=True)
        _, ix, iy, _ = candidates[0]
        return ix, iy
    # Fallback: clamp into bottom-right
    return (max(margin, W - iw - margin), max(margin, H - ih - margin))


def draw_dashed_line(img, start, end, color_rgba, width=2, dash=10, gap=8):
    import math
    d = ImageDraw.Draw(img, "RGBA")
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    length = math.hypot(dx, dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    dist = 0.0
    while dist < length:
        x1 = sx + ux * dist
        y1 = sy + uy * dist
        seg_end = min(dist + dash, length)
        x2 = sx + ux * seg_end
        y2 = sy + uy * seg_end
        d.line([(x1, y1), (x2, y2)], fill=color_rgba, width=width)
        dist += dash + gap


def draw_arrow(img, start, end, color_rgb, stroke):
    import math
    d = ImageDraw.Draw(img, "RGBA")
    sx, sy = start
    ex, ey = end
    d.line([sx, sy, ex, ey], fill=color_rgb + (255,), width=stroke)
    # Arrowhead
    angle = math.atan2(ey - sy, ex - sx)
    head_len = max(18, stroke * 5)
    head_w = max(10, stroke * 3)
    left = (ex - head_len * math.cos(angle - 0.4),
            ey - head_len * math.sin(angle - 0.4))
    right = (ex - head_len * math.cos(angle + 0.4),
             ey - head_len * math.sin(angle + 0.4))
    d.polygon([end, left, right], fill=color_rgb + (255,))


def style_cursor_zoom(img, target, is_point, zoom_factor, zoom_corner,
                      show_cursor, show_zoom, color_rgb, caption,
                      cursor_color="auto", cursor_size=56):
    base = img.convert("RGBA")
    W, H = base.size
    x, y, w, h = target

    # Cursor overlay at top-left of target (or at the point itself).
    # For small targets, scale the cursor down so it doesn't overwhelm the UI.
    if show_cursor:
        if cursor_color == "auto":
            variant = detect_cursor_variant(base, target)
        elif cursor_color in ("white", "light"):
            variant = "light"
        else:
            variant = "dark"
        cursor = load_or_make_cursor(variant)
        # Resize to requested size; default cursor asset is 56px.
        if cursor_size and cursor_size != cursor.width:
            cursor = cursor.resize((cursor_size, cursor_size), Image.LANCZOS)
        # Auto-shrink for tiny targets so the cursor doesn't swallow the UI.
        tgt_min = min(w, h)
        if tgt_min < cursor.width * 0.8:
            scale = max(0.4, tgt_min / (cursor.width * 1.2))
            new_size = (max(16, int(cursor.width * scale)),
                        max(16, int(cursor.height * scale)))
            cursor = cursor.resize(new_size, Image.LANCZOS)
        # Place cursor TIP at the target's center. The macOS cursor's hotspot
        # is at the top-left corner of the cursor image (the pointer tip).
        # Scale the tip offset with cursor size.
        tip_scale = cursor.width / 56
        tip_x, tip_y = int(2 * tip_scale), int(2 * tip_scale)
        target_cx, target_cy = x + w // 2, y + h // 2
        base.paste(cursor, (target_cx - tip_x, target_cy - tip_y), cursor)

    if show_zoom:
        # Crop focus region with padding
        pad = max(20, int(min(w, h) * 0.3))
        cx0, cy0 = max(0, x - pad), max(0, y - pad)
        cx1, cy1 = min(W, x + w + pad), min(H, y + h + pad)
        crop = base.crop((cx0, cy0, cx1, cy1))
        zw = int(crop.width * zoom_factor)
        zh = int(crop.height * zoom_factor)
        # Cap inset to ~35% of image
        max_w, max_h = int(W * 0.35), int(H * 0.35)
        if zw > max_w or zh > max_h:
            scale = min(max_w / zw, max_h / zh)
            zw, zh = max(1, int(zw * scale)), max(1, int(zh * scale))
        zoomed = crop.resize((zw, zh), Image.LANCZOS)

        # By default, place the inset ADJACENT to the target (small gap, on the
        # side with the most free space) so the connection between target and
        # zoom is visually obvious. Only pin to a page corner when the user
        # explicitly passes --zoom-corner.
        margin = 24
        gap = 36
        if zoom_corner:
            corners = {
                "tl": (margin, margin),
                "tr": (W - zw - margin, margin),
                "bl": (margin, H - zh - margin),
                "br": (W - zw - margin, H - zh - margin),
            }
            ix, iy = corners.get(zoom_corner, corners["br"])
        else:
            ix, iy = place_inset_adjacent(target, (zw, zh), (W, H), gap, margin)

        # Border + shadow
        shadow = Image.new("RGBA", (zw + 16, zh + 16), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle([8, 8, zw + 16, zh + 16], radius=14, fill=(0, 0, 0, 110))
        shadow = shadow.filter(ImageFilter.GaussianBlur(8))
        base.alpha_composite(shadow, (ix - 8, iy - 8))

        # Frame
        frame = Image.new("RGBA", (zw, zh), (0, 0, 0, 0))
        fd = ImageDraw.Draw(frame)
        fd.rounded_rectangle([0, 0, zw - 1, zh - 1], radius=12, outline=color_rgb + (255,), width=4)
        # Mask the zoom into rounded shape
        mask = Image.new("L", (zw, zh), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, zw, zh], radius=12, fill=255)
        base.paste(zoomed, (ix, iy), mask)
        base.alpha_composite(frame, (ix, iy))

        # Connector: thin dashed line from the target edge to the inset edge,
        # clipped so it starts/ends just outside each box.
        tgt_box = (x, y, x + w, y + h)
        inset_box = (ix, iy, ix + zw, iy + zh)
        icx, icy = (ix + zw) // 2, (iy + zh) // 2
        tcx, tcy = (x + x + w) // 2, (y + y + h) // 2
        start_pt = clip_line_to_box_edge((icx, icy), tgt_box, gap=6)
        end_pt = clip_line_to_box_edge((tcx, tcy), inset_box, gap=6)
        draw_dashed_line(base, end_pt, start_pt,
                         color_rgb + (170,), width=2, dash=10, gap=7)

    if caption:
        # Anchor caption near the inset when one is shown — far from the
        # actual UI we're trying not to obscure.
        if show_zoom:
            margin = 24
            # Place caption just below the inset; if it would clip the bottom,
            # place above. Horizontal: align to inset's left edge.
            anchor_y = iy + zh + 10
            if anchor_y + 40 > H - margin:
                anchor_y = max(margin, iy - 50)
            draw_caption(base, caption, (ix, anchor_y), color_rgb)
        else:
            draw_caption(base, caption, (x, max(8, y - 50)), color_rgb)
    return base


def load_or_make_cursor(variant="dark"):
    """variant: 'dark' (black cursor for light UIs) or 'light' (white cursor for dark UIs)."""
    name = "macos-cursor.png" if variant == "dark" else "macos-cursor-white.png"
    p = ASSETS_DIR / name
    if p.exists():
        return Image.open(p).convert("RGBA")
    # Fallback: draw a simple arrow cursor in the requested color
    fill = (17, 17, 17, 255) if variant == "dark" else (245, 245, 245, 255)
    outline = (255, 255, 255, 255) if variant == "dark" else (17, 17, 17, 255)
    size = 36
    cur = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(cur)
    poly = [(2, 2), (2, 28), (10, 22), (15, 32), (19, 30), (14, 21), (22, 21)]
    d.polygon(poly, fill=fill, outline=outline)
    return cur


def detect_cursor_variant(img_rgba, target):
    """Sample background brightness around the target and pick a cursor variant
    that contrasts with it. Dark background → light cursor; light → dark."""
    x, y, w, h = target
    W, H = img_rgba.size
    # Sample a ring outside the target so we read the actual background,
    # not the element being pointed at (which could mislead the heuristic).
    pad = max(20, int(max(w, h) * 0.4))
    bx0, by0 = max(0, x - pad), max(0, y - pad)
    bx1, by1 = min(W, x + w + pad), min(H, y + h + pad)
    crop = img_rgba.convert("RGB").crop((bx0, by0, bx1, by1))
    crop.thumbnail((64, 64))
    pixels = list(crop.getdata())
    n = len(pixels) or 1
    lum = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in pixels) / n
    return "light" if lum < 110 else "dark"


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Annotate a screenshot to highlight a focus area.")
    ap.add_argument("--input", required=True, help="Input image path")
    ap.add_argument("--output", required=True, help="Output image path (PNG)")
    ap.add_argument("--style", required=True,
                    choices=["spotlight", "blur", "shape", "cursor-zoom"])
    ap.add_argument("--region", help="Area target: 'x,y,w,h'")
    ap.add_argument("--point", help="Point target: 'x,y'")
    ap.add_argument("--radius", type=int, default=80,
                    help="Radius around --point (default 80)")
    ap.add_argument("--caption", help="Optional caption text")
    ap.add_argument("--color", help="Hex color e.g. #E53935")
    # Style-specific
    ap.add_argument("--dim-opacity", type=float, default=0.65,
                    help="spotlight: 0.0-1.0 darkness outside focus")
    ap.add_argument("--blur-radius", type=int, default=8,
                    help="blur: Gaussian radius")
    ap.add_argument("--shape", choices=["circle", "rect"], default="rect",
                    help="shape: which outline to draw (default rect for areas)")
    ap.add_argument("--stroke", type=int, default=4, help="shape: stroke width")
    ap.add_argument("--arrow-from", choices=["tl", "tr", "bl", "br"],
                    help="shape: arrow direction relative to the shape (top-left, "
                         "top-right, bottom-left, bottom-right). The arrow originates "
                         "~140px from the shape in this direction, NOT from the page "
                         "corner. Use --arrow-length to adjust.")
    ap.add_argument("--arrow-length", type=int, default=140,
                    help="shape: arrow length in pixels, measured from the shape edge "
                         "outward in the --arrow-from direction. Default 140.")
    ap.add_argument("--zoom-factor", type=float, default=2.0,
                    help="cursor-zoom: magnification")
    ap.add_argument("--zoom-corner", choices=["tl", "tr", "bl", "br"], default=None,
                    help="cursor-zoom: pin the inset to a page corner. By default the "
                         "inset is placed adjacent to the target on the side with the "
                         "most free space.")
    ap.add_argument("--no-cursor", action="store_true", help="cursor-zoom: skip cursor")
    ap.add_argument("--no-zoom", action="store_true", help="cursor-zoom: skip zoom inset")
    ap.add_argument("--cursor-color", choices=["auto", "dark", "black", "light", "white"],
                    default="auto",
                    help="cursor-zoom: cursor color. 'auto' picks based on background "
                         "brightness; 'dark/black' for light UIs; 'light/white' for dark UIs.")
    ap.add_argument("--cursor-size", type=int, default=56,
                    help="cursor-zoom: cursor size in pixels (square). Default 56. "
                         "Auto-shrinks if the target is smaller than the cursor.")
    args = ap.parse_args()

    img = Image.open(args.input).convert("RGBA")
    region = parse_region(args.region)
    point = parse_point(args.point)
    target, is_point = normalize_target(region, point, args.radius, img.size)
    target = clamp_box(target, img.size)
    color_rgb = hex_to_rgb(args.color)

    if args.style == "spotlight":
        out = style_spotlight(img, target, is_point, args.dim_opacity, color_rgb, args.caption)
    elif args.style == "blur":
        out = style_blur(img, target, is_point, args.blur_radius, color_rgb, args.caption)
    elif args.style == "shape":
        kind = "circle" if is_point else args.shape
        out = style_shape(img, target, is_point, kind, color_rgb, args.stroke,
                          args.caption, args.arrow_from,
                          arrow_length=args.arrow_length)
    elif args.style == "cursor-zoom":
        show_cursor = not args.no_cursor
        show_zoom = not args.no_zoom
        if not (show_cursor or show_zoom):
            print("cursor-zoom: nothing to draw (both --no-cursor and --no-zoom set)",
                  file=sys.stderr)
            sys.exit(2)
        # Normalize cursor color aliases
        cursor_color = args.cursor_color
        if cursor_color == "black":
            cursor_color = "dark"
        elif cursor_color == "white":
            cursor_color = "light"
        out = style_cursor_zoom(img, target, is_point, args.zoom_factor, args.zoom_corner,
                                show_cursor, show_zoom, color_rgb, args.caption,
                                cursor_color=cursor_color, cursor_size=args.cursor_size)
    else:
        raise SystemExit(f"unknown style {args.style}")

    out.convert("RGB").save(args.output, "PNG")
    print(args.output)


if __name__ == "__main__":
    main()
