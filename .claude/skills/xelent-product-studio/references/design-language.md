# Design language: turning research into products that can be made and sold

A design is ready when a pattern maker could cut it and a buyer can picture wearing it. Every product in
`studio.json` is written against these rules, and `studio.py check-designs` enforces the mechanical ones.

## 1. Start from the direction, then make it practical

For each product, answer in the `design` text:
- **Who wears it and when** (a Sunday-league team in the rain, a gym regular, a skater in autumn).
- **Silhouette and fit**: cut (slim athletic, regular, relaxed, boxy, oversized, cropped), length, collar or
  neckline, sleeve (set-in, raglan, drop shoulder), hem (straight, curved, split, ribbed), closures.
- **Panels and seams**: where colour changes happen, they happen on a seam or on a printed line. Name the
  panels (front body, back body, side panels, sleeves, yoke, collar, cuffs, waistband).
- **Fabric and weight**: fibre content and gsm. Typical ranges: football/teamwear jersey 120-160 gsm polyester
  interlock or mesh; tee 160-220 gsm cotton; heavyweight streetwear tee 240-300 gsm; hoodie 280-400 gsm
  fleece or French terry; leggings 220-280 gsm nylon or polyester elastane; windbreaker 60-90 gsm nylon
  taffeta or ripstop; BJJ gi 350-550 gsm pearl or gold weave cotton.
- **Decoration**: the method for every mark (sublimation, screen print, embroidery, heat transfer, DTF, DTG,
  woven label, patch, silicone print), its placement, and its size in cm.
- **Trims**: zips (type, colour, length), cords and tips, labels, tapes, piping, rib colours.

Write it so the image model and a factory read the same thing. Specific beats pretty: "a 4 cm tonal navy band
across the chest, printed, stopping at the side seams" beats "a sleek modern chest detail".

Go outside in: base cloth and colour, panels, trims, every logo with its colour, size and place, the back,
the inside. Name positions the way a pattern maker would (left chest, upper back, left sleeve at the bicep);
"left" means the wearer's left. Say what is not there when it matters ("plain back, nothing else"), or the
model decorates.

## 2. Balance and restraint

- **One loud idea per garment.** A bold all-over print plus heavy panelling plus big graphics is three ideas
  fighting. Rate each element quiet or busy; more than one busy element needs a reason.
- **A gradient layered on another gradient, marble, tie-dye or watercolour reads as a print fault.**
- **A repeating stripe under another repeating pattern turns to noise**, especially on narrow pieces
  (legs, sleeves, socks).
- **Fine piping and thin tipping disappear under a busy all-over print.**
- **Tonal and restrained looks need texture or finish to carry them**: a jacquard-effect print, a rib contrast,
  a woven label, or a different fabric on one panel.
- **Colour proportion**: roughly 60% base, 30% secondary, 10% accent. Three colours plus white or black is plenty.
- **Contrast for purpose**: team kits need numbers and names readable at 30 m; streetwear graphics need to
  read in a 200 px marketplace thumbnail.
- **Scale**: logos on a chest 7-10 cm wide; a back graphic 25-30 cm; a sleeve mark 5-8 cm; numbers on a
  football back 20-25 cm tall.

## 3. Decoration methods: what each can and cannot do

| Method | Works on | Good for | Limits |
|---|---|---|---|
| Sublimation | polyester and poly-rich blends, white or light base | all-over prints, gradients, photographic art, full kits | dull or impossible on cotton; cannot print white or lighten a dark fabric |
| Screen print | cotton, blends, poly with the right ink | flat spot colours, big graphics, retail tees | one screen per colour; fine gradients need halftones; cost rises with colours |
| Embroidery | most fabrics (support needed on thin knits) | logos, crests, small text, premium feel | text under about 5 mm and hairlines fill in; big fills are heavy and stiff |
| Heat transfer / vinyl | most fabrics | names and numbers, small logos | solid colours, visible edge, can crack on heavy stretch |
| DTF | cotton, poly, blends | full-colour art on any colour, short runs | thin film surface, less breathable over large areas |
| DTG | cotton | full-colour art, short runs | poor on polyester; white underbase on dark fabric |
| Woven label / patch | anything, sewn | premium branding, heritage | fine yarn detail only; small text limited |
| Silicone / HD print | performance fabrics | raised logos, grip, tech look | small areas; not for all-over |

Design only with methods listed in `business.capabilities.decoration`. Say how each looks when made:
sublimation is flat and inside the fibre; embroidery has stitch direction and relief; screen print sits on the
surface; vinyl has a crisp edge. The image prompts use this wording so the photographs look manufactured.

## 4. Segment languages

### Teamwear (football, basketball, cricket, rugby, hockey, baseball)
- The kit is a system: shirt, shorts, socks, often a training top and jacket. Design ranges, not orphans.
- Customisable areas must stay clear: chest crest area, sponsor area across the chest, back numbers and
  names, sleeve badge. A graphic that runs under the number makes the number unreadable.
- Colourways are the product: the same template in 4-8 team colour combinations sells to more clubs.
- Kit law (follow it for playing kits; training and fan wear are freer):
  - Football (IFAB Law 4): socks cover shin guards; undershorts and tights match the main shorts colour;
    goalkeepers wear colours distinct from outfield players.
  - Basketball (FIBA): all team members' shirts share one dominant front and back colour; shorts match that
    colour; numbers of the regulated sizes and contrast.
  - Ice hockey (IIHF): numbers on the back and both sleeves.
  - Rugby playing shirts: no zips or hard fastenings.
  - US school sports (NFHS): number size, contrast and placement rules; check the current year's document.
- Common modern language: engineered tonal patterns, wrap-over or ribbed crew collars, raglan sleeves,
  side mesh panels, retro polo collars on heritage lines, sublimated gradients used sparingly.

### Streetwear
- Silhouette carries the brand: boxy and cropped tees, heavyweight hoodies with dropped shoulders, wide or
  straight-leg bottoms, washed and garment-dyed finishes.
- Graphics are editorial: a strong back print with a small front mark, type-led designs, puff or cracked
  print, embroidery on heavyweight fabric. Original typography and artwork only.
- Fabric weight and finish are selling points: say the gsm and the wash.

### Activewear and gym
- Fit and function first: squat-proof, gusset, high waist, flatlock seams, sweat-wicking, four-way stretch.
  Only claim what the fabric does.
- Palettes are tonal and muted with one seasonal colour; branding small and placed at the hip or back.
- Sets (bra plus leggings, shorts plus top) sell better than single pieces.

### Combat sports (BJJ gis, rash guards, fight shorts, gloves)
- Gis: IBJJF rules for competition gis (white, blue or black; limits on where patches go). Weave (pearl, gold,
  ripstop pants), weight, collar fill and reinforcement are the specification.
- Rash guards and shorts: sublimated art, bold themes, but original characters only.
- Gloves and pads: materials (synthetic or genuine leather), padding, closure, weight in oz.

### Outerwear
- Construction is the design: seams, taping, zips, hoods, pockets, cuffs, hems, linings. Name each.
- Only claim waterproofing with a rating the fabric actually has.

## 5. Practical and fresh

- **Fresh** means a recognisable trend expressed in a way the current top listings do not: a new colour story on a
  proven silhouette, a better construction detail, a range that coordinates.
- **Practical** means it can be made at the factory's MOQ and price, washes and wears well, fits real bodies,
  and can be personalised where the market expects it (teamwear names and numbers, club crests, gift text on Etsy).
- Every product should answer: why would a buyer pick this over the first page of results?

## 6. Writing `view_details`

List, per view, what must be visible from that angle, so no view drops a detail:
```json
"view_details": {
  "front": "left-chest embroidered crest 8 cm; 4 cm tonal chest band; navy rib collar",
  "back": "blank number area; neck tape with a small woven label below the collar",
  "left": "raglan seam; mesh side panel; small printed sleeve mark near the cuff",
  "right": "raglan seam; mesh side panel"
}
```
Lined garments (type `gi`, `jacket`) automatically get "lining visible at the neck" on the front view.
