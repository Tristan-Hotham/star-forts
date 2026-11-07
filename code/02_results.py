"""Step 2: every number of the study (data/results.json), the tables in data/ and the page data.
Reads WORK/forts.json (step 1), data/forts_outlines.geojson and Natural Earth land."""
import csv, math, collections, statistics
import numpy as np
from scipy import stats
from shapely.geometry import shape
from common import *

D = jload(f"{WORK}/forts.json")
F = D["forts"]
M = [f for f in F if f["main"]]
DT = [f for f in M if f["year"]]
H = [f for f in F if f.get("year_src") == "Wikipedia"]
C = D["counts"]
R = {"meta": {"page": PAGE, "repo": REPO, "slug": SLUG, "first_year": FIRST_YEAR, "last_year": LAST_YEAR}}
pc = lambda a, b: round(100 * a / b, 1)

sconce = [f for f in M if f["kind"] == "catalogue" and ("Q91203" in f["classes"] or "Q6653030" in f["classes"])]
R["counts"] = {"records": len(F), "main": len(M), "outlines": sum(f["outline"] for f in M), "catalogue": sum(f["kind"] == "catalogue" for f in M),
               "hand_added": sum(f["kind"] == "hand_added" for f in M), "bavarian": sum(f["kind"] == "bavarian_listed" for f in F),
               "lookalike": sum(f["kind"] == "lookalike" for f in F), "lookalike_outlines": sum(f["kind"] == "lookalike" and f["outline"] for f in F),
               "outline_in": C["outline_in"], "catalogue_in": C["catalogue_in"], "merged": C["merged"], "osm_matched": C["osm_matched"],
               "sconce_catalogue": len(sconce), "countries": len({f["iso"] for f in M if f["iso"]}),
               "named": sum(1 for f in M if not f["named_from"].startswith("nearest")),
               "unnamed_outlines": sum(1 for f in M if f["named_from"].startswith("nearest")),
               "wikidata_ids": sum(1 for f in M if f["qid"])}
R["counts"]["outline_pct"] = pc(R["counts"]["outlines"], len(M))
R["counts"]["europe"] = sum(1 for f in M if f["region"] in EUROPE)
R["counts"]["europe_pct"] = pc(R["counts"]["europe"], len(M))
R["counts"]["beyond_europe"] = len(M) - R["counts"]["europe"]
assert R["counts"]["outline_in"] == 1022 and R["counts"]["records"] == len(F)

src = collections.Counter(f["year_src"] for f in DT)
R["dates"] = {"dated": len(DT), "dated_pct": pc(len(DT), len(M)), "hand": src["Wikipedia"], "hand_rows": len(D["hand"]),
              "wikidata": src["Wikidata inception"] + src["Wikidata start time"] + src["Wikidata opening"], "osm": src["OpenStreetMap start_date"],
              "nonhand": len(DT) - src["Wikipedia"], "nonhand_pct": pc(len(DT) - src["Wikipedia"], len(M)),
              "medieval_only": sum(1 for f in M if f["medieval"]),
              "outline_dated": sum(1 for f in DT if f["outline"]), "outline_dated_pct": pc(sum(1 for f in DT if f["outline"]), R["counts"]["outlines"]),
              "median_year": int(statistics.median(f["year"] for f in DT)),
              "before_1600": sum(f["year"] < 1600 for f in DT), "y1600_1699": sum(1600 <= f["year"] < 1700 for f in DT),
              "y1700_1799": sum(1700 <= f["year"] < 1800 for f in DT), "from_1800": sum(f["year"] >= 1800 for f in DT)}
for k in ("before_1600", "y1600_1699", "y1700_1799", "from_1800"):
    R["dates"][k + "_pct"] = pc(R["dates"][k], len(DT))
assert R["dates"]["hand"] == len(D["hand"])
R["dates"]["first"] = min(DT, key=lambda f: f["year"])["year"]

# ---------------------------------------------------------------- decades
dec = []
for d0 in range(1480, 1950, 10):
    xs = [f for f in DT if d0 <= f["year"] < d0 + 10]
    row = {"decade": d0, "n": len(xs), "europe": sum(f["region"] in EUROPE for f in xs)}
    row["beyond"] = row["n"] - row["europe"]
    dec.append(row)
assert sum(r["n"] for r in dec) == sum(1 for f in DT if 1480 <= f["year"] < 1950)
R["decades"] = dec
with open(f"{DATA}/decades.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["decade", "n", "europe", "beyond"]); w.writeheader(); w.writerows(dec)

# ---------------------------------------------------------------- regions and countries
FLO = (43.7696, 11.2558)     # Florence: the early bastion works of Sangallo and Michelangelo
regs = []
for r in RNAMES:
    xs = [f for f in M if f["region"] == r]; ds = sorted([f for f in xs if f["year"]], key=lambda f: (f["year"], f["name"]))
    o = [f["area_ha"] for f in xs if f["outline"]]
    regs.append({"region": r, "n": len(xs), "outlines": sum(f["outline"] for f in xs), "dated": len(ds),
                 "dated_pct": pc(len(ds), len(xs)) if xs else 0,
                 "first_year": ds[0]["year"] if ds else None, "first_name": ds[0]["name"] if ds else "", "first_src": ds[0]["year_src"] if ds else "",
                 "first_country": ds[0]["country"] if ds else "",
                 "median_year": int(statistics.median(f["year"] for f in ds)) if ds else None,
                 "median_area_ha": round(statistics.median(o), 2) if o else None})
R["regions"] = regs
with open(f"{DATA}/regions.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(regs[0])); w.writeheader(); w.writerows(regs)
assert sum(r["n"] for r in regs) == len(M), "every main fort has a region"

cty = []
for iso in sorted({f["iso"] for f in M if f["iso"]}):
    xs = [f for f in M if f["iso"] == iso]; ds = sorted([f for f in xs if f["year"]], key=lambda f: (f["year"], f["name"]))
    first = ds[0] if ds else None
    cty.append({"iso": iso, "country": xs[0]["country"], "region": xs[0]["region"], "n": len(xs), "outlines": sum(f["outline"] for f in xs),
                "dated": len(ds), "first_year": first["year"] if first else None, "first_name": first["name"] if first else "",
                "first_src": first["year_src"] if first else "", "first_id": first["id"] if first else "",
                "km_from_florence": round(km(FLO[0], FLO[1], first["lat"], first["lon"])) if first else None})
cty.sort(key=lambda c: -c["n"])
with open(f"{DATA}/countries.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(cty[0])); w.writeheader(); w.writerows(cty)
R["countries_top"] = [{k: c[k] for k in ("iso", "country", "n", "outlines", "dated")} for c in cty[:12]]
fc = sorted([c for c in cty if c["first_year"]], key=lambda c: (c["first_year"], c["country"]))
R["first_by_country"] = [{k: c[k] for k in ("iso", "country", "region", "first_year", "first_name", "first_src", "km_from_florence")} for c in fc]
R["n_countries_dated"] = len(fc)
R["n_countries_undated"] = len(cty) - len(fc)
# diffusion: is a country's first dated fort later the further it lies from Florence?
dist = np.array([c["km_from_florence"] for c in fc]); yr = np.array([c["first_year"] for c in fc])
rho, p = stats.spearmanr(dist, yr)
lr = stats.linregress(yr, dist)
eu = [c for c in fc if c["region"] in EUROPE]
rho_e, p_e = stats.spearmanr([c["km_from_florence"] for c in eu], [c["first_year"] for c in eu])
R["diffusion"] = {"n": len(fc), "rho": round(float(rho), 2), "p": float(p), "km_per_year": round(float(lr.slope), 1),
                  "n_europe": len(eu), "rho_europe": round(float(rho_e), 2), "p_europe": float(p_e),
                  "median_first_europe": int(statistics.median(c["first_year"] for c in eu)),
                  "median_first_beyond": int(statistics.median(c["first_year"] for c in fc if c["region"] not in EUROPE))}

# ---------------------------------------------------------------- the colonial chain (hand-dated forts beyond Europe)
hand = {h["name"]: h for h in D["hand"]}
over = sorted([f for f in H if f["region"] not in EUROPE], key=lambda f: f["year"])
chain = collections.OrderedDict()
for f in over:
    b = f["builder"]
    chain.setdefault(b, []).append({"name": f["name"], "year": f["year"], "country": f["country"], "region": f["region"], "id": f["id"]})
R["colonial"] = [{"builder": b, "n": len(xs), "first_year": xs[0]["year"], "first_name": xs[0]["name"], "first_country": xs[0]["country"],
                  "forts": xs} for b, xs in chain.items()]
R["colonial_n"] = len(over)
R["colonial_span"] = [over[0]["year"], over[-1]["year"]]
HB = collections.Counter(f["builder"] for f in H)
R["hand_builders"] = dict(HB.most_common())

# ---------------------------------------------------------------- sizes from the outlines
O = [f for f in M if f["outline"]]
A = np.array([f["area_ha"] for f in O]); P_ = np.array([f["points"] for f in O]); Dm = np.array([f["diameter_m"] for f in O])
pts = collections.Counter(int(x) for x in P_)
R["sizes"] = {"n": len(O), "median_ha": round(float(np.median(A)), 2), "q1_ha": round(float(np.percentile(A, 25)), 2),
              "q3_ha": round(float(np.percentile(A, 75)), 2), "p90_ha": round(float(np.percentile(A, 90)), 1),
              "under_2ha_pct": pc(int((A < 2).sum()), len(A)), "over_10ha": int((A >= 10).sum()), "over_50ha": int((A >= 50).sum()),
              "median_diameter_m": int(np.median(Dm)), "median_points": int(np.median(P_)),
              "points_mode": pts.most_common(1)[0][0], "points_mode_n": pts.most_common(1)[0][1],
              "points_mode_pct": pc(pts.most_common(1)[0][1], len(O)),
              "points_4_6_pct": pc(sum(pts[k] for k in (4, 5, 6)), len(O)),
              "points_counts": {str(k): pts[k] for k in sorted(pts)}}
big = sorted(O, key=lambda f: -f["area_ha"])[:12]
R["largest"] = [{"id": f["id"], "name": f["name"], "country": f["country"], "area_ha": f["area_ha"], "points": f["points"], "year": f["year"]} for f in big]
ages = []
for a0, a1, lab in ((1450, 1600, "before 1600"), (1600, 1700, "1600s"), (1700, 1800, "1700s"), (1800, 1950, "1800 and after")):
    xs = [f["area_ha"] for f in O if f["year"] and a0 <= f["year"] < a1]
    ages.append({"period": lab, "n": len(xs), "median_ha": round(statistics.median(xs), 2) if xs else None})
R["size_by_period"] = ages
od = [f for f in O if f["year"]]
rs, ps = stats.spearmanr([f["year"] for f in od], [f["area_ha"] for f in od])
R["size_year"] = {"n": len(od), "rho": round(float(rs), 2), "p": float(ps)}

# ---------------------------------------------------------------- the great fortress towns
FAMOUS = ["Palmanova", "Naarden", "Bourtange", "Neuf-Brisach", "Valletta", "Elvas", "Goryōkaku"]
STRIP = ["Palmanova", "Naarden", "Neuf-Brisach", "Alba Carolina Fortress", "Elvas", "Willemstad", "Almeida", "Citadel of Lille", "Citadel of Jaca",
         "Goryōkaku", "Fort McHenry", "Castillo de San Marcos"]
byname = {f["name"]: f for f in M if f["year_src"] == "Wikipedia"}
fam = []
for n in dict.fromkeys(FAMOUS + STRIP):
    f = byname[n]
    assert f["outline"], n
    fam.append({"id": f["id"], "name": n, "country": f["country"], "year": f["year"], "builder": f["builder"], "area_ha": f["area_ha"],
                "points": f["points"], "diameter_m": f["diameter_m"], "perimeter_m": f["perimeter_m"], "wikipedia": f["wikipedia"]})
R["famous"] = [x for x in fam if x["name"] in FAMOUS]
R["strip"] = [next(x for x in fam if x["name"] == n) for n in STRIP]
with open(f"{DATA}/famous.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(fam[0])); w.writeheader(); w.writerows(fam)
R["famous_rank"] = {x["name"]: 1 + sum(1 for f in O if f["area_ha"] > x["area_ha"]) for x in fam}

# ---------------------------------------------------------------- survival
vh = [f for f in H if f["status"] == "vanished"]
R["survival"] = {"outline_main": R["counts"]["outlines"], "outline_pct": R["counts"]["outline_pct"],
                 "no_outline": len(M) - R["counts"]["outlines"], "no_outline_pct": pc(len(M) - R["counts"]["outlines"], len(M)),
                 "hand_n": len(H), "hand_with_outline": sum(f["outline"] for f in H), "hand_with_outline_pct": pc(sum(f["outline"] for f in H), len(H)),
                 "hand_vanished": len(vh), "hand_vanished_names": [f["name"] for f in vh],
                 "hand_vanished_outline": [f["name"] for f in vh if f["outline"]],
                 "wd_end": sum(1 for f in M if f["wd_end"]),
                 "europe_outline_pct": pc(sum(f["outline"] for f in M if f["region"] in EUROPE), sum(f["region"] in EUROPE for f in M)),
                 "beyond_outline_pct": pc(sum(f["outline"] for f in M if f["region"] not in EUROPE), sum(f["region"] not in EUROPE for f in M))}

# ---------------------------------------------------------------- density
land = jload(f"{GEO}/ne_10m_admin_0_countries.geojson")["features"]
area_km2 = {}
from pyproj import Geod
geod = Geod(ellps="WGS84")
for c in land:
    p = c["properties"]; iso = p["ADM0_A3"]
    iso = {"SDS": "SSD", "SAH": "ESH", "PSX": "PSE"}.get(iso, iso)
    g = shape(c["geometry"])
    area_km2[iso] = area_km2.get(iso, 0) + abs(geod.geometry_area_perimeter(g)[0]) / 1e6
dens = []
for c in cty:
    if c["iso"] in area_km2 and c["n"] >= 8:
        dens.append({"iso": c["iso"], "country": c["country"], "n": c["n"], "per_10k_km2": round(c["n"] / area_km2[c["iso"]] * 1e4, 2)})
dens.sort(key=lambda d: -d["per_10k_km2"])
R["density"] = dens[:10]
cell = collections.Counter((math.floor(f["lon"]), math.floor(f["lat"])) for f in M)
(cx, cy), cn = cell.most_common(1)[0]
cellf = [f for f in M if (math.floor(f["lon"]), math.floor(f["lat"])) == (cx, cy)]
R["densest_cell"] = {"lon": cx, "lat": cy, "n": cn, "country": collections.Counter(f["country"] for f in cellf).most_common(1)[0][0]}
R["sweden"] = {"n": next(c["n"] for c in cty if c["iso"] == "SWE"), "catalogue": sum(1 for f in M if f["iso"] == "SWE" and f["kind"] == "catalogue")}
R["europe_cells"] = sum(1 for (x, y), n in cell.items() if n >= 1)

# ---------------------------------------------------------------- page data
KIND = {"outline": "o", "catalogue": "c", "hand_added": "h", "bavarian_listed": "b", "lookalike": "l"}
SRC = {"Wikipedia": "p", "Wikidata inception": "i", "Wikidata start time": "s", "Wikidata opening": "s", "OpenStreetMap start_date": "m", None: ""}
pts_out = []
for f in F:
    pr = {"id": f["id"], "n": f["name"], "k": KIND[f["kind"]], "c": f["country"], "r": RNAMES.index(f["region"]) if f["region"] in RNAMES else -1}
    if f["year"]: pr["y"] = f["year"]; pr["s"] = SRC[f["year_src"]]
    if f["outline"]: pr.update({"a": f["area_ha"], "p": f["points"]})
    if f["qid"]: pr["q"] = f["qid"]
    if f["wikipedia"]: pr["w"] = f["wikipedia"].replace("https://en.wikipedia.org/wiki/", "")
    if f["builder"]: pr["b"] = f["builder"]
    if f["status"] == "vanished": pr["v"] = 1
    if f["note"]: pr["t"] = f["note"]
    if f["medieval"]: pr["md"] = f["wd_inception"] if f["wd_inception"] is not None else ""
    if f.get("osm"): pr["o"] = f["osm"]
    if f["named_from"].startswith("nearest"): pr["u"] = 1
    pts_out.append({"type": "Feature", "properties": pr, "geometry": {"type": "Point", "coordinates": [round(f["lon"], 5), round(f["lat"], 5)]}})
jsave({"type": "FeatureCollection", "features": pts_out}, f"{DATA}/forts_points.geojson")
# search index: named forts and countries
idx = [[f["name"], round(f["lon"], 4), round(f["lat"], 4), f["id"], f["country"]] for f in F if not f["named_from"].startswith("nearest") and f["kind"] != "bavarian_listed"]
jsave(idx, f"{DATA}/search.json")
jsave(R, f"{DATA}/results.json", indent=1)
print(json.dumps({k: R[k] for k in ("counts", "dates", "diffusion", "sizes", "survival")}, ensure_ascii=False, indent=0)[:3500])
print([(r["region"], r["n"], r["dated"], r["first_year"], r["first_name"]) for r in regs])
print([(c["country"], c["first_year"], c["first_name"]) for c in fc[:20]])
print([(c["builder"], c["n"], c["first_year"], c["first_name"]) for c in R["colonial"]])
print(R["density"][:6], R["densest_cell"], R["size_by_period"], R["size_year"])
