#!/usr/bin/env python3
"""Check, preview and approve listings: listings/<id>.alibaba.json and listings/<id>.etsy.json.

  listing.py --dir D --check   [--only ID ...]     marketplace rules, product facts, research keywords, IP, claims
  listing.py --dir D --preview [--only ID ...]     review/listings.html: every listing as the buyer will read it
  listing.py --dir D --approve ID [ID ...] | --all record the user's approval (publish.mjs refuses anything else)

Approval is tied to the file's contents: edit a listing after approval and it has to be approved again.
"""
import argparse, glob, hashlib, html, json, os, re, sys, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load, save  # noqa: E402
from studio import banned_hits  # noqa: E402

CONTACT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|https?://|www\.|\bwhats ?app\b|\bwechat\b|\btelegram\b|\bskype\b"
                     r"|\+\d{1,3}[\s-]?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,5}|\b(phone|tel|mobile|call us)\b[:\s]*\+?\d", re.I)
AI_WORDS = re.compile(r"\bA\.?I\.?\b|artificial intelligence|\bgenerated\b|\brender(ed|ing|s)?\b|\bmock-?ups?\b|\bCGI\b|midjourney|nano ?banana|gemini|dall-?e|stable diffusion", re.I)
CLAIMS = {
    r"oeko-?tex": "OEKO-TEX", r"\bgots\b": "GOTS", r"bluesign": "bluesign", r"\bgrs\b|global recycled standard": "GRS", r"\bbsci\b|amfori": "BSCI",
    r"\bwrap\b certified": "WRAP", r"\bsedex\b": "Sedex", r"\biso ?9001\b": "ISO 9001", r"\bce\b (certified|marked)": "CE", r"\bfda\b": "FDA",
}
SOFT_CLAIMS = re.compile(r"\b(best|#1|number one|cheapest|guaranteed|100% waterproof|waterproof|antibacterial|anti-?microbial|upf ?\d+|uv protection|bulletproof|fire-?proof|flame retardant)\b", re.I)
ALIBABA_SECTIONS = {"overview": r"overview|about (this|the) product|product (description|details)", "specification": r"specification|specs",
                    "customisation": r"customi[sz]|oem|odm|private label", "sizes": r"\bsize", "packaging": r"packag", "lead time": r"lead time|production time|delivery",
                    "samples": r"sample"}
ALIBABA_ATTRS = ["Material", "Technics", "Gender", "Style", "Feature", "Supply Type"]
ETSY_TAG = re.compile(r"^[\w \-'™©®]+$", re.U)
ETSY_TITLE_FILLER = ["beautiful", "gorgeous", "amazing", "perfect", "stunning", "unique", "must have", "best", "gift for", "present for",
                     "on sale", "sale", "free shipping", "fast shipping", "best seller", "bestseller", "trending"]


def text_of(html_s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(html_s or ""))).strip()


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:20]


def words(s):
    return re.findall(r"[a-z0-9]+", s.lower())


def keyword_terms(D, m):
    return [k["term"] if isinstance(k, dict) else k for k in load(os.path.join(D, "research", "keywords.json"), {}).get(m, [])]


def check_common(m, l, p, studio, D, title, body, tags):
    err, warn = [], []
    everything = " ".join([title, body, " ".join(tags), json.dumps(l.get("attributes", []))])
    hits = banned_hits(everything)
    if hits: err.append(f"protected marks or banned subjects: {', '.join(hits)}.")
    c = sorted({m.group(0).strip() for m in CONTACT.finditer(title + " " + body)})
    if c: err.append(f"contact details or links are not allowed in listings ({', '.join(c[:3])}).")
    certs = [x.lower() for x in studio.get("business", {}).get("certifications", [])]
    for pat, name in CLAIMS.items():
        if re.search(pat, everything, re.I) and not any(name.lower() in x for x in certs):
            err.append(f"claims {name} but business.certifications does not list it; remove the claim or add the certificate.")
    for s in sorted({x.lower() for x in SOFT_CLAIMS.findall(everything)}):
        warn.append(f'"{s}" is a claim buyers and marketplaces hold you to; keep it only if it is tested and true.')
    # facts from the product must survive into the listing
    fabric_words = [w for w in words(p.get("fabric", "")) if len(w) > 3 and not w.isdigit()]
    if fabric_words and not any(w in body.lower() for w in fabric_words):
        err.append(f"the description never states the fabric ({p.get('fabric')}).")
    if p.get("gsm") and str(p["gsm"]) not in body:
        warn.append(f"the description does not give the fabric weight ({p['gsm']} gsm).")
    for s in p.get("sizes", []):
        if not re.search(rf"(?<![\w]){re.escape(s)}(?![\w])", body):
            warn.append(f"size {s} is sold but not mentioned in the description."); break
    for cw in p.get("colorways", []):
        if cw["name"].lower() not in (body + " " + json.dumps(l.get("variations", {}))).lower():
            warn.append(f"colourway {cw['name']} is not mentioned.")
    # AI wording follows the marketplace setting
    cfg = studio["marketplaces"].get(m, {})
    disclose = m == "etsy" and cfg.get("disclose_ai", True)
    if disclose:
        needed = cfg.get("ai_disclosure_text", "").strip()
        if not needed:
            err.append("marketplaces.etsy.disclose_ai is on but ai_disclosure_text is empty.")
        elif needed.lower() not in body.lower():
            err.append("marketplaces.etsy.disclose_ai is on, so the description must contain ai_disclosure_text word for word.")
    elif AI_WORDS.search(title + " " + body):
        err.append(f'the listing mentions "{AI_WORDS.search(title + " " + body).group(0)}"; describe the product itself, not how its images were made.')
    # research keywords
    terms = keyword_terms(D, m)
    if terms:
        where = (title + " " + " ".join(tags)).lower()
        used = [t for t in terms if t.lower() in where]
        if not any(t.lower() in title.lower() for t in terms[:8]):
            warn.append("the title uses none of the top research keywords; lead with the phrase buyers search for.")
        if len(used) < min(5, len(terms)):
            warn.append(f"only {len(used)} research keywords appear in the title/tags/keywords; use more of research/keywords.json.")
    return err, warn


def check_alibaba(l, p, studio, D):
    title, body = l.get("title", ""), l.get("description_html", "")
    err, warn = check_common("alibaba", l, p, studio, D, title, text_of(body), l.get("keywords", []))
    if not title: err.append("title is required.")
    if len(title) > 128: err.append(f"title is {len(title)} characters; Alibaba allows 128.")
    if len(title) < 50: warn.append(f"title is {len(title)} characters; 60-120 carries more search terms.")
    if re.search(r"[^\x20-\x7E]", title): err.append("title must be plain ASCII.")
    if re.search(r"[!|~^*<>{}\[\]]", title): err.append("title contains symbols Alibaba rejects (! | ~ ^ * < > { } [ ]).")
    rep = [w for w in set(words(title)) if len(w) > 3 and words(title).count(w) > 2]
    if rep: warn.append(f"title repeats {', '.join(rep)}; stuffing lowers ranking.")
    kws = l.get("keywords", [])
    if not kws: warn.append("no keywords; Alibaba will guess them.")
    if len(" ".join(kws)) > 384: err.append("keywords exceed 384 characters in total.")
    if any(re.search(r"[;:,]", k) for k in kws): err.append("keywords must not contain ; : or ,")
    if 0 < len(kws) < 10: warn.append(f"{len(kws)} keywords; Alibaba's form says 15 or more get more exposure (2-5 word phrases, up to 384 characters).")
    if any(len(k.split()) == 1 for k in kws): warn.append("single-word keywords rarely match buyer searches; use 2-5 word phrases.")
    if not body.strip(): err.append("description_html is required.")
    if len(body) > 20000: err.append("description_html is over 20,000 characters.")
    if re.search(r"<(script|iframe|form|object|embed)\b", body, re.I): err.append("description_html contains script, iframe, form or embed tags.")
    if re.search(r"<a\s", body, re.I): err.append("description_html must not link anywhere.")
    if "<table" not in body.lower(): warn.append("no specification table in the description.")
    for name, pat in ALIBABA_SECTIONS.items():
        if not re.search(pat, text_of(body), re.I): warn.append(f"the description has no {name} section.")
    tiers = l.get("price_tiers", [])
    if not tiers and not l.get("price_range"): err.append("give price_tiers or price_range.")
    pq, pp = 0, float("inf")
    for t in tiers:
        if not (isinstance(t.get("min_qty"), int) and t["min_qty"] > pq): err.append("price_tiers quantities must be whole numbers going up.")
        if not (0 < t.get("price", 0) <= pp): err.append("price_tiers prices must be above 0 and never rise with quantity.")
        if abs(round(t.get("price", 0) * 100) - t.get("price", 0) * 100) > 1e-6: err.append("prices take at most 2 decimals.")
        pq, pp = t.get("min_qty", pq), t.get("price", pp)
    if len(tiers) > 3: warn.append("more than 3 price tiers; the spreadsheet fallback only carries 3.")
    moq = studio.get("business", {}).get("capabilities", {}).get("moq")
    if tiers and moq and tiers[0]["min_qty"] < moq: warn.append(f"the first tier starts at {tiers[0]['min_qty']}, below the factory MOQ of {moq}.")
    names = [a.get("name", "") for a in l.get("attributes", [])]
    for a in l.get("attributes", []):
        if len(str(a.get("value", ""))) > 70: err.append(f"attribute {a.get('name')} is over 70 characters.")
    missing = [x for x in ALIBABA_ATTRS if not any(x.lower() in n.lower() for n in names)]
    if missing: warn.append("attributes missing: " + ", ".join(missing) + " (buyers filter on them).")
    return sorted(set(err)), sorted(set(warn))


def check_etsy(l, p, studio, D):
    title, body, tags = l.get("title", ""), l.get("description", ""), l.get("tags", [])
    err, warn = check_common("etsy", l, p, studio, D, title, body, tags)
    if not title: err.append("title is required.")
    if len(title) > 140: err.append(f"title is {len(title)} characters; Etsy allows 140.")
    for ch in "%:&+":
        if title.count(ch) > 1: err.append(f'"{ch}" may appear only once in an Etsy title.')
    if re.search(r"\b[A-Z]{4,}\b", title) and sum(1 for w in title.split() if w.isupper() and len(w) > 3) > 1:
        warn.append("several words in capitals; Etsy asks for sentence-style titles.")
    if len(title.split()) > 15: warn.append(f"title is {len(title.split())} words; short, readable titles (under ~15 words) do better on Etsy.")
    filler = [w for w in ETSY_TITLE_FILLER if re.search(rf"\b{re.escape(w)}\b", title, re.I)]
    if filler: warn.append(f"title filler ({', '.join(filler)}): put gift and occasion words in tags; Etsy shows sale and shipping badges itself.")
    dup = [t for t in tags if t.lower() in {a.lower() for a in l.get("materials", [])}]
    if dup: warn.append(f"tags repeat materials ({', '.join(dup)}); materials are already searchable, use the tag for another phrase.")
    if len(tags) > 13: err.append(f"{len(tags)} tags; Etsy allows 13.")
    if len(tags) < 13: warn.append(f"{len(tags)} tags; use all 13.")
    for t in tags:
        if len(t) > 20: err.append(f'tag "{t}" is over 20 characters.')
        if not ETSY_TAG.match(t): err.append(f'tag "{t}" has characters Etsy rejects.')
    if len({t.lower() for t in tags}) != len(tags): err.append("tags repeat.")
    if len(l.get("materials", [])) > 13: err.append("Etsy allows 13 materials.")
    if len(l.get("styles", [])) > 2: err.append("Etsy allows 2 styles.")
    if len(body) < 700: warn.append(f"description is {len(body)} characters; say more about fit, fabric, care, sizing and making.")
    if not (l.get("price", 0) > 0): err.append("price must be above 0.")
    if not isinstance(l.get("taxonomy_id"), int): err.append("taxonomy_id is required (node xelent.mjs etsy-taxonomy \"hoodies\").")
    v = l.get("variations", {})
    bad = [s for s in v.get("sizes", []) if s not in p.get("sizes", [])]
    if bad: err.append(f"variation sizes {', '.join(bad)} are not in the product's sizes.")
    cws = {c["name"].lower() for c in p.get("colorways", [])}
    badc = [c for c in v.get("colors", []) if c.lower() not in cws]
    if badc: err.append(f"variation colours {', '.join(badc)} are not colourways of the product.")
    for a in l.get("image_alt_texts", []):
        if len(a) > 250: warn.append("an image alt text is over 250 characters."); break
    return sorted(set(err)), sorted(set(warn))


def files(D, only):
    out = []
    for f in sorted(glob.glob(os.path.join(D, "listings", "*.json"))):
        m = re.match(r"(.+)\.(alibaba|etsy)\.json$", os.path.basename(f))
        if m and (not only or m.group(1) in only): out.append((m.group(1), m.group(2), f))
    return out


def run_checks(D, studio, only):
    products = {p["id"]: p for p in studio["products"]}
    results = {}
    for pid, m, f in files(D, only):
        if pid not in products:
            results[(pid, m)] = (f, [f"no product {pid} in studio.json"], []); continue
        try:
            l = json.load(open(f))
        except json.JSONDecodeError as e:
            results[(pid, m)] = (f, [f"not valid JSON: {e}"], []); continue
        err, warn = (check_alibaba if m == "alibaba" else check_etsy)(l, products[pid], studio, D)
        results[(pid, m)] = (f, err, warn)
    return results


def preview(D, studio, only):
    rows = []
    for pid, m, f in files(D, only):
        l = json.load(open(f))
        man = load(os.path.join(D, "export", pid, m, "manifest.json"), [])
        imgs = "".join(f'<img src="../export/{pid}/{m}/{x["file"]}" alt="{html.escape(x["view"])}" loading="lazy">' for x in man)
        if m == "alibaba":
            body = l.get("description_html", "")
            meta = (f"<p><b>Keywords:</b> {html.escape(' | '.join(l.get('keywords', [])))}</p>"
                    f"<p><b>Price:</b> " + ", ".join(f"{t['min_qty']}+ pcs: {l.get('currency', 'USD')} {t['price']:.2f}" for t in l.get("price_tiers", [])) + "</p>"
                    "<table>" + "".join(f"<tr><th>{html.escape(a['name'])}</th><td>{html.escape(str(a['value']))}</td></tr>" for a in l.get("attributes", [])) + "</table>")
        else:
            body = "<div class=pre>" + html.escape(l.get("description", "")) + "</div>"
            meta = (f"<p><b>Tags ({len(l.get('tags', []))}):</b> " + " ".join(f"<span class=tag>{html.escape(t)}</span>" for t in l.get("tags", [])) + "</p>"
                    f"<p><b>Price:</b> {l.get('price')} &nbsp; <b>Materials:</b> {html.escape(', '.join(l.get('materials', [])))}</p>")
        rows.append(f"<section><div class=mk>{m.upper()} · {html.escape(pid)}</div><h2>{html.escape(l.get('title', ''))}</h2>"
                    f"<p class=n>{len(l.get('title', ''))} characters</p><div class=imgs>{imgs}</div>{meta}<div class=body>{body}</div></section>")
    css = ("body{margin:0;background:#eeeeea;font:16px/1.55 system-ui,sans-serif;color:#1b1b1b}header{position:sticky;top:0;background:#1b1b1b;color:#fff;padding:14px 20px;z-index:1}"
           "main{max-width:1100px;margin:0 auto;padding:16px}section{background:#fff;border-radius:6px;padding:20px 22px;margin:0 0 20px}.mk{font-size:12px;letter-spacing:.08em;color:#777}"
           "h2{margin:.2em 0 0;font-size:22px;line-height:1.3}.n{margin:.2em 0 1em;color:#888;font-size:13px}.imgs{display:flex;gap:6px;overflow-x:auto;margin-bottom:12px}"
           ".imgs img{width:150px;height:150px;object-fit:cover;border:1px solid #e3e3e0;flex:none}table{border-collapse:collapse;margin:8px 0;width:100%}th,td{border:1px solid #e3e3e0;padding:5px 8px;text-align:left;font-size:14px}"
           ".tag{display:inline-block;background:#f1f1ee;border-radius:12px;padding:2px 10px;margin:2px;font-size:13px}.pre{white-space:pre-wrap}.body{border-top:1px solid #eee;margin-top:12px;padding-top:12px}")
    out = os.path.join(D, "review", "listings.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write(f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Listings</title><style>{css}</style>"
                         f"<header><b>{html.escape(studio['brand'].get('name', ''))}: listings for approval</b></header><main>{''.join(rows)}</main>")
    print("preview:", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--approve", nargs="*")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    D = os.path.abspath(a.dir)
    studio = load(os.path.join(D, "studio.json"))
    only = a.only or (a.approve if a.approve else None)
    results = run_checks(D, studio, only)
    if not results: sys.exit("no listings/<id>.alibaba.json or listings/<id>.etsy.json files yet")
    failed = False
    for (pid, m), (f, err, warn) in results.items():
        if a.check or a.approve is not None or a.all:
            print(f"\n{pid} · {m}: {'OK' if not err else f'{len(err)} errors'}" + (f", {len(warn)} warnings" if warn else ""))
            for e in err: print("  error:", e)
            for w in warn: print("  warning:", w)
        failed |= bool(err)
    if a.preview: preview(D, studio, a.only)
    if a.approve is not None or a.all:
        if failed: sys.exit("\nFix the errors before approving.")
        st = load(os.path.join(D, "state.json"), {})
        st.setdefault("listings", {})
        for (pid, m), (f, _, _) in results.items():
            st["listings"][f"{pid}.{m}"] = {"hash": sha(f), "approved_at": dt.datetime.now().isoformat(timespec="seconds")}
        save(os.path.join(D, "state.json"), st)
        print(f"\napproved: {', '.join(f'{p}.{m}' for p, m in results)}")
    elif failed:
        sys.exit(2)


if __name__ == "__main__":
    main()
