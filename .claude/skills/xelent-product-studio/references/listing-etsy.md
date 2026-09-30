# Etsy listings

Etsy is a retail marketplace of individual buyers. They search in plain, descriptive and occasion language,
judge a listing by its first photo, and buy from listings that answer their questions about fit, fabric,
personalisation and delivery. Listings are created as **drafts**; the seller reviews and publishes them in
Etsy Shop Manager.

Write one file per product: `listings/<id>.etsy.json`. Shop-specific ids come from `studio.json`
(`marketplaces.etsy`) unless the file overrides them.

```json
{
  "title": "Custom Football Jersey with Name and Number, Recycled Polyester Team Shirt for Adults and Kids",
  "description": "A lightweight custom football jersey made to order with your team name, player names and numbers.\n\n...",
  "price": 34.0,
  "taxonomy_id": 1831,
  "tags": ["custom soccer jersey", "team football shirt", "personalized jersey", "name and number shirt", "..."],
  "materials": ["recycled polyester"],
  "styles": ["Sporty"],
  "variations": {"sizes": ["S", "M", "L", "XL"], "colors": ["Navy", "Forest"], "price_by_size": {"XL": 36.0}},
  "image_alt_texts": ["Front of a navy custom football jersey with tonal chest band, on white", "..."]
}
```
The `taxonomy_id` above is only an illustration; look up the real one for each product.

## Title (max 140 characters)
- Lead with the phrase a buyer types (the **primary noun phrase**): "Custom Football Jersey", "Heavyweight
  Boxy Hoodie", "Personalised BJJ Rash Guard". Put the most important objective traits next: material,
  personalisation, audience.
- Readable sentence case, ideally under 15 words. `% : & +` at most once each. No ALL CAPS, no emoji.
- Skip filler and badges Etsy shows itself: "best", "perfect", "unique", "gift for", "sale", "free shipping".
  Gift and occasion words belong in tags.

## Tags (13, each up to 20 characters)
- Use all 13. Multi-word phrases from `research/keywords.json` (etsy list), varied intent: product, style,
  personalisation, audience, use, occasion, recipient.
- Letters, numbers, spaces, hyphens and apostrophes only. No repeats, no competitor brands or teams.
- Don't spend tags on the materials field's words; materials are searchable on their own.

## Description
Etsy shows the first lines in search previews and Google indexes them. Write for a phone screen:
1. One or two sentences that say exactly what it is, with the primary noun phrase.
2. What makes it good (fabric, fit, decoration, personalisation) in a short paragraph.
3. A feature list with `•` bullets: fabric and gsm, fit, decoration method, sizes, colourways, care.
4. **Personalisation**: what to send (names, numbers, logo file), and what happens next (proof before production).
5. **Sizing**: how it fits and a pointer to the size-chart photo.
6. **Making and delivery**: made to order, production time, shipping from where (from `studio.json`).
7. Care instructions and a short, friendly close.
No links, no contact details off Etsy, no claims you cannot prove.

## Fields
- `taxonomy_id`: the most specific Etsy category: `node xelent.mjs etsy-taxonomy "football jersey"`.
- `who_made`: `i_did` when the seller's own business makes it (a factory selling its own products);
  `someone_else` when another business makes it, which also needs `production_partner_ids` (create the partner in
  Etsy Shop Manager > Settings > Production partners first).
- `when_made`: `made_to_order` for custom and produced-after-order items.
- `shipping_profile_id`, `readiness_state_id` (processing profile), `return_policy_id`: from
  `node xelent.mjs etsy-reference`; put them in `studio.json` once.
- `variations`: sizes and colours become Etsy inventory rows; `price_by_size` for size-based pricing.
- `image_alt_texts`: one per image, describing what is in that image (not a copy of the title), up to 250 characters.
- Personalisation questions and EU product-safety (GPSR) details are set in Shop Manager after the draft exists.

## Images
Up to 20 square 2000 px JPEGs (Etsy asks for at least 2000 px on the shortest side; 1:1 or 4:3), about 1 MB
each. Order: front, lifestyle, back, side, detail, flat lay, inside view, colourways, size chart. Etsy crops
the first image into a landscape thumbnail, so the product sits centred with room at the sides.

## AI imagery and Etsy's rules
Etsy's creativity standards require sellers to disclose when AI tools were used to create an item or its design,
and they expect photos to represent the item the buyer receives. Rendered or generated images are tolerated for
made-to-order and custom items when they match what will be made.

This skill makes that a per-shop setting, `marketplaces.etsy.disclose_ai`:
- `true` (the template default): the description must contain `ai_disclosure_text` word for word, for example
  "Product photos are digital renderings of the made-to-order design; your item is produced to the same specification."
- `false`: the listing must not mention how the images were made, and the listing is presented purely as the
  design. Tell the seller, once, when they choose this: Etsy can deactivate listings or suspend shops that do not
  disclose AI use, and buyers can open cases when an item does not match its photos. The skill's consistency and
  manufacturability checks reduce the second risk; only disclosure removes the first.

Whatever the setting, the photographs must show exactly what the factory will make: same cut, colours,
decoration method and placement. That is also why the sheets are approved before anything is listed.

## Submitting
`publish.mjs --submit` hosts the images, then Xelent API creates the draft through Etsy's Open API v3
(createDraftListing, then uploads each image, then sets inventory). The seller's own Etsy app key is used: each
seller creates an app at etsy.com/developers with the callback URL shown on xelentapi.com/dashboard/marketplaces,
and connects there. The draft opens in the listing editor at the link `publish.mjs` prints. Nothing is activated.
