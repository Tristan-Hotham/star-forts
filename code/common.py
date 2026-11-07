"""Shared paths, groupings and helpers for the star-forts study ("The star fort belt").

Raw inputs (read in place, never modified; from step 02 onward only data/ is needed):
  INK_FORTS  /home/claude/studies/ink-map/data/forts.geojson
      Star forts of The Inked World study (code/02g_forts.py there): 1,022 bastioned outlines found by shape in
      OpenStreetMap (historic=fort, fortification_type=*, town walls and moats; ODbL), each followed by its label point,
      then 1,061 catalogue-only points from Wikidata (star fort Q12797, sconce Q91203/Q6653030, polygonal fort Q92080;
      CC0) that have no traced outline. Properties: n (name), q (Wikidata id), w (English Wikipedia title), z (zoom).
  OSM_FORTS  /home/claude/newdata/raw13/fort_*.json
      The Overpass extracts the outlines came from (ways and relations with geometry and tags; ODbL): used here for the
      OpenStreetMap start_date, name and wikidata tags of the elements that overlap each outline.
  WD_DATES   /home/claude/newdata/raw_new6/forts/forts_dates_by_qid_1.tsv, _2.tsv
      QLever/Wikidata: for every Wikidata id in INK_FORTS, inception (P571) with precision, start time (P580), official
      opening (P1619), dissolved/demolished (P576), classes (P31) and architect (P84). CC0.
  WD_BASTION /home/claude/newdata/raw_new6/forts/forts_bastion_wikidata.tsv
      QLever/Wikidata: every item under star fort (Q12797) or fortified town (Q677678) with coordinates and dates. CC0.
  WD_AUDIT   /home/claude/newdata/raw_new6/forts/forts_class_audit.tsv   labels and counts of the classes used.
  HAND       data/hand_dates.csv   (input, written by hand): 81 important forts dated from English Wikipedia
      (CC BY-SA 4.0 text; dates are facts), with the builder and whether the works survive.
  GEO        /home/claude/newdata/raw/geo/ne_10m_admin_0_countries.geojson, ne_50m_land.geojson,
             ne_10m_populated_places_simple.geojson  Natural Earth (public domain)
  FONTS      /home/claude/ref/fonts  Fraunces, Source Serif 4, IBM Plex Mono; ink fonts in /home/claude/studies/ink-map/fonts/ttf
"""
import json, gzip, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INK = os.environ.get("SF_INK", "/home/claude/studies/ink-map")
INK_FORTS = os.path.join(INK, "data", "forts.geojson")
OSM_FORTS = os.environ.get("SF_OSM", "/home/claude/newdata/raw13")
RAWF = os.environ.get("SF_RAW", "/home/claude/newdata/raw_new6/forts")
GEO = os.environ.get("SF_GEO", "/home/claude/newdata/raw/geo")
FONTS = os.environ.get("SF_FONTS", "/home/claude/ref/fonts")
INKFONTS = os.path.join(INK, "fonts", "ttf")
DATA = os.path.join(ROOT, "data")
WORK = os.path.join(os.environ.get("SFTMP", "/home/claude/work/new6/star-forts"), "work")
for d in (DATA, WORK):
    os.makedirs(d, exist_ok=True)

SLUG = "star-forts"
PAGE = f"https://maps.tristanhotham.com/{SLUG}/"
REPO = f"https://github.com/Tristan-Hotham/{SLUG}"
INKPAGE = "https://maps.tristanhotham.com/ink-map/"
AI = ("I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped "
      "prepare the analysis code. I reviewed and checked all text and results.")
BYLINE = "Dr Tristan Hotham · Independent researcher · 2026"

FIRST_YEAR = 1450        # a date before this is the site's medieval origin, not its bastions
LAST_YEAR = 1945

# Regions (modern countries, ISO A3), in legend order
REGIONS = [
    ("Italy and Malta", "#A3261B", {"ITA", "MLT", "SMR", "VAT"}),
    ("Iberia", "#B5651D", {"ESP", "PRT", "AND", "GIB"}),
    ("France", "#3D6E9E", {"FRA", "MCO"}),
    ("Low Countries", "#D08A1E", {"NLD", "BEL", "LUX"}),
    ("German lands and Central Europe", "#4E7A3A", {"DEU", "AUT", "CHE", "CZE", "SVK", "POL", "HUN", "LIE", "SVN"}),
    ("Scandinavia and the Baltic", "#2E7F86", {"DNK", "NOR", "SWE", "FIN", "EST", "LVA", "LTU", "ISL", "ALA"}),
    ("British Isles", "#7B4B94", {"GBR", "IRL", "IMN", "JEY", "GGY"}),
    ("Eastern Europe, Balkans and Turkey", "#8A5A44", {"RUS", "UKR", "BLR", "MDA", "ROU", "BGR", "SRB", "HRV", "BIH", "MNE",
                                                        "MKD", "ALB", "GRC", "CYP", "TUR", "KOS", "GEO", "ARM", "AZE", "CYN"}),
    ("Africa", "#6B6B2A", None),
    ("Americas", "#2B5F4A", None),
    ("Asia and Oceania", "#5A4A8A", None),
]
RNAMES = [r[0] for r in REGIONS]
RCOL = {r[0]: r[1] for r in REGIONS}
EUROPE = set(RNAMES[:8])


# Countries where the shape test mostly finds fortifications of other traditions (towered walls of Chinese and Korean towns,
# Mughal and Rajput forts, medina and kasbah walls, Persian and Central Asian forts): their towers can make a star-like
# outline. Outlines there count as "look-alikes", outside the main counts, unless dated by hand or named in COLONIAL.
LOOKALIKE_ISO = {"CHN", "KOR", "PRK", "MNG", "IND", "PAK", "BGD", "NPL", "AFG", "IRN", "IRQ", "SYR", "LBN", "JOR", "ISR", "PSE",
                 "SAU", "YEM", "OMN", "ARE", "QAT", "KWT", "BHR", "UZB", "KAZ", "TKM", "KGZ", "TJK", "MAR", "DZA", "TUN", "LBY",
                 "EGY", "SDN", "ETH", "MLI", "NER", "TCD", "MRT"}
# European-built (or European-designed) forts in those countries that are in the data under these names
COLONIAL = {"Fort Sadras", "Fort St. David", "Fort Saint David", "Fort Dansborg", "Fort Geldria", "Fort Manuel", "Fort Cochin",
            "Thalassery Fort", "Fort St. Angelo", "Borj Nord", "Fort Tegallen"}


def region_of(iso, continent):
    for n, c, s in REGIONS:
        if s and iso in s:
            return n
    if continent == "Africa":
        return "Africa"
    if continent in ("North America", "South America"):
        return "Americas"
    if continent in ("Asia", "Oceania"):
        return "Asia and Oceania"
    if continent == "Europe":
        return "Eastern Europe, Balkans and Turkey"
    return None


def jload(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def dash(v):
    """Remove em and en dashes and double hyphens from text (house style)."""
    if isinstance(v, str):
        v = re.sub(r"(\d)\s*[–—]\s*(\d)", r"\1 to \2", v)
        v = v.replace(" — ", ", ").replace("—", ", ").replace(" – ", ", ").replace("–", "-")
        while "--" in v:
            v = v.replace("--", "-")
        return v
    if isinstance(v, list):
        return [dash(x) for x in v]
    if isinstance(v, dict):
        return {k: dash(x) for k, x in v.items()}
    return v


def nonan(v):
    if isinstance(v, float) and v != v:
        return None
    if isinstance(v, list):
        return [nonan(x) for x in v]
    if isinstance(v, dict):
        return {k: nonan(x) for k, x in v.items()}
    return v


def jsave(obj, path, indent=None):
    obj = nonan(obj)
    if os.path.abspath(path).startswith(DATA):
        obj = dash(obj)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, allow_nan=False, indent=indent, separators=None if indent else (",", ":"))


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return re.sub(r"[\W_]+", " ", s).strip()


def tsv(path):
    """Parse a QLever TSV result into a list of dicts with plain values."""
    lines = open(path, encoding="utf-8").read().rstrip("\n").split("\n")
    head = [h.lstrip("?") for h in lines[0].split("\t")]
    out = []
    for ln in lines[1:]:
        f = ln.split("\t")
        row = {}
        for h, v in zip(head, f + [""] * (len(head) - len(f))):
            v = v.strip()
            if v.startswith("<http://www.wikidata.org/entity/"):
                v = v[len("<http://www.wikidata.org/entity/"):-1]
            elif v.startswith("<") and v.endswith(">"):
                v = v[1:-1]
            else:
                m = re.match(r'^"(.*)"(@[\w-]+|\^\^<[^>]+>)?$', v, re.S)
                if m:
                    v = m.group(1).replace('\\"', '"').replace("\\\\", "\\")
            row[h] = v
        out.append(row)
    return out


def get(R, path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f=None):
    if f is None or f == "raw": return str(v)
    if f == "int": return f"{round(float(v)):,}"
    if f == "pc": return f"{round(float(v))}%"
    if f == "pc1": return f"{float(v):.1f}%"
    if f == "f1": return f"{float(v):.1f}"
    raise ValueError(f)


def km(lat1, lon1, lat2, lon2):
    import math
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))
