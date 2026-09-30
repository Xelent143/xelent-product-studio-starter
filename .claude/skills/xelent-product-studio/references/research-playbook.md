# Research playbook

Nothing is designed until the industry has been studied. Designs made from memory drift to the same clichés
(a sash, three stripes, a gradient, a skull) and miss what buyers are searching for this season. The research
produces four files in `research/`, and `studio.py check-research` refuses to pass until they are complete,
sourced and dated.

```
research/
  sources.json      every page read: url, type, accessed date, takeaways
  notes/            optional scratch notes, one file per source or theme
  brief.md          the synthesis: what the market wants now, and why
  directions.json   3-6 design directions, each grounded in cited sources
  keywords.json     the words buyers actually search, per marketplace, with evidence
```

## Method

Work through the five passes in order. Use WebSearch to find current pages and WebFetch to read them; read
the page, never just the search snippet. Record every source you use in `sources.json` as you go, so the
brief can cite it.

1. **Scope** (from `studio.json`): segment (teamwear, streetwear, activewear, combat sports, outerwear, basics),
   garment types, audience, marketplaces, the factory's decoration methods and fabrics, price position.
   Research only what this business can make and sell.
2. **Trend pass**: what is new this season and next in the segment. Colour, silhouettes, graphics, materials.
   Prefer sources dated within the last 6 months; anything older is background, not a trend.
3. **Market pass**: what is already selling. Best-seller lists, marketplace search results, competitor
   new-in pages. Note price bands, what the top listings have in common, and what is overdone.
4. **Buyer-language pass**: the words buyers type. Marketplace autocomplete, tags and titles of top listings,
   Google Trends comparisons. This becomes `keywords.json`.
5. **Design-theory pass**: the rules of the category. Kit laws for teamwear, construction norms, how the
   decoration methods behave (see [design-language.md](design-language.md)). Rules become constraints on the
   directions, not decoration.

Then synthesise (below), write the brief and directions, run `studio.py check-research`, and show the user the
brief and the directions. **Stop and wait** for the user to choose directions; record the choice with
`studio.py approve-research --directions ...`.

## Source types and where to look

Each entry: what it is good for, and a search that finds its current material. Domains change their paths; search
the domain rather than trusting a deep link. `type` is the value to write in `sources.json`.

### `trend`: industry news and trend forecasting (every segment)
- Business of Fashion (businessoffashion.com): market direction, category growth, brand moves.
- Vogue Business (voguebusiness.com), WWD (wwd.com), Drapers (drapersonline.com), FashionUnited (fashionunited.com).
- Sourcing Journal (sourcingjournal.com), Just Style (just-style.com): sourcing, fabrics, what factories are making.
- Heuritech (heuritech.com), WGSN public blog (wgsn.com): forecast summaries (the full reports are paid; use what is public).
- Lyst Index (lyst.com): quarterly hottest brands and products; shows which silhouettes are pulling demand.
  Search: `"<segment>" trends <season> <year>`, `site:voguebusiness.com <category> <year>`.

### `colour`: colour direction
- Pantone Colour of the Year and seasonal palettes (pantone.com), Coloro (coloro.com), WGSN colour forecasts.
- Pinterest Predicts (business.pinterest.com) and Pinterest Trends (trends.pinterest.com): consumer-side colour and style searches.
  Record colours as hex plus a name; note which are forecast versus already selling.

### `category`: segment specialists
- **Football and teamwear**: Footy Headlines (footyheadlines.com) for the season's templates and kit language;
  Football Kit Archive (footballkitarchive.com) for history and naming; custom teamwear configurators and catalogues
  (Spized, Owayo, Macron, Kappa, Erreà, Joma, Hummel, Kelme) for what teams can order now.
- **US team sports**: Uni Watch (uni-watch.com), SportsLogos.net news (news.sportslogos.net) for uniform language
  (piping, stripe packages, number fonts); NFHS, FIBA, IIHF, IFAB rules for what is legal on a playing kit.
- **Streetwear**: Hypebeast (hypebeast.com), Highsnobiety (highsnobiety.com), Complex Style (complex.com/style),
  Grailed's editorial (grailed.com/drycleanonly), END. Features (endclothing.com), SSENSE editorial.
- **Activewear and gym**: new-in pages of Gymshark, Alo, Lululemon, Vuori, Represent 247; Athletech News (athletechnews.com).
- **Combat sports (BJJ, MMA, boxing, muay thai)**: new drops of Shoyoroll, Tatami, Hayabusa, Venum, Fairtex; BJJ and
  MMA news sites for competition rules (IBJJF uniform rules for gis).
- **Outerwear and performance**: ISPO (ispo.com), Gear Patrol (gearpatrol.com), Outside (outsideonline.com).
- **Workwear and heritage**: Heddels (heddels.com) for construction and fabric vocabulary.

### `street`: street-level and social signals
- TikTok Creative Center (ads.tiktok.com/business/creativecenter): trending hashtags and products.
- Instagram and Pinterest searches for the category, Reddit communities (r/streetwear, r/footballkits, r/bjj).
  Use for what people wear and argue about, not for numbers.

### `materials`: fabrics, trims and processes
- Textile Exchange (textileexchange.org): recycled and preferred fibres, certification names.
- Première Vision (premierevision.com), Performance Days (performancedays.com): fabric innovation.
- Fibre2Fashion (fibre2fashion.com), Textile Learner (textilelearner.net): process basics, gsm norms, construction.

### `marketplace`: demand and buyer language (required)
- **Etsy**: search results and autocomplete for the category (etsy.com/search?q=...), best-seller and
  "popular now" badges in results, the tags and titles of the top listings, Etsy's trend reports in the
  Etsy newsroom and seller handbook. eRank (erank.com) free keyword data if available.
- **Alibaba**: alibaba.com search autocomplete, the result filters and "Top ranking" lists for the category,
  titles and attributes of verified suppliers ranking first, typical MOQ and price tiers.
- **Amazon**: Best Sellers and Movers & Shakers in the clothing category, for silhouettes and price bands.
- **Google Trends** (trends.google.com): compare the candidate terms over 12 months and by region.

### `competitor`: direct competitors
- The top 5-10 shops or suppliers selling this category on the target marketplaces: what they list, how they
  photograph it, their price tiers, their weak spots (thin descriptions, bad size information, few colourways).

### `design-theory`: rules and principles
- Kit and uniform regulations (IFAB Law 4, FIBA Official Basketball Rules, NFHS uniform rules, IIHF rule book,
  IBJJF uniform rules) for teamwear and combat sports.
- Colour theory and harmony tools (color.adobe.com), garment terminology references (fashionary.org).
- [design-language.md](design-language.md) in this skill: decoration limits, balance rules, what reads as a fault.

**Minimums** enforced by `check-research`: 10 sources, from at least 6 sites, covering at least 4 source types,
including `marketplace`; every source dated within 45 days and carrying takeaways.

## File formats

`sources.json`
```json
[
  {"url": "https://www.footyheadlines.com/...", "title": "2026-27 teamwear templates leaked",
   "type": "category", "accessed": "2026-09-30",
   "takeaways": ["Engineered tonal knit patterns replace full sublimated prints on mid-tier templates",
                 "Wrap-over V collars and ribbed crews dominate; polo collars on retro lines only"]}
]
```

`directions.json`
```json
[
  {"id": "tonal-engineered",
   "name": "Tonal engineered knit",
   "summary": "Quiet, premium teamwear: one base colour with a tone-on-tone engineered pattern ...",
   "why_now": "Premium templates this season moved from loud prints to tonal texture (sources 1, 4) ...",
   "audience": "Adult amateur clubs and academies buying a step up from stock templates",
   "silhouettes": ["slim athletic fit crew-neck jersey", "tapered training pant"],
   "palette": [{"name": "Deep navy", "hex": "#1B2A41"}, {"name": "Slate", "hex": "#4A5A6A"}, {"name": "Signal white", "hex": "#F4F4F2"}],
   "graphics": "tone-on-tone engineered stripes, micro geometric jacquard effect via sublimation",
   "materials": "recycled polyester interlock 140-160 gsm, mesh side panels",
   "decoration": ["sublimation", "heat-transfer crest", "silicone number print"],
   "lifestyle_scene": "an evening training session on a floodlit artificial pitch",
   "price_position": "mid",
   "risks": "Can look plain in a thumbnail; lead with the detail shot on Etsy",
   "sources": ["https://www.footyheadlines.com/...", "https://www.lyst.com/..."]}
]
```

`keywords.json` (one list per enabled marketplace, most important first)
```json
{"etsy": [{"term": "custom football jersey", "evidence": "Etsy autocomplete; 7 of the top 12 listings lead with it", "intent": "custom"}],
 "alibaba": [{"term": "sublimated soccer jersey", "evidence": "alibaba.com autocomplete, top-ranking list title", "intent": "wholesale"}]}
```
Gather at least 15 terms per marketplace. Etsy buyers search in plain, gift-and-occasion language
("personalised team shirt", "gift for coach"); Alibaba buyers search in trade language ("OEM", "sublimated",
"wholesale", "custom logo", fabric and gsm terms). Keep the two lists separate.

## Synthesis: writing brief.md

The brief is a decision document, not a list of links. It must have these sections (checked by name):

- `## Scope`: segment, garments, audience, marketplaces, what the factory can make.
- `## Trend signals`: 5-10 signals, each with the evidence (cite sources by number) and how strong it is
  (one source is a hint; three independent sources is a trend).
- `## Colour`: the palette logic, with hex values, what is forecast and what is already selling.
- `## Silhouettes and construction`: cuts, fits, collars, lengths, panelling, fabric weights.
- `## Graphics and decoration`: pattern families, placement, scale, which decoration method suits each.
- `## Materials`: fabrics and gsm, finishes, sustainability claims that are actually possible for this factory.
- `## Demand and pricing`: what sells now on each marketplace, price bands, MOQ norms, gaps in the market.
- `## Keyword bank`: the strongest buyer terms per marketplace and how they map to products.
- `## Design directions`: 3-6 directions (summarised; full detail in directions.json), each with why now.
- `## Avoid`: what is overdone, what is illegal or infringing, what the factory cannot make well.

Rules for good synthesis:
- **Triangulate.** A signal counts when trend press, the market and buyers all point at it. Say which it is.
- **Separate forecast from demand.** A forecast colour with no search volume is a risk; say so.
- **Translate every trend into something sewable** by this factory: fabric, method, placement, size.
- **Name the gap.** The best directions sit where demand is proven and the current listings are weak.
- **Stay original.** Learn the language of a trend; never copy a specific brand's design, logo, or signature
  pattern (see [ip-and-restricted.md](ip-and-restricted.md)).
- Keep it readable: short paragraphs, specific nouns, numbers where you have them.

## Presenting to the user

Show `brief.md` (or a short summary with the file path) and the directions as a numbered list: name, one-line
summary, palette, why now. Recommend the two or three you would build first and why. Ask which directions to
develop and how many products per direction. Do not write products into `studio.json` before they answer.

## Refreshing

Research older than 45 days fails the check. For a new season or a new segment, start a new workspace or
move the old `research/` aside and redo the passes; the keyword bank goes stale fastest.
