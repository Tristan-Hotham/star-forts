"""Step 1: one table of star forts with outlines, names, countries, sizes and dates.

Reads INK_FORTS (outlines and catalogue points), OSM_FORTS (tags of the OpenStreetMap elements under each outline),
WD_DATES and WD_BASTION (Wikidata dates and names), data/hand_dates.csv and Natural Earth.
Writes data/forts.csv, data/forts_outlines.geojson and WORK/forts.json.
"""
import csv, glob, math, re, collections, urllib.parse
from shapely.geometry import shape, Point, Polygon, LineString, mapping
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from shapely.ops import transform, polygonize, unary_union
from shapely.strtree import STRtree
from common import *

# ---------------------------------------------------------------- the forts of The Inked World
feats = jload(INK_FORTS)["features"]
forts = []
i = 0
while i < len(feats) and feats[i]["geometry"]["type"] == "Polygon":
    pol, pt = feats[i], feats[i + 1]
    assert pt["geometry"]["type"] == "Point" and pt["properties"]["n"] == pol["properties"]["n"]
    forts.append({"poly": shape(pol["geometry"]), "lon": pt["geometry"]["coordinates"][0], "lat": pt["geometry"]["coordinates"][1],
                  "name": pol["properties"]["n"] or "", "qid": pol["properties"]["q"] or "", "enwiki": pol["properties"].get("w") or "",
                  "outline": True, "src": "osm_outline"})
    i += 2
N_OUTLINE_IN = len(forts)
cat = []
for f in feats[i:]:
    p = f["properties"]
    cat.append({"poly": None, "lon": f["geometry"]["coordinates"][0], "lat": f["geometry"]["coordinates"][1], "name": p["n"] or "",
                "qid": p["q"] or "", "enwiki": p.get("w") or "", "outline": False, "src": "wikidata_catalogue"})
N_CAT_IN = len(cat)
print("outlines", N_OUTLINE_IN, "catalogue points", N_CAT_IN)


def proj(lat0, lon0):
    k = 111320 * math.cos(math.radians(lat0))
    return lambda x, y: ((x - lon0) * k, (y - lat0) * 110574)


def shape_stats(pm):
    """salients (bastion points): convex corners sharper than 100 degrees that stick out from the centre
    (the same test The Inked World used to find the outlines)"""
    pts = list(pm.exterior.coords)[:-1]
    n = len(pts); cx, cy = pm.centroid.x, pm.centroid.y
    orient = 1 if pm.exterior.is_ccw else -1
    sal = 0
    for j in range(n):
        ax, ay = pts[j - 1]; bx, by = pts[j]; qx, qy = pts[(j + 1) % n]
        v1 = (ax - bx, ay - by); v2 = (qx - bx, qy - by)
        l1 = math.hypot(*v1); l2 = math.hypot(*v2)
        if l1 < 3 or l2 < 3: continue
        ang = math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)))))
        cross = (bx - ax) * (qy - by) - (by - ay) * (qx - bx)
        if cross * orient > 0 and ang < 100:
            d = math.hypot(bx - cx, by - cy)
            if d >= math.hypot(ax - cx, ay - cy) and d >= math.hypot(qx - cx, qy - cy): sal += 1
    return sal


for f in forts:
    c = f["poly"].centroid
    pm = transform(proj(c.y, c.x), f["poly"])
    if not pm.is_valid: pm = pm.buffer(0)
    if pm.geom_type == "MultiPolygon": pm = max(pm.geoms, key=lambda g: g.area)
    hull = list(pm.convex_hull.exterior.coords)
    f["area_ha"] = round(pm.area / 1e4, 2)
    f["perimeter_m"] = round(pm.exterior.length)
    f["diameter_m"] = round(max(math.hypot(a[0] - b[0], a[1] - b[1]) for a in hull for b in hull))
    f["points"] = shape_stats(pm.simplify(4))

# ---------------------------------------------------------------- OpenStreetMap tags under each outline
tree = STRtree([f["poly"] for f in forts])
osm_hits = collections.defaultdict(list)
n_el = 0


def el_geom(el):
    if el["type"] == "way":
        g = el.get("geometry") or []
        if len(g) < 2: return None
        cs = [(p["lon"], p["lat"]) for p in g]
        return Polygon(cs) if len(cs) >= 4 and cs[0] == cs[-1] else LineString(cs)
    lines = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]]) for m in el.get("members", [])
             if m.get("type") == "way" and m.get("role") != "inner" and len(m.get("geometry") or []) >= 2]
    if not lines: return None
    ps = list(polygonize(unary_union(lines)))
    return unary_union(ps) if ps else unary_union(lines)


for fn in sorted(glob.glob(f"{OSM_FORTS}/fort_*.json")):
    for el in jload(fn)["elements"]:
        t = el.get("tags", {})
        if not (t.get("name") or t.get("start_date") or t.get("wikidata")): continue
        g = el_geom(el)
        if g is None or g.is_empty: continue
        if not g.is_valid: g = g.buffer(0)
        n_el += 1
        for j in tree.query(g):
            P = forts[j]["poly"]
            if not g.intersects(P): continue
            # the element must be the fort itself, not a bastion, barracks or a town round it: its outline (or the
            # outline of its line) covers between a third and three times the fort's area
            ga = g.area if g.geom_type in ("Polygon", "MultiPolygon") else (g.convex_hull.area if g.length > 0 else 0)
            if ga <= 0: continue
            r = ga / P.area
            if 0.33 <= r <= 3 and g.centroid.distance(P) < 0.002:
                osm_hits[j].append({"type": el["type"], "id": el["id"], "name": t.get("name:en") or t.get("name") or "",
                                    "start": t.get("start_date", ""), "q": t.get("wikidata", ""), "r": abs(math.log(r))})
print("OSM elements with a name, start date or wikidata", n_el, "; outlines with a match", len(osm_hits))


def year_of(s):
    """first four-digit year in an OSM start_date (1634, 1634-05, ~1634, C17 = century)"""
    s = (s or "").strip()
    m = re.match(r"^~?(?:before |after |early |late |mid )?(\d{4})", s)
    if m: return int(m.group(1)), ("approx" if s.startswith("~") else "year")
    m = re.match(r"^(\d{3})\d?0s$", s)
    if m: return int(s[:4]), "decade"
    return None, None


osm_q_used = {f["qid"] for f in forts if f["qid"]}
for j, hits in sorted(osm_hits.items()):
    f = forts[j]
    hits.sort(key=lambda h: h["r"])
    f["osm"] = ";".join(f"{h['type'][0]}{h['id']}" for h in hits[:3])
    if not f["name"]:
        nm = next((h["name"] for h in hits if h["name"]), "")
        if nm: f["name"], f["named_from"] = nm, "OpenStreetMap"
    if not f["qid"]:
        q = next((h["q"] for h in hits if re.match(r"^Q\d+$", h["q"])), "")
        if q and q not in osm_q_used: f["qid"] = q; osm_q_used.add(q)
    sd = [(year_of(h["start"]), h["start"]) for h in hits if h["start"]]
    sd = [(y, p, raw) for (y, p), raw in sd if y]
    if sd:
        y, p, raw = sd[0]
        f["osm_start"] = raw; f["osm_year"] = y; f["osm_prec"] = p

# ---------------------------------------------------------------- Wikidata classes and dates
WDD = {r["item"]: r for fn in ("forts_dates_by_qid_1.tsv", "forts_dates_by_qid_2.tsv") for r in tsv(f"{RAWF}/{fn}")}
BAST = {r["item"]: r for r in tsv(f"{RAWF}/forts_bastion_wikidata.tsv")}
AUDIT = tsv(f"{RAWF}/forts_class_audit.tsv")
BAVARIAN = "Q22969563"       # "Bavarian monument" (Bodendenkmal in Bayern)


def wd_point(r):
    m = re.match(r"POINT\(([-\d.eE]+) ([-\d.eE]+)\)", r.get("coords", ""))
    return (float(m.group(1)), float(m.group(2))) if m else None


# catalogue points that sit on a traced outline are the same fort: give their id and name to the outline
ptree = STRtree([f["poly"] for f in forts])
kept, merged = [], 0
for c in cat:
    P = Point(c["lon"], c["lat"])
    js = [j for j in ptree.query(P.buffer(0.0025)) if forts[j]["poly"].distance(P) < 0.0025]
    js = [j for j in js if not forts[j]["qid"] or forts[j]["qid"] == c["qid"]]
    if js:
        j = min(js, key=lambda j: forts[j]["poly"].distance(P))
        f = forts[j]
        if not f["qid"]: f["qid"] = c["qid"]
        if not f["name"] or f.get("named_from") == "OpenStreetMap": f["name"], f["named_from"] = c["name"], "Wikidata"
        f["enwiki"] = f["enwiki"] or c["enwiki"]
        merged += 1
    else:
        kept.append(c)
cat = kept
print("catalogue points merged into outlines", merged)
# fortified towns and star forts of Wikidata lying on an outline: their name, id and dates
n_town = 0
for q, r in BAST.items():
    xy = wd_point(r)
    if not xy: continue
    P = Point(*xy)
    js = [j for j in ptree.query(P) if forts[j]["poly"].contains(P)]
    for j in js:
        f = forts[j]
        if f["qid"] and f["qid"] != q: continue
        if not f["qid"] and q in {g["qid"] for g in forts + cat}: continue
        if not f["qid"]:
            f["qid"] = q; n_town += 1
        if not f["name"] or f.get("named_from") == "OpenStreetMap":
            f["name"], f["named_from"] = r["name"], "Wikidata"
        if r.get("enwikiUrl"): f["enwiki"] = f["enwiki"] or urllib.parse.unquote(r["enwikiUrl"].rsplit("/", 1)[1]).replace("_", " ")
print("Wikidata fortified towns or star forts placed on an outline", n_town)
# Wikidata star forts (Q12797) that are in neither list
have_q = {f["qid"] for f in forts + cat if f["qid"]}
n_newstar = 0
for q, r in BAST.items():
    if q in have_q or "Q12797" not in r["roots"]: continue
    xy = wd_point(r)
    if not xy: continue
    cat.append({"poly": None, "lon": xy[0], "lat": xy[1], "name": r["name"], "qid": q, "outline": False, "src": "wikidata_star_fort",
                "enwiki": urllib.parse.unquote(r["enwikiUrl"].rsplit("/", 1)[1]).replace("_", " ") if r.get("enwikiUrl") else ""})
    n_newstar += 1
print("extra Wikidata star forts", n_newstar)

allf = forts + cat
for f in allf:
    f.setdefault("named_from", "OpenStreetMap" if f["outline"] and f["name"] else "Wikidata" if f["name"] else "")
    r = WDD.get(f["qid"]) or {}
    cls = {c.rsplit("/", 1)[-1] for c in (r.get("classes") or "").split("|") if c}
    f["classes"] = sorted(cls)
    f["bavarian"] = (BAVARIAN in cls or f["name"].startswith("Cultural heritage D-")) and not f["outline"]
    br = BAST.get(f["qid"]) or {}
    for k_out, k_in in (("wd_inception", "inception"), ("wd_prec", "inception_precision"), ("wd_start", "start"),
                        ("wd_opened", "opened"), ("wd_end", "end")):
        v = r.get(k_in) or br.get(k_in) or ""
        f[k_out] = int(v) if re.match(r"^-?\d+$", v) else None
    f["architects"] = [a.rsplit("/", 1)[-1] for a in (r.get("architects") or "").split("|") if a]

# ---------------------------------------------------------------- hand dates (English Wikipedia)
GENERIC = {"fort", "forte", "fortress", "fortezza", "fortaleza", "castle", "castillo", "castel", "citadel", "citadelle", "cittadella",
           "walls", "venetian", "the", "of", "de", "da", "do", "di", "del", "dos", "san", "santa", "sant", "saint", "old", "town", "star",
           "fuerte", "nossa", "senhora", "upon"}


def compatible(hname, f):
    if not f["name"]:
        return True
    a = {w for w in norm(hname).split() if w not in GENERIC and len(w) >= 4}
    b = {w for w in norm(f["name"]).split() if w not in GENERIC and len(w) >= 4}
    return bool(a & b)


hand = list(csv.DictReader(open(f"{DATA}/hand_dates.csv", encoding="utf-8")))
byq = {f["qid"]: f for f in allf if f["qid"]}
n_added = 0
for h in hand:
    h["lat"], h["lon"], h["year"] = float(h["lat"]), float(h["lon"]), int(h["year"])
    tgt = byq.get(h["qid"]) if h["qid"] else None
    P = Point(h["lon"], h["lat"])
    # by position: only onto a fort with no name of its own, or one whose name shares a word with the hand entry (so a
    # town is never put on one of its own bastions or on a neighbouring fort)
    if tgt is None:
        inside = [f for f in forts if f["poly"].contains(P) and "hand" not in f and compatible(h["name"], f)]
        if inside:
            tgt = min(inside, key=lambda f: f["poly"].area)
    if tgt is None:
        near = [(km(h["lat"], h["lon"], f["lat"], f["lon"]), f) for f in allf if not f["bavarian"] and "hand" not in f and compatible(h["name"], f)]
        near = [x for x in near if x[0] < (1.0 if x[1]["name"] else 0.3)]
        if near:
            tgt = min(near, key=lambda x: (x[0] - (0.5 if x[1]["outline"] else 0)))[1]
    if tgt is None:
        tgt = {"poly": None, "lon": h["lon"], "lat": h["lat"], "name": h["name"], "qid": h["qid"], "outline": False, "src": "hand_added",
               "named_from": "Wikipedia", "enwiki": "", "classes": [], "bavarian": False, "architects": []}
        for k in ("wd_inception", "wd_prec", "wd_start", "wd_opened", "wd_end"): tgt[k] = None
        allf.append(tgt); n_added += 1
    assert "hand" not in tgt, h["name"]
    tgt["hand"] = h
    tgt["name"], tgt["named_from"] = h["name"], "Wikipedia"
print("hand-dated", len(hand), "; added as new points", n_added)

# ---------------------------------------------------------------- the date of each fort's bastions
for f in allf:
    y = src = prec = None
    h = f.get("hand")
    if h:
        y, src, prec = h["year"], "Wikipedia", "year"
    if y is None:
        for k, lab in (("wd_start", "Wikidata start time"), ("wd_opened", "Wikidata opening")):
            if f[k] and FIRST_YEAR <= f[k] <= LAST_YEAR: y, src, prec = f[k], lab, "year"; break
    # an inception is the date of the site, which for a monastery or a medieval castle is not the date of its bastions;
    # a decade-precision inception before 1550 is too vague to say whether the first works were bastioned
    wd_ok = "Q44613" not in f["classes"] and not ((f["wd_prec"] or 0) == 8 and (f["wd_inception"] or 9999) < 1550)
    if y is None and wd_ok and f["wd_inception"] is not None and (f["wd_prec"] or 0) >= 8 and FIRST_YEAR <= f["wd_inception"] <= LAST_YEAR:
        y, src, prec = f["wd_inception"], "Wikidata inception", "decade" if f["wd_prec"] == 8 else "year"
    if y is None and f.get("osm_year") and FIRST_YEAR <= f["osm_year"] <= LAST_YEAR:
        y, src, prec = f["osm_year"], "OpenStreetMap start_date", f["osm_prec"]
    f["year"], f["year_src"], f["year_prec"] = y, src, prec
    f["medieval"] = bool(y is None and ((f["wd_inception"] is not None and f["wd_inception"] < FIRST_YEAR) or (f.get("osm_year") and f["osm_year"] < FIRST_YEAR)))
    f["late"] = bool(y is None and ((f["wd_inception"] or 0) > LAST_YEAR or (f.get("osm_year") or 0) > LAST_YEAR))
    f["century_only"] = bool(y is None and f["wd_inception"] is not None and (f["wd_prec"] or 0) < 8 and FIRST_YEAR <= f["wd_inception"] <= LAST_YEAR + 100)

# ---------------------------------------------------------------- countries and names for the unnamed
ISO_FIX = {"Bourtange": ("NLD", "Netherlands", "Europe")}
ne = jload(f"{GEO}/ne_10m_admin_0_countries.geojson")["features"]
cs = [(shape(c["geometry"]), c["properties"]) for c in ne]
ctree = STRtree([g for g, _ in cs])
for f in allf:
    P = Point(f["lon"], f["lat"])
    js = [j for j in ctree.query(P) if cs[j][0].contains(P)]
    if not js:
        js = [min(ctree.query(P.buffer(0.5)), key=lambda j: cs[j][0].distance(P), default=None)]
        js = [j for j in js if j is not None]
    if js:
        p = cs[js[0]][1]
        iso = p["ADM0_A3"] if p["ADM0_A3"] not in ("-99",) else p["ISO_A3"]
        iso = {"SDS": "SSD", "SAH": "ESH", "KOS": "KOS", "PSX": "PSE", "CYN": "CYP"}.get(iso, iso)
        f["iso"], f["country"], f["continent"] = iso, p["NAME_EN"] if p.get("NAME_EN") else p["NAME"], p["CONTINENT"]
        if iso == "CYP": f["country"] = "Cyprus"
    else:
        f["iso"], f["country"], f["continent"] = "", "", ""
    if f["name"] in ISO_FIX:      # Natural Earth's 1:10m border puts these few on the wrong side
        f["iso"], f["country"], f["continent"] = ISO_FIX[f["name"]]
    f["region"] = region_of(f["iso"], f["continent"])
pp = jload(f"{GEO}/ne_10m_populated_places_simple.geojson")["features"]
ppt = [(Point(p["geometry"]["coordinates"]), p["properties"]["name"]) for p in pp]
pptree = STRtree([g for g, _ in ppt])
for f in allf:
    if f["name"]: continue
    P = Point(f["lon"], f["lat"])
    j = pptree.nearest(P)
    g, nm = ppt[j]
    d = km(f["lat"], f["lon"], g.y, g.x)
    f["name"], f["named_from"] = (f"Star fort near {nm}" if d > 3 else f"Star fort at {nm}"), "nearest town (Natural Earth)"
    f["near_km"] = round(d, 1)

# ---------------------------------------------------------------- ids, kinds and output
# outlines that pass the shape test but are known not to be bastioned works: Maginot Line blocks (ouvrages) and the
# towered medieval wall of Smolensk
NOT_BASTION = re.compile(r"^Ouvrage |Smolensk")
allf.sort(key=lambda f: (f["bavarian"], not f["outline"], round(-f["lat"], 3), f["lon"]))
for k, f in enumerate(allf):
    f["id"] = f"SF{k + 1:04d}"
    f["lookalike"] = ((f["iso"] in LOOKALIKE_ISO and "hand" not in f and f["name"] not in COLONIAL) or bool(NOT_BASTION.search(f["name"]))) and not f["bavarian"]
    f["kind"] = ("bavarian_listed" if f["bavarian"] else "lookalike" if f["lookalike"] else "hand_added" if f["src"] == "hand_added"
                 else "outline" if f["outline"] else "catalogue")
    f["main"] = not (f["bavarian"] or f["lookalike"])
    h = f.get("hand") or {}
    f["builder"], f["status"] = h.get("builder", ""), h.get("status", "")
    f["wikipedia"] = h.get("wikipedia") or (("https://en.wikipedia.org/wiki/" + urllib.parse.quote(f["enwiki"].replace(" ", "_"))) if f.get("enwiki") else "")
    f["note"] = h.get("note", "")

COLS = ["id", "name", "named_from", "kind", "main", "outline", "lon", "lat", "iso", "country", "region", "qid", "osm", "area_ha",
        "perimeter_m", "diameter_m", "points", "year", "year_src", "year_prec", "medieval", "wd_inception", "wd_prec", "wd_start",
        "wd_opened", "wd_end", "osm_start", "builder", "status", "wikipedia", "note"]
with open(f"{DATA}/forts.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(COLS)
    for f in allf:
        w.writerow([dash(str(f.get(c))) if isinstance(f.get(c), str) else ("" if f.get(c) is None else f.get(c)) for c in COLS])


def r5(v): return round(v, 5)


ol = []
for f in allf:
    if not f["outline"]: continue
    ring = list(f["poly"].simplify(0.00001).exterior.coords)
    if Polygon(ring).exterior.is_ccw: ring = ring[::-1]       # clockwise, as on The Inked World (moat outside, rampart inside)
    ol.append({"type": "Feature", "properties": {"id": f["id"], "n": f["name"], "y": f["year"]},
               "geometry": {"type": "Polygon", "coordinates": [[[r5(a), r5(b)] for a, b in ring]]}})
jsave({"type": "FeatureCollection", "features": ol}, f"{DATA}/forts_outlines.geojson")
out = []
for f in allf:
    g = {k: v for k, v in f.items() if k not in ("poly", "hand")}
    out.append(g)
jsave({"forts": out, "audit": AUDIT, "hand": [{k: v for k, v in h.items()} for h in hand],
       "counts": {"outline_in": N_OUTLINE_IN, "catalogue_in": N_CAT_IN, "merged": merged, "towns_on_outline": n_town,
                  "extra_wd_star": n_newstar, "hand_added": n_added, "osm_elements": n_el, "osm_matched": len(osm_hits)}},
      f"{WORK}/forts.json")
C = collections.Counter(f["kind"] for f in allf)
print(C, "dated", sum(1 for f in allf if f["year"] and f["main"]), "of", sum(1 for f in allf if f["main"]),
      collections.Counter(f["year_src"] for f in allf if f["main"]))
print("unnamed given a town name", sum(1 for f in allf if f["named_from"].startswith("nearest")))
