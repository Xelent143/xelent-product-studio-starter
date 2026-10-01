#!/usr/bin/env node
// Xelent API client, shared by the xelent-product-studio and xelent-product-video skills (keep the two copies
// identical). Every image, video and listing goes through Xelent API (https://api.xelentapi.com); no other
// image or video service is used.
//
//   node xelent.mjs login --key sk-...          verify a key and save it (~/.config/xelent/credentials, mode 600)
//   node xelent.mjs check                        verify the saved key; print credits and marketplace connections
//   node xelent.mjs marketplaces                 which marketplaces are connected
//   node xelent.mjs etsy-reference               Etsy shipping / processing / return / partner ids for listings
//   node xelent.mjs etsy-taxonomy "hoodies"      search Etsy category ids
//   node xelent.mjs alibaba-category "<title>"   the Alibaba category (id and path) a title would be filed under
//   node xelent.mjs alibaba-product <listing_id> an Alibaba listing's live product: status, review state, category, attributes
//   node xelent.mjs alibaba-attributes <category_id>  the attributes a category takes: required ones and accepted values
//   node xelent.mjs alibaba-score <listing_id>   Alibaba's quality score for a live product
//   node xelent.mjs alibaba-edit <listing_id> edit.json [--apply]   preview (default) or apply an edit to a live product
//   node xelent.mjs alibaba-edits <listing_id>   a product's edit history;  alibaba-undo <listing_id> <edit_id> puts the latest back
//   node xelent.mjs prices                       per-image credits at 2K and 4K, per-second video credits, and the balance
//   node xelent.mjs jobs [--status failed] [--q text] [--from YYYY-MM-DD] [--to YYYY-MM-DD]   job history and totals
//   node xelent.mjs ledger [--from YYYY-MM-DD] [--to YYYY-MM-DD]   credit ledger: every credit in and out, and whether it adds up
//
// Imported by run.mjs, render.mjs and publish.mjs for generation, assets and listings.
import { readFileSync, writeFileSync, mkdirSync, existsSync, chmodSync } from "node:fs";
import { homedir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

export const DEFAULT_BASE = "https://api.xelentapi.com";
const CRED = join(homedir(), ".config", "xelent", "credentials");

/** Only Xelent API hosts (xelentapi.com, and its card site ayzelify.com) and a local development server are accepted. */
export function apiBase() {
  const raw = (process.env.XELENT_API_BASE || DEFAULT_BASE).replace(/\/+$/, "");
  let url;
  try {
    url = new URL(raw);
  } catch {
    throw new Error(`XELENT_API_BASE is not a URL: ${raw}`);
  }
  const host = url.hostname;
  const local = host === "localhost" || host === "127.0.0.1";
  const xelentHost = ["xelentapi.com", "ayzelify.com"].some((d) => host === d || host.endsWith("." + d));
  if (!local && !xelentHost) {
    throw new Error(`This skill only works with Xelent API. ${host} is not a Xelent API host. Unset XELENT_API_BASE or point it at api.xelentapi.com.`);
  }
  if (xelentHost && url.protocol !== "https:") throw new Error("Xelent API must be reached over https.");
  return raw;
}

export function apiKey() {
  const env = process.env.XELENT_API_KEY?.trim();
  if (env) return env;
  if (existsSync(CRED)) {
    const saved = readFileSync(CRED, "utf8").trim();
    if (saved) return saved;
  }
  throw new Error("No Xelent API key. Create one at https://xelentapi.com/dashboard/keys, then run: node xelent.mjs login --key sk-...");
}

export class XelentError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function xelent(path, { method = "GET", body, form, key, timeout = 120_000 } = {}) {
  const base = apiBase(); // throws for anything that is not Xelent API, before a key is ever sent
  const headers = { Authorization: `Bearer ${key ?? apiKey()}` };
  let payload;
  if (form) payload = form;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(base + path, { method, headers, body: payload, signal: AbortSignal.timeout(timeout) });
  } catch (e) {
    throw new XelentError(`Could not reach Xelent API (${e.cause?.code || e.name}).`, 0, "network");
  }
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new XelentError(`Xelent API returned HTTP ${res.status}: ${text.slice(0, 200)}`, res.status, "bad_response");
  }
  if (!res.ok && res.status !== 422) {
    const message = data?.error?.message ?? data?.error ?? `HTTP ${res.status}`;
    throw new XelentError(String(message), res.status, data?.code ?? data?.error?.code ?? "error");
  }
  return data;
}

/** A key counts as a Xelent key only if Xelent API accepts it and answers like Xelent API. */
export async function verifyKey(key) {
  const acct = await xelent("/v1/account", { key });
  if (typeof acct?.balance_credits !== "number") throw new XelentError("That key did not return a Xelent API account.", 401, "not_xelent");
  return acct;
}

// ---------------------------------------------------------------------------
// Generation (used by run.mjs)
// ---------------------------------------------------------------------------

/** Submits one generation in async mode and returns the Xelent generation id. */
export async function submitGeneration({ model, prompt, aspectRatio, imageSize, quality, resolution, duration, seed, images }) {
  const body = { model, prompt, aspectRatio, replyType: "async" };
  if (imageSize) body.imageSize = imageSize;
  if (quality) body.quality = quality;
  if (resolution) body.resolution = resolution; // video
  if (duration) body.duration = duration; // video, whole seconds
  if (Number.isInteger(seed)) body.seed = seed;
  if (images?.length) body.images = images;
  const r = await xelent("/v1/api/generate", { method: "POST", body, timeout: 180_000 });
  if (!r.id) throw new XelentError(`No generation id: ${JSON.stringify(r).slice(0, 200)}`, 502, "no_id");
  return r.id;
}

export const generationResult = (id) => xelent(`/v1/api/result?id=${encodeURIComponent(id)}`, { timeout: 60_000 });

// ---------------------------------------------------------------------------
// Assets and listings (used by publish.mjs)
// ---------------------------------------------------------------------------

export async function uploadAsset(bytes, name, type) {
  const form = new FormData();
  form.set("file", new Blob([bytes], { type }), name);
  return xelent("/v1/assets", { method: "POST", form, timeout: 180_000 });
}

export const validateListing = (payload) => xelent("/v1/listings/validate", { method: "POST", body: payload });
export const submitListing = (payload) => xelent("/v1/listings", { method: "POST", body: payload, timeout: 300_000 });
export const listingStatus = (id) => xelent(`/v1/listings/${id}`);
export const alibabaCategory = (title, description = "") =>
  xelent(`/v1/marketplaces/alibaba/category?${new URLSearchParams({ title, ...(description ? { description } : {}) })}`);
export const alibabaProduct = (listingId) => xelent(`/v1/listings/${encodeURIComponent(listingId)}/alibaba`);
export const alibabaScore = (listingId) => xelent(`/v1/listings/${encodeURIComponent(listingId)}/alibaba/score`);
export const alibabaEdit = (listingId, edit) => xelent(`/v1/listings/${encodeURIComponent(listingId)}/alibaba`, { method: "PATCH", body: edit });
export const alibabaEdits = (listingId) => xelent(`/v1/listings/${encodeURIComponent(listingId)}/alibaba/edits`);
export const alibabaUndo = (listingId, editId) => xelent(`/v1/listings/${encodeURIComponent(listingId)}/alibaba/edits/${encodeURIComponent(editId)}/undo`, { method: "POST", body: {} });
export const alibabaAttributes = (categoryId) => xelent(`/v1/marketplaces/alibaba/category/${encodeURIComponent(categoryId)}/attributes`);
export const marketplaces = () => xelent("/v1/marketplaces");

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

async function cli() {
  const [cmd, ...rest] = process.argv.slice(2);
  const arg = (name) => {
    const i = rest.indexOf(name);
    return i > -1 ? rest[i + 1] : undefined;
  };
  if (cmd === "login") {
    const key = arg("--key")?.trim();
    if (!key) throw new Error("Usage: node xelent.mjs login --key sk-...");
    const acct = await verifyKey(key);
    mkdirSync(dirname(CRED), { recursive: true });
    writeFileSync(CRED, key + "\n", { mode: 0o600 });
    chmodSync(CRED, 0o600);
    console.log(`Saved. Xelent API key works: ${acct.balance_credits} credits available.`);
    return;
  }
  if (cmd === "check") {
    const acct = await verifyKey();
    const m = await marketplaces();
    console.log(
      JSON.stringify(
        {
          api: apiBase(),
          credits: acct.balance_credits,
          held: acct.held_credits,
          alibaba:
            m.alibaba?.connection?.status === "connected"
              ? `connected (${m.alibaba.connection.account})`
              : "not connected: connect it at https://xelentapi.com/dashboard/marketplaces (your own Alibaba app, or the platform's if offered); until then listings go to the bulk-upload spreadsheet",
          etsy: m.etsy?.connection?.status === "connected" ? `connected (${m.etsy.connection.account})` : "not connected",
        },
        null,
        1,
      ),
    );
    return;
  }
  if (cmd === "marketplaces") return console.log(JSON.stringify(await marketplaces(), null, 1));
  if (cmd === "prices") {
    const [acct, models] = await Promise.all([verifyKey(), xelent("/v1/models")]);
    const price = (id) => models.data?.find((m) => m.id === id)?.credits?.default;
    const nb2 = price("nano-banana-2");
    const sun = price("gpt-image-2.5-sunburst");
    console.log(`2K (Nano Banana 2): ${nb2 ?? "not available"} credits per image`);
    console.log(`4K (GPT Image 2.5 Sunburst): ${sun ?? "not available"} credits per image`);
    const video = models.data?.find((m) => m.id === "minimax-h3")?.credits;
    if (video) console.log(`Video (MiniMax H3), per second: ${Object.entries(video).map(([r, c]) => `${r} ${c}`).join(", ")} credits`);
    console.log(`Balance: ${acct.balance_credits} credits (1 credit = 1 PKR). Prices depend on the package the credits came from.`);
    return;
  }
  if (cmd === "jobs" || cmd === "ledger") {
    const q = new URLSearchParams();
    for (const f of ["status", "q", "from", "to", "model", "key"]) if (arg(`--${f}`)) q.set(f, arg(`--${f}`));
    q.set("limit", arg("--limit") ?? "20");
    if (cmd === "jobs") {
      const r = await xelent(`/v1/usage?${q}`);
      console.log(JSON.stringify({ totals: r.totals, jobs: r.data.map((j) => ({ id: j.id, when: new Date(j.created_at * 1000).toISOString(), model: j.model, status: j.status, credits: j.credits_used, error: j.error_code ?? undefined, prompt: j.prompt.slice(0, 80) })) }, null, 1));
    } else {
      const r = await xelent(`/v1/statement?${q}`);
      console.log(JSON.stringify({ summary: r.summary, entries: r.data.map((e) => ({ when: new Date(e.at * 1000).toISOString(), what: e.description, ref: e.ref, credits: e.credits, balance_after: e.balance_after })) }, null, 1));
    }
    return;
  }
  if (cmd === "etsy-reference") return console.log(JSON.stringify(await xelent("/v1/marketplaces/etsy/reference"), null, 1));
  if (cmd === "etsy-taxonomy") return console.log(JSON.stringify(await xelent(`/v1/marketplaces/etsy/taxonomy?q=${encodeURIComponent(rest.join(" "))}`), null, 1));
  if (cmd === "alibaba-category") return console.log(JSON.stringify(await alibabaCategory(rest.join(" ")), null, 1));
  if (cmd === "alibaba-product") return console.log(JSON.stringify(await alibabaProduct(rest[0] ?? ""), null, 1));
  if (cmd === "alibaba-score") return console.log(JSON.stringify(await alibabaScore(rest[0] ?? ""), null, 1));
  if (cmd === "alibaba-edits") return console.log(JSON.stringify(await alibabaEdits(rest[0] ?? ""), null, 1));
  if (cmd === "alibaba-undo") return console.log(JSON.stringify(await alibabaUndo(rest[0] ?? "", rest[1] ?? ""), null, 1));
  if (cmd === "alibaba-edit") {
    const edit = JSON.parse(readFileSync(rest[1] ?? "", "utf8"));
    const apply = rest.includes("--apply");
    const r = await alibabaEdit(rest[0] ?? "", { ...edit, dry_run: !apply });
    console.log(JSON.stringify(r, null, 1));
    if (!apply) console.log("Preview only. Show the user the before and after; with their OK, run again with --apply. Applying takes the product offline until Alibaba approves it again.");
    return;
  }
  if (cmd === "alibaba-attributes") {
    const s = await alibabaAttributes(rest[0] ?? "");
    const line = (a) => `${a.required ? "REQUIRED  " : "          "}${a.name}${a.custom ? "" : " (only these values)"}${a.multi ? " (several allowed)" : ""}${a.values.length ? ": " + a.values.map((v) => v.name).join(" | ") : ""}`;
    console.log(`Category ${s.category_id} attributes:\n${s.attributes.map(line).join("\n")}`);
    if (s.sale_attributes.length) console.log(`Options (sizes, colours; describe them in the listing, not as attributes):\n${s.sale_attributes.map(line).join("\n")}`);
    return;
  }
  console.log(readFileSync(fileURLToPath(import.meta.url), "utf8").split("\n").slice(1, 20).map((l) => l.replace(/^\/\/ ?/, "")).join("\n"));
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  cli().catch((e) => {
    console.error(`xelent: ${e.message}`);
    process.exit(1);
  });
}
