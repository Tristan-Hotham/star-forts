"""The Reddit collage (2400 x 3200 px, light parchment): the world shaded by the period of each country's first dated star
fort, the colonial firsts lettered on the open sea, the European belt, twelve outlines at one scale and the key numbers.
Run from the repository root: python3 reddit/collage.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
import csv
from PIL import Image
from matplotlib.patches import Patch
import matplotlib.patheffects as pe
from shapely.geometry import shape
from figstyle import *

R = jload(f"{DATA}/results.json")
F = [f for f in csv.DictReader(open(f"{DATA}/forts.csv", encoding="utf-8")) if f["main"] == "True"]
OL = {x["properties"]["id"]: shape(x["geometry"]) for x in jload(f"{DATA}/forts_outlines.geojson")["features"]}
first = {c["iso"]: c for c in R["first_by_country"]}
have = {c["iso"] for c in csv.DictReader(open(f"{DATA}/countries.csv", encoding="utf-8"))}
H = {h["name"]: h for h in csv.DictReader(open(f"{DATA}/hand_dates.csv", encoding="utf-8"))}
HALO = [pe.withStroke(linewidth=4, foreground=PAPER)]
ISOFIX = {"CYN": "CYP", "SDS": "SSD", "PSX": "PSE", "SAH": "ESH"}


def cfc(iso):
    iso = ISOFIX.get(iso, iso)
    if iso in first: return period_col(first[iso]["first_year"])
    if iso in have: return "#DCCFB0"
    return None


fig = plt.figure(figsize=(12, 16)); parchment(fig, seed=11)
fig.text(0.04, 0.955, "The star fort belt", fontproperties=HAND, fontsize=50, color=RED)
fig.text(0.04, 0.928, "How the bastion spread from Italy round the world: every star fort in OpenStreetMap and",
         fontproperties=FELLIT, fontsize=19, color=INKC)
fig.text(0.04, 0.912, "Wikidata, each country shaded by its first dated fort, and the colonial firsts from Wikipedia",
         fontproperties=FELLIT, fontsize=19, color=INKC)

# ---- the world
ax = fig.add_axes([0.01, 0.53, 0.98, 0.37])
ext, f = ink_base(ax, 8857, (-168, 180, -45, 68), ripple_m=(70e3, 170e3), country_fc=cfc, coast_lw=0.7, min_area=2e8)
x, y = f(np.array([float(g["lon"]) for g in F]), np.array([float(g["lat"]) for g in F]))
ax.scatter(x, y, s=10, marker=STAR, fc=INKC, ec="none", zorder=7, alpha=0.8)
# colonial firsts, lettered on the open sea (label position chosen by hand in open water)
LAB = [("Fort Zeelandia", "Taiwan", 128, 24), ("Goryōkaku", "Hakodate", 150, 36), ("Fort Santiago", "Manila", 140, 9), ("Fort St George", "Madras", 88, 14), ("Diu Fort", "Diu", 64, 5), ("Castillo San Felipe del Morro", "San Juan", -50, 20), ("Mazagan", "Mazagan", -29, 25), ("Morro Castle", "Havana", -71, 30), ("Fort Jesus", "Mombasa", 55, -12), ("Fort Belgica", "Banda Neira", 124, -17), ("Castle of Good Hope", "Cape Town", 4, -40), ("Fortress of Louisbourg", "Louisbourg", -38, 49), ("Forte dos Reis Magos", "Natal", -23, -6), ("Fortaleza del Real Felipe", "Callao", -97, -14)]
from shapely.geometry import box as _box
_land = [p for _, g in project_geoms(NE_LAND, 8857, _box(-180, -60, 180, 85)) for p in (g.geoms if hasattr(g, 'geoms') else [g]) if p.area >= 2e8]
from shapely.strtree import STRtree as _T
_lt = _T(_land)
fig.canvas.draw(); _rend = fig.canvas.get_renderer(); _inv = ax.transData.inverted()
_placed = []
_leaders = []
from shapely.geometry import LineString


def _bbox(t):
    bb = t.get_window_extent(_rend); (x0, y0), (x1, y1) = _inv.transform([(bb.x0 - 3, bb.y0 - 3), (bb.x1 + 3, bb.y1 + 3)])
    return _box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _free(b):
    return not any(_land[i].intersects(b) for i in _lt.query(b)) and not any(b.intersects(q) for q in _placed) and \
        ext[0] < b.bounds[0] and b.bounds[2] < ext[1] and ext[2] < b.bounds[1] and b.bounds[3] < ext[3]


# each label starts at a hand-chosen spot in open water and moves, in growing rings, to the nearest spot where both lines
# sit on open sea or paper, clear of land and of every other label
for key, lab, lx, ly in LAB:
    h = H[key]
    px, py = f(float(h["lon"]), float(h["lat"]))
    t1 = ax.text(0, 0, lab, fontproperties=FELLSC, fontsize=14, color=RED, ha="center", va="bottom", zorder=10, path_effects=HALO)
    t2 = ax.text(0, 0, f"{h['year']} · {h['builder'].replace('Dutch Republic', 'Dutch').replace('Great Britain', 'British').replace('England', 'English').replace('United States', 'USA')}",
                 fontproperties=FELLIT, fontsize=11.5, color=INKC, ha="center", va="top", zorder=10, path_effects=HALO)
    done = False
    for r in range(0, 45):
        for a in range(0, 360, 20 if r else 360):
            qx, qy = f(lx + r * np.cos(np.radians(a)), ly + 0.8 * r * np.sin(np.radians(a)))
            if not np.isfinite(qx): continue
            t1.set_position((qx, qy)); t2.set_position((qx, qy))
            b = _bbox(t1).union(_bbox(t2)).envelope
            ld = LineString([(px, py), (qx, b.bounds[3] if qy > py else b.bounds[1]) if False else (qx, qy)])
            # the leader may not cross another label or leader, and the label may not sit on another leader
            if _free(b) and not any(ld.intersects(q) for q in _placed) and not any(b.intersects(l2) or ld.crosses(l2) for l2 in _leaders):
                _placed.append(b); _leaders.append(ld); done = True; break
        if done: break
    assert done, lab
    ax.plot([px, qx], [py, qy], color=INKC, lw=0.7, zorder=8)
    ax.scatter([px], [py], s=70, marker=STAR, fc=RED, ec=INKC, lw=0.6, zorder=9)
for nm, lon, lat in (("ATLANTIC OCEAN", -32, 2), ("INDIAN OCEAN", 78, -24), ("PACIFIC OCEAN", -118, -28)):
    t = ax.text(0, 0, nm, fontproperties=FELLIT, fontsize=15, color=BLUE, ha="center", zorder=6)
    ok = False
    for r in range(0, 45):
        ok = False
        for a in range(0, 360, 30 if r else 360):
            qx, qy = f(lon + r * np.cos(np.radians(a)), lat + 0.8 * r * np.sin(np.radians(a)))
            t.set_position((qx, qy)); b = _bbox(t)
            if _free(b) and not any(b.intersects(l2) for l2 in _leaders): _placed.append(b); ok = True; break
        if ok: break
    if not ok: t.remove()

# check: no lettering on the world map touches land, and no two labels overlap
_bad = [t.get_text() for t in ax.texts if any(_land[i].intersects(_bbox(t)) for i in _lt.query(_bbox(t)))]
print("labels touching land:", _bad)
assert not _bad, _bad

# ---- key for the periods (full names)
lax = fig.add_axes([0.04, 0.455, 0.92, 0.065]); lax.axis("off")
lax.text(0, 0.95, "First dated star fort in each country", fontproperties=FELLSC, fontsize=15, color=INKC, va="top")
items = [(c, lab) for a, b, lab, c in PERIODS] + [("#DCCFB0", "forts, none dated")]
for i, (c, lab) in enumerate(items):
    xx = 0.0 + i * 0.142
    lax.add_patch(plt.Rectangle((xx, 0.12), 0.03, 0.35, fc=c, ec=INKC, lw=0.6, transform=lax.transAxes))
    lax.text(xx + 0.036, 0.29, lab, fontproperties=FELL, fontsize=13, color=INKC, va="center", transform=lax.transAxes)

# ---- Europe: the belt
eax = fig.add_axes([0.02, 0.2, 0.55, 0.255])
ext2, f2 = ink_base(eax, 3035, (-17, 31, 35, 61), ripple_m=(8e3, 20e3), coast_lw=0.7)
o = [g for g in F if g["outline"] == "True"]; c_ = [g for g in F if g["outline"] != "True"]
for grp, col in ((c_, SEPIA), (o, INKC)):
    xx, yy = f2(np.array([float(g["lon"]) for g in grp]), np.array([float(g["lat"]) for g in grp]))
    eax.scatter(xx, yy, s=14, marker=STAR, fc=PAPER2 if col == INKC else "#E6D2AC", ec=col, lw=0.5, zorder=6)
qx, qy = f2(-14, 45.6); eax.text(qx, qy, "THE BELT", fontproperties=FELLSC, fontsize=17, color=RED, ha="center", path_effects=HALO, zorder=9)
qx, qy = f2(-14, 44.6); eax.text(qx, qy, f"{R['counts']['europe']:,} forts in Europe", fontproperties=FELLIT, fontsize=12.5, color=INKC, ha="center", path_effects=HALO, zorder=9)
for nm, lon, lat in (("North Sea", 3.5, 56.2), ("Baltic", 19.3, 56.6), ("Mediterranean", 17.5, 35.6)):
    qx, qy = f2(lon, lat); eax.text(qx, qy, nm, fontproperties=FELLIT, fontsize=12, color=BLUE, ha="center", zorder=9)
eax.scatter([], [], s=60, marker=STAR, fc=PAPER2, ec=INKC, lw=0.7, label="outline traced")
eax.scatter([], [], s=60, marker=STAR, fc="#E6D2AC", ec=SEPIA, lw=0.7, label="point only")
lg = eax.legend(loc="upper left", frameon=True); lg.get_frame().set_facecolor(PAPER); lg.get_frame().set_edgecolor(INKC)
for t in lg.get_texts(): t.set_fontproperties(FELL); t.set_fontsize(12)

# ---- numbers
nx = 0.61
def big(y, num, txt, col=RED):
    fig.text(nx, y, num, fontproperties=HAND, fontsize=34, color=col)
    fig.text(nx, y - 0.008, txt, fontproperties=FELL, fontsize=15, color=INKC, va="top", linespacing=1.15)
big(0.43, f"{R['counts']['main']:,}", f"star forts in {R['counts']['countries']} countries;\n{R['counts']['outlines']:,} with a real outline traced")
big(0.36, f"{R['dates']['dated_pct']:.0f}%", f"can be dated ({R['dates']['dated']:,});\n{R['dates']['hand']} of them by hand from Wikipedia", INKC)
big(0.29, f"{R['colonial_span'][0]} to {R['colonial_span'][1]}", "Portuguese Diu to Japanese Hakodate:\nthe bastion went by sea as fast as by land")
big(0.22, f"{R['sizes']['median_ha']:.1f} ha", f"the median fort, about {R['sizes']['median_diameter_m']} m across;\n{R['sizes']['points_mode_pct']:.0f}% have four points", INKC)

# ---- twelve outlines at one scale
sax = fig.add_axes([0.02, 0.045, 0.96, 0.14])
cell = 1700
fig.text(0.04, 0.183, "Twelve star forts at one scale: walls and moats as mapped", fontproperties=FELLSC, fontsize=16, color=INKC)
for i, s in enumerate(R["strip"]):
    cx = i * cell
    g = OL[s["id"]]; c0 = g.centroid
    draw_detail(sax, s["id"], (c0.x, c0.y), cx, 0, lw=0.9, clip=g.buffer(0.0014))
    nm = s["name"].replace("Castillo de San Marcos", "San Marcos").replace("Citadel of Lille", "Lille").replace("Citadel of Jaca", "Jaca").replace("Alba Carolina Fortress", "Alba Carolina").replace("Fort McHenry", "McHenry")
    sax.text(cx, -980, nm, ha="center", va="top", fontproperties=FELLSC, fontsize=10, color=RED)
    sax.text(cx, -1330, f"{s['year']}", ha="center", va="top", fontproperties=FELLIT, fontsize=11, color=INKC)
sax.plot([-700, -200], [800, 800], color=INKC, lw=2); sax.text(-450, 870, "500 m", ha="center", fontproperties=FELL, fontsize=11, color=INKC)
sax.set_xlim(-850, 11 * cell + 850); sax.set_ylim(-1700, 1050); sax.set_aspect("equal"); sax.axis("off")

fig.text(0.04, 0.012, "Data: OpenStreetMap contributors (ODbL), Wikidata (CC0), English Wikipedia (dates of the labelled forts), Natural Earth. Look-alike outlines and Bavarian listed earthworks left out.",
         fontproperties=FELLIT, fontsize=11, color=MUT)
fig.text(0.04, 0.026, "Dr Tristan Hotham · maps.tristanhotham.com/star-forts", fontproperties=FELLIT, fontsize=13, color=INKC)
OUTP = os.path.join(ROOT, "reddit", "star_fort_belt.png")
fig.savefig(OUTP, dpi=200, facecolor=fig.get_facecolor()); plt.close(fig)
print(Image.open(OUTP).size)
