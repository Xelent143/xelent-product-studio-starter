# studio.json

One file per workspace, created by `studio.py init` from `studio.template.json`. Every script reads it, so edit
it and re-run the step to change anything. Facts in listings come from here and nowhere else.

## brand
| Field | Meaning |
|---|---|
| `name` | Brand name, used in prompts, boards, listings (Brand name attribute) |
| `logo` | Path to the logo image (workspace-relative or absolute). Only used when `use_logo` is true |
| `logo_description` | One sentence describing the logo's shape and spelling, so the model reproduces it |
| `use_logo` | Default for every product; true only when the user wants their logo on the products |
| `voice` | How the listing copy should sound |

## business
| Field | Meaning |
|---|---|
| `kind` | `manufacturer`, `brand`, `retailer` or `maker` |
| `country`, `city` | Where it is made (place of origin, shipping-from) |
| `segments` | e.g. `["teamwear", "streetwear"]`: scopes the research |
| `audience` | Who buys: clubs and academies, streetwear shoppers, gyms, schools |
| `capabilities.decoration` | Methods the factory actually runs. Designs may only use these |
| `capabilities.fabrics` | Fabrics it stocks or sources reliably |
| `capabilities.moq`, `sample_days`, `lead_time_days` | Used in listings and checked against price tiers |
| `certifications` | Only certificates the business holds. Listings may claim nothing else |
| `facts` | Short true statements for "why us" sections (years in business, machines, QC steps) |

## style
`background`: `white` (default; Alibaba's main image needs white) or `grey`. `notes`: one or two sentences of house
style added to every image prompt.

## generation
`resolution`: `"2K"` or `"4K"`, the user's answer to "which resolution?" (set it with `studio.py set-resolution`,
never guess). It picks the model for every image in the workspace:

| Resolution | Model | Output |
|---|---|---|
| `2K` | Nano Banana 2 | about 2048 px on the long side |
| `4K` | GPT Image 2.5 Sunburst, quality `high` | 2880 x 2880 square, 3840 px wide for boards |

`run.mjs` refuses to start while it is `null`. The price per image is on the user's account (`node xelent.mjs prices`).

## marketplaces
`alibaba`: `enabled`, `currency`, `unit`, `place_of_origin`, `image_order` (null for the default),
`xlsx` defaults for the spreadsheet (`shipping_template`, `lead_times` `[{qty, days}]`, `gross_weight_kg`, `dimensions_cm`).

`etsy`: `enabled`, `currency`, `who_made`, `when_made`, `production_partner_ids`, `shipping_profile_id`,
`readiness_state_id`, `return_policy_id` (ids from `node xelent.mjs etsy-reference`), `quantity`, `image_order`,
`disclose_ai` and `ai_disclosure_text` (see [listing-etsy.md](listing-etsy.md)).

## products[]
```json
{
  "id": "tonal-band-jersey",
  "name": "Tonal Band Football Jersey",
  "direction": "tonal-engineered",
  "type": "top",
  "noun": "short-sleeve football jersey",
  "design": "Slim athletic fit short-sleeve football jersey in deep navy (#1B2A41) recycled polyester interlock. Crew neck with a 2 cm navy rib collar. Raglan sleeves. Across the chest, a 4 cm tonal band in slate (#4A5A6A) printed edge to edge between the side seams, with a fine 3 mm signal-white (#F4F4F2) line on its top edge. Side panels of navy micro-mesh from underarm to hem. Left chest: a round embroidered crest area 8 cm wide in white thread showing a simple shield outline (placeholder for the club crest). Back: plain navy, nothing printed; a small woven white label centred under the collar. Straight hem with a 2 cm double-needle finish. Sleeve ends plain with a double-needle hem.",
  "view_details": {
    "front": "tonal chest band with its white top line; embroidered crest outline on the left chest; rib collar",
    "back": "plain back with the small woven label under the collar",
    "left": "raglan seam, mesh side panel, end of the chest band at the side seam",
    "right": "raglan seam, mesh side panel"
  },
  "fabric": "100% recycled polyester interlock with polyester micro-mesh side panels",
  "gsm": 150,
  "fit": "slim athletic",
  "sizes": ["XS", "S", "M", "L", "XL", "2XL"],
  "colorways": [
    {"name": "Navy", "hex": "#1B2A41"},
    {"name": "Forest", "hex": "#1F4D3A", "design": "the body becomes forest green #1F4D3A, the band a lighter moss green #5E7F5A, the top line stays white"},
    {"name": "Crimson", "hex": "#8E1B2C"}
  ],
  "decoration": ["sublimation", "embroidery", "woven label"],
  "extras": ["detail", "flatlay", "lifestyle", "colorways"],
  "detail_focus": "the edge of the tonal chest band, its white line and the interlock knit, with the crest embroidery at the side",
  "lifestyle": {"scene": "an evening training session on a floodlit artificial pitch", "model": "an adult amateur footballer in his late twenties"},
  "size_chart": {"unit": "cm", "how": "Measured flat across the garment", "tolerance": "±2 cm",
                 "columns": ["Chest width", "Body length", "Sleeve length"],
                 "rows": {"XS": [46, 68, 19], "S": [49, 70, 20], "M": [52, 72, 21], "L": [55, 74, 22], "XL": [58, 76, 23], "2XL": [61, 78, 24]}},
  "pricing": {"alibaba": [{"min_qty": 20, "price": 9.8}, {"min_qty": 100, "price": 8.5}, {"min_qty": 500, "price": 7.2}], "etsy": 34.0}
}
```

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | lowercase slug, unique; file names use it |
| `name` | yes | product name for boards and a starting point for titles |
| `direction` | yes | one of the approved research direction ids |
| `type` | yes | view set: `top dress jacket gi bottom vest headwear socks gloves belt object` ([image-direction.md](image-direction.md)) |
| `noun` | recommended | what the product is called in prompts ("heavyweight pullover hoodie", "pair of fight shorts") |
| `design` | yes, 250+ characters | the complete design, outside in; everything any view shows ([design-language.md](design-language.md)) |
| `view_details` | yes | what each view must show |
| `fabric`, `gsm`, `fit` | yes | stated in prompts and required in listings |
| `sizes` | yes | the run sold; each needs a size-chart row |
| `colorways` | yes | first one is the design as described; others get their own front image |
| `decoration` | yes | methods used, each from `business.capabilities.decoration` |
| `extras` | no | subset of `detail flatlay lifestyle colorways` (default all) |
| `detail_focus`, `lifestyle`, `flatlay_surface` | no | direct the extras |
| `size_chart` | recommended | drawn by `size_chart.py` |
| `pricing` | before listings | the business's prices; ask the user, never guess |
| `refs`, `use_logo`, `views` | no | extra reference images, logo override, view override |
