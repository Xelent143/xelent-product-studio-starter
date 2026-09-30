#!/usr/bin/env python3
"""Plan the Xelent API jobs for one stage and write <dir>/jobs.json. run.mjs executes them.

  plan.py --dir D --stage sheets  [--only ID ...] [--fresh ID ...]
  plan.py --dir D --stage views   [--only ID ...] [--redo VIEW ...]
  plan.py --dir D --stage extras  [--only ID ...] [--redo NAME ...]

sheets  one concept sheet per product that is not approved yet: every view of the same product side by side.
views   approved products only: one photograph per view (at the chosen 2K or 4K), each drawn from the approved sheet.
extras  after the views exist: detail close-up, flat lay, on-body lifestyle and one front per extra colourway,
        each drawn from the approved sheet plus the finished front (and back) view, so they cannot drift.

Nothing is planned until the research is approved and the current designs pass (studio.py).
"""
import argparse, json, os, re, shutil, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from studio import gate, load  # noqa: E402

TYPES = {
    "gi": dict(noun="Brazilian jiu-jitsu gi jacket (kimono top), shown without pants or belt", views=["front", "back", "left", "right", "open"], kind="garment", lined=True),
    "jacket": dict(noun="jacket", views=["front", "back", "left", "right", "open"], kind="garment", lined=True),
    "top": dict(noun="top", views=["front", "back", "left", "right"], kind="garment"),
    "dress": dict(noun="dress", views=["front", "back", "left", "right"], kind="garment"),
    "bottom": dict(noun="pair of full-length trousers", views=["front", "back", "left", "right"], kind="legwear"),
    "vest": dict(noun="sleeveless vest", views=["front", "back", "left", "right"], kind="vest"),
    "gloves": dict(noun="pair of gloves", views=["front", "back", "left", "right"], kind="gloves"),
    "belt": dict(noun="martial arts belt", views=["front", "back", "left", "right"], kind="belt"),
    "headwear": dict(noun="cap", views=["front", "back", "left", "right"], kind="headwear"),
    "socks": dict(noun="pair of socks", views=["front", "back", "left", "right"], kind="socks"),
    "object": dict(noun="product", views=["front", "back", "left", "right"], kind="object"),
}
VIEW_TEXT = {
    "garment": {
        "front": "the front view, straight on",
        "back": "the back view, straight on from directly behind",
        "left": ("the left side view: a straight profile of the wearer's left side, turned so the front of the garment faces the LEFT edge "
                 "of the picture and the back faces the right edge; the left sleeve is nearest the camera, and anything on the left chest "
                 "shows near the front edge"),
        "right": ("the right side view: a straight profile of the wearer's right side, turned so the front of the garment faces the RIGHT "
                  "edge of the picture and the back faces the left edge; the right sleeve is nearest the camera, and anything on the left "
                  "chest is hidden"),
        "open": "the open view: the garment laid flat and fully open, seen from directly above, both front panels folded out to the sides and both sleeves spread out at full length, so the whole inside (lining, inner print, seam tape and the inside of the collar) is visible",
    },
    "legwear": {
        "front": "the front view, straight on, the whole garment from waistband to hem",
        "back": "the back view, straight on from directly behind, the whole garment from waistband to hem",
        "left": ("the left side view: a straight profile of the wearer's left leg and left side seam, the front of the garment facing the "
                 "LEFT edge of the picture, the whole garment from waistband to hem"),
        "right": ("the right side view: a straight profile of the wearer's right leg and right side seam, the front of the garment facing "
                  "the RIGHT edge of the picture, the whole garment from waistband to hem"),
    },
    "vest": {
        "front": "the front view, straight on",
        "back": "the back view, straight on from directly behind",
        "left": ("the left side view: a straight profile of the wearer's left side, the front of the garment facing the LEFT edge of the "
                 "picture, showing the left armhole and side seam (no sleeves)"),
        "right": ("the right side view: a straight profile of the wearer's right side, the front of the garment facing the RIGHT edge of "
                  "the picture, showing the right armhole and side seam (no sleeves)"),
    },
    "gloves": {
        "front": "the front view: the pair standing upright side by side, backs of the hands facing the camera",
        "back": "the back view: the pair turned round so the palm side faces the camera",
        "left": "the left side view: the pair in profile from the left, showing the thumb side and the cuff",
        "right": "the right side view: the pair in profile from the right, showing the little-finger side and the cuff",
    },
    "belt": {
        "front": "the front view: the belt coiled into a neat flat spiral lying face-on, both ends extending out to the right",
        "back": "the back view: the belt tied in a flat square knot as it sits when worn, shaped into a loop as if around a waist, no person",
        "left": "the left end: a close view of the rank-bar end of the belt",
        "right": "the right end: a close view of the other end of the belt, with its label",
    },
    "headwear": {
        "front": "the front view, straight on at eye level, the peak or brim pointing at the camera",
        "back": "the back view, straight on from directly behind, showing the closure and any back embroidery",
        "left": "the left side view, in profile, the peak pointing left",
        "right": "the right side view, in profile, the peak pointing right",
    },
    "socks": {
        "front": "the front view: the pair side by side on invisible leg forms, the front of the leg and the top of the foot facing the camera",
        "back": "the back view: the pair side by side on invisible leg forms, seen from behind, heels facing the camera",
        "left": "the outer side view: one sock in profile on an invisible leg form, toe pointing left, showing the outer side of the leg and foot",
        "right": "the inner side view: one sock in profile on an invisible leg form, toe pointing right, showing the inner side of the leg and foot",
    },
    "object": {
        "front": "the front view, straight on",
        "back": "the back view, straight on from behind",
        "left": "the left side view, in profile",
        "right": "the right side view, in profile",
    },
}
GHOST = ("Garments are shown on an invisible ghost mannequin: the garment holds the three-dimensional shape of an athletic body, "
         "but no body, mannequin, hanger or stand is visible and the openings are hollow.")
PRESENT = {
    "garment": GHOST + " The open view, when there is one, is a flat lay.",
    "legwear": GHOST, "vest": GHOST,
    "gloves": "No hands and no people; the gloves stand on their own.",
    "belt": "No people.",
    "headwear": "No head and no people; the cap holds its own shape as if worn, with the crown filled out.",
    "socks": "No legs and no people; the socks hold the shape of an invisible leg and foot.",
    "object": "The product stands on its own, with no people and no hands.",
}
BG = {
    "white": "Plain pure white seamless background (#FFFFFF) with a soft, natural contact shadow.",
    "grey": "Plain light grey seamless background (#EDEDED) with a soft, natural contact shadow.",
}
LINED_FRONT = ("The neck opening shows the inside of the garment: the lining, its print and any label on it are clearly visible behind "
               "the collar, exactly as they appear in the open view.")
EVERY = "Every logo, patch, label, tape and print that faces the camera in this view is visible and identical to the other views."
ORIENT = ("Left and right mean the wearer's left and right: in the front view the wearer's left side is on the right of the picture, "
          "in the back view it is on the left of the picture.")
NOTEXT = ("No labels, captions, arrows, measurements or watermark, and no text anywhere except what is printed, woven or stitched "
          "on the product itself as the design describes. No other brands' logos, no sports-league, club, event or federation marks.")
REAL = ("It must look like a real photograph of a real, manufactured product: true fabric weight and drape, real seams and stitch "
        "lines, trims and prints at their true scale, nothing that could not be sewn, printed or embroidered.")
ORDINALS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"]
EXTRAS = ["detail", "flatlay", "lifestyle", "colorways"]
WEARABLE = {"garment", "legwear", "vest", "headwear", "socks", "gloves"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def must_show(p, t, v):
    parts = []
    if t.get("lined") and v == "front": parts.append(LINED_FRONT)
    if p.get("view_details", {}).get(v): parts.append(p["view_details"][v])
    return " ".join(parts)


def construction(p):
    bits = [f"Fabric: {p['fabric']}" + (f", {p['gsm']} gsm" if p.get("gsm") else "") + "."]
    if p.get("fit"): bits.append(f"Fit: {p['fit']}.")
    if p.get("decoration"): bits.append("Decoration: " + ", ".join(p["decoration"]) + ", rendered exactly as that technique looks when manufactured.")
    return " ".join(bits)


def ref_line(labels, brand):
    parts = [f"The {ORDINALS[i]} attached image is {l}." for i, l in enumerate(labels)]
    if "the brand logo" in labels:
        parts.append("Every brand logo on the product must reproduce that logo exactly: the same shape and the same spelling"
                     + (f" ({brand['logo_description']})" if brand.get("logo_description") else "") + ".")
    return (" " + " ".join(parts)) if parts else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--stage", choices=["sheets", "views", "extras"], required=True)
    ap.add_argument("--only", nargs="*", default=None, help="product ids to include")
    ap.add_argument("--redo", nargs="*", default=None, help="views/extras: regenerate these even if the files exist")
    ap.add_argument("--fresh", nargs="*", default=[], help="sheets: do not attach the previous version for these ids")
    a = ap.parse_args()
    D = os.path.abspath(a.dir)
    gate(D, a.stage)
    studio = load(os.path.join(D, "studio.json"))
    brand, style = studio.get("brand", {}), studio.get("style", {})
    directions = {d["id"]: d for d in load(os.path.join(D, "research", "directions.json"), [])}
    ap_path = os.path.join(D, "approvals.json")
    approvals = load(ap_path, {})
    for p in studio["products"]:
        approvals.setdefault(p["id"], {"status": "pending", "version": 1, "notes": []})
    json.dump(approvals, open(ap_path, "w"), indent=1)

    def path(rel): return rel if os.path.isabs(rel) else os.path.normpath(os.path.join(D, rel))
    logo = path(brand["logo"]) if brand.get("logo") else None
    if logo and not os.path.exists(logo): sys.exit(f"logo not found: {logo}")
    bgname = style.get("background", "white") if style.get("background") in BG else "white"
    house = (" " + style["notes"]) if style.get("notes") else ""

    jobs = []
    for p in studio["products"]:
        if a.only is not None and p["id"] not in a.only: continue
        t = TYPES[p["type"]]
        kind, views = t["kind"], p.get("views") or t["views"]
        noun = p.get("noun") or t["noun"]
        st = approvals[p["id"]]
        ver = st["version"]
        use_logo = p.get("use_logo", brand.get("use_logo", False)) and bool(logo)
        extra_refs = [path(r) for r in p.get("refs", [])]
        orient = ORIENT if kind in ("garment", "legwear", "vest") else ""
        spec = f"\n\nThe product: {p['design']}\n{construction(p)}"

        if a.stage == "sheets":
            if st["status"] == "approved": continue
            refs, labels = [], []
            prev = os.path.join(D, "sheets", f"{p['id']}-v{ver - 1}.png")
            change = ""
            if st["status"] == "changes" and st["notes"]:
                attach = os.path.exists(prev) and p["id"] not in a.fresh
                if attach: refs.append(prev); labels.append("the previous version of this sheet")
                change = (" The previous version" + (" (attached)" if attach else "") + " was reviewed and these changes were asked for: "
                          + " ".join(st["notes"][-3:]) + " Apply exactly these changes and keep everything else the same.")
            if use_logo: refs.append(logo); labels.append("the brand logo")
            for r in extra_refs: refs.append(r); labels.append("a reference supplied by the client")
            panel = "; ".join(f"panel {i + 1}: {VIEW_TEXT[kind].get(v, v + ' view')}" + (f" (it must show: {must_show(p, t, v)})" if must_show(p, t, v) else "")
                              for i, v in enumerate(views))
            prompt = (f"Product design concept sheet for {brand.get('name', 'a brand')}: one single image showing the same {noun} from {len(views)} views, "
                      f"arranged left to right in {len(views)} equal panels with clear space between them ({panel}). Every panel shows the identical product: "
                      "the same design, colours, artwork, proportions and the same placement and size of every logo and trim; only the camera angle changes. "
                      "Each panel contains that one view of the product once, large, filling most of the panel's height with a small even margin above "
                      "and below, at the same scale as the other panels; the rest of the panel is clean, empty background, one continuous background across "
                      f"the whole sheet with no dividing lines. {EVERY} {orient} {PRESENT[kind]} {BG[bgname]} Soft even studio light, crisp detail, "
                      f"accurate colours. {REAL}{house} {NOTEXT}{spec}")
            prompt += ref_line(labels, brand) + change
            jobs.append(dict(name=f"sheet-{p['id']}-v{ver}", id=p["id"], view="sheet", out=os.path.join(D, "sheets", f"{p['id']}-v{ver}.png"),
                             aspect="21:9" if len(views) >= 5 else "16:9", refs=refs, prompt=prompt))
            continue

        if st["status"] != "approved": continue
        sheet = os.path.join(D, "sheets", f"{p['id']}-v{ver}.png")
        if not os.path.exists(sheet): sys.exit(f"{p['id']} is approved but {sheet} is missing")
        base_refs, base_labels = [sheet], ["the approved design sheet for this exact product, showing it from several angles"]
        if use_logo: base_refs.append(logo); base_labels.append("the brand logo")
        for r in extra_refs: base_refs.append(r); base_labels.append("a reference supplied by the client")
        vdir = os.path.join(D, "views", p["id"])

        def retire(out, name):
            if a.redo and name in a.redo and os.path.exists(out):
                old = os.path.join(vdir, "old"); os.makedirs(old, exist_ok=True)
                shutil.move(out, os.path.join(old, f"{name}-{int(time.time())}.png"))

        if a.stage == "views":
            one = "exactly one pair" if kind in ("gloves", "socks") else "exactly one"
            for n, v in enumerate(views, 1):
                out = os.path.join(vdir, f"{v}.png"); retire(out, v)
                ms = must_show(p, t, v)
                prompt = (f"Professional e-commerce product photograph of a {noun} for {brand.get('name', 'a brand')}. The first attached image is the "
                          f"approved design sheet for this exact product; its panel {n} of {len(views)} is the {v} view. Produce one photograph showing only "
                          f"{VIEW_TEXT[kind].get(v, v + ' view')}. The photograph contains {one} {noun}, shown once: never two copies, never "
                          "several angles side by side, never the other panels of the sheet. " + (f"This view must show: {ms} " if ms else "") +
                          f"{EVERY} {orient} Copy the design from the sheet exactly: the same colours, cloth, panels, trims, artwork, and "
                          "every logo in the same place and at the same size. Add nothing that is not on the sheet and leave nothing out. "
                          f"{PRESENT[kind]} The whole product centred in the frame, filling about 85% of it, with an even margin on all sides. {BG[bgname]} "
                          f"High-resolution detail: fabric texture, stitching and print crisp and sharp. {REAL}{house} {NOTEXT}\n\nDesign notes, for reference: "
                          f"{p['design']}\n{construction(p)}")
                prompt += ref_line(base_labels, brand)
                jobs.append(dict(name=f"view-{p['id']}-v{ver}-{v}", id=p["id"], view=v, out=out, aspect="1:1", refs=list(base_refs), prompt=prompt))
            continue

        # extras: anchored on the finished front and back views as well as the sheet
        front, back = os.path.join(vdir, "front.png"), os.path.join(vdir, "back.png")
        if not os.path.exists(front): sys.exit(f"{p['id']}: views/{p['id']}/front.png is missing; run the views stage first")
        refs, labels = [front], ["the finished front photograph of this exact product"]
        if os.path.exists(back): refs.append(back); labels.append("the finished back photograph of this exact product")
        refs += base_refs; labels += base_labels
        wanted = p.get("extras", ["detail", "flatlay", "lifestyle", "colorways"])
        direction = directions.get(p.get("direction"), {})
        copy = ("Copy the product exactly from the attached photographs: the same colours, cloth, panels, trims, artwork, and every logo "
                "in the same place and at the same size. Add nothing and leave nothing out.")

        if "detail" in wanted:
            out = os.path.join(vdir, "detail.png"); retire(out, "detail")
            focus = p.get("detail_focus") or "the main decoration and the fabric"
            prompt = (f"Close-up product detail photograph of the {noun} in the attached photographs: a tight macro crop showing {focus}. "
                      "Sharp enough to see the weave or knit of the fabric, the stitch lines and the texture of the decoration (embroidery thread relief, "
                      "the flat smoothness of a sublimated print, the edge of a heat-transfer or the raised surface of a patch, as appropriate). "
                      f"{copy} Soft, raking studio light that shows texture, shallow depth of field. {REAL} {NOTEXT}\n\nDesign notes: {p['design']}\n{construction(p)}")
            jobs.append(dict(name=f"extra-{p['id']}-v{ver}-detail", id=p["id"], view="detail", out=out, aspect="1:1", refs=list(refs), prompt=prompt + ref_line(labels, brand)))

        if "flatlay" in wanted and kind in WEARABLE | {"object"}:
            out = os.path.join(vdir, "flatlay.png"); retire(out, "flatlay")
            surface = p.get("flatlay_surface") or "a clean, light, softly textured neutral surface"
            prompt = (f"Styled flat-lay product photograph: the {noun} from the attached photographs laid flat and neatly arranged on {surface}, "
                      "seen from directly above, front side up, the whole product in frame with a comfortable margin. At most two small, unbranded "
                      f"props that suit the product and do not cover it. {copy} Soft, even daylight. {REAL} {NOTEXT}\n\nDesign notes: {p['design']}")
            jobs.append(dict(name=f"extra-{p['id']}-v{ver}-flatlay", id=p["id"], view="flatlay", out=out, aspect="1:1", refs=list(refs), prompt=prompt + ref_line(labels, brand)))

        if "lifestyle" in wanted and kind in WEARABLE:
            out = os.path.join(vdir, "lifestyle.png"); retire(out, "lifestyle")
            life = p.get("lifestyle", {})
            scene = life.get("scene") or direction.get("lifestyle_scene") or "a setting where this product is really used"
            person = life.get("model") or "an adult model whose build suits the product"
            prompt = (f"Lifestyle product photograph for an online store: {person} wearing the {noun} from the attached photographs, in {scene}. "
                      f"The product is the hero: fully visible from a flattering three-quarter angle, in sharp focus, occupying a large part of the frame. {copy} "
                      "The fit, length and proportions match the attached photographs. Natural, believable light and a realistic, candid pose; real skin "
                      "texture; nobody else's logos, no team, league or event branding anywhere in the scene. " + REAL + " " + NOTEXT +
                      f"\n\nDesign notes: {p['design']}\n{construction(p)}")
            jobs.append(dict(name=f"extra-{p['id']}-v{ver}-lifestyle", id=p["id"], view="lifestyle", out=out, aspect="1:1", refs=list(refs), prompt=prompt + ref_line(labels, brand)))

        if "colorways" in wanted:
            for cw in p.get("colorways", [])[1:]:
                name = f"color-{slug(cw['name'])}"
                out = os.path.join(vdir, f"{name}.png"); retire(out, name)
                recolour = cw.get("design") or f"the main colour becomes {cw['name']} ({cw.get('hex', '')}), with the trims and prints in colours that suit it"
                prompt = (f"Professional e-commerce product photograph: the same {noun} as the first attached photograph, identical in cut, panels, trims, "
                          f"artwork, logos, their placement and size, the angle, the framing and the lighting. Only the colours change: {recolour}. "
                          f"Colourway name: {cw['name']}. The photograph contains exactly one {noun}, shown once. "
                          f"{PRESENT[kind]} {BG[bgname]} {REAL} {NOTEXT}")
                jobs.append(dict(name=f"extra-{p['id']}-v{ver}-{name}", id=p["id"], view=name, out=out, aspect="1:1",
                                 refs=[front] + base_refs, prompt=prompt + ref_line(["the finished front photograph of this exact product"] + base_labels, brand)))

    for j in jobs:
        if len(j["prompt"]) > 9800: sys.exit(f"{j['name']}: the prompt is {len(j['prompt'])} characters; Xelent API takes 10,000. Shorten the design text.")
        if len(j["refs"]) > 8: sys.exit(f"{j['name']}: {len(j['refs'])} reference images; keep it to 8 or fewer.")
    json.dump(jobs, open(os.path.join(D, "jobs.json"), "w"), indent=1)
    if not jobs and a.stage != "sheets":
        print(f"{a.stage}: nothing to plan; no product has an approved sheet yet (approve.py --ids ...)."); return
    todo = [j for j in jobs if not os.path.exists(j["out"])]
    print(f"{a.stage}: {len(jobs)} jobs planned, {len(todo)} to generate ({len(jobs) - len(todo)} already on disk). "
          f"Next: node run.mjs --dir {a.dir}")


if __name__ == "__main__":
    main()
