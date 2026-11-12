"""Scent Finder tools over Lakebase: search, similarity, collection, scent DNA and wear logging.

Plain functions shared by the app API, the in-app agent and the MCP server (mcp_server.py).
Write tools: log_wear and add_to_collection (add_to_collection only writes when confirm=true).
"""

import os
import re
import time
from contextvars import ContextVar
from collections import Counter
from datetime import date

from typing import Any

import numpy as np
import psycopg
import psycopg.rows
from .db import Row, connect, embed, q

# Assumed USD ranges for a full bottle; the data has bands, not prices.
PRICE_BANDS = {"budget": (0, 80), "mid": (80, 200), "niche": (200, 400), "luxury": (400, 10_000)}
PRICE_NOTE = ("Prices are not in the data: bands are assumed as budget <$80, mid $80-200, "
              "niche $200-400, luxury $400+; most mass-market rows have no band (price unknown).")

COLS = """f.id, f.name, f.house, f.year, f.family, f.notes, f.accords, f.season, f.season_inferred,
          f.price_band, f.source, f.low_confidence, left(f.description, 220) AS description,
          m.status AS my_status, m.rating AS my_rating"""

# Whose shelf the tools read and write. The app sets it per request from the signed-in
# email; the MCP server / Omnigent use SCENT_FINDER_USER.
_user: ContextVar[str] = ContextVar("scent_finder_user", default=os.environ.get("SCENT_FINDER_USER", "local@scent-finder"))


def set_user(email: str | None) -> None:
    _user.set((email or os.environ.get("SCENT_FINDER_USER") or "local@scent-finder").lower())


def current_user() -> str:
    return _user.get()


_conn: psycopg.Connection | None = None
_conn_at = 0.0


def db() -> psycopg.Connection:
    """Reuse one connection; refresh before the ~1h OAuth token expires."""
    global _conn, _conn_at
    if _conn is None or _conn.closed or time.time() - _conn_at > 45 * 60:
        if _conn is not None and not _conn.closed:
            _conn.close()
        _conn, _conn_at = connect(), time.time()
        # Keep scanning the HNSW index until filtered results fill the limit (pgvector >= 0.8).
        _conn.execute("SET hnsw.iterative_scan = strict_order")
    return _conn


def rows(sql: str, params: Any = ()) -> list[Row]:
    if isinstance(params, dict):
        params = {"me": current_user(), **params}
    cur = db().cursor(row_factory=psycopg.rows.dict_row)
    try:
        return cur.execute(q(sql), params).fetchall()
    except psycopg.OperationalError:
        global _conn
        _conn = None
        return db().cursor(row_factory=psycopg.rows.dict_row).execute(q(sql), params).fetchall()


def bands_under(max_price_usd: float) -> list[str]:
    return [b for b, (lo, _hi) in PRICE_BANDS.items() if lo < max_price_usd and _hi <= max_price_usd] or ["budget"]


def clean(r: dict) -> dict:
    """Drop empty fields so tool output stays compact for the model."""
    out = {k: v for k, v in r.items() if v not in (None, [], "", False)}
    if r.get("season_inferred"):
        out["season_inferred"] = True
    return out


def resolve(name: str, limit: int = 5) -> list[dict]:
    """Fuzzy-match a fragrance name (optionally with house), preferring my collection and curated rows."""
    q = re.sub(r"\s+", " ", name.lower()).strip()
    return rows(
        f"""SELECT {COLS},
                   greatest(similarity(lower(unaccent(f.name)), unaccent(%(q)s)),
                            word_similarity(unaccent(%(q)s), lower(unaccent(f.name || ' ' || f.house)))) AS match_score
            FROM fragrances f LEFT JOIN my_collection m ON m.fragrance_id = f.id AND m.user_email = %(me)s
            WHERE lower(f.name || ' ' || f.house) %% %(q)s OR lower(f.name) %% %(q)s
               OR lower(f.name || ' ' || f.house) ILIKE '%%' || %(q)s || '%%'
            ORDER BY match_score DESC, (m.status IS NOT NULL) DESC, (f.source = 'curated') DESC
            LIMIT %(limit)s""",
        {"q": q, "limit": limit},
    )


def best_match(name: str) -> tuple[dict | None, list[dict]]:
    """Return (match, alternatives). match is None when the name is ambiguous or unknown."""
    hits = resolve(name)
    if not hits or hits[0]["match_score"] < 0.3:
        return None, hits
    top = hits[0]
    rivals = [h for h in hits[1:] if h["match_score"] >= top["match_score"] - 0.02
              and (h["name"], h["house"]) != (top["name"], top["house"])]
    if rivals and top["my_status"] is None and top["source"] != "curated":
        return None, hits
    return top, hits


def filters(family, season, price_band, max_price_usd, exclude_owned) -> tuple[list[str], dict]:
    where, p = [], {}
    if family:
        where.append("f.family = %(family)s")
        p["family"] = family.lower()
    if season:
        where.append("%(season)s = ANY(f.season)")
        p["season"] = {"autumn": "fall"}.get(season.lower(), season.lower())
    bands = [price_band.lower()] if price_band else (bands_under(max_price_usd) if max_price_usd else None)
    if bands:
        where.append("f.price_band = ANY(%(bands)s)")
        p["bands"] = bands
    if exclude_owned:
        where.append("(m.status IS DISTINCT FROM 'owned')")
    return where, p


def search_by_notes(
    include_notes: list[str] | None = None,
    exclude_notes: list[str] | None = None,
    family: str | None = None,
    season: str | None = None,
    price_band: str | None = None,
    max_price_usd: float | None = None,
    exclude_owned: bool = True,
    limit: int = 10,
) -> dict:
    """Filtered search. include_notes/exclude_notes match notes or accords by substring
    (e.g. "vetiver", "smoky", "incense"); results rank by how many include terms match.
    family: woody, floral, amber, citrus, aromatic, chypre, leather, musk, green, spicy, gourmand, aquatic.
    season: spring, summer, fall, winter. price_band: budget, mid, niche, luxury.
    max_price_usd maps to assumed price bands (see price_note). Owned fragrances are excluded by default."""
    inc = [n.lower().strip() for n in include_notes or [] if n.strip()]
    exc = [n.lower().strip() for n in exclude_notes or [] if n.strip()]
    where, p = filters(family, season, price_band, max_price_usd, exclude_owned)
    p.update(inc=inc, exc=exc, limit=min(limit, 25))
    term_hit = "EXISTS (SELECT 1 FROM unnest(f.notes || f.accords) n WHERE n LIKE '%%' || t || '%%')"
    if inc:
        where.append(f"EXISTS (SELECT 1 FROM unnest(%(inc)s::text[]) t WHERE {term_hit})")
    if exc:
        where.append(f"NOT EXISTS (SELECT 1 FROM unnest(%(exc)s::text[]) t WHERE {term_hit})")
    res = rows(
        f"""SELECT {COLS},
                   (SELECT array_agg(t) FROM unnest(%(inc)s::text[]) t WHERE {term_hit}) AS matched_terms
            FROM fragrances f LEFT JOIN my_collection m ON m.fragrance_id = f.id AND m.user_email = %(me)s
            {'WHERE ' + ' AND '.join(where) if where else ''}
            ORDER BY coalesce(array_length((SELECT array_agg(t) FROM unnest(%(inc)s::text[]) t WHERE {term_hit}), 1), 0) DESC,
                     (f.source = 'curated') DESC, (f.price_band IS NOT NULL) DESC, f.year DESC NULLS LAST
            LIMIT %(limit)s""",
        p,
    )
    out = {"results": [clean(r) for r in res]}
    if max_price_usd or price_band:
        out["price_note"] = PRICE_NOTE
    return out


def find_similar(
    query: str,
    exclude_owned: bool = True,
    family: str | None = None,
    season: str | None = None,
    price_band: str | None = None,
    max_price_usd: float | None = None,
    limit: int = 8,
) -> dict:
    """Vector similarity on note profiles. query is a fragrance name (fuzzy: "bergamote 22"),
    the literal "my favourites" (owned items, weighted by rating), or a free-text description
    ("warm smoky vetiver for winter"). Returns similarity (0-1), shared_notes and contrasting_notes
    versus the reference. Filters as in search_by_notes; owned fragrances excluded by default."""
    ref, ref_notes = None, set()
    if query.strip().lower() in ("my favourites", "my favorites", "my collection"):
        fav = rows("""SELECT f.embedding, f.notes, coalesce(m.rating, 3) AS w FROM my_collection m
                      JOIN fragrances f ON f.id = m.fragrance_id
                      WHERE m.status = 'owned' AND m.user_email = %(me)s""", {})
        if not fav:
            return {"error": "No owned fragrances in the collection yet."}
        vec = np.average([r["embedding"].to_numpy() for r in fav], axis=0, weights=[r["w"] for r in fav])
        ref_notes = {n for r in fav for n in r["notes"]}
        ref = {"reference": "your owned fragrances (rating-weighted)"}
    else:
        match, alts = best_match(query) if len(query.split()) <= 6 else (None, [])
        if match:
            vec = rows("SELECT embedding FROM fragrances WHERE id = %s", (match["id"],))[0]["embedding"].to_numpy()
            ref_notes = set(match["notes"])
            ref = {"reference": clean({k: match[k] for k in ("name", "house", "family", "notes", "accords", "season")})}
        else:
            vec = np.array(embed([query])[0])
            ref = {"reference": f"free-text: {query}"}
            ref_notes = {w for w in re.split(r"[^a-z\- ]+", query.lower()) for w in [w.strip()] if w}
            ref_notes |= set(query.lower().replace(",", " ").split())

    where, p = filters(family, season, price_band, max_price_usd, exclude_owned)
    if ref.get("reference", {}) and isinstance(ref["reference"], dict):
        where.append("NOT (f.name = %(rname)s AND f.house = %(rhouse)s)")
        p.update(rname=ref["reference"]["name"], rhouse=ref["reference"]["house"])
    p.update(vec=vec.astype(np.float32), limit=min(limit, 25))
    res = rows(
        f"""SELECT {COLS}, round((1 - (f.embedding <=> %(vec)s))::numeric, 3)::float AS similarity
            FROM fragrances f LEFT JOIN my_collection m ON m.fragrance_id = f.id AND m.user_email = %(me)s
            {'WHERE ' + ' AND '.join(where) if where else ''}
            ORDER BY f.embedding <=> %(vec)s LIMIT %(limit)s""",
        p,
    )
    out = []
    for r in res:
        r = clean(r)
        if ref_notes:
            r["shared_notes"] = [n for n in r.get("notes", []) if n in ref_notes]
            r["contrasting_notes"] = [n for n in r.get("notes", []) if n not in ref_notes][:6]
        out.append(r)
    result = {**ref, "results": out}
    if max_price_usd or price_band:
        result["price_note"] = PRICE_NOTE
    return result


def get_my_collection(status: str | None = None) -> dict:
    """My fragrances with status (owned / sampled / wishlist), rating, family, notes, accords,
    wear count and last worn date. status filters; omit for everything."""
    res = rows(
        f"""SELECT {COLS}, m.notes AS my_notes, count(w.id) AS times_worn, max(w.worn_on)::text AS last_worn,
                   round(avg(w.rating), 1)::float AS avg_wear_rating
            FROM my_collection m JOIN fragrances f ON f.id = m.fragrance_id
            LEFT JOIN wear_log w ON w.fragrance_id = f.id AND w.user_email = m.user_email
            WHERE m.user_email = %(me)s AND (%(s)s::text IS NULL OR m.status = %(s)s)
            GROUP BY f.id, m.user_email, m.fragrance_id ORDER BY m.status, m.rating DESC NULLS LAST, f.house""",
        {"s": status.lower() if status else None},
    )
    return {"count": len(res), "items": [clean(r) for r in res]}


def get_scent_dna(status: str = "owned", top_n: int = 6) -> dict:
    """Analyse my collection: family/accord profile as bars, the notes I tend to like,
    families I own nothing in (gaps), and my favourites. Weighted by my rating
    (and wear-log ratings) when present; unrated items count as 3/5."""
    items = rows(
        """SELECT f.name, f.house, f.family, f.notes, f.accords, coalesce(m.rating, avg_w.r, 3) AS weight
           FROM my_collection m JOIN fragrances f ON f.id = m.fragrance_id
           LEFT JOIN LATERAL (SELECT avg(rating) r FROM wear_log w
                              WHERE w.fragrance_id = f.id AND w.user_email = m.user_email) avg_w ON true
           WHERE m.status = %(status)s AND m.user_email = %(me)s""",
        {"status": status},
    )
    if not items:
        return {"error": f"No {status} fragrances in the collection yet."}
    profile: Counter[str] = Counter()
    notes: Counter[str] = Counter()
    for it in items:
        w = round(float(it["weight"]) * 10)  # integer weights keep Counter exact
        for a in {it["family"], *it["accords"]}:
            profile[a] += w
        for n in it["notes"]:
            notes[n] += w
    top = profile.most_common(top_n)
    scale = 10 / top[0][1]
    bars = "\n".join(f"{a.title():<10} {'█' * max(1, round(v * scale))}" for a, v in top)
    owned_families = {it["family"] for it in items}
    all_families = [r["family"] for r in rows(
        "SELECT family FROM fragrances GROUP BY family HAVING count(*) >= 10 ORDER BY count(*) DESC")]
    favs = sorted(items, key=lambda i: -float(i["weight"]))[:3]
    return {
        "based_on": f"{len(items)} {status} fragrances",
        "scent_dna_bars": bars,
        "profile": {a: round(v / sum(profile.values()) * 100) for a, v in top},
        "you_tend_to_like": [n for n, c in notes.most_common(top_n) if c > 3] or [n for n, _ in notes.most_common(top_n)],
        "family_gaps": [f for f in all_families if f not in owned_families],
        "favourites": [f"{f['name']} ({f['house']})" for f in favs],
        "today": date.today().isoformat(),
    }


def log_wear(fragrance_name: str, rating: int | None = None, context: str | None = None,
             worn_on: str | None = None) -> dict:
    """Record that I wore a fragrance (the main write tool). fragrance_name is fuzzy-matched
    ("bergamote 22"); rating 1-5; context e.g. "office", "evening, rainy"; worn_on YYYY-MM-DD
    (default today). Writes nothing and returns candidates if the name is ambiguous."""
    if rating is not None and not 1 <= rating <= 5:
        return {"error": "rating must be 1-5"}
    match, alts = best_match(fragrance_name)
    if not match:
        return {"logged": False, "reason": "No confident match; ask which one was meant.",
                "candidates": [f"{a['name']} ({a['house']})" for a in alts]}
    r = rows("""INSERT INTO wear_log (user_email, fragrance_id, worn_on, rating, context)
                VALUES (%s, %s, coalesce(%s::date, CURRENT_DATE), %s, %s)
                RETURNING id, worn_on::text, rating, context""",
             (current_user(), match["id"], worn_on, rating, context))[0]
    return {"logged": True, "fragrance": f"{match['name']} ({match['house']})", **clean(r)}


def _parse_csv(text: str) -> list[str] | None:
    """A CSV upload with a header naming the fragrance (and optionally house/brand) column."""
    import csv
    import io

    first = text.lstrip().splitlines()[0].lower() if text.strip() else ""
    if "," not in first or not any(k in first for k in ("name", "fragrance", "perfume")):
        return None
    reader = csv.DictReader(io.StringIO(text.lstrip()))
    cols = {c.lower().strip(): c for c in reader.fieldnames or []}
    name_col = next((cols[k] for k in ("name", "fragrance", "perfume", "fragrance name") if k in cols), None)
    house_col = next((cols[k] for k in ("house", "brand", "designer") if k in cols), None)
    if not name_col:
        return None
    return [f"{r.get(name_col, '')} {r.get(house_col, '') if house_col else ''}".strip()
            for r in reader if (r.get(name_col) or "").strip()]


def parse_pasted_list(text: str) -> list[str]:
    """Split a pasted list or uploaded file (e.g. from Fragrantica: "Santal 33 Le Labo", "Le Labo - Santal 33",
    "Santal 33 by Le Labo for women and men", or a CSV with name/house columns) into lookup strings."""
    as_csv = _parse_csv(text)
    if as_csv is not None:
        return as_csv
    out = []
    for line in re.split(r"[\n;]+", text):
        line = re.sub(r"^\s*([-*•\d.)]+\s+)", "", line)
        line = re.sub(r"\bfor (women and men|women|men)\b", "", line, flags=re.I)
        line = re.sub(r"\s+(by|-|–|—|\|)\s+", " ", line)
        line = re.sub(r"\(\d{4}\)|\b(eau de (parfum|toilette)|edp|edt|parfum|extrait)\b", "", line, flags=re.I)
        line = re.sub(r"\s+", " ", line).strip(" ,")
        if len(line) > 1:
            out.append(line)
    return out


def add_to_collection(items: str, status: str = "owned", rating: int | None = None,
                      confirm: bool = False) -> dict:
    """Import fragrances into my collection. items is one name per line or a pasted Fragrantica
    list. With confirm=false (default) it only previews matches and unmatched lines; call again
    with confirm=true after the user approves to save. status: owned, sampled or wishlist.
    Existing entries get their status (and rating, if given) updated."""
    if status not in ("owned", "sampled", "wishlist"):
        return {"error": "status must be owned, sampled or wishlist"}
    if rating is not None and not 1 <= rating <= 5:
        return {"error": "rating must be 1-5"}
    matched, unmatched = [], []
    for line in parse_pasted_list(items)[:50]:
        m, alts = best_match(line)
        if m:
            matched.append({"input": line, "id": m["id"], "match": f"{m['name']} ({m['house']})",
                            "already": m["my_status"], "score": round(m["match_score"], 2)})
        else:
            unmatched.append({"input": line, "did_you_mean": [f"{a['name']} ({a['house']})" for a in alts[:3]]})
    if not confirm:
        return {"saved": False, "preview": matched, "unmatched": unmatched,
                "next": "Show this to the user; call again with confirm=true to save the matches."}
    for m in matched:
        rows("""INSERT INTO my_collection (user_email, fragrance_id, status, rating) VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_email, fragrance_id) DO UPDATE SET status = EXCLUDED.status,
                rating = coalesce(EXCLUDED.rating, my_collection.rating) RETURNING fragrance_id""",
             (current_user(), m["id"], status, rating))
    return {"saved": True, "added_or_updated": [m["match"] for m in matched], "unmatched": unmatched}



def save_to_collection(fragrance_ids: list[int], status: str = "owned", rating: int | None = None) -> dict:
    """Save already-previewed matches by id (the UI's confirm step)."""
    if status not in ("owned", "sampled", "wishlist"):
        return {"error": "status must be owned, sampled or wishlist"}
    saved = []
    for fid in fragrance_ids[:50]:
        saved += rows("""INSERT INTO my_collection (user_email, fragrance_id, status, rating) VALUES (%s, %s, %s, %s)
                         ON CONFLICT (user_email, fragrance_id) DO UPDATE SET status = EXCLUDED.status,
                         rating = coalesce(EXCLUDED.rating, my_collection.rating) RETURNING fragrance_id""",
                      (current_user(), fid, status, rating))
    return {"saved": True, "count": len(saved)}


def update_collection_item(fragrance_id: int, status: str | None = None, rating: int | None = None) -> dict:
    """Change status and/or rating (1-5) of one collection item."""
    res = rows("""UPDATE my_collection SET status = coalesce(%s, status), rating = coalesce(%s, rating)
                  WHERE user_email = %s AND fragrance_id = %s RETURNING fragrance_id, status, rating""",
               (status, rating, current_user(), fragrance_id))
    return res[0] if res else {"error": "not in collection"}


def remove_from_collection(fragrance_id: int) -> dict:
    res = rows("DELETE FROM my_collection WHERE user_email = %s AND fragrance_id = %s RETURNING fragrance_id",
               (current_user(), fragrance_id))
    return {"removed": bool(res)}


def lookup(q: str, limit: int = 8) -> list[dict]:
    """Fuzzy name search for the wardrobe's add box."""
    if len(q.strip()) < 2:
        return []
    return [clean({k: r[k] for k in ("id", "name", "house", "year", "family", "my_status", "source")})
            for r in resolve(q, limit)]


DAILY_MESSAGE_LIMIT = int(os.environ.get("DAILY_MESSAGE_LIMIT", "30"))


def take_message_quota() -> tuple[bool, int]:
    """Count one guide message for the current user today. Returns (allowed, remaining)."""
    used = rows("""INSERT INTO chat_usage (user_email, day, messages) VALUES (%(me)s, CURRENT_DATE, 1)
                   ON CONFLICT (user_email, day) DO UPDATE SET messages = chat_usage.messages + 1
                   RETURNING messages""", {})[0]["messages"]
    return used <= DAILY_MESSAGE_LIMIT, max(0, DAILY_MESSAGE_LIMIT - used)
