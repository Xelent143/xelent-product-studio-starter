#!/usr/bin/env python3
"""Draw each product's size chart as an image: views/<id>/sizechart.png (2000 x 2000, white).

  size_chart.py --dir D [--only ID ...]

Measurements are typeset here, never generated: a generated chart invents numbers. The chart comes from the
product's `size_chart` in studio.json:

  "size_chart": {"unit": "cm", "how": "Measured flat across the garment", "columns": ["Chest width", "Body length", "Sleeve"],
                 "rows": {"S": [50, 70, 21], "M": [53, 72, 22]}, "inches": true, "tolerance": "±2 cm"}
"""
import argparse, os, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import font, load  # noqa: E402

S = 2000
INK, SOFT, RULE, BAND = (23, 23, 23), (105, 105, 105), (215, 215, 212), (246, 246, 244)


def fmt(v):
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


def table(d, x, y, w, title, columns, rows, conv=None):
    d.text((x, y), title, font=font(40, True), fill=INK)
    y += 70
    cols = ["Size"] + columns
    cw = w / len(cols)
    rh = min(96, int(1100 / (len(rows) + 1) / (2 if conv else 1)))
    hf, bf = font(max(22, min(34, int(cw / 7))), True), font(max(24, min(38, int(cw / 6))))
    d.rectangle((x, y, x + w, y + rh), fill=INK)
    for i, c in enumerate(cols):
        tw = d.textlength(c, font=hf)
        d.text((x + cw * i + (cw - tw) / 2, y + (rh - hf.size) / 2), c, font=hf, fill=(255, 255, 255))
    y += rh
    for r, (size, vals) in enumerate(rows.items()):
        if r % 2: d.rectangle((x, y, x + w, y + rh), fill=BAND)
        cells = [size] + [fmt(conv(v) if conv and isinstance(v, (int, float)) else v) for v in vals]
        for i, c in enumerate(cells):
            f = font(bf.size, i == 0)
            tw = d.textlength(c, font=f)
            d.text((x + cw * i + (cw - tw) / 2, y + (rh - f.size) / 2), c, font=f, fill=INK)
        y += rh
        d.line((x, y, x + w, y), fill=RULE, width=2)
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    D = os.path.abspath(a.dir)
    studio = load(os.path.join(D, "studio.json"))
    made = 0
    for p in studio["products"]:
        if a.only and p["id"] not in a.only: continue
        sc = p.get("size_chart")
        if not sc:
            print(f"{p['id']}: no size_chart in studio.json, skipped"); continue
        rows, cols = sc["rows"], sc["columns"]
        bad = [k for k, v in rows.items() if len(v) != len(cols)]
        if bad: sys.exit(f"{p['id']}: size_chart rows {', '.join(bad)} do not have {len(cols)} values")
        missing = [s for s in p.get("sizes", []) if s not in rows]
        if missing: sys.exit(f"{p['id']}: sizes {', '.join(missing)} are sold but have no row in size_chart")
        im = Image.new("RGB", (S, S), (255, 255, 255)); d = ImageDraw.Draw(im)
        m = 140
        d.text((m, 120), p["name"], font=font(64, True), fill=INK)
        d.text((m, 210), "SIZE CHART", font=font(36, True), fill=SOFT)
        unit = sc.get("unit", "cm")
        y = table(d, m, 330, S - 2 * m, f"Measurements ({unit})", cols, rows)
        if sc.get("inches", unit == "cm") and unit == "cm":
            y = table(d, m, y + 70, S - 2 * m, "Measurements (inches)", cols, rows, conv=lambda v: round(v / 2.54, 1))
        notes = [n for n in [sc.get("how"), f"Tolerance {sc['tolerance']}" if sc.get("tolerance") else None, sc.get("note")] if n]
        ny = max(y + 60, S - 120 - 56 * len(notes))
        for n in notes:
            d.text((m, ny), n, font=font(34), fill=SOFT); ny += 56
        brand = studio.get("brand", {}).get("name", "")
        if brand:
            d.text((S - m - d.textlength(brand, font=font(30, True)), 130), brand, font=font(30, True), fill=SOFT)
        out = os.path.join(D, "views", p["id"], "sizechart.png")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        im.save(out); made += 1
        print("size chart:", out)
    print(f"{made} size charts drawn")


if __name__ == "__main__":
    main()
