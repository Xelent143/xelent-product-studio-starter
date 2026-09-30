# Choosing a style, and what goes wrong

## What to recommend

| Product | Styles that sell it | Looks |
|---|---|---|
| Football, basketball, cricket kits | Sport in action, Team walk-out, 360° turn | Stadium floodlights, Clean studio |
| Fightwear: rash guards, shorts, gis | Sport in action (BJJ drill, shadowboxing), UGC try-on | Gym grit, Clean studio |
| Activewear, gym wear, leggings | Sport in action, UGC try-on, Performance test (stretch) | Gym grit, Phone camera at home |
| Hoodies, tees, streetwear | Street style, Lookbook poses, UGC try-on | Urban street, Neon night, Golden hour |
| Jackets, outerwear, windbreakers | 360° turn, Performance test (water, wind), Runway walk | Outdoors, Urban street, Editorial |
| Hunting and outdoor wear | 360° turn, Street style (on a trail), Detail close-ups | Outdoors |
| Leather jackets, premium pieces | Hero reveal, Runway walk, Lookbook poses | Luxury dark, Editorial |
| Any product for wholesale buyers | Detail close-ups, Made in our factory, 360° turn | Clean studio, Factory floor |
| A photo of the garment on a mannequin | Mannequin 360° (send a back photo too), Detail close-ups | Same as my photo |

| Where | Shape | Length | Style |
|---|---|---|---|
| Etsy listing | horizontal | 5 to 15 s, silent | 360° turn or Flat lay to worn, Clean studio |
| Alibaba product | horizontal | 15 to 30 s | Detail close-ups, Made in our factory, 360° turn |
| Reels, TikTok, Shorts | vertical | 8 to 15 s (or a 20 to 30 s edit) | Street style, UGC try-on, Sport in action |
| Website hero | horizontal | 10 to 20 s | Hero reveal, Runway walk |

A 5 to 15 s single shot is the most reliable. Edits of several shots give more variety but each shot is a new
chance for the product or face to drift, so check each one.

## How the prompts work

- The **cast** still (Nano Banana 2) puts the chosen model in the product, using every product photo. It is
  reused in every model shot, so the same person and the same outfit appear throughout.
- Each **opening frame** (Nano Banana 2) is the first frame of its shot, in the shot's setting, light and framing,
  made from the cast and the product photos. Most mistakes are cheaper to fix here than in the video.
- Each **clip** (MiniMax H3) gets the opening frame first, then the cast, then the product photos (at most 9
  images), and a prompt with the camera, the opening, the action, the setting, light, look and sound. Every prompt
  numbers its reference images so the model knows which is which.
- A **note** (`--note`) is added to that shot's prompt as a correction and kept for later redos. Be concrete: "hood
  down", "waist-up framing", "the orange band is on the left sleeve only", "no one else in the frame".

## What goes wrong (check every strip)

- **A cut in the middle of a clip.** MiniMax sometimes jumps to a new angle. If the jump is near the start, use a
  later in-point (`assemble --in N=SECONDS`); otherwise redo the clip.
- **The product drifts:** a logo moves, a panel changes colour, pockets appear or vanish, a hood goes up. Redo with
  a note naming the part.
- **The face changes** between shots or during a turn. Redo the clip; if it keeps happening, redo the cast from a
  clearer face.
- **Hands and limbs:** extra fingers, arms passing through the body during a turn. Redo.
- **Setting leaks:** a shared setting line drags an outdoor shot indoors. Each shot carries its own setting line
  from the look; keep it that way when editing prompts.
- **The finished garment appears in a factory shot.** Process shots deliberately send no product photos and no
  product description. Do not add them.
- **Text and logos:** signs, captions or invented brand marks. Redo with "no text or signs anywhere". Small print on
  the garment itself (fine lettering, katakana, barcodes) can blur or change a little; large graphics hold.
- **The back without a back photo** (Mannequin 360°, 360° turn, Runway walk, Hero reveal): the model invents it.
  Ask for a back photo; if there is none, tell the user the back is a guess.
- **Team walk-out:** each player's face is different by design, and small kit details can vary between players.
  Say so to the user when they pick it.

Clips come back about 0.6 s longer than asked; the edit trims them to the exact length. Output is 24 fps with
natural sound (no music, no speech).
