"""Create the schema and load fragrances (curated + doevent/perfume), my_collection and embeddings.

Usage: python -m scripts.seed   (drops and recreates all three tables, including wear_log)
"""

import ast
import csv
import os
import re
import sys
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np

from typing import Any

from scent_finder.fragrance.db import connect, embed, q

ROOT = Path(__file__).resolve().parent.parent
DOEVENT_REV = "9d2db452d8f0d649c4bfb0189a2fcc5282028a3c"  # pinned Hugging Face revision
DOEVENT_URL = f"https://huggingface.co/datasets/doevent/perfume/resolve/{DOEVENT_REV}/perfumes.csv"
DOEVENT_CSV = ROOT / "data" / "raw" / "doevent_perfumes.csv"
# Whose shelf data/my_collection.csv seeds (your workspace login email).
SEED_USER = os.environ.get("SCENT_FINDER_USER", "local@scent-finder").lower()

CURATED_FIELDS = ["name", "house", "year", "perfumer", "family", "top_notes", "heart_notes",
                  "base_notes", "accords", "season", "price_band", "low_confidence", "description"]
LISTS = {"top_notes", "heart_notes", "base_notes", "accords", "season"}
COLUMNS = ["name", "house", "year", "perfumer", "family", "subfamily", "top_notes", "heart_notes",
           "base_notes", "notes", "accords", "season", "season_inferred", "price_band", "gender",
           "description", "source", "low_confidence"]

FAMILY_MAP = {"FLORAL": "floral", "WOODY": "woody", "AMBERY (ORIENTAL)": "amber", "CITRUS": "citrus",
              "AROMATIC FOUGERE": "aromatic", "CHYPRE": "chypre", "LEATHER": "leather"}
SUBFAMILY_ACCORD = {"AMBERY (ORIENTAL)": "ambery", "CITRUS": "citrus", "FRUITY": "fruity",
                    "FLORAL": "floral", "WOODY": "woody", "GREEN": "green", "MUSK SKIN": "musky",
                    "AROMATIC FOUGERE": "aromatic", "WATERY": "aquatic", "GOURMAND": "gourmand",
                    "SPICY": "spicy", "ALDEHYDIC": "aldehydic", "CHYPRE": "chypre", "LEATHER": "leathery"}
# Rule-of-thumb seasons for rows without sourced seasons (flagged season_inferred).
SEASON_BY_ACCORD = {
    "citrus": ["spring", "summer"], "aquatic": ["summer"], "green": ["spring", "summer"],
    "fruity": ["spring", "summer"], "floral": ["spring", "summer"], "aldehydic": ["fall", "winter"],
    "musky": ["spring", "fall"], "aromatic": ["spring", "fall"], "chypre": ["spring", "fall"],
    "woody": ["fall", "winter"], "spicy": ["fall", "winter"], "ambery": ["fall", "winter"],
    "gourmand": ["fall", "winter"], "leathery": ["fall", "winter"],
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def norm_house(s: str) -> str:
    h = norm(s)
    return {"maison margiela": "maison margiela replica",
            "editions de parfums frederic malle": "frederic malle"}.get(h, h)


def clean_note(n: str) -> str:
    """'Sandalwood (Australia)' -> 'sandalwood'; 'Iris / Orris' -> 'iris'."""
    n = re.sub(r"\(.*?\)", "", n).split("/")[0]
    return re.sub(r"\s+", " ", n).strip().lower()


def load_curated() -> list[dict]:
    rows = []
    for line in (ROOT / "data" / "fragrances.psv").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        r: dict[str, Any] = dict(zip(CURATED_FIELDS, line.split("|"), strict=True))
        for k in LISTS:
            r[k] = [v.strip() for v in r[k].split(",") if v.strip()]
        r.update(
            year=int(r["year"]) if r["year"] else None,
            perfumer=r["perfumer"] or None,
            low_confidence=r["low_confidence"] == "1",
            subfamily=None, gender=None, source="curated", season_inferred=False,
            notes=list(dict.fromkeys(r["top_notes"] + r["heart_notes"] + r["base_notes"])),
        )
        rows.append(r)
    return rows


def load_doevent(price_by_house: dict[str, str]) -> list[dict]:
    if not DOEVENT_CSV.exists():
        DOEVENT_CSV.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {DOEVENT_URL}")
        urllib.request.urlretrieve(DOEVENT_URL, DOEVENT_CSV)
    rows = []
    with open(DOEVENT_CSV, encoding="utf-8", errors="replace", newline="") as f:
        for d in csv.DictReader(f, delimiter="|"):
            name, house = (d["name_perfume"] or "").strip(), (d["brand"] or "").strip()
            if not name or not house or d["family"] not in FAMILY_MAP:
                continue
            if house == "Maison Margiela" and name.lower().startswith("replica"):
                name, house = re.sub(r"^replica\s*:?\s*", "", name, flags=re.I), "Maison Margiela Replica"
            if house == "Comme Des Garçons":
                house = "Comme des Garçons"
            try:
                notes = [clean_note(n) for n in ast.literal_eval(d["ingredients"])]
            except (ValueError, SyntaxError):
                notes = []
            accords = list(dict.fromkeys(
                [FAMILY_MAP[d["family"]]] + ([SUBFAMILY_ACCORD[d["subfamily"]]] if d["subfamily"] in SUBFAMILY_ACCORD else [])
                + [w.lower() for w in (d["fragrances"] or "").split() if w.lower() not in ("classical", "fresher")]
            ))
            season = sorted({s for a in accords for s in SEASON_BY_ACCORD.get(a, [])})
            year = d["years"][:4]
            rows.append(dict(
                name=name, house=house, year=int(year) if year.isdigit() else None, perfumer=None,
                family=FAMILY_MAP[d["family"]], subfamily=(d["subfamily"] or "").lower() or None,
                top_notes=[], heart_notes=[], base_notes=[], notes=list(dict.fromkeys(n for n in notes if n)),
                accords=accords, season=season, season_inferred=True,
                price_band=price_by_house.get(norm_house(house)), gender=d["gender"] or None,
                description=(d["description"] or "").strip() or None, source="doevent", low_confidence=False,
            ))
    return rows


def embedding_text(r: dict) -> str:
    """Text blob embedded per fragrance: family + accords + notes + description."""
    pyramid = (f"Top: {', '.join(r['top_notes'])}. Heart: {', '.join(r['heart_notes'])}. "
               f"Base: {', '.join(r['base_notes'])}." if r["top_notes"] else f"Notes: {', '.join(r['notes'])}.")
    return (f"{r['family']} fragrance"
            f"{' (' + r['subfamily'] + ')' if r['subfamily'] else ''}. Accords: {', '.join(r['accords'])}. "
            f"{pyramid} {r['description'] or ''}")[:2000]


def main() -> None:
    curated = load_curated()
    # Price bands are only known for curated houses; spread the house's most common band.
    bands: dict[str, Counter] = {}
    for r in curated:
        bands.setdefault(norm_house(r["house"]), Counter())[r["price_band"]] += 1
    price_by_house = {h: c.most_common(1)[0][0] for h, c in bands.items()}

    seen = {(norm(r["name"]), norm_house(r["house"])) for r in curated}
    rows = list(curated)
    dupes = 0
    for r in load_doevent(price_by_house):
        key = (norm(r["name"]), norm_house(r["house"]))
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        rows.append(r)
    print(f"{len(curated)} curated + {len(rows) - len(curated)} doevent ({dupes} duplicates skipped)")

    print("Embedding...", flush=True)
    vectors = embed([embedding_text(r) for r in rows])

    conn = connect(register=False)
    conn.execute(q((ROOT / "scripts" / "schema.sql").read_text()))
    conn.close()
    conn = connect()  # re-open so the vector type is registered
    with conn.cursor() as cur:
        cur.executemany(
            q(f"INSERT INTO fragrances ({', '.join(COLUMNS)}, embedding) VALUES ({', '.join(['%s'] * (len(COLUMNS) + 1))})"),
            [[r[c] for c in COLUMNS] + [np.array(v, dtype=np.float32)] for r, v in zip(rows, vectors, strict=True)],
        )
        with open(ROOT / "data" / "my_collection.csv", newline="", encoding="utf-8") as f:
            for c in csv.DictReader(f):
                cur.execute("SELECT id FROM fragrances WHERE name = %s AND house = %s AND source = 'curated'",
                            (c["name"], c["house"]))
                hit = cur.fetchone()
                if not hit:
                    sys.exit(f"my_collection: no fragrance {c['name']!r} by {c['house']!r}")
                cur.execute(
                    "INSERT INTO my_collection (user_email, fragrance_id, status, rating, notes) VALUES (%s, %s, %s, %s, %s)",
                    (SEED_USER, hit[0], c["status"], int(c["rating"]) if c["rating"] else None, c["notes"] or None),
                )
    print(f"Seeded {len(rows)} fragrances.")


if __name__ == "__main__":
    main()
