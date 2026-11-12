# Scent Finder — product

**Who:** one fragrance enthusiast with a niche-leaning collection (Le Labo, Vyrao, Mad et Len, Naomi Goodsir…), browsing at home, often in the evening.

**Job:** know what I own, see my "scent DNA", and get three well-reasoned picks I don't already own — tied to real notes, not hype.

**Primary actions**
1. Build the wardrobe: search and add, or paste a Fragrantica list → preview matches → Save.
2. Read the Scent DNA: accord profile bars, notes I tend to like, family gaps.
3. Ask the guide: "Find me something different", "Find the gap in my collection", "What should I wear tonight?", "Something similar to my favourites but under $200", "Log that I wore X today, 4/5, office".

**Truths to keep visible**
- Data is approximate: 164 curated rows written from model knowledge + 26k rows from the public `doevent/perfume` dataset (Hugging Face, MIT-tagged). Seasons for imported rows and all price bands are inferred.
- Prices are bands (budget <$80, mid $80–200, niche $200–400, luxury $400+), assumed.
- Writes: Save in the import card, rating/status edits, and log_wear from chat. Nothing else writes.

**Voice:** a knowledgeable, concise perfumery guide. Plain, specific, a little dry. Notes are lowercase nouns ("bergamot", "cade").
