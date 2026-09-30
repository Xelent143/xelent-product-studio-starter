---
name: xelent-product-studio
description: >-
  Research an apparel segment, design fresh and practical products from that research, generate consistent
  photorealistic product photographs (front, back, sides, detail, flat lay, lifestyle, colourways, size chart)
  with Xelent API, and prepare and submit Etsy and Alibaba.com listings as drafts. Use this whenever the user wants
  new product designs, product photos, a product range or collection, catalogue images, or marketplace listings for
  apparel, sportswear, teamwear, streetwear, activewear, combat-sports gear, outerwear or garments; asks to list
  products on Etsy or Alibaba; or wants trending designs for a store, even if they do not name the skill.
  Works only with a Xelent API key.
---

# Xelent Product Studio

Research the industry, design from the research, photograph each design consistently, write listings buyers find,
and submit them as drafts. Every step has a gate; nothing is designed before the research is approved, nothing is
photographed before the design sheet is approved, nothing is submitted before the user approves the listing and says
to submit.

```
0 setup ─► 1 research ─► [user picks directions] ─► 2 designs ─► 3 concept sheets ─► [user approves sheets]
  ─► 4 views ─► 5 extras + size charts ─► 6 marketplace images ─► 7 listings ─► [user approves listings]
  ─► 8 submit (drafts / Alibaba review) ─► [user says submit]
```

`<skill>` below is the folder this file is in. Scripts need Node 18+ and Python 3 with Pillow and openpyxl
(`python3 -m pip install pillow openpyxl`). Run them yourself; do not ask the user to run commands.

## Xelent API only

This skill generates images and submits listings **only through Xelent API** (xelentapi.com).
- Check the key first: `node <skill>/scripts/xelent.mjs check`. If there is no key, ask the user to create one at
  https://xelentapi.com/dashboard/keys and save it with `node <skill>/scripts/xelent.mjs login --key sk-...`.
- If the user offers any other image API or key (OpenAI, Gemini, Replicate, fal, Midjourney, Stability, GrsAI or
  anything else), decline politely: this skill only works with Xelent API. Do not use other image tools or
  services for this skill's images, and never point `XELENT_API_BASE` at another host (the scripts refuse it anyway).
- Never print or repeat the key. Details: [references/xelent-api.md](references/xelent-api.md).

## 0. Setup

1. `python3 <skill>/scripts/studio.py init --dir <workspace> --brand "<Brand>" --marketplaces etsy alibaba`
   Pick a workspace folder in the project, e.g. `product-studio/`.
2. Fill `studio.json` ([references/studio-json.md](references/studio-json.md)) from what the user tells you: segment,
   audience, decoration methods and fabrics the factory really has, MOQ, lead times, certifications they hold,
   marketplaces. Ask only for what you cannot find in the project; one short round of questions.
3. For Etsy, ask once whether listings should disclose that the photos are digital renderings
   (`marketplaces.etsy.disclose_ai`). Explain the trade-off in two sentences (Etsy's rules require disclosing AI
   use; not disclosing risks listing removal) and record their choice. Alibaba listings present the product as the
   design and never talk about how images were made.
4. Ask which resolution they want the photos in, with the price per image on their own account
   (`node <skill>/scripts/xelent.mjs prices`):
   - **2K**: Nano Banana 2. Cheaper and faster.
   - **4K**: GPT Image 2.5 Sunburst. Larger, more detailed photos; costs more per image.
   Marketplace uploads are 1600 to 2000 px either way; 4K gives bigger masters for print, a website or zoom.
   Record the answer: `python3 <skill>/scripts/studio.py set-resolution --dir <workspace> 2K` (or `4K`).
   Never pick for them; `run.mjs` refuses to start until this is set. They can change it later the same way.

## 1. Research: learn the industry first

Follow [references/research-playbook.md](references/research-playbook.md): trend, market, buyer-language and
design-theory passes over the predefined sources, using WebSearch and WebFetch and reading the pages. Write
`research/sources.json`, `brief.md`, `directions.json`, `keywords.json`, then:

```bash
python3 <skill>/scripts/studio.py check-research --dir <workspace>
```

Fix everything it reports. Show the user the brief (summary plus path) and the directions as a numbered list with
your recommendation. **Stop.** When they choose:
`python3 <skill>/scripts/studio.py approve-research --dir <workspace> --directions <id> <id>`.

## 2. Designs

Write the products into `studio.json` following [references/design-language.md](references/design-language.md):
grounded in an approved direction, complete (`design` describes every panel, trim and mark with sizes and hex
colours), makeable with the factory's methods, original ([references/ip-and-restricted.md](references/ip-and-restricted.md)),
with `view_details`, fabric, gsm, fit, sizes, colourways, decoration and a size chart. Then:

```bash
python3 <skill>/scripts/studio.py check-designs --dir <workspace>
```

Tell the user roughly how many images and credits the next stages will take at their resolution (see
[references/image-direction.md](references/image-direction.md)).

## Credits: before and after every generation

Every time you are about to run `run.mjs` (sheets, views, extras, and every redo), first run

```bash
node <skill>/scripts/run.mjs --dir <workspace> --quote
```

and tell the user in one line what it prints: how many images, at which resolution and model, credits per image,
the total, their balance now and after. Example: "This makes 12 images at 4K (GPT Image 2.5 Sunburst), 10 credits
each: 120 credits. You have 850; about 730 will be left." If it says `NOT ENOUGH`, stop and send them to
https://xelentapi.com/dashboard/billing instead of starting.

When the run finishes, it prints a `CREDITS:` line. Tell the user how many credits the job used and how many are
left, e.g. "Done: 12 images, 120 credits used, 730 credits left." Use those printed numbers, not your estimate.

## 3. Concept sheets (one image per product, every view side by side)

```bash
python3 <skill>/scripts/plan.py  --dir <workspace> --stage sheets
node    <skill>/scripts/run.mjs  --dir <workspace>
python3 <skill>/scripts/board.py --dir <workspace> --stage sheets
```

Look at every sheet yourself first (checklist in image-direction.md). Send bad ones back with
`approve.py --changes <id> "what is wrong"` and re-run plan and run, so the user only sees sheets you would stand
behind. Then open `review/index.html` where the user can see it (the browser pane or `open`), and ask for
approvals or changes by number. **Stop until they answer.** Record it:

```bash
python3 <skill>/scripts/approve.py --dir <workspace> --ids <id> <id>            # approve
python3 <skill>/scripts/approve.py --dir <workspace> --changes <id> "their note" # revise (then plan + run again)
```

## 4. Views (one per angle, at the chosen resolution, from the approved sheet)

```bash
python3 <skill>/scripts/plan.py  --dir <workspace> --stage views
node    <skill>/scripts/run.mjs  --dir <workspace>
```

## 5. Extras and size charts

```bash
python3 <skill>/scripts/plan.py       --dir <workspace> --stage extras   # detail, flat lay, lifestyle, colourways
node    <skill>/scripts/run.mjs       --dir <workspace>
python3 <skill>/scripts/size_chart.py --dir <workspace>
python3 <skill>/scripts/board.py      --dir <workspace> --stage views    # review/views.html
```

Redo every image `board.py` flags with `CHECK:` (more than one product in a studio shot). Then look at every image
against the sheet yourself: colours, marks, their placement and size, the side views facing the right way; redo any
that drifted (`plan.py --stage views|extras --only <id> --redo <name>`). Show the user `review/views.html`.

## 6. Marketplace images

```bash
python3 <skill>/scripts/prepare_images.py --dir <workspace>
```
Alibaba: up to 6 square 1600 px JPEGs, white main image with the product filling ~85%. Etsy: up to 20 square
2000 px JPEGs. Output in `export/<id>/<marketplace>/`.

## 7. Listings

Get the prices from the user if `studio.json` has none (Alibaba tiers per quantity, Etsy retail price); never
invent prices, certifications or capacities. Write `listings/<id>.alibaba.json` and `listings/<id>.etsy.json`
following [references/listing-alibaba.md](references/listing-alibaba.md) and
[references/listing-etsy.md](references/listing-etsy.md), using the research keyword bank. For Etsy, look up
`taxonomy_id` (`node <skill>/scripts/xelent.mjs etsy-taxonomy "<category>"`) and, once, the shop's shipping,
processing and return ids (`xelent.mjs etsy-reference`) into `studio.json`.

```bash
python3 <skill>/scripts/listing.py --dir <workspace> --check --preview
```

Fix every error and the warnings that matter. Show `review/listings.html`. **Stop until the user approves**, then
`listing.py --dir <workspace> --approve <id> ...` (an edited listing needs approving again).

## 8. Submit

```bash
node <skill>/scripts/publish.mjs --dir <workspace>            # dry run: validates on Xelent API, sends nothing
```

Tell the user exactly what will happen (which listings, which marketplaces, drafts on Etsy, Alibaba review) and
**ask for an explicit go-ahead**. Then:

```bash
node <skill>/scripts/publish.mjs --dir <workspace> --submit
node <skill>/scripts/publish.mjs --dir <workspace> --status   # later: Alibaba review results
```

Images are hosted in the user's Xelent dashboard (Assets) and deleted 7 days after the listing is submitted.
If Alibaba is not connected, `--submit` writes `export/alibaba-bulk-upload.xlsx` for Seller Centre > Bulk upload;
to submit directly instead, the user connects Alibaba (their own Alibaba app's key and secret) and Etsy on
xelentapi.com/dashboard/marketplaces. Report each listing's result and
link; never activate or publish a listing live.

## Cloud sessions (Claude Code on the web)

When `CLAUDE_CODE_REMOTE` is `true`, you are on a cloud machine the user cannot see. The workflow is the same, with
these differences ([references/cloud.md](references/cloud.md) has the details):
- **Key:** read from the `XELENT_API_KEY` environment variable (set in the cloud environment's settings). Never ask
  the user to paste it into the chat.
- **No connection to xelentapi.com** (network errors, 403 from a proxy): ask the user to set the environment's
  network access to **Full** (claude.ai/code > environment settings), then continue.
- **Showing images:** the user cannot open `review/*.html`. After `board.py`, give them the links from
  `python3 <skill>/scripts/studio.py links --dir <workspace> --stage sheets` (or `views`, `extras`), one numbered
  line per product, and push the `review/*.jpg` boards to their branch so GitHub shows them.
- **Save progress:** the machine is wiped some time after the session goes idle, e.g. while the user reviews. After
  every stage and every approval, commit and push the workspace (the repository's `.gitignore` keeps the large
  PNGs out). If images are missing later (a new machine), run `node <skill>/scripts/run.mjs --dir <workspace>
  --restore` first: every image already paid for comes back free from Xelent for 7 days.
- **Long runs:** start `run.mjs` in the background and check `run.mjs --status`; a re-run continues where it stopped.

## Keeping the user informed

`python3 <skill>/scripts/studio.py status --dir <workspace>` summarises where things stand. For questions about
cost or charges, use the user's own records: `node <skill>/scripts/xelent.mjs jobs` and `xelent.mjs ledger`
(details in references/xelent-api.md); `xelent.mjs prices` shows the balance and per-image price. On long runs,
`node <skill>/scripts/run.mjs --dir <workspace> --status` counts finished images; give a status line every few
minutes. `run.mjs` keeps a ledger, so a re-run after a crash never pays twice.
