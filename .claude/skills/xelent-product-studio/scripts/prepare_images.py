#!/usr/bin/env python3
"""Turn the approved photographs into marketplace-ready JPEGs: export/<id>/<marketplace>/NN-<name>.jpg + manifest.json.

  prepare_images.py --dir D [--only ID ...] [--marketplace alibaba etsy]

alibaba  up to 6 images, 1600 x 1600, white background, product filling ~85% of the main image, each under 3 MB.
etsy     up to 20 images, 2000 x 2000 (Etsy asks for 2000 px on the shortest side), sRGB, each about 1 MB.

The order comes from marketplaces.<m>.image_order in studio.json. Tokens: front back left right side (the first side
view that exists) open detail flatlay lifestyle colorways (every color-* image) sizechart. A missing image is skipped.
"""
import argparse, glob, hashlib, io, json, os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load, save  # noqa: E402

SPEC = {
    "alibaba": dict(side=1600, max_images=6, max_bytes=2_900_000, min_q=70,
                    order=["front", "back", "side", "detail", "lifestyle", "sizechart"], fallback=["flatlay", "colorways", "open", "right"]),
    "etsy": dict(side=2000, max_images=20, max_bytes=1_000_000, min_q=78,
                 order=["front", "lifestyle", "back", "side", "detail", "flatlay", "open", "colorways", "sizechart"], fallback=[]),
}


def expand(token, vdir):
    have = lambda n: os.path.exists(os.path.join(vdir, f"{n}.png"))
    if token == "side": return [n for n in ("left", "right") if have(n)][:1]
    if token == "colorways": return sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(vdir, "color-*.png")))
    return [token] if have(token) else []


def whiteness(im):
    w, h = im.size; b = max(4, w // 33)
    px = [im.getpixel((x, y)) for x in range(0, w, 7) for y in list(range(0, b, 3)) + list(range(h - b, h, 3))]
    px += [im.getpixel((x, y)) for y in range(0, h, 7) for x in list(range(0, b, 3)) + list(range(w - b, w, 3))]
    return sum(sum(p) / 3 for p in px) / len(px)


def product_box(im):
    """Bounding box of everything that is not near-white."""
    g = im.convert("L").point(lambda v: 255 if v < 238 else 0)
    return g.getbbox()


def fit_main(im, fill=0.86):
    """Crop to the product and pad it back to a white square so it fills about 86% of the frame."""
    box = product_box(im)
    if not box: return im, 0.0
    bw, bh = box[2] - box[0], box[3] - box[1]
    before = max(bw, bh) / im.width
    if before >= 0.8: return im, before
    side = int(max(bw, bh) / fill)
    cx, cy = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
    canvas = Image.new("RGB", (side, side), (255, 255, 255))
    canvas.paste(im, (side // 2 - cx, side // 2 - cy))  # shifted so the product is centred; the rest stays white
    return canvas, before


def encode(im, spec):
    for q in range(92, spec["min_q"] - 1, -3):
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= spec["max_bytes"]: return buf.getvalue(), q
    return buf.getvalue(), spec["min_q"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--marketplace", nargs="*", choices=list(SPEC))
    a = ap.parse_args()
    D = os.path.abspath(a.dir)
    studio = load(os.path.join(D, "studio.json"))
    approvals = load(os.path.join(D, "approvals.json"), {})
    enabled = [m for m, c in studio["marketplaces"].items() if c.get("enabled") and m in SPEC]
    markets = [m for m in (a.marketplace or enabled)]
    warnings = []
    for p in studio["products"]:
        if a.only and p["id"] not in a.only: continue
        if approvals.get(p["id"], {}).get("status") != "approved":
            print(f"{p['id']}: sheet not approved, skipped"); continue
        vdir = os.path.join(D, "views", p["id"])
        for m in markets:
            spec, cfg = SPEC[m], studio["marketplaces"].get(m, {})
            names = []
            for t in cfg.get("image_order") or spec["order"]:
                for n in expand(t, vdir):
                    if n not in names: names.append(n)
            for t in spec["fallback"]:
                if len(names) >= spec["max_images"]: break
                for n in expand(t, vdir):
                    if n not in names and len(names) < spec["max_images"]: names.append(n)
            names = names[:spec["max_images"]]
            if not names or names[0] != "front":
                warnings.append(f"{p['id']}/{m}: the first image is {names[0] if names else 'missing'}; the front view should lead.")
            out_dir = os.path.join(D, "export", p["id"], m)
            os.makedirs(out_dir, exist_ok=True)
            for old in glob.glob(os.path.join(out_dir, "*.jpg")): os.remove(old)
            manifest = []
            for i, n in enumerate(names, 1):
                src = os.path.join(vdir, f"{n}.png")
                im = Image.open(src)
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGBA"); bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im); im = bg
                im = im.convert("RGB")
                if im.width != im.height:
                    s = max(im.size); c = Image.new("RGB", (s, s), (255, 255, 255)); c.paste(im, ((s - im.width) // 2, (s - im.height) // 2)); im = c
                if m == "alibaba" and i == 1:
                    white = whiteness(im)
                    if white < 246: warnings.append(f"{p['id']}/alibaba: the main image background is not white (border brightness {white:.0f}/255); regenerate the front on white.")
                    im, before = fit_main(im)
                    if before and before < 0.8: print(f"{p['id']}/alibaba: main image re-framed, product filled {before:.0%} of the frame, now about 86%")
                im = im.resize((spec["side"], spec["side"]), Image.LANCZOS)
                data, q = encode(im, spec)
                name = f"{i:02d}-{n}.jpg"
                open(os.path.join(out_dir, name), "wb").write(data)
                manifest.append(dict(file=name, view=n, bytes=len(data), quality=q, sha256=hashlib.sha256(data).hexdigest()))
            save(os.path.join(out_dir, "manifest.json"), manifest)
            print(f"{p['id']}/{m}: {len(manifest)} images -> {out_dir}  ({', '.join(x['view'] for x in manifest)})")
            if m == "alibaba" and "sizechart" not in names and p.get("sizes"):
                warnings.append(f"{p['id']}/alibaba: no size chart image; run size_chart.py.")
    for w in warnings: print("warning:", w)


if __name__ == "__main__":
    main()
