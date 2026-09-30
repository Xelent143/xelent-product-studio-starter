#!/usr/bin/env python3
"""Workspace and gates for xelent-product-studio.

  studio.py init --dir D --brand "Name" [--marketplaces etsy alibaba]
  studio.py check-research --dir D                 are the research files complete and fresh?
  studio.py approve-research --dir D --directions ID [ID ...]   record the user's choice of directions
  studio.py check-designs --dir D                  are the product designs grounded, practical and clean?
  studio.py status --dir D                         where the workspace stands and what to do next
  studio.py set-resolution --dir D 2K|4K           the user's choice: 2K = Nano Banana 2, 4K = GPT Image 2.5 Sunburst
  studio.py links --dir D [--stage sheets|views|extras] [--only ID ...]   web links to the images (kept 7 days)

The order is enforced: plan.py refuses to draw anything until the research is approved and the designs pass.
"""
import argparse, datetime as dt, hashlib, json, os, re, sys
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import load, save  # noqa: E402

SOURCE_TYPES = {"trend", "colour", "category", "street", "materials", "marketplace", "competitor", "design-theory"}
MIN_SOURCES, MIN_TYPES, MIN_DIRECTIONS, FRESH_DAYS = 10, 4, 3, 45
BRIEF_SECTIONS = ["Scope", "Trend signals", "Colour", "Silhouettes and construction", "Graphics and decoration",
                  "Materials", "Demand and pricing", "Keyword bank", "Design directions", "Avoid"]

# Marks, events and uniforms that get listings removed or accounts closed (see references/ip-and-restricted.md).
BANNED = [
    r"\bnike\b", r"\badidas\b", r"\bpuma\b", r"\bunder armou?r\b", r"\breebok\b", r"\bnew balance\b", r"\bumbro\b", r"\bkappa\b",
    r"\blululemon\b", r"\bgymshark\b", r"\bsupreme\b", r"\bst[uü]ssy\b", r"\bbape\b", r"\boff-white\b", r"\bchampion (brand|hoodie|reverse weave)\b",
    r"\bthe north face\b", r"\bpatagonia\b", r"\bcarhartt\b", r"\bvenum\b", r"\bhayabusa\b", r"\bjordan\b", r"\byeezy\b",
    r"\bfifa\b", r"\bworld cup\b", r"\bmundial\b", r"\bolympic", r"\buefa\b", r"\bchampions league\b", r"\bpremier league\b",
    r"\bla ?liga\b", r"\bbundesliga\b", r"\bserie a\b", r"\bnba\b", r"\bnfl\b", r"\bmlb\b", r"\bnhl\b", r"\bmls\b", r"\bncaa\b",
    r"\bufc\b", r"\bwwe\b", r"\bipl\b", r"\bpsl\b", r"\breal madrid\b", r"\bbarcelona\b", r"\bmanchester (united|city)\b",
    r"\bliverpool fc\b", r"\bjuventus\b", r"\bpsg\b", r"\bpolice\b", r"\bmilitary (uniform|issue|insignia)\b", r"\barmy (uniform|issue)\b",
    r"\bswat\b", r"\bfbi\b", r"\bofficial\b", r"\blicensed\b", r"\breplica\b", r"\bsame style\b", r"\bdupe\b",
    r"\bdisney\b", r"\bmarvel\b", r"\bpok[eé]mon\b", r"\bnaruto\b", r"\bdragon ball\b", r"\bone piece (anime|manga)\b",
]

TYPES = {"gi", "jacket", "top", "bottom", "vest", "gloves", "belt", "object", "dress", "headwear", "socks"}


METHODS = [("sublimation", r"sublimat"), ("screen print", r"screen|silk ?screen|plastisol|water-?based ink"), ("embroidery", r"embroider"),
           ("heat transfer", r"heat[- ]?transfer|vinyl|\bhtv\b|heat[- ]?press"), ("dtf", r"\bdtf\b|direct[- ]to[- ]film"),
           ("dtg", r"\bdtg\b|direct[- ]to[- ]garment"), ("woven label", r"woven"), ("patch", r"patch|badge|applique|appliqué"),
           ("silicone print", r"silicone|\bhd print|high[- ]density"), ("puff print", r"puff"), ("tackle twill", r"tackle twill|twill"),
           ("reflective", r"reflective"), ("laser", r"laser|perforat"), ("jacquard", r"jacquard|knit-?in")]


def method_of(text):
    """The decoration method a phrase describes ("embroidered crest" -> embroidery), or the phrase itself."""
    t = text.lower()
    for name, pat in METHODS:
        if re.search(pat, t):
            return name
    return t.strip()


def banned_hits(text):
    t = text.lower()
    return sorted({m.group(0) for p in BANNED for m in re.finditer(p, t)})


def state_of(D):
    return load(os.path.join(D, "state.json"), {"research": {}, "designs": {}})


def products_hash(studio):
    return hashlib.sha256(json.dumps(studio.get("products", []), sort_keys=True).encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

def cmd_init(a):
    D = os.path.abspath(a.dir)
    for sub in ["research/notes", "sheets", "views", "review", "listings", "export"]:
        os.makedirs(os.path.join(D, sub), exist_ok=True)
    path = os.path.join(D, "studio.json")
    if os.path.exists(path):
        sys.exit(f"{path} already exists; edit it instead of re-running init.")
    template = json.load(open(os.path.join(HERE, "..", "references", "studio.template.json")))
    template["brand"]["name"] = a.brand
    for m in list(template["marketplaces"]):
        template["marketplaces"][m]["enabled"] = m in a.marketplaces
    save(path, template)
    save(os.path.join(D, "state.json"), {"research": {}, "designs": {}})
    print(f"Workspace ready: {D}\nNext: fill in studio.json (brand, business, marketplaces), then research (references/research-playbook.md).")


# ---------------------------------------------------------------------------
# research
# ---------------------------------------------------------------------------

def research_problems(D, studio):
    problems = []
    R = os.path.join(D, "research")
    sources = load(os.path.join(R, "sources.json"), [])
    brief_path = os.path.join(R, "brief.md")
    directions = load(os.path.join(R, "directions.json"), [])
    keywords = load(os.path.join(R, "keywords.json"), {})
    today = dt.date.today()

    if len(sources) < MIN_SOURCES:
        problems.append(f"research/sources.json has {len(sources)} sources; at least {MIN_SOURCES} are required.")
    types = {s.get("type") for s in sources}
    if len(types & SOURCE_TYPES) < MIN_TYPES:
        problems.append(f"sources cover {len(types & SOURCE_TYPES)} kinds ({', '.join(sorted(types & SOURCE_TYPES)) or 'none'}); cover at least {MIN_TYPES} of: {', '.join(sorted(SOURCE_TYPES))}.")
    if "marketplace" not in types:
        problems.append("no marketplace demand source (Etsy/Alibaba search, best-sellers, Google Trends).")
    urls = set()
    for i, s in enumerate(sources):
        u = s.get("url", "")
        if not urlparse(u).scheme.startswith("http"):
            problems.append(f"source {i + 1} has no http(s) url.")
        urls.add(u)
        if s.get("type") not in SOURCE_TYPES:
            problems.append(f"source {i + 1} ({u}) has type {s.get('type')!r}; use one of {', '.join(sorted(SOURCE_TYPES))}.")
        try:
            accessed = dt.date.fromisoformat(s.get("accessed", ""))
            if (today - accessed).days > FRESH_DAYS:
                problems.append(f"source {u} was read {accessed}; research older than {FRESH_DAYS} days must be refreshed.")
        except ValueError:
            problems.append(f"source {u} needs \"accessed\": \"YYYY-MM-DD\".")
        if not s.get("takeaways"):
            problems.append(f"source {u} has no takeaways: write what it tells you.")
    domains = {urlparse(u).netloc.removeprefix("www.") for u in urls}
    if len(domains) < 6:
        problems.append(f"sources come from {len(domains)} sites; use at least 6 different sites.")

    if not os.path.exists(brief_path):
        problems.append("research/brief.md is missing.")
    else:
        brief = open(brief_path).read()
        for sec in BRIEF_SECTIONS:
            if not re.search(rf"^##\s+{re.escape(sec)}\b", brief, re.M | re.I):
                problems.append(f"brief.md has no \"## {sec}\" section.")
        if len(brief) < 3000:
            problems.append(f"brief.md is {len(brief)} characters; a useful synthesis is at least 3,000.")

    if len(directions) < MIN_DIRECTIONS:
        problems.append(f"research/directions.json has {len(directions)} directions; propose at least {MIN_DIRECTIONS}.")
    ids = set()
    for d in directions:
        did = d.get("id", "")
        if not re.fullmatch(r"[a-z0-9-]{2,40}", did):
            problems.append(f"direction id {did!r} must be a short slug.")
        ids.add(did)
        cited = [u for u in d.get("sources", []) if u in urls]
        if len(cited) < 2:
            problems.append(f"direction {did} cites {len(cited)} of the listed sources; ground it in at least 2.")
        if len(d.get("palette", [])) < 3 or not all(re.fullmatch(r"#[0-9A-Fa-f]{6}", c.get("hex", "")) for c in d.get("palette", [])):
            problems.append(f"direction {did} needs a palette of 3+ colours with hex values.")
        for field in ["summary", "silhouettes", "graphics", "materials", "decoration"]:
            if not d.get(field):
                problems.append(f"direction {did} has no {field}.")
        hits = banned_hits(json.dumps(d))
        if hits:
            problems.append(f"direction {did} leans on protected marks or banned subjects ({', '.join(hits)}); keep the idea, drop the marks.")
    if len(ids) != len(directions):
        problems.append("direction ids repeat.")

    for m, cfg in studio.get("marketplaces", {}).items():
        if not cfg.get("enabled"):
            continue
        terms = keywords.get(m, [])
        if len(terms) < 15:
            problems.append(f"research/keywords.json has {len(terms)} {m} terms; gather at least 15 with evidence.")
        if any(not t.get("evidence") for t in terms):
            problems.append(f"every {m} keyword needs evidence (where you saw buyers use it).")
    return problems


def cmd_check_research(a):
    D = os.path.abspath(a.dir)
    studio = load(os.path.join(D, "studio.json"))
    if not studio:
        sys.exit("no studio.json; run studio.py init first")
    problems = research_problems(D, studio)
    st = state_of(D)
    st["research"]["checked"] = not problems
    save(os.path.join(D, "state.json"), st)
    if problems:
        print("Research is not ready:\n- " + "\n- ".join(problems))
        sys.exit(2)
    print("Research complete. Show the user research/brief.md and the directions, then record their choice with approve-research.")


def cmd_approve_research(a):
    D = os.path.abspath(a.dir)
    studio = load(os.path.join(D, "studio.json"))
    problems = research_problems(D, studio)
    if problems:
        sys.exit("Run check-research and fix it first:\n- " + "\n- ".join(problems))
    directions = {d["id"] for d in load(os.path.join(D, "research", "directions.json"), [])}
    unknown = [d for d in a.directions if d not in directions]
    if unknown:
        sys.exit(f"unknown direction ids: {', '.join(unknown)}")
    st = state_of(D)
    st["research"] = {"checked": True, "approved": True, "directions": a.directions, "approved_at": dt.datetime.now().isoformat(timespec="seconds")}
    save(os.path.join(D, "state.json"), st)
    print(f"Research approved with directions: {', '.join(a.directions)}. Next: write the products into studio.json and run check-designs.")


# ---------------------------------------------------------------------------
# designs
# ---------------------------------------------------------------------------

def design_problems(D, studio, st):
    problems, warnings = [], []
    approved = set(st.get("research", {}).get("directions", []))
    if not st.get("research", {}).get("approved"):
        problems.append("research is not approved yet (studio.py approve-research).")
    caps = [c.lower() for c in studio.get("business", {}).get("capabilities", {}).get("decoration", [])]
    products = studio.get("products", [])
    if not products:
        problems.append("studio.json has no products.")
    seen = set()
    for p in products:
        pid = p.get("id", "?")
        if not re.fullmatch(r"[a-z0-9-]{2,60}", pid):
            problems.append(f"{pid}: id must be a lowercase slug.")
        if pid in seen:
            problems.append(f"{pid}: duplicate id.")
        seen.add(pid)
        if p.get("type") not in TYPES:
            problems.append(f"{pid}: type {p.get('type')!r} is not one of {', '.join(sorted(TYPES))}.")
        if p.get("direction") not in approved:
            problems.append(f"{pid}: direction {p.get('direction')!r} is not one of the approved directions ({', '.join(sorted(approved))}).")
        if len(p.get("design", "")) < 250:
            problems.append(f"{pid}: the design text is {len(p.get('design', ''))} characters; describe every panel, trim, logo and print (250+).")
        for field in ["name", "fabric", "gsm", "fit", "sizes", "colorways", "decoration", "view_details"]:
            if not p.get(field):
                problems.append(f"{pid}: {field} is missing.")
        cap_methods = {method_of(c) for c in caps}
        for d in p.get("decoration", []):
            m = method_of(d)
            if caps and m not in cap_methods and not any(d.lower() in c or c in d.lower() for c in caps):
                problems.append(f"{pid}: decoration {d!r} is not something the factory lists in business.capabilities.decoration.")
        fabric = p.get("fabric", "").lower()
        methods = {method_of(d) for d in p.get("decoration", [])}
        if "sublimation" in methods and "poly" not in fabric:
            problems.append(f"{pid}: sublimation needs a polyester-rich fabric; {p.get('fabric')!r} will print dull or not at all.")
        if "dtg" in methods and "cotton" not in fabric:
            warnings.append(f"{pid}: DTG prints best on cotton; on {p.get('fabric')!r} consider DTF or sublimation.")
        if p.get("gsm") and not (40 <= float(p["gsm"]) <= 700):
            problems.append(f"{pid}: gsm {p['gsm']} is not a real fabric weight.")
        hits = banned_hits(" ".join([p.get("name", ""), p.get("design", ""), json.dumps(p.get("colorways", []))]))
        if hits:
            problems.append(f"{pid}: remove protected marks or banned subjects: {', '.join(hits)}.")
        if len(p.get("colorways", [])) > 1 and not p.get("colorway_views", True):
            warnings.append(f"{pid}: several colourways without colourway images; Alibaba needs them as SKUs of one listing with a photo each.")
        vd = p.get("view_details", {})
        if isinstance(vd, dict) and "front" not in vd:
            warnings.append(f"{pid}: view_details has no 'front' entry; the front view may drop details.")
    return problems, warnings


def cmd_check_designs(a):
    D = os.path.abspath(a.dir)
    studio = load(os.path.join(D, "studio.json"))
    st = state_of(D)
    problems, warnings = design_problems(D, studio, st)
    st["designs"] = {"checked": not problems, "hash": products_hash(studio) if not problems else None}
    save(os.path.join(D, "state.json"), st)
    for w in warnings:
        print("warning:", w)
    if problems:
        print("Designs need work:\n- " + "\n- ".join(problems))
        sys.exit(2)
    print(f"{len(studio['products'])} designs pass. Next: python3 plan.py --dir {a.dir} --stage sheets")


def gate(D, stage):
    """Called by plan.py: nothing is drawn until research is approved and the current designs pass."""
    studio = load(os.path.join(D, "studio.json"))
    st = state_of(D)
    if not st.get("research", {}).get("approved"):
        sys.exit("Stop: the industry research is not approved yet. Do the research (references/research-playbook.md), run "
                 "studio.py check-research, show the user the brief and directions, then studio.py approve-research.")
    if not st.get("designs", {}).get("checked") or st["designs"].get("hash") != products_hash(studio):
        sys.exit("Stop: the products changed since they were checked (or were never checked). Run studio.py check-designs first.")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# resolution: the user's choice decides the model and the price of every image
# ---------------------------------------------------------------------------

RESOLUTIONS = {"2K": "Nano Banana 2 at 2K", "4K": "GPT Image 2.5 Sunburst at 4K"}


def cmd_set_resolution(a):
    D = os.path.abspath(a.dir)
    path = os.path.join(D, "studio.json")
    studio = load(path)
    if not studio:
        sys.exit("no studio.json here")
    studio.setdefault("generation", {})["resolution"] = a.resolution
    save(path, studio)
    print(f"Images will be made at {a.resolution} with {RESOLUTIONS[a.resolution]}. "
          f"Before each stage, `node run.mjs --dir <workspace> --quote` shows its cost.")


# ---------------------------------------------------------------------------
# links: the images as web links, for a user who cannot open files on this machine (a cloud session)
# ---------------------------------------------------------------------------

STAGE_PREFIX = {"sheets": "sheet-", "views": "view-", "extras": "extra-"}


def cmd_links(a):
    D = os.path.abspath(a.dir)
    ledger = load(os.path.join(D, "ledger.json"), {})
    prefix = STAGE_PREFIX.get(a.stage, "")
    latest = {}
    for name, entry in ledger.items():
        if not name.startswith(prefix):
            continue
        made = [x for x in entry.get("attempts", []) if x.get("status") == "succeeded" and x.get("url")]
        if not made:
            continue
        # name is <stage>-<product id>-v<version>[-<view>]; keep only each product's newest version
        m = re.match(r"^(sheet|view|extra)-(.+)-v(\d+)(?:-(.+))?$", name)
        if not m:
            continue
        kind, pid, ver, view = m.group(1), m.group(2), int(m.group(3)), m.group(4) or "sheet"
        if a.only and pid not in a.only:
            continue
        key = (kind, pid, view)
        if key not in latest or ver >= latest[key][0]:
            latest[key] = (ver, made[-1]["url"], made[-1].get("doneAt") or made[-1].get("at", ""))
    if not latest:
        sys.exit("No finished images recorded for that selection yet.")
    current = None
    for (kind, pid, view), (ver, url, at) in sorted(latest.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
        if pid != current:
            print(f"\n{pid} (version {ver})")
            current = pid
        print(f"  {view}: {url}")
    print("\nLinks work for 7 days after each image was made.")


def cmd_status(a):
    D = os.path.abspath(a.dir)
    studio = load(os.path.join(D, "studio.json"))
    if not studio:
        sys.exit("no studio.json here")
    st = state_of(D)
    approvals = load(os.path.join(D, "approvals.json"), {})
    lines = [f"Brand: {studio['brand'].get('name')}",
             f"Marketplaces: {', '.join(m for m, c in studio['marketplaces'].items() if c.get('enabled'))}",
             f"Research: {'approved (' + ', '.join(st['research'].get('directions', [])) + ')' if st['research'].get('approved') else 'checked, waiting for approval' if st['research'].get('checked') else 'not done'}",
             f"Designs: {len(studio.get('products', []))} ({'checked' if st.get('designs', {}).get('checked') else 'not checked'})"]
    res = (studio.get("generation") or {}).get("resolution")
    lines.append(f"Resolution: {res + ' (' + RESOLUTIONS[res] + ')' if res in RESOLUTIONS else 'not chosen yet (ask the user: 2K or 4K)'}")
    if approvals:
        counts = {}
        for s in approvals.values():
            counts[s["status"]] = counts.get(s["status"], 0) + 1
        lines.append("Sheets: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    listings = [f for f in os.listdir(os.path.join(D, "listings"))] if os.path.isdir(os.path.join(D, "listings")) else []
    lines.append(f"Listing files: {len(listings)}")
    pub = load(os.path.join(D, "published.json"), {})
    if pub:
        lines.append("Submitted: " + ", ".join(f"{k} {v.get('status')}" for k, v in pub.items()))
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("--dir", required=True); p.add_argument("--brand", required=True)
    p.add_argument("--marketplaces", nargs="+", default=["etsy", "alibaba"], choices=["etsy", "alibaba"]); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("check-research"); p.add_argument("--dir", required=True); p.set_defaults(fn=cmd_check_research)
    p = sub.add_parser("approve-research"); p.add_argument("--dir", required=True); p.add_argument("--directions", nargs="+", required=True); p.set_defaults(fn=cmd_approve_research)
    p = sub.add_parser("check-designs"); p.add_argument("--dir", required=True); p.set_defaults(fn=cmd_check_designs)
    p = sub.add_parser("status"); p.add_argument("--dir", required=True); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("set-resolution"); p.add_argument("--dir", required=True); p.add_argument("resolution", choices=list(RESOLUTIONS))
    p.set_defaults(fn=cmd_set_resolution)
    p = sub.add_parser("links"); p.add_argument("--dir", required=True); p.add_argument("--stage", choices=list(STAGE_PREFIX))
    p.add_argument("--only", nargs="+"); p.set_defaults(fn=cmd_links)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
