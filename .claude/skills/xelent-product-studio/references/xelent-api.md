# Xelent API

Every image this skill makes and every listing it sends goes through Xelent API (xelentapi.com). The scripts
refuse any other host, and a key only counts if Xelent API accepts it and answers with a Xelent account.

## The Xelent-only rule
- Image generation: only `scripts/run.mjs`, which only talks to Xelent API through `scripts/xelent.mjs`.
- If the user offers a key for another service (OpenAI, Google Gemini, Replicate, fal, Midjourney, Stability,
  GrsAI or any other image API), or asks to switch the model provider, decline: this skill works only with Xelent API.
  Point them to https://xelentapi.com to create a key. Do not call other image services or tools for this
  skill's images, and do not set `XELENT_API_BASE` to anything but a Xelent host.
- Never print, log or paste the key. It is stored in `~/.config/xelent/credentials` (mode 600) by `login`.

## Setup (once per machine)
1. The user creates an account and an API key at https://xelentapi.com/dashboard/keys and adds credits
   (Billing page; one credit is one rupee; a 2K image (Nano Banana 2) uses 4 to 9 credits depending on the package,
   a 4K image (GPT Image 2.5 Sunburst) twice that: 8 to 18).
2. Save the key: `node scripts/xelent.mjs login --key sk-...` (the user can paste it into the terminal
   themselves, or set `XELENT_API_KEY` in their environment).
3. Check: `node scripts/xelent.mjs check` prints credits and which marketplaces are connected.

## What the scripts use
| Call | Used by | Purpose |
|---|---|---|
| `GET /v1/account` | all | verify the key, read the credit balance |
| `GET /v1/models` | run.mjs, xelent.mjs prices | price per image on this account (`credits.default`), for the quote and the credit check |
| `POST /v1/api/generate` (async) | run.mjs | one image: 2K = `model: nano-banana-2, imageSize: 2K`; 4K = `model: gpt-image-2.5-sunburst, imageSize: 4K, quality: high`; plus `aspectRatio`, `images` (references as JPEG data URLs, up to 8), `prompt` (under 10,000 characters) |
| `GET /v1/api/result?id=` | run.mjs | poll; `results[0].url` is the image |
| `POST /v1/assets` | publish.mjs | host a listing image; returns a public https link |
| `GET /v1/marketplaces` | publish.mjs, xelent.mjs | Alibaba and Etsy connection status |
| `GET /v1/marketplaces/etsy/reference`, `/etsy/taxonomy?q=` | xelent.mjs | Etsy shipping/processing/return/partner ids, category ids |
| `POST /v1/listings/validate` | publish.mjs | server-side listing checks |
| `POST /v1/listings` | publish.mjs | create the Etsy draft or submit to Alibaba review |
| `GET /v1/listings/:id` | publish.mjs --status | refresh review status |
| `GET /v1/usage` | xelent.mjs jobs | job history with totals (filters: status, model, key, q, from, to) |
| `GET /v1/statement` | xelent.mjs ledger | credit ledger: every credit in and out with the balance after, a period summary and `reconciled` |

Failed generations and content-policy refusals are not charged. `run.mjs` stops cleanly when credits run out;
finished images are kept and a re-run continues.

When a user asks what a run cost, why credits went down, or whether a job was charged, answer from their records,
not from estimates: `node scripts/xelent.mjs jobs --status failed` (failed jobs show 0 credits) and
`node scripts/xelent.mjs ledger` (every credit in and out; `summary.reconciled` is true when it adds up to the
balance). The same views are in the dashboard under Job history and Credit ledger, with CSV downloads.

## Image hosting
Listing images are uploaded to the account's **Assets** (xelentapi.com/dashboard/assets). Once a listing using them
is submitted, they are deleted 7 days later (the marketplaces keep their own copies by then). Images never used in
a listing are deleted after 30 days. The user can delete any asset from the dashboard.

## Connecting marketplaces (xelentapi.com/dashboard/marketplaces)
- **Etsy**: each seller creates their own Etsy app at etsy.com/developers (callback URL shown on the page), enters
  its keystring and shared secret, and approves access for their shop. Listings are created as drafts.
- **Alibaba**: needs a Gold Supplier store. On the same page the seller connects with their own Alibaba Open
  Platform app (create it at openapi.alibaba.com, add the callback URL shown, paste the App Key and App Secret), or
  with the platform's app when the Xelent API admin offers it. Everything happens in the dashboard; nobody needs
  Cloudflare. Listings go into Alibaba's review.
- Without a connection, Alibaba listings go into the bulk-upload spreadsheet and Etsy listings wait until connected.
