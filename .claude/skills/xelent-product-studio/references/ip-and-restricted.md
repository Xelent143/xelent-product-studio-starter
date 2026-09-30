# Intellectual property and restricted items

Infringing listings are removed, stores are penalised or closed, and goods are seized at customs. Both Etsy and
Alibaba act on rights-holder complaints quickly. `studio.py` and `listing.py` block the common names, but the rule
is about the design, not just the words.

## Never
- **Brand marks and signature designs**: another company's logo, name, wordmark, or a design recognisably
  theirs (three parallel stripes on a sleeve for sportswear, a swoosh-like tick, a famous monogram, a signature
  plaid or camo). "Inspired by", "style", "dupe", "replica", "same as" plus a brand name are all infringing.
- **Leagues, clubs, teams, events and federations**: FIFA, World Cup, UEFA, Olympics, NBA, NFL, MLB, NHL, NCAA,
  Premier League, IPL, UFC and the like; club crests, club names, club colour schemes presented as that club's kit,
  player names with numbers that identify a real player.
- **Characters and entertainment IP**: anime, cartoons, comics, films, games, mascots. Design original characters
  and check the images for accidental likenesses (hair, costume, colours, silhouette).
- **Real people's likeness or names** without permission.
- **Uniforms of police, military and emergency services**, their insignia and rank marks, and anything that could
  be used to impersonate them. "Military-style" design language is fine; real insignia are not.
- **Hate symbols, extremist imagery, sexualised content involving minors.** Not negotiable.
- **Protected claims without proof**: certifications (OEKO-TEX, GOTS, GRS, BSCI, WRAP, ISO), "waterproof" ratings,
  UV protection, antibacterial, medical or safety protection (for example "impact protection" on fight gear) unless
  the business has the test report and lists it in `studio.json`.

## Fine
- Generic sports words: football, soccer, basketball, jersey, kit, team, club (as a word), training, match.
- Traditional pattern families: stripes, hoops, chevrons, halves, quarters, camo patterns in general, checks,
  geometric prints, gradients, when not copying a specific brand's version.
- Country names and colours for national-themed fan wear, without federation crests or official marks.
- Personalisation with the buyer's own team name and logo: the buyer supplies it and confirms they own it; say so in
  the listing ("You confirm you have the right to use any logo you send").

## When the user asks for something infringing
Say why in one line, then offer the original version: "I can't make Real Madrid's kit; here is an original white
and violet home kit for a club of your own." Do not generate the infringing design, even as a draft.

## Checking generated images
Look at every sheet and view for: stray real logos or brand-like marks the model added, a swoosh-like or
three-stripe element, readable text that was not asked for, a crest that resembles a real club, a character that
resembles a known one. Regenerate with the note "no logos or marks except the ones described" when you see any.
