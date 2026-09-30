# Image direction: consistent, photorealistic, accurate

Separately generated views drift: the back gets a different logo, the sleeve loses its patch, the colours shift.
This skill agrees the design once, on one **concept sheet** showing every view of the same product, and then
draws every final photograph from that approved sheet. Extras (detail, flat lay, lifestyle, colourways) are
drawn from the sheet **and** the finished front and back photographs, so they inherit the approved look.

```
studio.json products ──► sheets (1 image per product) ──► user approves ──► views (1 per angle, 2K or 4K)
                                                                              └─► extras (detail, flat lay,
                                                                                  lifestyle, colourways)
size_chart.py draws the size chart; nothing numeric is ever generated.
```

## Views by type

| type | views | notes |
|---|---|---|
| `top`, `dress` | front, back, left, right | ghost mannequin. Hoodies, tees, jerseys, polos, sweatshirts: set `noun` |
| `jacket`, `gi` | front, back, left, right, open | the open view shows the lining; the front view shows it at the neck |
| `bottom` | front, back, left, right | trousers by default; set `noun` for shorts, leggings, joggers |
| `vest` | front, back, left, right | sleeveless |
| `headwear` | front, back, left, right | caps, beanies, bucket hats: set `noun` |
| `socks` | front, back, left (outer), right (inner) | on invisible leg forms |
| `gloves` | front (backs of hands), back (palms), left, right | no hands |
| `belt`, `object` | front, back, left, right | bags, pads, accessories use `object` with a `noun` |

Override with `views` on the product when needed.

Extras, per product (`extras`, default all): `detail` (macro of `detail_focus`), `flatlay`, `lifestyle`
(worn in a scene: `lifestyle.scene` and `lifestyle.model`, falling back to the direction's `lifestyle_scene`),
`colorways` (one front per extra colourway, recoloured from the finished front).

## What every prompt carries
- The product's complete `design`, fabric, gsm, fit and decoration methods.
- The views' `view_details`, so each angle shows its own details.
- A realism clause: true fabric weight and drape, real seams, prints at true scale, nothing unsewable.
- A no-text clause: no captions, measurements or watermarks, no other brands' logos, no league or event marks.
- White background (`style.background: "white"`, Alibaba's main image needs it) or light grey.

## Your checks (do these before the user sees anything)

**Sheets**: every panel is the same product; all views present and in order; each `view_details` item visible
in its view (zoom into the neck of lined garments); logos match the brand; nothing written that was not asked for;
no real brand, club or character look-alikes; the decoration looks like its method (embroidery has stitches,
sublimation is flat); the garment is physically possible (seams where panels meet, sleeves attached sensibly,
symmetrical where the design is symmetrical). Send bad ones back yourself:
`approve.py --changes <id> "what is wrong"`, then plan and run again. Only show the user sheets you would stand behind.

**Views**: compare each against the sheet: same colours, same logo placement and size, right angle, whole product
in frame, clean white background, no mannequin visible, and exactly one product in the picture. `board.py --stage views`
prints a `CHECK:` line (and frames the thumbnail in red) when a view or colourway contains more than one separate
product, which happens when the model copies several sheet panels; redo every flagged image. Check side views by
their front edge: in `left` the garment's front faces the left edge of the picture and a left-chest mark shows; in
`right` the front faces right. Redo a view: `plan.py --stage views --only <id> --redo back`.

**Extras**: detail shows the actual decoration and fabric of this product; the lifestyle garment matches the views
exactly (colours, panels, logos, fit) and nothing else in the scene carries a brand; colourways change colours only.

## When the model misbehaves
- A revision keeps an artifact from the previous sheet: re-plan with `--fresh <id>` so the old sheet is not
  attached, and word the note as what the sheet should show.
- Text appears on the garment: add "plain, no text" to the part where it appeared, in the design text.
- Logo drifts between views: give the logo's size in cm and its exact position, and use `brand.logo` with
  `logo_description` when a brand logo is wanted.
- Colours drift: give hex values in the design text and name the colour the same way everywhere.
- The model refuses (content policy): usually a brand, club or character name in the design; rephrase.
- Lifestyle faces look uncanny: pick a three-quarter or back-turned pose, or drop the lifestyle extra.
- Side views come out mirrored (the left view shows the right side): the prompts state which way the front faces;
  if it still happens, add the facing direction to that view's `view_details`.

## Cost
Each image is one job at the resolution the user chose (`generation.resolution` in studio.json):

| Resolution | Model | Credits per image (1 credit = 1 PKR) |
|---|---|---|
| 2K | Nano Banana 2 | 4 to 9, depending on the package the credits came from |
| 4K | GPT Image 2.5 Sunburst (quality high) | 8 to 18, twice the 2K price |

The exact price on the user's account: `node scripts/xelent.mjs prices`. A product with 4 views, all extras and
3 colourways is about 1 sheet + 4 views + 3 extras + 2 colourways = 10 images, plus revisions.

Before each stage run `run.mjs --quote` and tell the user the images, credits per image, total and balance after;
`run.mjs` also refuses to start when the balance or the key's spending limit is too low. After each stage tell the
user the credits used and the balance left from the `CREDITS:` line `run.mjs` prints.
