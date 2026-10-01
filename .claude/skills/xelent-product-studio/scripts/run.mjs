#!/usr/bin/env node
// Execute <dir>/jobs.json on Xelent API at the resolution the user chose (studio.json generation.resolution):
//   2K -> Nano Banana 2 at 2K        4K -> GPT Image 2.5 Sunburst at 4K (high quality)
// Safe to stop and re-run at any time.
//   node run.mjs --dir D --quote       what this stage will cost and the balance after; generates nothing
//   node run.mjs --dir D               generate, then report the credits used and the balance left
//   node run.mjs --dir D --status      progress only
//   node run.mjs --dir D --restore     download again (free) every image already made whose file is missing
//   options: --concurrency 6   --resolution 2K|4K (overrides studio.json for this run)
// A job is done when its output file exists. Every generation id is written to <dir>/ledger.json before anything
// else, so a re-run polls generations already submitted instead of paying for them again, and an image that was
// made but whose file is gone (a cloud session's machine was reset) is downloaded again from the link Xelent keeps
// for 7 days instead of being made twice. References go up as 1600px JPEG copies (<dir>/refs): full-size PNGs are
// several MB and time out on a slow uplink.
import { readFileSync, writeFileSync, existsSync, mkdirSync, renameSync, statSync } from "node:fs";
import { dirname, join, resolve, basename } from "node:path";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { apiBase, verifyKey, submitGeneration, generationResult, xelent, XelentError } from "./xelent.mjs";

const argv = process.argv.slice(2);
const arg = (n, d) => { const i = argv.indexOf(n); return i > -1 && argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : d; };
const D = resolve(arg("--dir", "."));
// The user picks the resolution once (studio.py set-resolution); each maps to one model.
const PROFILES = {
  "2K": { model: "nano-banana-2", imageSize: "2K", label: "Nano Banana 2 at 2K" },
  "4K": { model: "gpt-image-2.5-sunburst", imageSize: "4K", quality: "high", label: "GPT Image 2.5 Sunburst at 4K" },
};
const studioFile = join(D, "studio.json");
const chosen = arg("--resolution") ?? (existsSync(studioFile) ? JSON.parse(readFileSync(studioFile, "utf8")).generation?.resolution : null);
if (chosen && !PROFILES[chosen]) {
  console.error(`Resolution must be 2K or 4K, not "${chosen}".`);
  process.exit(4);
}
if (!argv.includes("--status") && !argv.includes("--restore") && !PROFILES[chosen]) {
  console.error(
    "No resolution chosen yet. Ask the user: 2K (Nano Banana 2) or 4K (GPT Image 2.5 Sunburst)? " +
      "Show them each price with `node xelent.mjs prices`, then record the answer: python3 studio.py set-resolution --dir <workspace> 2K|4K",
  );
  process.exit(4);
}
const PROFILE = PROFILES[chosen] ?? PROFILES["2K"];
const MODEL = PROFILE.model;
const SIZE = PROFILE.imageSize;
const CONC = +arg("--concurrency", "6");
// Xelent API refunds a still not finished after 30 minutes; wait longer than that before trying again, so nothing it
// may still charge for is ever made twice.
const MAX_TRIES = 4, MAX_NET = 8, STALE_MIN = 40, POLL_MS = 8000;

const JOBS = existsSync(join(D, "jobs.json")) ? JSON.parse(readFileSync(join(D, "jobs.json"), "utf8")) : [];
const LEDGER = join(D, "ledger.json");
const ledger = existsSync(LEDGER) ? JSON.parse(readFileSync(LEDGER, "utf8")) : {};
// Each entry remembers where its image goes, so --restore can bring back images from earlier stages too.
for (const j of JOBS) { ledger[j.name] ??= { attempts: [] }; ledger[j.name].out = j.out; }
const save = () => { writeFileSync(LEDGER + ".tmp", JSON.stringify(ledger, null, 1)); renameSync(LEDGER + ".tmp", LEDGER); };
const log = (...a) => console.log(new Date().toTimeString().slice(0, 8), ...a);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const done = (j) => existsSync(j.out);
const last = (j) => ledger[j.name].attempts.at(-1);
const tries = (j) => ledger[j.name].attempts.filter((a) => a.id).length;
const netErrs = (j) => ledger[j.name].attempts.filter((a) => a.status === "neterror").length;
const gaveUp = (j) => tries(j) >= MAX_TRIES || netErrs(j) >= MAX_NET || last(j)?.status === "violation";

function status() {
  const c = { done: 0, running: 0, waiting: 0, failed: 0 };
  const missing = [];
  for (const j of JOBS) {
    if (done(j)) { c.done++; continue; }
    missing.push(j.name);
    if (last(j)?.status === "pending") c.running++;
    else if (gaveUp(j)) c.failed++;
    else c.waiting++;
  }
  return { ...c, total: JOBS.length, missing };
}
if (argv.includes("--status")) { const s = status(); console.log(JSON.stringify({ ...s, missing: s.missing.slice(0, 40) }, null, 1)); process.exit(0); }

// small JPEG copy of a reference: 1600px on the long side, quality 85
function small(p) {
  if (!existsSync(p)) throw new Error("reference not found: " + p);
  const st = statSync(p);
  const out = join(D, "refs", createHash("md5").update(p + st.mtimeMs).digest("hex").slice(0, 12) + "-" + basename(p).replace(/\.\w+$/, "") + ".jpg");
  if (existsSync(out)) return out;
  mkdirSync(join(D, "refs"), { recursive: true });
  try { execFileSync("sips", ["-s", "format", "jpeg", "-s", "formatOptions", "85", "-Z", "1600", p, "--out", out], { stdio: "ignore" }); }
  catch {
    execFileSync("python3", ["-c", "import sys;from PIL import Image;i=Image.open(sys.argv[1]).convert('RGB');i.thumbnail((1600,1600));i.save(sys.argv[2],quality=85)", p, out]);
  }
  return out;
}

const isNet = (e) => e instanceof XelentError && (e.status === 0 || e.status >= 500 || e.status === 429);

async function submit(j) {
  const at = new Date().toISOString();
  try {
    const images = (j.refs || []).map((r) => "data:image/jpeg;base64," + readFileSync(small(r)).toString("base64"));
    const id = await submitGeneration({ model: MODEL, prompt: j.prompt, aspectRatio: j.aspect || "1:1", imageSize: SIZE, quality: PROFILE.quality, images });
    ledger[j.name].attempts.push({ id, at, status: "pending", model: MODEL, size: SIZE });
    log("submitted", j.name);
  } catch (e) {
    const violation = e instanceof XelentError && e.code === "content_policy_violation";
    ledger[j.name].attempts.push({ id: null, at, status: violation ? "violation" : isNet(e) ? "neterror" : "failed", reason: e.message });
    log(violation ? "REFUSED (content policy; reword the design)" : "submit failed", j.name, e.message);
    if (e instanceof XelentError && (e.status === 401 || e.status === 402 || e.code === "insufficient_credits")) {
      save();
      console.error(`\nStopped: ${e.message}\nTop up at https://xelentapi.com/dashboard/billing, then run this again; finished images are kept.`);
      process.exit(3);
    }
  }
  save();
}

class Expired extends Error {}
async function download(url, out) {
  const img = await fetch(url, { signal: AbortSignal.timeout(180_000) });
  if (img.status === 404 || img.status === 410) throw new Expired("file no longer on Xelent");
  if (!img.ok) throw new Error("download HTTP " + img.status);
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out + ".part", Buffer.from(await img.arrayBuffer()));
  renameSync(out + ".part", out);
}

async function poll(j) {
  const a = last(j);
  try {
    const r = await generationResult(a.id);
    if (r.status === "succeeded") {
      const url = r.results?.[0]?.url;
      if (!url) throw new Error("succeeded without a result url");
      await download(url, j.out);
      a.status = "succeeded"; a.url = url; a.credits = r.credits_used; a.doneAt = new Date().toISOString(); log("done", j.name);
    } else if (r.status === "failed" || r.status === "violation") {
      a.status = r.status; a.reason = r.error || "unknown"; log(r.status.toUpperCase(), j.name, a.reason);
    } else if (Date.now() - Date.parse(a.at) > STALE_MIN * 60_000) {
      a.status = "stale"; log("stale, will resubmit", j.name);
    }
  } catch (e) { a.lastError = e.message; }
  save();
}

async function pool(items, n, fn) { const q = [...items]; await Promise.all(Array.from({ length: Math.min(n, q.length) }, async () => { while (q.length) await fn(q.shift()); })); }

// --restore: after a cloud machine was wiped, bring back every image this workspace already paid for.
if (argv.includes("--restore")) {
  const missing = Object.entries(ledger)
    .map(([name, e]) => ({ name, out: e.out, a: e.attempts.filter((x) => x.status === "succeeded" && x.url).at(-1) }))
    .filter((x) => x.out && x.a && !existsSync(x.out));
  const counts = { restored: 0, expired: 0, failed: 0 };
  await pool(missing, 6, async (x) => {
    for (let attempt = 1; ; attempt++) {
      try { await download(x.a.url, x.out); counts.restored++; return; }
      catch (e) {
        if (e instanceof Expired) { counts.expired++; log("no longer on Xelent (older than 7 days):", x.name); return; }
        if (attempt >= 3) { counts.failed++; log("could not download:", x.name, e.message); return; }
        await sleep(3000 * attempt);
      }
    }
  });
  console.log(`RESTORE: ${counts.restored} image(s) downloaded again for free` +
    (counts.expired ? `, ${counts.expired} no longer on Xelent (plan and run that stage to make them again)` : "") +
    (counts.failed ? `, ${counts.failed} failed (run --restore again)` : "") + ".");
  process.exit(counts.failed ? 5 : 0);
}

// Images already made and paid for whose files are missing: download them again, free. Only a file Xelent has
// already deleted (after 7 days) is made again, and that is counted in the price below.
const paidFor = (j) => { const a = last(j); return !done(j) && a?.status === "succeeded" && a.url ? a : null; };
const lost = JOBS.filter(paidFor);
if (lost.length) {
  log(`${lost.length} image${lost.length === 1 ? " was" : "s were"} already made and paid for but the file is missing; downloading again (free).`);
  const failed = [];
  await pool(lost, 6, async (j) => {
    const a = paidFor(j);
    for (let attempt = 1; ; attempt++) {
      try { await download(a.url, j.out); log("downloaded again", j.name); return; }
      catch (e) {
        if (e instanceof Expired) { a.status = "expired"; log("no longer on Xelent (older than 7 days); it will be made again", j.name); return; }
        if (attempt >= 3) { failed.push(j.name); return; }
        await sleep(3000 * attempt);
      }
    }
  });
  save();
  if (failed.length) {
    console.error(`Could not download ${failed.length} paid image(s) again: ${failed.join(", ")}. Nothing was charged. Check the connection to xelentapi.com and run again.`);
    process.exit(5);
  }
}

// Before paying for anything: the key must be a Xelent API key with enough credits for what is left to do.
const todo = JOBS.filter((j) => !done(j));
if (!todo.length) { log(argv.includes("--quote") ? "QUOTE: 0 images, 0 credits: every output is already on disk." : "nothing to generate: every output is already on disk"); process.exit(0); }
const acct = await verifyKey().catch((e) => { console.error(`Xelent API: ${e.message}`); process.exit(1); });
const models = await xelent("/v1/models").catch(() => ({ data: [] }));
const listed = models.data?.find((m) => m.id === MODEL);
if (!listed) {
  console.error(`${PROFILE.label} is not available on this Xelent API account right now. Ask the user to choose the other resolution (studio.py set-resolution).`);
  process.exit(4);
}
const price = listed.credits?.default ?? listed.credits?.[SIZE] ?? 1;
const unsubmitted = todo.filter((j) => last(j)?.status !== "pending").length;
const need = +(unsubmitted * price).toFixed(2);
const after = +(acct.balance_credits - need).toFixed(2);
if (argv.includes("--quote")) {
  console.log(
    `QUOTE: ${unsubmitted} image${unsubmitted === 1 ? "" : "s"} with ${PROFILE.label} at ${price} credits each = ${need} credits. ` +
      `Balance now ${acct.balance_credits} credits` + (after >= 0 ? `; about ${after} after this stage.` : ".") +
      (todo.length > unsubmitted ? ` (${todo.length - unsubmitted} more already running from an earlier start, already paid for.)` : ""),
  );
  if (after < 0) console.log(`NOT ENOUGH: ${+(need - acct.balance_credits).toFixed(2)} more credits are needed. Top up at https://xelentapi.com/dashboard/billing.`);
  const capLeft = acct.key?.spend_limit_credits == null ? null : +(acct.key.spend_limit_credits - (acct.key.spent_credits ?? 0)).toFixed(2);
  if (capLeft !== null && capLeft < need) {
    console.log(`NOT ENOUGH ON THE KEY: the key "${acct.key.name}" has ${capLeft} credits of its spending limit left. Raise the limit to at least ${Math.ceil((acct.key.spent_credits ?? 0) + need)} or remove it at https://xelentapi.com/dashboard/keys.`);
  }
  process.exit(0);
}
log(`Xelent API ${apiBase()}: ${acct.balance_credits} credits available; ${todo.length} images to make with ${PROFILE.label} (${unsubmitted} new, about ${need} credits).`);
const startedAt = new Date().toISOString();
if (acct.balance_credits < need) {
  console.error(`Not enough credits: ${need} needed, ${acct.balance_credits} available. Top up at https://xelentapi.com/dashboard/billing or run fewer products (plan.py --only).`);
  process.exit(3);
}
// A key can carry its own spending cap, separate from the balance. Check it too, so a stage never stops halfway.
const cap = acct.key?.spend_limit_credits;
if (cap !== null && cap !== undefined) {
  const left = +(cap - (acct.key.spent_credits ?? 0)).toFixed(2);
  if (left < need) {
    console.error(
      `This API key has ${left} of its ${cap}-credit spending limit left, and this stage needs about ${need} credits (${unsubmitted} images at ${price}). ` +
        `The account balance (${acct.balance_credits} credits) is fine: the limit is on the key. Raise the key's limit to at least ${Math.ceil((acct.key.spent_credits ?? 0) + need)} credits, ` +
        `or remove it, at https://xelentapi.com/dashboard/keys (edit the key "${acct.key.name}"), then run again. Finished images are kept.`,
    );
    process.exit(3);
  }
}

let lastLine = 0;
for (;;) {
  const pending = JOBS.filter((j) => !done(j) && last(j)?.status === "pending");
  if (pending.length) await pool(pending, 8, poll);
  const ready = JOBS.filter((j) => {
    if (done(j)) return false;
    const a = last(j);
    if (a?.status === "pending" || gaveUp(j)) return false;
    if (a?.status === "neterror" && Date.now() - Date.parse(a.at) < 15_000) return false;
    return true;
  });
  const slots = Math.max(0, CONC - JOBS.filter((j) => !done(j) && last(j)?.status === "pending").length);
  if (ready.length && slots) await pool(ready.slice(0, slots), slots, submit);
  const s = status();
  if (Date.now() - lastLine > 60_000 || (!s.running && !s.waiting)) { log(`progress: ${s.done}/${s.total} done, ${s.running} running, ${s.waiting} waiting, ${s.failed} gave up`); lastLine = Date.now(); }
  if (!s.running && !s.waiting) break;
  await sleep(POLL_MS);
}
const s = status();
log(`FINISHED ${s.done}/${s.total}` + (s.missing.length ? `; missing: ${s.missing.join(", ")}` : ""));
// What this run cost (failed and refused images are never charged) and what is left.
const madeNow = JOBS.flatMap((j) => ledger[j.name].attempts).filter((a) => a.status === "succeeded" && a.doneAt >= startedAt);
const used = +madeNow.reduce((sum, a) => sum + (a.credits ?? price), 0).toFixed(2);
const now = await verifyKey().catch(() => null);
console.log(
  `CREDITS: this run used ${used} credits for ${madeNow.length} image${madeNow.length === 1 ? "" : "s"}` +
    (now ? `. Balance left: ${now.balance_credits} credits` + (now.held_credits ? ` (${now.held_credits} more are on hold for images still finishing, refunded if they fail)` : "") + "." : "."),
);
process.exit(s.missing.length ? 2 : 0);
