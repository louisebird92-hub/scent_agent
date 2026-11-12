# Scent Finder

A fragrance wardrobe and perfumery guide on Databricks. Import what you own, read your **scent DNA**, and ask a guide for three picks you don't already own, each explained through shared or contrasting notes.

Built during a Databricks AI Dev Day as a **Databricks App** (APX: React + FastAPI) on **Lakebase** (Postgres + pgvector), with a **Claude Opus 5.5** tool-calling guide via Unity Gateway. The same six tools are also exposed as an **MCP server** with an **Omnigent** agent spec, for use from the terminal.

> **Data is approximate and for demo purposes only.** 164 entries were written from model knowledge (notes, years and perfumers may be wrong; `low_confidence` marks best guesses). 26,123 entries come from the public [`doevent/perfume`](https://huggingface.co/datasets/doevent/perfume) dataset on Hugging Face (tagged MIT; provenance of the underlying data is not stated, so treat it as demo data). Seasons for imported rows and **all price bands are inferred**. No employer data is used.

## What it does

- **Chat-first home:** one question, "What do you want to smell like?", with a few suggestions. Works for anyone, with or without a shelf.
- **Your shelf (optional):** each signed-in person has their own private shelf (keyed to their workspace login). Add fragrances by search, by pasting a list, or by uploading a `.csv` (with `name` and `brand`/`house` columns) or `.txt` (one per line, Fragrantica-style lines are cleaned up).
- **Wardrobe:** search 26k fragrances and add as owned / wishlist / sampled, or paste a list (e.g. from Fragrantica). It previews fuzzy matches and saves only when you press Save. Rate 1–5, change status, remove.
- **Scent DNA:** accord profile bars (weighted by your ratings), the notes you tend to like, and families missing from your shelf.
- **Ask the guide:** "Find me something different", "Find the gap in my collection", "What should I wear tonight?", "Something similar to my favourites but under $200", "Log that I wore Witchy Woo today, 4/5, office".

## Architecture

```
React UI ──► FastAPI (/api) ──► scent_finder.fragrance.tools ──► Lakebase Postgres
                 │                     ▲                         fragrances (+ vector(1024), pg_trgm)
                 └► agent.py ──────────┘                         my_collection, wear_log
                    Opus 5.5 via Unity Gateway (system.ai.claude-opus-5-5)
                    embeddings: system.ai.gte-large-en

Omnigent agent (agent/) ──► MCP stdio server (scent_finder.fragrance.mcp_server) ──► same tools
```

| Tool | Writes? | What it does |
|---|---|---|
| `search_by_notes` | no | include/exclude notes or accords, family, season, price band / max USD |
| `find_similar` | no | pgvector cosine similarity from a name (fuzzy), "my favourites", or free text; returns shared and contrasting notes |
| `get_my_collection` | no | owned / sampled / wishlist with ratings, wear counts, last worn |
| `get_scent_dna` | no | accord bars, liked notes, family gaps, favourites |
| `log_wear` | **yes** | inserts into `wear_log` (fuzzy name; refuses if ambiguous) |
| `add_to_collection` | **yes, on confirm** | previews matches; writes only with `confirm=true` (in the app, the Save button) |

**Who can use it:** anyone with access to the Databricks App (workspace sign-in). It is not on the open internet; a truly public version would need separate hosting, anonymous sessions and abuse protection. Each person gets **30 guide messages a day** (`DAILY_MESSAGE_LIMIT`, stored in `chat_usage`), questions are capped at 1,000 characters, and every collection/wear query is scoped to the caller's email.

Guardrails: the guide only acts through these tools; at most 6 tool rounds and 1,200 output tokens per message, with history trimmed to 12 messages. The Omnigent spec adds a $1 per-session hard cost cap, 25 tool calls per session and 15 iterations.

**Price bands (assumed, USD full bottle):** budget < $80 · mid $80–200 · niche $200–400 · luxury $400+. Bands are only known for curated houses (about 10% of rows); the rest show "price unknown".

## Setup

Prerequisites: a Databricks workspace with Lakebase Autoscaling and the `system.ai` models (`claude-opus-5-5`, `gte-large-en`), the Databricks CLI (authenticated), [`uv`](https://docs.astral.sh/uv/) and [`apx`](https://databricks-solutions.github.io/apx/).

```bash
# 1. Lakebase project (Postgres 17)
databricks postgres create-project scent-finder --json '{"spec":{"display_name":"scent-finder","pg_version":17}}'

# 2. Python env + seed (downloads doevent/perfume at a pinned revision, embeds ~26k rows: ~5 min)
#    data/my_collection.csv is loaded onto SCENT_FINDER_USER's shelf (your login email)
uv sync
SCENT_FINDER_USER=you@example.com uv run python -m scripts.seed

# 3. Run locally
apx dev start          # prints the local URL

# 4. Deploy as a Databricks App
apx build
databricks bundle deploy && databricks bundle run scent-finder-app
#   then grant the app's Postgres role table access (see scripts/grant_app.sql; role id = app service principal client id)
```

`databricks.yml` binds the Lakebase branch as an app resource; `app.yml` reads `LAKEBASE_ENDPOINT` from it. The seed recreates all three tables, **including `wear_log`**. Your collection is reloaded from `data/my_collection.csv`.

### Omnigent agent (terminal)

```bash
SCENT_FINDER_ROOT=$PWD SCENT_FINDER_USER=you@example.com omnigent run ./agent -p "Something like Bergamote 22 but warmer for winter"
```

## Repo layout

```
src/scent_finder/fragrance/   db.py (Lakebase + gateway), tools.py, agent.py, mcp_server.py
src/scent_finder/backend/     FastAPI app, routes, models
src/scent_finder/ui/          React UI (Scent DNA, Wardrobe, Guide)
scripts/                      schema.sql, seed.py, grant_app.sql
data/                         fragrances.psv (curated), my_collection.csv
agent/                        Omnigent spec + MCP sidecar
tests/                        unit tests (uv run pytest)
```
