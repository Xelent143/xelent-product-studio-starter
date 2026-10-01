# Alibaba.com listings

Alibaba is a B2B marketplace: buyers are brands, teams, wholesalers and retailers sourcing a manufacturer.
They search in trade language, compare specifications and price tiers, and send inquiries. A listing wins on
the right keywords, complete attributes, a clear specification, believable pricing and a strong main image.

Write one file per product: `listings/<id>.alibaba.json`. `listing.py --check` lints it; Xelent API validates
it again and submits it.

```json
{
  "title": "Custom Sublimated Football Jersey Recycled Polyester 150 GSM Team Soccer Shirt OEM Club Kit",
  "keywords": ["sublimated soccer jersey", "custom football jersey", "team soccer uniform", "OEM football kit",
               "recycled polyester jersey", "club soccer shirt", "custom team jersey with logo", "..."],
  "category_id": 127734135,
  "category": "Sportswear > Soccer Wear",
  "brand_name": "Xelent",
  "model_number": "XT-FB-2611",
  "place_of_origin": "Pakistan",
  "attributes": [
    {"name": "Material", "value": "100% Recycled Polyester"},
    {"name": "Fabric Weight", "value": "150 GSM"},
    {"name": "Technics", "value": "Sublimation Printing"},
    {"name": "Gender", "value": "Men, Women, Kids"},
    {"name": "Style", "value": "Short Sleeve Crew Neck"},
    {"name": "Feature", "value": "Breathable, Quick Dry"},
    {"name": "Supply Type", "value": "OEM Service"},
    {"name": "Sportswear Type", "value": "Soccer Wear"}
  ],
  "price_tiers": [{"min_qty": 20, "price": 9.8}, {"min_qty": 100, "price": 8.5}, {"min_qty": 500, "price": 7.2}],
  "currency": "USD",
  "unit": "Piece",
  "description_html": "<h2>Product overview</h2><p>...</p> ...",
  "xlsx": {"gross_weight_kg": 0.25, "shipping_template": "", "lead_times": [{"qty": 100, "days": 15}, {"qty": 500, "days": 25}]}
}
```
Brand, place of origin, currency and unit default to `studio.json` when left out.

## Category (set it; never leave it to Alibaba)
A store may only publish in the categories Alibaba has approved for it. When no `category_id` is sent, Alibaba
predicts one from the title, and a prediction outside the store's categories is refused, often with nothing more than
"A system error occurred" and the code `PUB_BIZCHECK_CAT_PUB_RESTRICT`. So every Alibaba listing carries `category_id`
(Alibaba's numeric leaf category) and `category` (its path, for the reader):

1. `node scripts/xelent.mjs alibaba-category "<title>"` shows the category Alibaba would choose. Show the user the
   path and ask whether it is right for the product and is one their store sells in.
2. When the store already has an accepted listing of the same kind of product, reuse its category:
   `node scripts/xelent.mjs alibaba-product <listing_id>` (the `listing_id` is in `published.json`) prints the live
   product's `category.id` and full `category.path`. A range (base layers, fleece, jackets, bibs, vests) usually needs a
   category per garment type, not one for all.
3. Alibaba's predictor sometimes answers nothing (it did for the Huntgear bibs five times running); set
   `category_id` yourself rather than relying on it. Hunting apparel goes in Hunting Wear, `201270883`
   (Sportswear & Outdoor Apparel / Sports & Outdoor Clothing / Hunting Wear).
4. If the user is unsure, they can find the path in Seller Center (Products > Manage Products > the accepted
   product > Category) and the id with step 1 using a title of that kind.

After a submission, `published.json` records the category used (`given` or `predicted`) and Alibaba's own error code
(`alibaba_code`). A refusal names both, so the fix is a different `category_id`, not a rewrite of the listing.

## Title (max 128 characters, plain ASCII)
- Formula: **main keyword + material/fabric + key feature or construction + use or market + customisation**.
  "Custom Sublimated Football Jersey Recycled Polyester 150 GSM Team Soccer Shirt OEM Club Kit".
- Lead with the phrase with the most buyer evidence in `research/keywords.json` (alibaba list).
- Use the words buyers use (both "soccer" and "football" when the market uses both), no repeated word more
  than twice, no brand names you do not own, no symbols `! | ~ ^ * < > { } [ ]`, no emoji, no contact details.
- 60-120 characters is the useful range.

## Keywords (up to 384 characters in total, no `; : ,`)
- 15-20 phrases of 2-5 words. Alibaba's form notes that 15 or more keywords get more exposure.
- Cover: head term, long-tail variants, material, construction, decoration method, audience (men, women, kids,
  youth, club, school), use, season, OEM/ODM/private label/wholesale/custom logo variants, place (e.g. "Sialkot").
- Every phrase must describe this product truthfully. No competitor brands, no leagues or events.
- Do not paste the range's shared research keywords onto every listing: "hunting fleece jacket" on a base layer, or
  "camouflage" on a solid-colour piece, misleads buyers and Alibaba's matching. `listing.py --check` warns about them.

## Attributes (values up to 70 characters): the category's own, with its values
Buyers filter on attributes, but each category has its own list, a few of them required, and some that take only
fixed values. Alibaba refuses a listing that carries certain names outside its category, with nothing more than
"A system error occurred" (`S_COMMON_INTERNAL_ERROR`). In the Huntgear pilot, `Collar`, `Closure Type`,
`Waterproof Rating` and `Insulation` sank four listings in Hunting Wear, while `Fabric Weight` and `Fit Type` were kept.

1. Once the category is set, run `node scripts/xelent.mjs alibaba-attributes <category_id>`. It lists every attribute
   of the category, which are REQUIRED, and which take only fixed values.
2. Fill every REQUIRED attribute (Hunting Wear: Place of Origin, Material). Use the category's names exactly, and for
   fixed-value attributes one of its values, e.g. Season `Autumn` not `Autumn, Winter`, Supply Type `Oem Service`.
3. Put anything the category does not list (closure, collar, waterproof rating, insulation, fabric weight) in the
   description's specification table instead of an attribute.
4. Sizes and colours are options (Alibaba's sale attributes), not attributes: give them in the description.

`publish.mjs` (dry run) checks this against the live category and prints `~` warnings: required attributes missing,
values the category does not take, names outside the category. If Alibaba still refuses a listing, Xelent API retries
with only the category's own attributes, then only its required ones, and `published.json` records which attempt
went through (`attempt`) and what was left out (`attribute_fit`).

## Description (HTML, up to 20,000 characters)
Allowed: `h2 h3 p ul ol li table tr th td strong em br img`. No scripts, iframes, forms or links, no contact
details, no claims you cannot prove. Structure (checked by name):

1. **Product overview**: what it is, who it is for, the one reason to choose it (2 short paragraphs).
2. **Key features**: 6-8 bullets, each a benefit tied to a fact ("150 gsm recycled polyester interlock:
   light, breathable and colour-fast through repeated washes").
3. **Specifications**: a table: fabric, gsm, fit, collar, sleeves, construction, decoration, sizes, colours,
   labels and packaging options.
4. **Customisation (OEM / ODM)**: what the buyer can change: colours, logos, names and numbers, sponsor
   prints, labels, hang tags, packaging; artwork formats accepted.
5. **Sizes**: the run and how measured; the size chart image is in the gallery.
6. **Samples**: sample availability, cost policy (state it as the business sets it in studio.json), sample time.
7. **Packaging and shipping**: poly bag, carton quantity, carton size and weight if known.
8. **Lead time and MOQ**: MOQ per design or per colour, production days by quantity.
9. **Why work with us**: factory capabilities from `studio.json` (years, machines, QC steps) only if true.
10. **FAQ**: 4-6 real questions (custom logos, mixed sizes, sample cost, payment, delivery).

Facts come from `studio.json` only. Never invent certifications (OEKO-TEX, BSCI, ISO), capacities or
test results: `listing.py` fails a listing that claims a certificate not listed in `business.certifications`.

## Price tiers
- 2-3 tiers, quantities rising, prices never rising, at most 2 decimals, first tier at or above the factory MOQ.
- Tier prices are the business's numbers, not guesses. If `studio.json` has no costing, ask the user for FOB
  prices per tier before writing the listing.
- `price_range` (min, max) instead of tiers only when prices vary too much by customisation.

## Colourways and sizes
Alibaba treats colour and size variations of one design as one product. List colourways in the description,
attributes and (optionally) SKU rows in the spreadsheet (`"skus": [{"attributes": {"Color": "Navy", "Size": "M"},
"price": 8.5}]`); never create separate listings that differ only in colour, which Alibaba treats as duplicates.

## Images
`prepare_images.py` makes up to 6 square 1600 px JPEGs under 3 MB, in this order: front (white background,
product filling about 85% of the frame), back, side, detail, lifestyle, size chart. The main image carries no
text, border, watermark or collage. See [image-direction.md](image-direction.md).

## Submitting
- **Connected store** (Alibaba connected at xelentapi.com/dashboard/marketplaces): `publish.mjs --submit` hosts the
  images on Xelent API, which passes their links to Alibaba; Alibaba copies them into the store's Photo Bank.
  The product is created through the Alibaba Open Platform (ICBU product listing API) and goes into Alibaba's
  review. It is never set live by this skill. If no category is given, Alibaba predicts one.
- **Not connected**: `publish.mjs --submit` (or `--upload-only` then `alibaba_xlsx.py`) writes
  `export/alibaba-bulk-upload.xlsx` in Alibaba's default bulk template with hosted image links. The user uploads it in
  seller centre (Products > Bulk upload). Links for images not yet used in a listing stay up for 30 days.
- Alibaba's API access requires a Gold Supplier store and an Alibaba Open Platform app. The seller connects on
  xelentapi.com/dashboard/marketplaces with their own app's App Key and App Secret (or the platform's app, when
  offered). No server or Cloudflare access is involved.

## Common rejections and fixes
- `PUB_BIZCHECK_CAT_PUB_RESTRICT`, or "A system error occurred" with a predicted category: the store may not publish
  in that category. Set `category_id` to one the store sells in (see Category) and submit again with `--force`.
- Title or keywords contain a brand, league, club or event name: remove it.
- Main image has text, a collage or a coloured background: regenerate the front on white.
- Duplicate listings for colour variants: merge into one listing.
- Prices not ascending by quantity or with more than 2 decimals.
- Attribute value too long (over 70 characters) or a free-text sentence in an attribute.
- Contact details or links in the description.
