"""Helpers shared by the Python scripts."""
import json, os

FONT_FILES = {
    False: ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"],
    True: ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"],
}


def font(size, bold=False):
    from PIL import ImageFont
    for f in FONT_FILES[bold]:
        if os.path.exists(f): return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def separate_objects(path, min_share=0.05):
    """How many separate large objects stand on the plain background of a studio shot.

    A view should hold one product (one pair for gloves and socks). A model that copies several panels of the
    concept sheet produces two or more; this catches it without looking. Shadows and faint texture are ignored.
    """
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((200, 200))
    w, h = im.size
    px = im.load()
    border = [px[x, y] for x in range(w) for y in (0, h - 1)] + [px[x, y] for y in range(h) for x in (0, w - 1)]
    bg = tuple(sorted(c[i] for c in border)[len(border) // 2] for i in range(3))
    fg = [[max(abs(px[x, y][i] - bg[i]) for i in range(3)) > 45 for x in range(w)] for y in range(h)]
    seen = [[False] * w for _ in range(h)]
    big = 0
    for y0 in range(h):
        for x0 in range(w):
            if not fg[y0][x0] or seen[y0][x0]: continue
            stack, area = [(x0, y0)], 0
            seen[y0][x0] = True
            while stack:
                x, y = stack.pop(); area += 1
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and fg[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True; stack.append((nx, ny))
            if area >= min_share * w * h: big += 1
    return big


def load(path, default=None):
    return json.load(open(path)) if os.path.exists(path) else default


def save(path, data):
    tmp = path + ".tmp"
    json.dump(data, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, path)
