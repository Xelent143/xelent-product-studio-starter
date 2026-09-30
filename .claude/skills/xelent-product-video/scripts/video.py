#!/usr/bin/env python3
"""Product videos for clothing: brief, shot plan, prompts, review strips and the final edit.

  video.py init --dir D [--from-studio WS --product ID]   new video workspace (optionally with Product Studio photos)
  video.py options                                        the menus to show the user: styles, looks, destinations
  video.py check --dir D                                  is brief.json complete and possible?
  video.py plan --dir D                                   shot list from the brief (plan.json)
  video.py jobs --dir D --stage cast|keyframes|clips [--only N ...] [--redo N ... --note "what to fix"]
  video.py approve --dir D --stage cast|keyframes         record the user's approval (clips need approved keyframes)
  video.py strip --dir D [--only N ...]                   contact sheet of each clip (2 frames a second) in qa/
  video.py assemble --dir D [--in N=SECONDS ...]          the final video in final/, trimmed to the exact length
  video.py board --dir D                                  review page (review.html): cast, keyframes, clips and the final video
  video.py status --dir D                                 where the video stands
  video.py links --dir D                                  web links to the stills and clips (for cloud sessions)

render.mjs runs the jobs on Xelent API. Stages: cast (the model wearing the product, one still), keyframes (the
first frame of every shot), clips (MiniMax H3 video, one per shot), then assemble.
"""
import argparse, glob, json, math, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "..", "references")
CATALOG = json.load(open(os.path.join(REF, "styles.json")))
LOOKS = {l["id"]: l for l in json.load(open(os.path.join(REF, "looks.json")))["looks"]}
STYLES = {s["id"]: s for s in CATALOG["styles"]}
SHOTS = CATALOG["shots"]
DESTS = CATALOG["destinations"]

IMAGE_MODEL = "nano-banana-2"  # stills: cast and keyframes, 2K
VIDEO_MODEL = "minimax-h3"
MAX_SHOT = {"480p": 15, "768p": 15, "1080p": 10}
TARGET_SHOT = 8  # seconds per shot in a multi-shot edit
VIEWS = ["front", "back", "left", "right", "open", "detail", "flatlay"]
SIZE = {"portrait": (1080, 1920), "landscape": (1920, 1080)}


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:40] or "video"


# ---------------------------------------------------------------------------
# init / options
# ---------------------------------------------------------------------------

def cmd_init(a):
    D = os.path.abspath(a.dir)
    path = os.path.join(D, "brief.json")
    if os.path.exists(path):
        sys.exit(f"{path} already exists; edit it instead.")
    for sub in ["cast", "keyframes", "clips", "qa", "final", "inputs"]:
        os.makedirs(os.path.join(D, sub), exist_ok=True)
    brief = load(os.path.join(REF, "brief.template.json"))
    if a.from_studio:
        WS = os.path.abspath(a.from_studio)
        studio = load(os.path.join(WS, "studio.json"), {})
        p = next((x for x in studio.get("products", []) if x.get("id") == a.product), None)
        if not p:
            sys.exit(f"No product {a.product!r} in {WS}/studio.json")
        vdir = os.path.join(WS, "views", p["id"])
        brief["product"].update(
            name=p.get("name", ""), noun=p.get("noun", ""), details=p.get("design", "")[:600],
            fabric=p.get("fabric", ""), photos={v: os.path.join(vdir, f"{v}.png") for v in VIEWS if os.path.exists(os.path.join(vdir, f"{v}.png"))},
            colorways=[{"name": c["name"], "photo": f} for c in p.get("colorways", [])
                       for f in [os.path.join(vdir, f"color-{slug(c['name'])}.png")] if os.path.exists(f)])
        brief["brand"] = studio.get("brand", {}).get("name", "")
    save(path, brief)
    print(f"Video workspace ready: {D}\nNext: ask the user the questions in SKILL.md and fill brief.json, then video.py check.")


def cmd_options(a):
    print("VIDEO STYLES")
    for i, s in enumerate(CATALOG["styles"], 1):
        extra = f" (needs: {', '.join(s['needs'])})" if s.get("needs") else ""
        mins = f" (at least {s['min_seconds']} s)" if s.get("min_seconds") else ""
        print(f"{i:2}. {s['name']} [{s['id']}]{extra}{mins}\n    {s['pitch']}\n    Best for: {s['best_for']}")
    print("\nLOOKS")
    for i, l in enumerate(LOOKS.values(), 1):
        print(f"{i:2}. {l['name']} [{l['id']}]: {l['pitch']} Best for: {l['best_for']}")
    print("\nWHERE IT WILL BE POSTED (sets the shape and sensible lengths)")
    for k, d in DESTS.items():
        print(f"  {d['name']} [{k}]: {d['aspect']}, {d['min']}-{d['max']} s" + (f". {d['note']}" if d.get("note") else ""))
    print("\nLENGTH: 5 to 15 s is one continuous shot (up to 10 s at 1080p); longer videos (up to 60 s) are edits of 5-10 s shots.")
    print("RESOLUTION: 768p (default, social media) or 1080p (sharper, about 2x the price per second, 10 s per shot). 480p for drafts.")


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def problems_of(D, brief):
    out = []
    p = brief.get("product", {})
    photos = {k: v for k, v in (p.get("photos") or {}).items() if v}
    if not p.get("noun"):
        out.append("product.noun is empty: say what it is, e.g. 'hooded hunting jacket' or 'football jersey'.")
    if "front" not in photos:
        out.append("product.photos.front is missing: at least a front photo is needed (front and back is much better).")
    for k, f in photos.items():
        if not os.path.exists(os.path.join(D, f) if not os.path.isabs(f) else f):
            out.append(f"product.photos.{k}: file not found: {f}")
    style = STYLES.get(brief.get("style"))
    if not style:
        out.append(f"style must be one of: {', '.join(STYLES)}")
    if brief.get("look") not in LOOKS:
        out.append(f"look must be one of: {', '.join(LOOKS)}")
    dest = DESTS.get(brief.get("destination"))
    if not dest:
        out.append(f"destination must be one of: {', '.join(DESTS)}")
    if brief.get("aspect") not in SIZE:
        out.append("aspect must be portrait (9:16) or landscape (16:9).")
    if brief.get("resolution") not in MAX_SHOT:
        out.append("resolution must be 480p, 768p or 1080p.")
    T = brief.get("duration")
    if not isinstance(T, int) or T < 5 or T > 60:
        out.append("duration must be a whole number of seconds from 5 to 60.")
    elif dest and not (dest["min"] <= T <= dest["max"]):
        out.append(f"{dest['name']} takes {dest['min']} to {dest['max']} seconds; duration is {T}.")
    elif style and T < style.get("min_seconds", 5):
        out.append(f"{style['name']} needs at least {style['min_seconds']} seconds.")
    m = brief.get("model", {})
    if style and style["who"] == "model":
        if m.get("type") not in ("ai", "own"):
            out.append("model.type must be 'ai' (describe the model) or 'own' (a photo of your model) for this style.")
        elif m["type"] == "ai" and not m.get("description"):
            out.append("model.description is empty: describe the AI model (gender, age range, look, build, hair).")
        elif m["type"] == "own":
            f = m.get("photo") or ""
            if not os.path.exists(os.path.join(D, f) if f and not os.path.isabs(f) else f):
                out.append(f"model.photo not found: {f!r}")
            if not m.get("consent"):
                out.append("model.consent must be true: the user confirmed the person agreed to appear in their ads.")
    for need in (style or {}).get("needs", []):
        if need == "sport" and not brief.get("sport"):
            out.append("sport is empty: which sport (e.g. football, boxing, running, BJJ)?")
        if need == "feature" and not brief.get("feature"):
            out.append("feature is empty: which feature to show (e.g. water beading off the fabric, four-way stretch)?")
        if need == "colorways" and len(p.get("colorways") or []) < 2:
            out.append("product.colorways needs at least two entries, each {name, photo}.")
    if brief.get("sound") not in ("keep", "mute"):
        out.append("sound must be keep or mute.")
    return out


def read_brief(D):
    brief = load(os.path.join(D, "brief.json"))
    if not brief:
        sys.exit("no brief.json here; run video.py init first")
    return brief


def cmd_check(a):
    D = os.path.abspath(a.dir)
    brief = read_brief(D)
    probs = problems_of(D, brief)
    if probs:
        print("Fix these before planning:\n- " + "\n- ".join(probs))
        sys.exit(1)
    dest = DESTS[brief["destination"]]
    if brief["resolution"] == "1080p" and brief["duration"] > 10:
        print("NOTE: at 1080p each shot is at most 10 s, so this will be an edit of several shots.")
    if brief["destination"] == "etsy" and brief["sound"] == "keep":
        print("NOTE: Etsy removes the sound from listing videos; the Etsy file is made silent.")
    print(f"Brief OK: {STYLES[brief['style']]['name']}, {LOOKS[brief['look']]['name']}, {brief['duration']} s, "
          f"{brief['aspect']} {brief['resolution']}, for {dest['name']}.")


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------

def split_seconds(total, n):
    base, extra = divmod(total, n)
    return [base + (1 if i < extra else 0) for i in range(n)]


def shot_sequence(brief):
    style = STYLES[brief["style"]]
    T, res = brief["duration"], brief["resolution"]
    cap = MAX_SHOT[res]
    if brief["style"] == "colorways":
        cws = brief["product"]["colorways"]
        n = max(1, min(len(cws), T // 5))
        return [("colorway", s, {"colorway": cws[i]["name"], "colorway_photo": cws[i]["photo"]}) for i, s in enumerate(split_seconds(T, n))]
    base = list(style["shots"])
    if len(base) == 1 and T <= cap:
        return [(base[0], T, {})]
    # An edit: the style's own shots first (its edit list starts with them), then supporting shots, ending on the
    # closing shot when the style has one.
    n = max(len(base), math.ceil(T / min(TARGET_SHOT, cap)))
    while n > 1 and T / n < 5:
        n -= 1
    cycle = style["edit"]
    if n >= 3 and "hero_close" in cycle:
        body = [x for x in cycle if x != "hero_close"]
        names = [body[i % len(body)] for i in range(n - 1)] + ["hero_close"]
    else:
        names = [cycle[i % len(cycle)] for i in range(n)]
    seconds = split_seconds(T, len(names))
    if max(seconds) > cap:
        sys.exit(f"{T} s does not fit in {len(names)} shots of at most {cap} s; choose a shorter video or 768p.")
    return [(name, s, {}) for name, s in zip(names, seconds)]


def cmd_plan(a):
    D = os.path.abspath(a.dir)
    brief = read_brief(D)
    probs = problems_of(D, brief)
    if probs:
        sys.exit("Fix the brief first (video.py check):\n- " + "\n- ".join(probs))
    old = load(os.path.join(D, "plan.json"), {})
    shots = []
    for i, (name, secs, extra) in enumerate(shot_sequence(brief), 1):
        prev = next((s for s in old.get("shots", []) if s["n"] == i and s["shot"] == name), None)
        shots.append(dict(n=i, shot=name, seconds=secs, who=SHOTS[name]["who"], **extra,
                          keyframe_version=(prev or {}).get("keyframe_version", 1), clip_version=(prev or {}).get("clip_version", 1),
                          notes=(prev or {}).get("notes", [])))
    needs_cast = any(s["who"] == "model" for s in shots) and brief["model"].get("type") in ("ai", "own")
    same = old.get("brief_hash") == hash_brief(brief)
    kept = [s["n"] for s in shots if same and s["n"] in old.get("approved", {}).get("keyframes", [])]
    plan = dict(brief_hash=hash_brief(brief), cast=needs_cast, cast_version=old.get("cast_version", 1), cast_notes=old.get("cast_notes", []),
                shots=shots, approved={"cast": same and old.get("approved", {}).get("cast", False), "keyframes": kept})
    save(os.path.join(D, "plan.json"), plan)
    print(f"Plan: {len(shots)} shot{'s' if len(shots) > 1 else ''}, {brief['duration']} s, {brief['aspect']} {brief['resolution']}"
          f"{', one cast still first' if needs_cast else ''}:")
    for s in shots:
        extra = f" ({s['colorway']})" if s.get("colorway") else ""
        print(f"  {s['n']}. {s['shot']}{extra}: {s['seconds']} s. {SHOTS[s['shot']]['action'].format(**fmt(brief, s))[:150]}")
    print("Cost: node render.mjs --dir <dir> --estimate")


def hash_brief(brief):
    import hashlib
    return hashlib.sha256(json.dumps(brief, sort_keys=True).encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# prompts
# ---------------------------------------------------------------------------

def fmt(brief, shot):
    p = brief["product"]
    return dict(noun=p.get("noun") or "garment", sport=brief.get("sport") or "the sport", feature=brief.get("feature") or "the main feature",
                detail=shot.get("detail") or brief.get("detail_focus") or "construction details",
                colorway=shot.get("colorway", ""), fabric=p.get("fabric") or "the garment fabric",
                decoration=brief.get("factory", {}).get("decoration") or "screen printing")


def rel(D, f):
    return f if os.path.isabs(f) else os.path.join(D, f)


VIEW_LABEL = {"front": "the product from the front", "back": "the product from the back", "left": "the product's left side",
              "right": "the product's right side", "detail": "a close-up detail of the product", "open": "the product opened, showing the inside",
              "flatlay": "the product laid flat"}


def product_refs(D, brief, shot, limit):
    """[(path, label)] of the product photos to send, most useful first."""
    photos = brief["product"].get("photos") or {}
    order = ["front", "back", "left", "right", "detail", "open", "flatlay"]
    if shot and shot.get("colorway_photo"):
        first = [(rel(D, shot["colorway_photo"]), f"the product in the {shot['colorway']} colourway, from the front")]
        return first + [(rel(D, photos[k]), VIEW_LABEL[k] + " (colour may differ)") for k in ["back"] if photos.get(k)][: limit - 1]
    return [(rel(D, photos[k]), VIEW_LABEL[k]) for k in order if photos.get(k)][:limit]


def legend(labels):
    return " Reference images: " + "; ".join(f"{i} is {label}" for i, label in enumerate(labels, 1)) + "."


def split(refs):
    return [p for p, _ in refs], [l for _, l in refs]


def look_lines(brief, spec):
    look = LOOKS["factory_floor"] if spec["who"] == "process" else LOOKS[brief["look"]]
    setting = spec.get("setting") or look["setting"]
    if look["id"] == "as_photo" and brief.get("scene"):
        setting += f" ({brief['scene']})"
    return setting, look


def framing(brief):
    return ("A vertical 9:16 frame." if brief["aspect"] == "portrait" else "A horizontal 16:9 frame.")


def product_line(noun):
    return (f"The {noun} is exactly the one in the product reference photos: the same colours, cloth, panels, prints, logos and "
            "trims, each in the same place and at the same size. Nothing is added or left out.")


def person_line(brief, who, has_cast):
    m = brief.get("model", {})
    if who == "mannequin":
        return "The garment is on the mannequin from the product photo, dressed exactly as in the photo; no person appears."
    if who == "none":
        return "No person, mannequin or hanger is visible."
    if who == "hands":
        return "Only hands are visible, no face."
    if who == "team":
        return "Four different adult athletes, all wearing the identical kit from the product reference photos."
    if who == "process":
        return "Factory workers are shown only as hands and working figures; no one poses for the camera."
    if has_cast:
        return ("The person is exactly the person in the cast reference image: the same face, hair, skin tone, build and "
                "the same trousers and shoes, wearing the product.")
    return f"The person is {m.get('description') or 'an adult model'}."


def cast_prompt(brief):
    m = brief["model"]
    noun = brief["product"]["noun"]
    who = ("the person in the first reference image, keeping their face, hair, skin tone and build exactly"
           if m["type"] == "own" else m["description"])
    refs_note = ("The first reference image is the model; the others are the product." if m["type"] == "own"
                 else "The reference images are the product.")
    return (f"Full-length studio photograph of {who}, wearing the {noun} from the product reference photos, standing relaxed and "
            f"facing the camera, the whole body from head to toe in frame. {refs_note} {product_line(noun)} "
            f"{('Worn with simple plain ' + brief['outfit'] + '.') if brief.get('outfit') else 'Worn with plain, neutral clothing that does not compete with it.'} "
            "Plain light grey studio background, soft even light, true colours. Photorealistic, sharp, natural skin. "
            "No text, no logos other than those on the product, no watermark.")


def keyframe_prompt(brief, shot, has_cast):
    spec = SHOTS[shot["shot"]]
    f = fmt(brief, shot)
    setting, look = look_lines(brief, spec)
    parts = [f"The first frame of a video, as one photorealistic still: {spec['opening'].format(**f)}.",
             person_line(brief, spec["who"], has_cast)]
    if spec["who"] != "process":
        parts.append(product_line(f["noun"]))
    parts += [f"Setting: {setting}.", f"Light: {look['light']}.", f"Look: {look['grade']}.", framing(brief),
              "Sharp, true colours, natural proportions. No added text, captions or watermark; the garment's own prints and lettering stay exactly as in the photos."]
    if shot.get("notes"):
        parts.append("Corrections: " + " ".join(shot["notes"]))
    return " ".join(parts)


def clip_prompt(brief, shot, has_cast):
    spec = SHOTS[shot["shot"]]
    f = fmt(brief, shot)
    setting, look = look_lines(brief, spec)
    parts = [f"{spec['camera']}.",
             f"The video opens exactly on the scene in the first reference image: {spec['opening'].format(**f)}.",
             spec["action"].format(**f),
             person_line(brief, spec["who"], has_cast)]
    if spec["who"] != "process":
        parts.append(product_line(f["noun"]) + " It stays the same for the whole video.")
    parts += [f"Setting: {setting}.", f"Light: {look['light']}.", f"Look: {look['grade']}.",
              "One continuous shot: no cuts, no scene changes, no new people appearing. Realistic, natural motion and anatomy.",
              "No added on-screen text, captions or watermarks; the garment's own prints and lettering stay exactly as in the photos.", f"Sound: {look['sound']}."]
    if shot.get("notes"):
        parts.append("Corrections: " + " ".join(shot["notes"]))
    return " ".join(parts)


# ---------------------------------------------------------------------------
# jobs
# ---------------------------------------------------------------------------

def paths(D, plan, shot=None):
    cast = os.path.join(D, "cast", f"cast-v{plan['cast_version']}.png")
    if shot is None:
        return cast
    return (cast, os.path.join(D, "keyframes", f"shot-{shot['n']:02d}-v{shot['keyframe_version']}.png"),
            os.path.join(D, "clips", f"shot-{shot['n']:02d}-v{shot['clip_version']}.mp4"))


def cmd_jobs(a):
    D = os.path.abspath(a.dir)
    brief = read_brief(D)
    plan = load(os.path.join(D, "plan.json"))
    if not plan:
        sys.exit("no plan.json; run video.py plan first")
    if plan["brief_hash"] != hash_brief(brief):
        sys.exit("brief.json changed since the plan was made; run video.py plan again.")
    only = set(a.only or []) | set(a.redo or [])
    shots = [s for s in plan["shots"] if not only or s["n"] in only]
    kf_aspect = "9:16" if brief["aspect"] == "portrait" else "16:9"
    jobs = []

    if a.stage == "cast":
        if not plan["cast"]:
            sys.exit("This video has no model shots, so there is no cast still. Go on to keyframes.")
        if a.redo is not None or a.note:
            plan["cast_version"] += 1
            if a.note:
                plan["cast_notes"].append(a.note)
            plan["approved"]["cast"] = False
        m = brief["model"]
        refs = ([(rel(D, m["photo"]), "the model")] if m["type"] == "own" else []) + product_refs(D, brief, None, 6)
        files, labels = split(refs)
        prompt = cast_prompt(brief) + (" Corrections: " + " ".join(plan["cast_notes"]) if plan["cast_notes"] else "") + legend(labels)
        jobs.append(dict(name=f"cast-v{plan['cast_version']}", kind="image", model=IMAGE_MODEL, aspect="3:4", imageSize="2K",
                         refs=files, prompt=prompt, out=paths(D, plan)))

    elif a.stage == "keyframes":
        if plan["cast"] and not plan["approved"]["cast"]:
            sys.exit("The cast still is not approved yet. Show it to the user, then video.py approve --stage cast.")
        cast = paths(D, plan)
        for s in shots:
            if a.redo and s["n"] in a.redo:
                s["keyframe_version"] += 1
                s["clip_version"] += 1
                if a.note:
                    s["notes"].append(a.note)
                plan["approved"]["keyframes"] = [n for n in plan["approved"]["keyframes"] if n != s["n"]]
            has_cast = plan["cast"] and s["who"] == "model"
            refs = [] if s["who"] == "process" else ([(cast, "the cast: the model wearing the product")] if has_cast else []) + product_refs(D, brief, s, 6)
            files, labels = split(refs)
            _, kf, _ = paths(D, plan, s)
            jobs.append(dict(name=f"keyframe-{s['n']:02d}-v{s['keyframe_version']}", kind="image", model=IMAGE_MODEL, aspect=kf_aspect,
                             imageSize="2K", refs=files, prompt=keyframe_prompt(brief, s, has_cast) + (legend(labels) if labels else ""), out=kf))

    elif a.stage == "clips":
        for s in shots:
            if s["n"] not in plan["approved"]["keyframes"]:
                sys.exit(f"Keyframe {s['n']} is not approved yet. Show the keyframes, then video.py approve --stage keyframes.")
            if a.redo and s["n"] in a.redo:
                s["clip_version"] += 1
                if a.note:
                    s["notes"].append(a.note)
            has_cast = plan["cast"] and s["who"] == "model"
            cast, kf, clip = paths(D, plan, s)
            if not os.path.exists(kf):
                sys.exit(f"Keyframe {s['n']} is missing ({kf}). Run render.mjs --restore, or make the keyframes again.")
            refs = [(kf, "the opening frame")]
            if s["who"] != "process":
                refs += ([(cast, "the cast: the model wearing the product")] if has_cast else []) + product_refs(D, brief, s, 9 - 1 - (1 if has_cast else 0))
            files, labels = split(refs[:9])
            jobs.append(dict(name=f"clip-{s['n']:02d}-v{s['clip_version']}", kind="video", model=VIDEO_MODEL,
                             aspect=brief["aspect"], resolution=brief["resolution"], duration=s["seconds"],
                             refs=files, prompt=clip_prompt(brief, s, has_cast) + legend(labels), out=clip))
    save(os.path.join(D, "plan.json"), plan)
    save(os.path.join(D, "jobs.json"), jobs)
    print(f"{len(jobs)} {a.stage} job{'s' if len(jobs) != 1 else ''} written to jobs.json. "
          f"Next: node render.mjs --dir {D} --quote, tell the user the cost, then node render.mjs --dir {D}")


def cmd_approve(a):
    D = os.path.abspath(a.dir)
    plan = load(os.path.join(D, "plan.json"))
    if a.stage == "cast":
        if not os.path.exists(paths(D, plan)):
            sys.exit("The cast still has not been made yet.")
        plan["approved"]["cast"] = True
    else:
        wanted = a.shots or [s["n"] for s in plan["shots"]]
        for s in plan["shots"]:
            if s["n"] in wanted and not os.path.exists(paths(D, plan, s)[1]):
                sys.exit(f"Keyframe {s['n']} has not been made yet.")
        plan["approved"]["keyframes"] = sorted(set(plan["approved"]["keyframes"]) | set(wanted))
    save(os.path.join(D, "plan.json"), plan)
    print(f"Approved {a.stage}" + (f": shots {', '.join(map(str, plan['approved']['keyframes']))}" if a.stage == "keyframes" else "."))


# ---------------------------------------------------------------------------
# ffmpeg: strips and the final edit
# ---------------------------------------------------------------------------

def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg is not installed. Install it with: python3 -m pip install imageio-ffmpeg")


def probe(path):
    """(duration seconds, has audio) from ffmpeg's own report; works without ffprobe."""
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0
    return dur, "Audio:" in r.stderr


def cmd_strip(a):
    from PIL import Image, ImageDraw
    D = os.path.abspath(a.dir)
    plan = load(os.path.join(D, "plan.json"))
    made = []
    for s in plan["shots"]:
        if a.only and s["n"] not in a.only:
            continue
        clip = paths(D, plan, s)[2]
        if not os.path.exists(clip):
            continue
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", clip, "-vf", "fps=2,scale=360:-2",
                            os.path.join(tmp, "f%03d.jpg")], check=True)
            frames = sorted(glob.glob(os.path.join(tmp, "f*.jpg")))
            if not frames:
                continue
            ims = [Image.open(f).convert("RGB") for f in frames]
            w, h = ims[0].size
            cols = 6
            rows = math.ceil(len(ims) / cols)
            sheet = Image.new("RGB", (cols * w, rows * (h + 22)), (18, 18, 18))
            d = ImageDraw.Draw(sheet)
            for i, im in enumerate(ims):
                x, y = (i % cols) * w, (i // cols) * (h + 22)
                sheet.paste(im, (x, y + 22))
                d.text((x + 6, y + 4), f"{i / 2:.1f}s", fill=(230, 230, 230))
            out = os.path.join(D, "qa", f"shot-{s['n']:02d}-v{s['clip_version']}.jpg")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            sheet.save(out, quality=82)
            dur, audio = probe(clip)
            made.append(out)
            print(f"shot {s['n']}: {dur:.1f} s{' with sound' if audio else ''}, strip {out}")
    if not made:
        sys.exit("No clips to check yet.")
    print("Look at every strip: one continuous shot (no cut to a new angle), the product matches the photos, the same face, "
          "natural hands and limbs, no text. Note any in-point (--in N=SECONDS) for assemble.")


def cmd_assemble(a):
    D = os.path.abspath(a.dir)
    brief = read_brief(D)
    plan = load(os.path.join(D, "plan.json"))
    ins = {}
    for item in a.ins or []:
        n, sec = item.split("=")
        ins[int(n)] = float(sec)
    W, H = SIZE[brief["aspect"]]
    clips, audio_ok = [], True
    for s in plan["shots"]:
        clip = paths(D, plan, s)[2]
        if not os.path.exists(clip):
            sys.exit(f"Clip {s['n']} is missing ({clip}). Render it, or run render.mjs --restore.")
        dur, has_audio = probe(clip)
        start = ins.get(s["n"], 0.0)
        if start + s["seconds"] > dur + 0.05:
            print(f"NOTE: clip {s['n']} is {dur:.1f} s; from {start:.1f} s it is short of {s['seconds']} s, so its last frame is held.")
        clips.append((clip, start, s["seconds"]))
        audio_ok = audio_ok and has_audio
    keep_sound = brief["sound"] == "keep" and audio_ok and brief["destination"] != "etsy"
    fade = LOOKS[brief["look"]]["fade"] if brief.get("transitions", "auto") == "auto" else brief["transitions"] == "fade"
    xf = 0.4 if fade and len(clips) > 1 else 0.0

    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y"]
    for clip, _, _ in clips:
        cmd += ["-i", clip]
    parts = []
    for i, (_, start, secs) in enumerate(clips):
        length = secs + (xf if i < len(clips) - 1 else 0)
        parts.append(f"[{i}:v]trim=start={start}:duration={length},setpts=PTS-STARTPTS,"
                     f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,fps=24,"
                     f"tpad=stop_mode=clone:stop_duration={length},trim=duration={length}[v{i}]")
        if keep_sound:
            parts.append(f"[{i}:a]atrim=start={start}:duration={length},asetpts=PTS-STARTPTS,aresample=48000,"
                         f"apad=whole_dur={length},afade=t=in:d=0.08,afade=t=out:st={max(0, length - 0.12)}:d=0.12[a{i}]")
    if len(clips) == 1:
        vout, aout = "[v0]", "[a0]" if keep_sound else None
    elif xf:
        prev, prev_a, offset = "[v0]", "[a0]", 0.0
        for i in range(1, len(clips)):
            offset += clips[i - 1][2]
            parts.append(f"{prev}[v{i}]xfade=transition=fade:duration={xf}:offset={offset:.3f}[vx{i}]")
            prev = f"[vx{i}]"
            if keep_sound:
                parts.append(f"{prev_a}[a{i}]acrossfade=d={xf}[ax{i}]")
                prev_a = f"[ax{i}]"
        vout, aout = prev, prev_a if keep_sound else None
    else:
        ins_list = "".join(f"[v{i}]" + (f"[a{i}]" if keep_sound else "") for i in range(len(clips)))
        parts.append(f"{ins_list}concat=n={len(clips)}:v=1:a={1 if keep_sound else 0}[vc]" + ("[ac]" if keep_sound else ""))
        vout, aout = "[vc]", "[ac]" if keep_sound else None
    name = f"{slug(brief['product'].get('name') or brief['product']['noun'])}-{brief['style']}-{brief['aspect']}-{brief['duration']}s"
    out = os.path.join(D, "final", name + ".mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd += ["-filter_complex", ";".join(parts), "-map", vout]
    if aout:
        cmd += ["-map", aout, "-c:a", "aac", "-b:a", "160k"]
    else:
        cmd += ["-an"]
    cmd += ["-t", str(brief["duration"]), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    poster = os.path.join(D, "final", name + "-poster.jpg")
    subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-ss", "1.0", "-i", out, "-frames:v", "1", "-q:v", "3", poster], check=True)
    dur, has_audio = probe(out)
    size = os.path.getsize(out) / 1e6
    print(f"FINAL: {out}\n  {W}x{H}, {dur:.2f} s, {'with sound' if has_audio else 'silent'}, {size:.1f} MB\n  poster: {poster}")
    dest = DESTS[brief["destination"]]
    if brief["destination"] == "etsy" and size > 100:
        print("WARNING: Etsy takes files up to 100 MB.")
    print(f"  made for {dest['name']}" + (f". {dest['note']}" if dest.get("note") else ""))


# ---------------------------------------------------------------------------
# status / links
# ---------------------------------------------------------------------------

def cmd_status(a):
    D = os.path.abspath(a.dir)
    brief = read_brief(D)
    plan = load(os.path.join(D, "plan.json"))
    print(f"Brief: {brief.get('style')} / {brief.get('look')} / {brief.get('duration')} s / {brief.get('aspect')} {brief.get('resolution')} / "
          f"{brief.get('destination')}")
    if not plan:
        print("Plan: not made (video.py plan)")
        return
    if plan["cast"]:
        c = paths(D, plan)
        print(f"Cast still: {'made' if os.path.exists(c) else 'not made'}{', approved' if plan['approved']['cast'] else ''}")
    for s in plan["shots"]:
        _, kf, clip = paths(D, plan, s)
        print(f"Shot {s['n']} {s['shot']} {s['seconds']} s: keyframe {'made' if os.path.exists(kf) else '-'}"
              f"{' (approved)' if s['n'] in plan['approved']['keyframes'] else ''}, clip {'made' if os.path.exists(clip) else '-'}")
    finals = sorted(glob.glob(os.path.join(D, "final", "*.mp4")))
    print("Final: " + (", ".join(finals) if finals else "not assembled"))


def cmd_board(a):
    import html as H
    D = os.path.abspath(a.dir)
    brief = read_brief(D)
    plan = load(os.path.join(D, "plan.json"))
    if not plan:
        sys.exit("no plan.json yet")
    r = lambda f: os.path.relpath(f, D)
    cards = []
    if plan["cast"] and os.path.exists(paths(D, plan)):
        cards.append(f"<section><h2>Model (cast){' · approved' if plan['approved']['cast'] else ''}</h2>"
                     f"<img src='{r(paths(D, plan))}' style='max-height:70vh'></section>")
    for s in plan["shots"]:
        _, kf, clip = paths(D, plan, s)
        media = ""
        if os.path.exists(clip):
            media = f"<video src='{r(clip)}' controls loop muted playsinline></video>"
        elif os.path.exists(kf):
            media = f"<img src='{r(kf)}'>"
        if media:
            state = "clip" if os.path.exists(clip) else "opening frame" + (" · approved" if s["n"] in plan["approved"]["keyframes"] else "")
            cards.append(f"<section><h2>{s['n']}. {H.escape(s['shot'].replace('_', ' '))} · {s['seconds']} s · {state}</h2>{media}</section>")
    for f in sorted(glob.glob(os.path.join(D, "final", "*.mp4"))):
        cards.append(f"<section><h2>Final: {H.escape(os.path.basename(f))}</h2><video src='{r(f)}' controls playsinline></video></section>")
    title = H.escape(f"{brief['product'].get('name') or brief['product'].get('noun')}: {STYLES[brief['style']]['name']}")
    page = (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>{title}</title>"
            "<style>body{font:15px system-ui;background:#111;color:#eee;margin:0;padding:16px}h1{font-size:20px}h2{font-size:15px;font-weight:500}"
            "main{display:flex;flex-wrap:wrap;gap:16px}section{background:#1c1c1c;padding:12px;border-radius:8px}"
            "img,video{display:block;max-height:60vh;max-width:100%;border-radius:4px}</style>"
            f"<h1>{title}</h1><p>Numbers refer to the shots. Tell me which to change and why.</p><main>{''.join(cards)}</main>")
    out = os.path.join(D, "review.html")
    open(out, "w").write(page)
    print("review page:", out)
    if os.environ.get("CLAUDE_CODE_REMOTE") == "true":
        print(f"CLOUD SESSION: the user cannot open this page. Give them the links from video.py links --dir {D}.")


def cmd_links(a):
    D = os.path.abspath(a.dir)
    ledger = load(os.path.join(D, "ledger.json"), {})
    rows = []
    for name, e in sorted(ledger.items()):
        ok = [x for x in e.get("attempts", []) if x.get("status") == "succeeded" and x.get("url")]
        if ok:
            rows.append(f"  {name}: {ok[-1]['url']}")
    if not rows:
        sys.exit("Nothing made yet.")
    print("\n".join(rows) + "\nLinks work for 7 days. The final edit is a file in final/; push it to the repository to share it.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("--dir", required=True); p.add_argument("--from-studio"); p.add_argument("--product")
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("options"); p.set_defaults(fn=cmd_options)
    for name, fn in [("check", cmd_check), ("plan", cmd_plan), ("status", cmd_status), ("links", cmd_links), ("board", cmd_board)]:
        p = sub.add_parser(name); p.add_argument("--dir", required=True); p.set_defaults(fn=fn)
    p = sub.add_parser("jobs"); p.add_argument("--dir", required=True); p.add_argument("--stage", required=True, choices=["cast", "keyframes", "clips"])
    p.add_argument("--only", nargs="+", type=int); p.add_argument("--redo", nargs="*", type=int); p.add_argument("--note"); p.set_defaults(fn=cmd_jobs)
    p = sub.add_parser("approve"); p.add_argument("--dir", required=True); p.add_argument("--stage", required=True, choices=["cast", "keyframes"])
    p.add_argument("--shots", nargs="+", type=int); p.set_defaults(fn=cmd_approve)
    p = sub.add_parser("strip"); p.add_argument("--dir", required=True); p.add_argument("--only", nargs="+", type=int); p.set_defaults(fn=cmd_strip)
    p = sub.add_parser("assemble"); p.add_argument("--dir", required=True); p.add_argument("--in", dest="ins", nargs="+"); p.set_defaults(fn=cmd_assemble)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
