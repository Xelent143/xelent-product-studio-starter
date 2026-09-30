#!/usr/bin/env python3
"""Review boards and pages for the user.

  board.py --dir D --stage sheets   review/<id>.jpg (numbered, named, views labelled), review/sheets-NN.jpg, review/index.html
  board.py --dir D --stage views    review/views-NN.jpg (sheet thumbnail, every view and extra per product), review/views.html

Labels are drawn here, not generated: generated text is unreliable and would leak into the final images.
"""
import argparse, glob, html, json, os, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import font, separate_objects  # noqa: E402
from plan import TYPES  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--dir", required=True)
ap.add_argument("--stage", choices=["sheets", "views"], required=True)
ap.add_argument("--per", type=int, default=0, help="items per board")
a = ap.parse_args()
D = os.path.abspath(a.dir)
studio = json.load(open(os.path.join(D, "studio.json")))
AP = os.path.join(D, "approvals.json")
st = json.load(open(AP)) if os.path.exists(AP) else {}
OUT = os.path.join(D, "review"); os.makedirs(OUT, exist_ok=True)
# a revised sheet that now exists goes back to "pending": it is waiting for the user again
changed = False
for i, s_ in st.items():
    if s_["status"] == "changes" and os.path.exists(os.path.join(D, "sheets", f"{i}-v{s_['version']}.png")): s_["status"] = "pending"; changed = True
if changed: json.dump(st, open(AP, "w"), indent=1)


INK, SOFT, W = (23, 23, 23), (98, 99, 100), 1800
COLOR = {"approved": (27, 120, 60), "changes": (190, 90, 0), "pending": (98, 99, 100)}
views_of = lambda p: p.get("views") or TYPES[p["type"]]["views"]
EXTRA_ORDER = ["detail", "flatlay", "lifestyle"]


def extras_of(p):
    vdir = os.path.join(D, "views", p["id"])
    found = [e for e in EXTRA_ORDER if os.path.exists(os.path.join(vdir, f"{e}.png"))]
    found += sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(vdir, "color-*.png")))
    return found


PAGE_CSS = ("body{margin:0;background:#e9e9e6;font:16px system-ui,sans-serif;color:#171717}header{position:sticky;top:0;background:#171717;color:#fff;padding:14px 20px;z-index:1}"
            "header p{margin:4px 0 0;opacity:.8}main{max-width:1800px;margin:0 auto;padding:16px}section{background:#fff;margin:0 0 18px;border-radius:4px;overflow:hidden}"
            "h2{margin:0;padding:12px 16px;font-size:20px}small{font-size:13px;margin-left:8px;padding:2px 8px;border-radius:3px;background:#eee}small.approved{background:#d5f0dc}"
            "small.changes{background:#fde2c8}img{display:block;width:100%;height:auto}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px;padding:0 12px 12px}"
            ".grid figure{margin:0}.grid figcaption{font-size:13px;color:#555;padding:4px 0;text-transform:uppercase;letter-spacing:.04em}")
made, suspects = [], []
brand = html.escape(studio.get("brand", {}).get("name", ""))

if a.stage == "sheets":
    rows = []
    for n, p in enumerate(studio["products"], 1):
        s = st.get(p["id"], {"status": "pending", "version": 1})
        f = os.path.join(D, "sheets", f"{p['id']}-v{s['version']}.png")
        if not os.path.exists(f): continue
        im = Image.open(f).convert("RGB"); im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
        head, foot = 64, 44
        c = Image.new("RGB", (W, head + im.height + foot), (255, 255, 255)); d = ImageDraw.Draw(c)
        d.text((24, 16), f"{n:02d}  {p['name']}", font=font(30, True), fill=INK)
        tag = f"{p['id']} · {p.get('direction', '')} · v{s['version']} · {s['status']}"
        d.text((W - 24 - d.textlength(tag, font=font(20)), 24), tag, font=font(20), fill=COLOR.get(s["status"], SOFT))
        c.paste(im, (0, head))
        vs = views_of(p); cw = W / len(vs)
        for i, v in enumerate(vs):
            t = v.upper(); d.text((cw * i + cw / 2 - d.textlength(t, font=font(20, True)) / 2, head + im.height + 10), t, font=font(20, True), fill=SOFT)
        c.save(os.path.join(OUT, f"{p['id']}.jpg"), quality=88); made.append(c)
        rows.append(f'<section><h2>{n:02d} &nbsp;{html.escape(p["name"])} <small class="{s["status"]}">{s["status"]}</small> <small>{html.escape(p.get("direction", ""))}</small></h2>'
                    f'<img src="{p["id"]}.jpg?v={s["version"]}" alt="{html.escape(p["name"])} concept sheet" loading="lazy"></section>')
    open(os.path.join(OUT, "index.html"), "w").write(
        f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Concept sheets</title><style>{PAGE_CSS}</style>"
        f"<header><b>{brand}: concept sheets for approval</b><p>Each sheet shows every view of one product. Reply with the numbers you approve "
        "and any changes.</p></header><main>" + "".join(rows) + "</main>")
    print("review page:", os.path.join(OUT, "index.html"))
    per = a.per or 4
else:
    rows = []
    for n, p in enumerate(studio["products"], 1):
        s = st.get(p["id"], {})
        if s.get("status") != "approved": continue
        vs = views_of(p) + extras_of(p)
        files = [os.path.join(D, "views", p["id"], f"{v}.png") for v in vs]
        if not any(os.path.exists(f) for f in files): continue
        T = 300; head = 50
        c = Image.new("RGB", (T * (len(vs) + 2), head + T + 36), (255, 255, 255)); d = ImageDraw.Draw(c)
        d.text((16, 12), f"{n:02d}  {p['name']}", font=font(26, True), fill=INK)
        sh = Image.open(os.path.join(D, "sheets", f"{p['id']}-v{s['version']}.png")).convert("RGB"); sh.thumbnail((T * 2 - 12, T))
        c.paste(sh, (6, head + (T - sh.height) // 2)); d.text((6, head + T + 6), "APPROVED SHEET", font=font(16, True), fill=SOFT)
        figs = []
        allowed = 2 if TYPES[p["type"]]["kind"] in ("gloves", "socks") else 1
        for i, (v, f) in enumerate(zip(vs, files)):
            x = T * (i + 2)
            if os.path.exists(f):
                im = Image.open(f).convert("RGBA"); im.thumbnail((T - 8, T - 8))
                bg = Image.new("RGBA", (T - 8, T - 8), (244, 244, 243, 255)); bg.alpha_composite(im, ((T - 8 - im.width) // 2, (T - 8 - im.height) // 2))
                c.paste(bg.convert("RGB"), (x + 4, head + 4))
                if (v in views_of(p) or v.startswith("color-")) and separate_objects(f) > allowed:
                    suspects.append(f"{p['id']}/{v}: more than one product in the picture (a copy of several sheet panels?); "
                                    f"redo it: plan.py --stage {'views' if v in views_of(p) else 'extras'} --only {p['id']} --redo {v}")
                    d.rectangle((x + 4, head + 4, x + T - 4, head + T - 4), outline=(200, 60, 60), width=5)
                thumb = os.path.join(OUT, "thumbs", p["id"], f"{v}.jpg"); os.makedirs(os.path.dirname(thumb), exist_ok=True)
                big = Image.open(f).convert("RGB"); big.thumbnail((900, 900)); big.save(thumb, quality=85)
                figs.append(f'<figure><img src="thumbs/{p["id"]}/{v}.jpg?t={int(os.path.getmtime(f))}" alt="{html.escape(p["name"])} {v}" loading="lazy"><figcaption>{v}</figcaption></figure>')
            else:
                d.rectangle((x + 4, head + 4, x + T - 4, head + T - 4), outline=(200, 60, 60), width=3); d.text((x + 20, head + T // 2), "missing", font=font(20), fill=(200, 60, 60))
            d.text((x + 8, head + T + 6), v.upper(), font=font(16, True), fill=SOFT)
        made.append(c)
        rows.append(f'<section><h2>{n:02d} &nbsp;{html.escape(p["name"])}</h2><div class="grid">{"".join(figs)}</div></section>')
    open(os.path.join(OUT, "views.html"), "w").write(
        f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Product photographs</title><style>{PAGE_CSS}</style>"
        f"<header><b>{brand}: product photographs</b><p>Every view and extra, per product. Tell me any image to redo and why.</p></header><main>"
        + "".join(rows) + "</main>")
    print("review page:", os.path.join(OUT, "views.html"))
    per = a.per or 6

boards = []
for b in range(0, len(made), per):
    group = made[b:b + per]; w = max(g.width for g in group); h = sum(g.height for g in group) + 16 * (len(group) - 1)
    board = Image.new("RGB", (w, h), (225, 225, 222)); y = 0
    for g in group: board.paste(g, (0, y)); y += g.height + 16
    name = os.path.join(OUT, f"{a.stage}-{b // per + 1:02d}.jpg")
    if board.width > 2400: board = board.resize((2400, round(board.height * 2400 / board.width)), Image.LANCZOS)
    board.save(name, quality=85); boards.append(name)
print(f"{len(made)} {a.stage} on {len(boards)} boards:"); print("\n".join(boards))
for s in suspects: print("CHECK:", s)
if os.environ.get("CLAUDE_CODE_REMOTE") == "true":
    which = "--stage sheets" if a.stage == "sheets" else "--stage views, then --stage extras"
    print(f"CLOUD SESSION: the user cannot open files on this machine. Give them the image links "
          f"(studio.py links --dir {D} {which}) and push the review/*.jpg boards to their GitHub branch.")
