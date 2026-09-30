---
name: xelent-product-video
description: >-
  Make short product videos of clothing with an AI model, the user's own model or their own mannequin photo: 360°
  turns, mannequin 360° spins, runway walks, lookbook poses, street style, sport in action, detail close-ups, hero
  reveals, UGC try-ons, team walk-outs and factory stories, in a chosen look, length (5 to 60 seconds), shape and resolution, generated with MiniMax video on
  Xelent API. Use this whenever the user wants a product video, fashion or apparel video, clothing reel, TikTok or
  Instagram Reel, Etsy or Alibaba listing video, lookbook video, a video of a model wearing their garment, or wants
  to animate product photos, even if they do not name the skill. Works only with a Xelent API key.
---

# Xelent Product Video

Turn product photos into a finished product video. Ask the user a few questions, make one still of the model
wearing the product (the cast), make the first frame of every shot, then animate each shot with MiniMax H3 and
edit them into one video of exactly the length asked for. The user approves the stills before any video is made,
because stills cost a few credits and video costs far more.

```
0 setup ─► 1 questions ─► 2 plan + estimate ─► [user agrees] ─► 3 cast still ─► [user approves]
  ─► 4 opening frames ─► [user approves] ─► 5 clips ─► 6 check every clip ─► 7 final edit ─► 8 hand over
```

`<skill>` is the folder this file is in. Scripts need Node 18+, Python 3 with Pillow, and ffmpeg (if it is missing:
`python3 -m pip install pillow imageio-ffmpeg`). Run them yourself; never ask the user to run commands.

## Xelent API only

Stills and video are made **only through Xelent API** (xelentapi.com), with the same rules as the
xelent-product-studio skill: check the key with `node <skill>/scripts/xelent.mjs check`; if there is none, the user
creates one at https://xelentapi.com/dashboard/keys and it is saved with `xelent.mjs login --key sk-...` (or comes
from `XELENT_API_KEY`). Decline any other image or video API or key, never print the key, and never point
`XELENT_API_BASE` elsewhere.

## Credits: before and after every stage

- After the plan: `node <skill>/scripts/render.mjs --dir <dir> --estimate` gives the whole video's cost. Tell the
  user, e.g. "4 stills at 9 and 20 s of 768p video at 10.5 a second: about 246 credits. You have 1,000."
- Before each stage: `render.mjs --dir <dir> --quote`, and say it in one line. If it says `NOT ENOUGH`, stop and
  send them to https://xelentapi.com/dashboard/billing.
- After each stage: `render.mjs` prints `CREDITS:`. Tell the user the credits used and the balance left.

Prices: `node <skill>/scripts/xelent.mjs prices` (stills per image; video per second at 480p, 768p and 1080p).
Failed and refused jobs are never charged.

## 1. Questions (one message)

Run `python3 <skill>/scripts/video.py options` for the menus. Ask everything in one numbered message with your
recommendation for each, so the user can answer in one line (for example "1 all views, 2 AI man 30s, 3 turntable,
4 outdoors, 5 Reels 15 s, 6 768p"):

1. **Product photos.** As many views as they have: front and back at least; left, right, detail and open
   (inside) views make the garment more accurate. Clean product photos on a plain background work best. If they
   used the xelent-product-studio skill, offer its photos (`video.py init --from-studio <workspace> --product <id>`).
2. **Model.** An AI model (ask for gender, age range, look, build, hair; offer to choose one that suits their
   buyers), their own model (a clear full-length photo, and they must confirm the person agreed to appear in their
   ads; never a celebrity or a photo of someone else), or no model: product-only styles, or **Mannequin 360°** when
   their photo shows the garment on a mannequin (pair it with the look **Same as my photo** and describe the
   photo's background in `scene`). A turn shows the back: without a back photo the back is invented, so ask for
   one.
3. **Video style.** Show the numbered styles from `options` and recommend two or three for their product and where
   it will be posted ([references/styles-guide.md](references/styles-guide.md) has the recommendations).
4. **Look.** The numbered looks from `options`, with a recommendation.
5. **Where it will be posted and how long.** That sets the shape (Reels, TikTok and Shorts vertical; Etsy, Alibaba
   and websites horizontal) and the length: 5 to 15 s is one continuous shot; 20 to 60 s is an edit of 5 to 10 s
   shots. Etsy takes 5 to 15 s and plays without sound.
6. **Resolution and sound.** 768p (default) or 1080p (sharper, about twice the price, 10 s per shot). Keep the
   natural sound the video model adds (footsteps, ambience; no music) or make it silent.

Only ask what the style needs: `sport` for Sport in action and Team walk-out, `feature` for Performance test,
colourway photos for Colourway parade, and what their factory does (`factory.decoration`) for Made in our factory.

## 2. Plan and estimate

```bash
python3 <skill>/scripts/video.py init  --dir <dir>          # e.g. product-video/<product>-<style>
# fill <dir>/brief.json from the answers (references/brief.template.json shows every field)
python3 <skill>/scripts/video.py check --dir <dir>
python3 <skill>/scripts/video.py plan  --dir <dir>
node    <skill>/scripts/render.mjs --dir <dir> --estimate
```

Photo paths in `brief.json` may be absolute or relative to `<dir>`. Tell the user the shot list in plain words and
the estimate, and **wait for a go-ahead** before making anything. To change the edit, edit `plan.json`'s shots
(shot names are in `references/styles.json`) or the brief, then plan again.

## 3. Cast still (only when a model appears)

```bash
python3 <skill>/scripts/video.py jobs --dir <dir> --stage cast
node    <skill>/scripts/render.mjs --dir <dir> --quote     # tell the user
node    <skill>/scripts/render.mjs --dir <dir>
python3 <skill>/scripts/video.py board --dir <dir>         # review.html; open it for the user
```

Look at the cast yourself first, next to the front photo: every colour, panel, logo, print and pocket in the same
place, the model as described, natural hands. Redo anything wrong before the user sees it:
`video.py jobs --stage cast --redo --note "what to fix"`. Then show the user and **wait**. When they approve:
`video.py approve --dir <dir> --stage cast`.

## 4. Opening frames

```bash
python3 <skill>/scripts/video.py jobs --dir <dir> --stage keyframes
node    <skill>/scripts/render.mjs --dir <dir> --quote && node <skill>/scripts/render.mjs --dir <dir>
python3 <skill>/scripts/video.py board --dir <dir>
```

Each frame is where its clip starts, so check the framing matches the shot (full body for a turn, waist-up for a
close) as well as the product. Redo a frame with `--redo <n> --note "..."`. Show the user, **wait**, then
`video.py approve --dir <dir> --stage keyframes` (or `--shots 1 3` for some).

## 5. Clips

```bash
python3 <skill>/scripts/video.py jobs --dir <dir> --stage clips
node    <skill>/scripts/render.mjs --dir <dir> --quote    # tell the user
node    <skill>/scripts/render.mjs --dir <dir>            # start in the background: 6 s takes ~7 min, 10-15 s up to ~17
```

Tell the user roughly how long it will take and give a short progress line now and then
(`render.mjs --status`).

## 6. Check every clip

```bash
python3 <skill>/scripts/video.py strip --dir <dir>        # qa/shot-NN-vN.jpg, two frames a second with times
```

Look at every strip ([references/styles-guide.md](references/styles-guide.md) lists what goes wrong):
one continuous shot (the model sometimes cuts to a new angle mid-clip), the product the same as the photos throughout,
the same face, natural hands and limbs, no extra people, no text. If a clip goes wrong only near its start, use a
later in-point in the edit (`--in 2=1.5`); otherwise redo it: `video.py jobs --stage clips --redo 2 --note "..."`,
quote, render. Show the user the clips on the board.

## 7. Final edit

```bash
python3 <skill>/scripts/video.py assemble --dir <dir> [--in 2=1.5]
python3 <skill>/scripts/video.py board --dir <dir>
```

The final is cut to exactly the asked length and size (1080x1920 vertical or 1920x1080 horizontal, H.264, 24 fps),
with a poster frame. Multi-shot edits cut or cross-fade depending on the look (`transitions` in the brief: auto,
cut or fade). Etsy videos are made silent. Check the final with `video.py strip`-style frames if in doubt.

## 8. Hand over

Give the user the final file (`final/<name>.mp4`) and the poster, what it is made for, the credits used in total
and the balance left. Suggest adding music inside Instagram or TikTok (the video carries only natural sound).
Offer a second version (another look, shape or length); stills already made are reused where they fit.

## Cloud sessions (Claude Code on the web)

When `CLAUDE_CODE_REMOTE` is `true`: the key comes from `XELENT_API_KEY`; the user cannot open `review.html`, so
give them the links from `video.py links --dir <dir>` (stills and clips, kept 7 days); commit and push
`brief.json`, `plan.json`, `ledger.json` and the final video after each stage so a reset machine loses nothing;
after a reset run `render.mjs --dir <dir> --restore` to download everything already paid for, free.
