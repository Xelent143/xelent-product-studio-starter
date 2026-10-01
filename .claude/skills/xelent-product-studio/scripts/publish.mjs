#!/usr/bin/env node
// Send approved listings to Alibaba and Etsy through Xelent API. Nothing goes live from here: Etsy listings are
// created as drafts and Alibaba listings go into Alibaba's own review.
//
//   node publish.mjs --dir D                       dry run: host nothing, validate every approved listing on Xelent API
//   node publish.mjs --dir D --upload-only         host the approved listings' images (links for the Alibaba spreadsheet)
//   node publish.mjs --dir D --submit              host images and submit (only after the user said to submit)
//   node publish.mjs --dir D --status              refresh the status of submitted listings
//   options: --only ID ...   --marketplace alibaba|etsy   --force (resubmit a listing already submitted)
//
// Images are hosted on the Xelent dashboard (Assets). Once a listing is submitted its images are deleted 7 days
// later; images never used in a listing are deleted after 30 days. Results are recorded in <dir>/published.json.
import { readFileSync, existsSync, writeFileSync, renameSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { uploadAsset, validateListing, submitListing, listingStatus, marketplaces, verifyKey } from "./xelent.mjs";

const argv = process.argv.slice(2);
const list = (n) => { const i = argv.indexOf(n); if (i < 0) return null; const out = []; for (let k = i + 1; k < argv.length && !argv[k].startsWith("--"); k++) out.push(argv[k]); return out; };
const D = resolve(list("--dir")?.[0] ?? ".");
const ONLY = list("--only");
const MARKETS = list("--marketplace");
const SUBMIT = argv.includes("--submit"), UPLOAD_ONLY = argv.includes("--upload-only"), STATUS = argv.includes("--status"), FORCE = argv.includes("--force");
const HERE = dirname(fileURLToPath(import.meta.url));

const read = (p, d) => (existsSync(p) ? JSON.parse(readFileSync(p, "utf8")) : d);
const studio = read(join(D, "studio.json"), null);
if (!studio) { console.error(`no studio.json in ${D}`); process.exit(1); }
const state = read(join(D, "state.json"), {});
const PUB = join(D, "published.json");
const pub = read(PUB, { assets: {}, listings: {} });
const save = () => { writeFileSync(PUB + ".tmp", JSON.stringify(pub, null, 1)); renameSync(PUB + ".tmp", PUB); };
const sha = (buf) => createHash("sha256").update(buf).digest("hex");
const fileHash = (p) => sha(readFileSync(p)).slice(0, 20);
const now = () => Math.floor(Date.now() / 1000);

// ---------------------------------------------------------------------------
if (STATUS) {
  for (const [key, rec] of Object.entries(pub.listings)) {
    if (!rec.listing_id || (ONLY && !ONLY.includes(key.split(".")[0]))) continue;
    try {
      const l = await listingStatus(rec.listing_id);
      Object.assign(rec, { status: l.status, external_url: l.external_url, error: l.error });
      console.log(`${key}: ${l.status}${l.external_url ? "  " + l.external_url : ""}${l.error ? "  " + l.error : ""}`);
    } catch (e) { console.log(`${key}: could not read (${e.message})`); }
  }
  save();
  process.exit(0);
}

// ---------------------------------------------------------------------------
// Which listings: approved in listing.py, and unchanged since.
const todo = [];
for (const [key, appr] of Object.entries(state.listings ?? {})) {
  const [pid, m] = [key.slice(0, key.lastIndexOf(".")), key.slice(key.lastIndexOf(".") + 1)];
  if (ONLY && !ONLY.includes(pid)) continue;
  if (MARKETS && !MARKETS.includes(m)) continue;
  if (!studio.marketplaces?.[m]?.enabled) continue;
  const file = join(D, "listings", `${pid}.${m}.json`);
  if (!existsSync(file)) continue;
  if (fileHash(file) !== appr.hash) { console.log(`${key}: changed since it was approved; run listing.py --check and --approve again. Skipped.`); continue; }
  const manifest = read(join(D, "export", pid, m, "manifest.json"), null);
  if (!manifest?.length) { console.log(`${key}: no exported images; run prepare_images.py. Skipped.`); continue; }
  todo.push({ key, pid, m, file, manifest, hash: appr.hash });
}
if (!todo.length) { console.log("Nothing to do: no approved listings (listing.py --approve)."); process.exit(0); }

const acct = await verifyKey().catch((e) => { console.error(`Xelent API: ${e.message}`); process.exit(1); });
const conn = await marketplaces();
const connected = { alibaba: conn.alibaba?.connection?.status === "connected", etsy: conn.etsy?.connection?.status === "connected" };
console.log(`Xelent API ok (${acct.balance_credits} credits). Alibaba: ${connected.alibaba ? "connected" : "not connected"}. Etsy: ${connected.etsy ? "connected" : "not connected"}.`);

async function hosted(pid, m, entry) {
  const path = join(D, "export", pid, m, entry.file);
  const bytes = readFileSync(path);
  const digest = sha(bytes);
  const known = pub.assets[digest];
  if (known && (!known.expires_at || known.expires_at - 3600 > now())) return known;
  const a = await uploadAsset(bytes, `${pid}-${entry.file}`, "image/jpeg");
  pub.assets[digest] = { id: a.id, url: a.url, expires_at: a.expires_at, file: `${pid}/${m}/${entry.file}` };
  save();
  return pub.assets[digest];
}

function payload(t, assetIds) {
  const l = JSON.parse(readFileSync(t.file, "utf8"));
  const cfg = studio.marketplaces[t.m] ?? {};
  if (t.m === "alibaba") {
    const { xlsx, skus, ...rest } = l;
    return {
      marketplace: "alibaba",
      images: assetIds,
      listing: { place_of_origin: cfg.place_of_origin, currency: cfg.currency ?? "USD", unit: cfg.unit ?? "Piece", brand_name: studio.brand?.name, ...rest },
    };
  }
  const pick = ["who_made", "when_made", "shipping_profile_id", "readiness_state_id", "return_policy_id", "production_partner_ids", "quantity", "is_supply"];
  const defaults = Object.fromEntries(pick.filter((k) => cfg[k] !== undefined && cfg[k] !== null).map((k) => [k, cfg[k]]));
  const product = studio.products.find((p) => p.id === t.pid);
  const alt = t.manifest.map((x) => `${product?.name ?? t.pid}, ${x.view === "sizechart" ? "size chart" : x.view.replace(/^color-/, "colourway ").replace(/-/g, " ") + " view"}`);
  return { marketplace: "etsy", images: assetIds, listing: { quantity: 999, is_supply: false, image_alt_texts: alt, ...defaults, ...l } };
}

const needSheet = [];
let failures = 0;
for (const t of todo) {
  const prev = pub.listings[t.key];
  if (SUBMIT && prev?.listing_id && ["pending_review", "draft", "online"].includes(prev.status) && prev.hash === t.hash && !FORCE) {
    console.log(`${t.key}: already submitted (${prev.status}) ${prev.external_url ?? ""}. Use --force to submit again.`);
    continue;
  }
  const willHost = SUBMIT || UPLOAD_ONLY;
  let ids = [];
  if (willHost) {
    try {
      for (const entry of t.manifest) ids.push((await hosted(t.pid, t.m, entry)).id);
      console.log(`${t.key}: ${ids.length} images hosted`);
    } catch (e) { console.log(`${t.key}: image upload failed: ${e.message}`); failures++; continue; }
  }
  if (UPLOAD_ONLY) { if (t.m === "alibaba") needSheet.push(t.pid); continue; }

  // validate (a dry run validates with placeholder ids: the server only counts and size-checks hosted images)
  const body = payload(t, ids);
  if (!willHost) body.images = [];
  const v = await validateListing(body).catch((e) => ({ valid: false, errors: [e.message] }));
  const errs = (v.errors ?? []).filter((e) => willHost || !/image/.test(e));
  if (errs.length) { console.log(`${t.key}: Xelent API found problems:\n  - ${errs.join("\n  - ")}`); failures++; continue; }
  if (v.warnings?.length) console.log(`${t.key}: checked against Alibaba category ${v.category ? `${v.category.id} ${v.category.name ?? ""}`.trim() : "(none suggested)"}:\n  ~ ${v.warnings.join("\n  ~ ")}`);
  if (!SUBMIT) { console.log(`${t.key}: valid (${t.manifest.length} images). Not submitted: dry run.`); continue; }

  if (!connected[t.m]) {
    if (t.m === "alibaba") { needSheet.push(t.pid); console.log(`${t.key}: Alibaba is not connected; adding it to the bulk-upload spreadsheet instead.`); }
    else console.log(`${t.key}: Etsy is not connected. Connect it at https://xelentapi.com/dashboard/marketplaces, then run --submit again.`);
    continue;
  }
  try {
    const r = await submitListing(body);
    pub.listings[t.key] = {
      listing_id: r.id, status: r.status, external_id: r.external_id, external_url: r.external_url, error: r.error,
      ...(t.m === "alibaba" ? { category: r.category ?? null, alibaba_code: r.alibaba_code ?? null, attempt: r.attempt ?? null, attribute_fit: r.attribute_fit ?? null } : {}),
      hash: t.hash, at: new Date().toISOString(),
    };
    save();
    const cat = r.category ? ` [category ${r.category.id}${r.category.name ? ` ${r.category.name}` : ""}, ${r.category.source}]` : "";
    if (r.status === "failed") { failures++; console.log(`${t.key}: FAILED: ${r.error}`); }
    else console.log(`${t.key}: ${r.status === "draft" ? "Etsy draft created" : "sent to Alibaba for review"}${cat}  ${r.external_url ?? ""}`);
  } catch (e) {
    failures++;
    pub.listings[t.key] = { status: "failed", error: e.message, hash: t.hash, at: new Date().toISOString() };
    save();
    console.log(`${t.key}: FAILED: ${e.message}`);
  }
}

if (needSheet.length) {
  try {
    const out = execFileSync("python3", [join(HERE, "alibaba_xlsx.py"), "--dir", D, "--only", ...needSheet], { encoding: "utf8" });
    process.stdout.write(out);
    for (const pid of needSheet) {
      pub.listings[`${pid}.alibaba`] = { ...(pub.listings[`${pid}.alibaba`] ?? {}), status: "exported", file: "export/alibaba-bulk-upload.xlsx", at: new Date().toISOString() };
    }
    save();
  } catch (e) { failures++; console.log(`Alibaba spreadsheet failed: ${e.stdout || ""}${e.stderr || e.message}`); }
}
process.exit(failures ? 2 : 0);
