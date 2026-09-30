#!/usr/bin/env node
// Run <dir>/jobs.json on Xelent API: stills (cast, keyframes) with Nano Banana 2 and video clips with MiniMax H3.
// Safe to stop and re-run at any time.
//   node render.mjs --dir D --estimate    what the whole video will cost from here (plan.json), and the balance
//   node render.mjs --dir D --quote       what this stage (jobs.json) will cost and the balance after; makes nothing
//   node render.mjs --dir D               make this stage, then report the credits used and the balance left
//   node render.mjs --dir D --status      progress only
//   node render.mjs --dir D --restore     download again (free) every still and clip already made whose file is missing
// A job is done when its output file exists. Every generation id is written to <dir>/ledger.json before anything
// else, so a re-run polls what was already submitted instead of paying again, and a still or clip whose file is gone
// (a cloud session's machine was reset) is downloaded again from the link Xelent keeps for 7 days.
import { readFileSync, writeFileSync, existsSync, mkdirSync, renameSync, statSync } from "node:fs";
import { dirname, join, resolve, basename } from "node:path";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { apiBase, verifyKey, submitGeneration, generationResult, xelent, XelentError } from "./xelent.mjs";

const argv = process.argv.slice(2);
const arg = (n, d) => { const i = argv.indexOf(n); return i > -1 && argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : d; };
const D = resolve(arg("--dir", "."));
const CONC = +arg("--concurrency", "4");
const MAX_TRIES = 3, MAX_NET = 8, POLL_MS = 10_000;
const STALE_MIN = { image: 20, video: 45 }; // MiniMax takes about 7 minutes for 6 s and up to 17 for 10-15 s

const JOBS = existsSync(join(D, "jobs.json")) ? JSON.parse(readFileSync(join(D, "jobs.json"), "utf8")) : [];
const LEDGER = join(D, "ledger.json");
const ledger = existsSync(LEDGER) ? JSON.parse(readFileSync(LEDGER, "utf8")) : {};
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
if (argv.includes("--status")) { console.log(JSON.stringify(status(), null, 1)); process.exit(0); }

// ---------------------------------------------------------------------------
// Prices: stills per image, video per second at its resolution (from this account's /v1/models)
// ---------------------------------------------------------------------------

let MODELS = null;
async function models() {
  MODELS ??= (await xelent("/v1/models")).data ?? [];
  return MODELS;
}
async function priceOf(job) {
  const m = (await models()).find((x) => x.id === job.model);
  if (!m) throw new Error(`${job.model} is not available on this Xelent API account right now.`);
  if (job.kind === "video") {
    const perSecond = m.credits?.[job.resolution];
    if (perSecond === undefined) throw new Error(`${job.model} has no price at ${job.resolution}.`);
    return +(perSecond * job.duration).toFixed(2);
  }
  return m.credits?.default ?? 0;
}

// ---------------------------------------------------------------------------
// Files
// ---------------------------------------------------------------------------

class Expired extends Error {}
async function download(url, out) {
  const res = await fetch(url, { signal: AbortSignal.timeout(300_000) });
  if (res.status === 404 || res.status === 410) throw new Expired("file no longer on Xelent");
  if (!res.ok) throw new Error("download HTTP " + res.status);
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out + ".part", Buffer.from(await res.arrayBuffer()));
  renameSync(out + ".part", out);
}

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

// --restore: bring back every still and clip this workspace already paid for.
async function pool(items, n, fn) { const q = [...items]; await Promise.all(Array.from({ length: Math.min(n, q.length) }, async () => { while (q.length) await fn(q.shift()); })); }
if (argv.includes("--restore")) {
  const missing = Object.entries(ledger)
    .map(([name, e]) => ({ name, out: e.out, a: e.attempts.filter((x) => x.status === "succeeded" && x.url).at(-1) }))
    .filter((x) => x.out && x.a && !existsSync(x.out));
  const counts = { restored: 0, expired: 0, failed: 0 };
  await pool(missing, 4, async (x) => {
    for (let attempt = 1; ; attempt++) {
      try { await download(x.a.url, x.out); counts.restored++; return; }
      catch (e) {
        if (e instanceof Expired) { counts.expired++; log("no longer on Xelent (older than 7 days):", x.name); return; }
        if (attempt >= 3) { counts.failed++; log("could not download:", x.name, e.message); return; }
        await sleep(3000 * attempt);
      }
    }
  });
  console.log(`RESTORE: ${counts.restored} file(s) downloaded again for free` +
    (counts.expired ? `, ${counts.expired} no longer on Xelent (make that stage again)` : "") +
    (counts.failed ? `, ${counts.failed} failed (run --restore again)` : "") + ".");
  process.exit(counts.failed ? 5 : 0);
}

// --estimate: everything still to make for the whole video, from plan.json.
if (argv.includes("--estimate")) {
  const plan = JSON.parse(readFileSync(join(D, "plan.json"), "utf8"));
  const brief = JSON.parse(readFileSync(join(D, "brief.json"), "utf8"));
  const acct = await verifyKey();
  const still = await priceOf({ kind: "image", model: "nano-banana-2" });
  const perSecond = (await priceOf({ kind: "video", model: "minimax-h3", resolution: brief.resolution, duration: 1 }));
  const castLeft = plan.cast && !existsSync(join(D, "cast", `cast-v${plan.cast_version}.png`)) ? 1 : 0;
  const kfLeft = plan.shots.filter((s) => !existsSync(join(D, "keyframes", `shot-${String(s.n).padStart(2, "0")}-v${s.keyframe_version}.png`))).length;
  const secsLeft = plan.shots.filter((s) => !existsSync(join(D, "clips", `shot-${String(s.n).padStart(2, "0")}-v${s.clip_version}.mp4`))).reduce((t, s) => t + s.seconds, 0);
  const total = +((castLeft + kfLeft) * still + secsLeft * perSecond).toFixed(2);
  console.log(
    `ESTIMATE: ${castLeft ? "1 cast still + " : ""}${kfLeft} keyframe still(s) at ${still} credits each` +
      ` + ${secsLeft} s of ${brief.resolution} video at ${perSecond} credits a second = about ${total} credits (redos extra).` +
      ` Balance now ${acct.balance_credits} credits` + (acct.balance_credits >= total ? `; about ${+(acct.balance_credits - total).toFixed(2)} after.` : `: NOT ENOUGH, ${+(total - acct.balance_credits).toFixed(2)} more needed.`),
  );
  process.exit(0);
}

// ---------------------------------------------------------------------------
// Submit and poll
// ---------------------------------------------------------------------------

const isNet = (e) => e instanceof XelentError && (e.status === 0 || e.status >= 500 || e.status === 429);

async function submit(j) {
  const at = new Date().toISOString();
  try {
    const images = (j.refs || []).map((r) => "data:image/jpeg;base64," + readFileSync(small(r)).toString("base64"));
    const params = j.kind === "video"
      ? { model: j.model, prompt: j.prompt, aspectRatio: j.aspect, resolution: j.resolution, duration: j.duration, images }
      : { model: j.model, prompt: j.prompt, aspectRatio: j.aspect, imageSize: j.imageSize, quality: j.quality, images };
    const id = await submitGeneration(params);
    ledger[j.name].attempts.push({ id, at, status: "pending", kind: j.kind });
    log("submitted", j.name);
  } catch (e) {
    const violation = e instanceof XelentError && e.code === "content_policy_violation";
    ledger[j.name].attempts.push({ id: null, at, status: violation ? "violation" : isNet(e) ? "neterror" : "failed", reason: e.message });
    log(violation ? "REFUSED (content policy; change the brief or the photos)" : "submit failed", j.name, e.message);
    if (e instanceof XelentError && (e.status === 401 || e.status === 402 || e.code === "insufficient_credits")) {
      save();
      console.error(`\nStopped: ${e.message}\nTop up at https://xelentapi.com/dashboard/billing, then run this again; finished files are kept.`);
      process.exit(3);
    }
  }
  save();
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
      a.status = r.status; a.reason = r.error || "unknown"; log(r.status.toUpperCase(), j.name, a.reason, "(not charged)");
    } else if (Date.now() - Date.parse(a.at) > STALE_MIN[j.kind] * 60_000) {
      a.status = "stale"; log("stale, will resubmit", j.name);
    }
  } catch (e) { a.lastError = e.message; }
  save();
}

// Already made and paid for, but the file is gone: download it again, free.
const paidFor = (j) => { const a = last(j); return !done(j) && a?.status === "succeeded" && a.url ? a : null; };
const lost = JOBS.filter(paidFor);
if (lost.length) {
  log(`${lost.length} file(s) already made and paid for are missing; downloading again (free).`);
  const failed = [];
  await pool(lost, 4, async (j) => {
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
    console.error(`Could not download ${failed.length} paid file(s) again: ${failed.join(", ")}. Nothing was charged. Check the connection and run again.`);
    process.exit(5);
  }
}

const todo = JOBS.filter((j) => !done(j));
if (!todo.length) { log(argv.includes("--quote") ? "QUOTE: 0 credits: everything in this stage is already made." : "nothing to make: every file is already here"); process.exit(0); }
const acct = await verifyKey().catch((e) => { console.error(`Xelent API: ${e.message}`); process.exit(1); });
const fresh = todo.filter((j) => last(j)?.status !== "pending");
let need = 0;
const lines = [];
for (const j of fresh) {
  const p = await priceOf(j).catch((e) => { console.error(e.message); process.exit(4); });
  need += p;
  lines.push(j.kind === "video" ? `${j.name}: ${j.duration} s at ${j.resolution} = ${p}` : `${j.name}: ${p}`);
}
need = +need.toFixed(2);
const after = +(acct.balance_credits - need).toFixed(2);
if (argv.includes("--quote")) {
  const clips = fresh.filter((j) => j.kind === "video");
  const stills = fresh.length - clips.length;
  console.log(
    `QUOTE: ${stills ? `${stills} still(s)` : ""}${stills && clips.length ? " + " : ""}${clips.length ? `${clips.length} clip(s), ${clips.reduce((t, j) => t + j.duration, 0)} s of video` : ""}` +
      ` = ${need} credits (${lines.join("; ")}). Balance now ${acct.balance_credits} credits` + (after >= 0 ? `; about ${after} after.` : ".") +
      (todo.length > fresh.length ? ` (${todo.length - fresh.length} more already running, already paid for.)` : ""),
  );
  if (after < 0) console.log(`NOT ENOUGH: ${+(need - acct.balance_credits).toFixed(2)} more credits are needed. Top up at https://xelentapi.com/dashboard/billing.`);
  const capLeft = acct.key?.spend_limit_credits == null ? null : +(acct.key.spend_limit_credits - (acct.key.spent_credits ?? 0)).toFixed(2);
  if (capLeft !== null && capLeft < need) console.log(`NOT ENOUGH ON THE KEY: the key "${acct.key.name}" has ${capLeft} credits of its limit left; raise it at https://xelentapi.com/dashboard/keys.`);
  process.exit(0);
}
log(`Xelent API ${apiBase()}: ${acct.balance_credits} credits available; ${todo.length} to make (${fresh.length} new, about ${need} credits).`);
if (acct.balance_credits < need) {
  console.error(`Not enough credits: ${need} needed, ${acct.balance_credits} available. Top up at https://xelentapi.com/dashboard/billing.`);
  process.exit(3);
}
const cap = acct.key?.spend_limit_credits;
if (cap !== null && cap !== undefined && +(cap - (acct.key.spent_credits ?? 0)).toFixed(2) < need) {
  console.error(`This API key's spending limit does not cover this stage (${need} credits). Raise or remove it at https://xelentapi.com/dashboard/keys (key "${acct.key.name}"). The balance is fine.`);
  process.exit(3);
}
const startedAt = new Date().toISOString();

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
log(`FINISHED ${s.done}/${s.total}` + (s.missing.length ? `; not made: ${s.missing.join(", ")}` : ""));
const madeNow = JOBS.flatMap((j) => ledger[j.name].attempts).filter((a) => a.status === "succeeded" && a.doneAt >= startedAt);
const used = +madeNow.reduce((sum, a) => sum + (a.credits ?? 0), 0).toFixed(2);
const now = await verifyKey().catch(() => null);
console.log(
  `CREDITS: this run used ${used} credits for ${madeNow.length} file(s)` +
    (now ? `. Balance left: ${now.balance_credits} credits` + (now.held_credits ? ` (${now.held_credits} more on hold for jobs still finishing, refunded if they fail)` : "") + "." : "."),
);
process.exit(s.missing.length ? 2 : 0);
