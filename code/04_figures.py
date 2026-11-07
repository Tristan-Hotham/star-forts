"""Step 4: figures for the page (img/), the blog (release/blog/b_*.png, 1800 px wide), the paper (release/paper/f_*.png)
and the social card (header.png). Reads data/ only."""
import csv, collections
from PIL import Image
from shapely.geometry import shape, Point
from figstyle import *

R = jload(f"{DATA}/results.json")
F = list(csv.DictReader(open(f"{DATA}/forts.csv", encoding="utf-8")))
for f in F:
    f["lon"], f["lat"] = float(f["lon"]), float(f["lat"])
    f["year"] = int(f["year"]) if f["year"] else None
    f["main"] = f["main"] == "True"; f["outline"] = f["outline"] == "True"
M = [f for f in F if f["main"]]
OL = {x["properties"]["id"]: shape(x["geometry"]) for x in jload(f"{DATA}/forts_outlines.geojson")["features"]}
IMG = os.path.join(ROOT, "img"); BL = os.path.join(ROOT, "release", "blog"); PA = os.path.join(ROOT, "release", "paper")
for d in (IMG, BL, PA): os.makedirs(d, exist_ok=True)


def out(fig, name, alt_jpg=True):
    """one figure, three copies: blog png 1800 px wide, paper png, page jpg 1200 px"""
    w_in = fig.get_figwidth()
    fig.savefig(f"{BL}/b_{name}.png", dpi=1800 / w_in, facecolor=fig.get_facecolor())
    plt.close(fig)
    im = Image.open(f"{BL}/b_{name}.png").convert("RGB")
    assert im.size[0] == 1800, im.size
    im.save(f"{PA}/f_{name}.png")
    if alt_jpg:
        j = im.copy(); j.thumbnail((1200, 3000)); j.save(f"{IMG}/{name}.jpg", quality=84)


def title(fig, t, sub=None, y=0.955):
    fig.text(0.03, y, t, fontproperties=HAND, fontsize=24, color=RED)
    if sub: fig.text(0.03, y - 0.045, sub, fontproperties=FELLIT, fontsize=13.5, color=INKC)


def credit(fig, s, y=0.015):
    fig.text(0.03, y, s, fontproperties=FELLIT, fontsize=9.5, color=MUT)


# ---------------------------------------------------------------- 1. the belt: Europe and the Mediterranean
def belt(ax, ms=26):
    ext, f = ink_base(ax, 3035, (-12, 36, 33.5, 62.5), ripple_m=(7e3, 17e3, 30e3))
    o = [x for x in M if x["outline"]]; c = [x for x in M if not x["outline"]]
    for grp, col, z in ((c, SEPIA, 5), (o, INKC, 6)):
        x, y = f(np.array([g["lon"] for g in grp]), np.array([g["lat"] for g in grp]))
        ax.scatter(x, y, s=ms, marker=STAR, fc=PAPER2 if col == INKC else "#E6D2AC", ec=col, lw=0.7, zorder=z)
    return ext, f


fig = plt.figure(figsize=(9, 7.6)); parchment(fig)
ax = fig.add_axes([0.02, 0.06, 0.96, 0.82])
ext, f = belt(ax)
title(fig, "The star fort belt", f"{R['counts']['europe']:,} of the {R['counts']['main']:,} star forts lie in Europe")
ax.scatter([], [], s=60, marker=STAR, fc=PAPER2, ec=INKC, lw=0.8, label="Outline traced in OpenStreetMap")
ax.scatter([], [], s=60, marker=STAR, fc="#E6D2AC", ec=SEPIA, lw=0.8, label="Point only (Wikidata or Wikipedia)")
lg = ax.legend(loc="lower left", frameon=True, prop=FELL, fontsize=11); lg.get_frame().set_facecolor(PAPER); lg.get_frame().set_edgecolor(INKC)
for t in lg.get_texts(): t.set_fontproperties(FELL); t.set_fontsize(11)
for nm, lon, lat, dx, dy in (("North Sea", 3.2, 56.3, 0, 0), ("Baltic Sea", 18.6, 56.4, 0, 0), ("Mediterranean Sea", 18.0, 34.6, 0, 0), ("Atlantic Ocean", -10.0, 46.5, 0, 0)):
    x, y = f(lon, lat); ax.text(x, y, nm.upper(), fontproperties=FELLIT, fontsize=11, color=BLUE, ha="center", zorder=8)
credit(fig, "Data: OpenStreetMap contributors (ODbL), Wikidata (CC0), English Wikipedia, Natural Earth. Look-alikes and Bavarian listed earthworks left out. maps.tristanhotham.com/star-forts")
out(fig, "belt")

# ---------------------------------------------------------------- 2. decades
dec = R["decades"]
dec = [d for d in dec if d["decade"] <= 1910]
fig = plt.figure(figsize=(9, 4.8)); parchment(fig)
ax = fig.add_axes([0.08, 0.14, 0.89, 0.62])
x = np.array([d["decade"] for d in dec]); e = np.array([d["europe"] for d in dec]); b = np.array([d["beyond"] for d in dec])
ax.bar(x + 5, e, width=8.4, color="#5A4A3A", ec=INKC, lw=0.6, label="In Europe")
ax.bar(x + 5, b, width=8.4, bottom=e, color=RED, ec=INKC, lw=0.6, label="Beyond Europe")
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.set_xlim(1478, 1922); ax.set_ylabel("dated forts begun", fontproperties=FELL, fontsize=13)
for t in ax.get_xticklabels() + ax.get_yticklabels(): t.set_fontproperties(FELL); t.set_fontsize(12)
lg = ax.legend(frameon=False, loc="upper left")
for t in lg.get_texts(): t.set_fontproperties(FELL); t.set_fontsize(12)
for d0, lab in ((1590, "Palmanova, Bourtange,\nFort Jesus"), (1670, "Vauban's France,\nNaarden"), (1750, "colonial wars"), (1870, "polygonal forts")):
    k = [d["decade"] for d in dec].index(d0)
    ax.annotate(lab, (d0 + 5, e[k] + b[k]), xytext=(0, 14), textcoords="offset points", ha="center", fontproperties=FELLIT, fontsize=11, color=INKC)
ax.set_ylim(0, max(e + b) * 1.45)
title(fig, "When the dated forts were begun", f"{R['dates']['dated']:,} of {R['counts']['main']:,} forts ({R['dates']['dated_pct']:.0f}%) have a date; {R['dates']['hand']} of them dated by hand from Wikipedia", y=0.93)
credit(fig, "Dates: English Wikipedia (by hand), Wikidata, OpenStreetMap start_date. Decades of first construction of the bastioned works.")
out(fig, "decades")

# ---------------------------------------------------------------- 3. the colonial chain
col = R["colonial"]
BCOL = {"Portugal": "#2E7F86", "Spain": RED, "Dutch Republic": "#D08A1E", "England": "#7B4B94", "Great Britain": "#7B4B94", "France": BLUE,
        "Denmark-Norway": "#4E7A3A", "United States": "#5A4A3A", "Japan": INKC}
allc = sorted([dict(x, builder=c["builder"]) for c in col for x in c["forts"]], key=lambda x: (x["year"], x["name"]))
fig = plt.figure(figsize=(9, 9.6)); parchment(fig)
ax = fig.add_axes([0.04, 0.07, 0.93, 0.8])
n = len(allc)
for i, x_ in enumerate(allc):
    yy = n - 1 - i
    ax.plot([1530, x_["year"]], [yy, yy], color=INKC, lw=0.35, alpha=0.35, ls=(0, (1, 3)))
    ax.scatter([x_["year"]], [yy], s=95, marker=STAR, fc=BCOL.get(x_["builder"], MUT), ec=INKC, lw=0.6, zorder=5)
    ax.text(x_["year"] + 4, yy, f"{x_['name']}, {x_['country'].replace('United States of America', 'USA')}  {x_['year']}", va="center", ha="left",
            fontproperties=FELL, fontsize=9.6, color=INKC)
ax.set_xlim(1530, 1960); ax.set_ylim(-1, n)
ax.set_yticks([])
for s_ in ("top", "right", "left"): ax.spines[s_].set_visible(False)
for t in ax.get_xticklabels(): t.set_fontproperties(FELL); t.set_fontsize(11)
from matplotlib.lines import Line2D
hs = [Line2D([], [], marker=STAR, ls="none", ms=10, mfc=c, mec=INKC, label=b) for b, c in BCOL.items() if b in {x["builder"] for x in allc} and b != "England"]
hs = [h if h.get_label() != "Great Britain" else Line2D([], [], marker=STAR, ls="none", ms=10, mfc=BCOL["England"], mec=INKC, label="England and Britain") for h in hs]
lg = ax.legend(handles=hs, loc="upper right", frameon=True, title="builder")
lg.get_frame().set_facecolor(PAPER); lg.get_frame().set_edgecolor(INKC)
for t in lg.get_texts(): t.set_fontproperties(FELL); t.set_fontsize(10.5)
lg.get_title().set_fontproperties(FELLSC); lg.get_title().set_fontsize(11)
title(fig, "The colonial chain", f"{R['colonial_n']} hand-dated star forts outside Europe, from Diu ({R['colonial_span'][0]}) to Hakodate ({R['colonial_span'][1]})", y=0.95)
credit(fig, "Dates and builders from English Wikipedia, one article per fort. A selection of famous forts, not a census.")
out(fig, "chain")

# ---------------------------------------------------------------- 4. twelve outlines at one scale
def local(g):
    c = g.centroid; k = 111320 * np.cos(np.radians(c.y))
    return stransform(lambda x, y, z=None: ((np.asarray(x) - c.x) * k, (np.asarray(y) - c.y) * 110574), g)


def draw_outline(ax, g, cx, cy, s=1.0, moat=True):
    g = local(g)
    from shapely import affinity
    g = affinity.translate(affinity.scale(g, s, s, origin=(0, 0)), cx, cy)
    if moat:
        patches(ax, g.buffer(28 * s, join_style=2, mitre_limit=4).difference(g), fc="#B9CFE0", ec="none", zorder=2)
        lines(ax, g.buffer(28 * s, join_style=2, mitre_limit=4), color=BLUE, lw=0.6, zorder=3)
    patches(ax, g, fc="#E3CF9E", ec="none", zorder=3)
    patches(ax, g.buffer(-14 * s, join_style=2, mitre_limit=4), fc=PAPER, ec="none", zorder=4)
    lines(ax, g, color=INKC, lw=1.3, zorder=5)
    return g


strip = R["strip"]


def strip_axes(ax, ncol=6, cell=1700, label_size=11, sub_size=9.5):
    ax.set_facecolor("none")
    for i, s in enumerate(strip):
        r, c = divmod(i, ncol)
        cx, cy = c * cell, -r * cell * 1.12
        g = OL[s["id"]]; ct = g.centroid
        draw_detail(ax, s["id"], (ct.x, ct.y), cx, cy, clip=g.buffer(0.0014))
        nm = s["name"].replace("Castillo de San Marcos", "San Marcos").replace("Citadel of Lille", "Lille citadel").replace("Citadel of Jaca", "Jaca citadel").replace("Alba Carolina Fortress", "Alba Carolina")
        ax.text(cx, cy - cell * 0.45, nm, ha="center", va="top", fontproperties=FELLSC, fontsize=label_size, color=RED)
        ax.text(cx, cy - cell * 0.58, f"{s['year']} · {s['area_ha']:.1f} ha", ha="center", va="top", fontproperties=FELLIT, fontsize=sub_size, color=INKC)
    nrow = (len(strip) + ncol - 1) // ncol
    ax.set_xlim(-cell * 0.55, (ncol - 0.45) * cell); ax.set_ylim(-(nrow - 1) * cell * 1.12 - cell * 0.78, cell * 0.55)
    ax.set_aspect("equal"); ax.axis("off")
    # scale bar: 500 m
    x0, y0 = -cell * 0.45, cell * 0.45
    ax.plot([x0, x0 + 500], [y0, y0], color=INKC, lw=2); ax.plot([x0, x0], [y0 - 40, y0 + 40], color=INKC, lw=1); ax.plot([x0 + 500, x0 + 500], [y0 - 40, y0 + 40], color=INKC, lw=1)
    ax.text(x0 + 250, y0 + 70, "500 m", ha="center", fontproperties=FELL, fontsize=10, color=INKC)


fig = plt.figure(figsize=(9, 4.9)); parchment(fig)
ax = fig.add_axes([0.01, 0.05, 0.98, 0.78])
strip_axes(ax)
title(fig, "Twelve star forts at one scale", "walls, ramparts and moats as mapped in OpenStreetMap, with the year begun and the area inside the outline", y=0.93)
credit(fig, "Walls, ramparts and moats © OpenStreetMap contributors (ODbL), drawn at full detail; dates from English Wikipedia.")
out(fig, "strip")

# ---------------------------------------------------------------- 5. the world by the decade of its first dated fort
first = {c["iso"]: c for c in R["first_by_country"]}
have = {c["iso"] for c in csv.DictReader(open(f"{DATA}/countries.csv", encoding="utf-8"))}
ISOFIX = {"CYN": "CYP", "SDS": "SSD", "PSX": "PSE", "SAH": "ESH"}


def cfc(iso):
    iso = ISOFIX.get(iso, iso)
    if iso in first: return period_col(first[iso]["first_year"])
    if iso in have: return "#DCCFB0"
    return None


def world_first(ax, ms=7, ripple=(60e3, 150e3)):
    ext, f = ink_base(ax, 8857, (-160, 152, -42, 70), ripple_m=ripple, country_fc=cfc, coast_lw=0.6, min_area=2e8)
    x, y = f(np.array([g["lon"] for g in M]), np.array([g["lat"] for g in M]))
    ax.scatter(x, y, s=ms, marker=STAR, fc=INKC, ec="none", zorder=7, alpha=0.75)
    return ext, f


fig = plt.figure(figsize=(9, 5.6)); parchment(fig)
ax = fig.add_axes([0.01, 0.1, 0.98, 0.76])
ext, f = world_first(ax)
from matplotlib.patches import Patch
hs = [Patch(fc=c, ec=INKC, lw=0.4, label=lab) for a, b_, lab, c in PERIODS] + [Patch(fc="#DCCFB0", ec=INKC, lw=0.4, label="forts, none dated")]
lg = ax.legend(handles=hs, loc="lower left", frameon=True, ncol=1, title="first dated fort")
lg.get_frame().set_facecolor(PAPER); lg.get_frame().set_edgecolor(INKC)
for t in lg.get_texts(): t.set_fontproperties(FELL); t.set_fontsize(10)
lg.get_title().set_fontproperties(FELLSC); lg.get_title().set_fontsize(11)
title(fig, "Where the bastion arrived, and when", f"each country shaded by its first dated star fort in the data ({R['n_countries_dated']} countries); black stars: all {R['counts']['main']:,} forts", y=0.94)
credit(fig, "Earliest date in this data, not the first fort ever built. Natural Earth borders of today.")
out(fig, "first")

# ---------------------------------------------------------------- 6. sizes and points
O = [f_ for f_ in M if f_["outline"]]
A = np.array([float(f_["area_ha"]) for f_ in O]); P_ = R["sizes"]["points_counts"]
fig = plt.figure(figsize=(9, 4.6)); parchment(fig)
a1 = fig.add_axes([0.08, 0.16, 0.5, 0.6]); a2 = fig.add_axes([0.66, 0.16, 0.31, 0.6])
bins = np.logspace(np.log10(0.1), np.log10(300), 30)
a1.hist(A, bins=bins, color="#5A4A3A", ec=INKC, lw=0.5); a1.set_xscale("log")
a1.axvline(R["sizes"]["median_ha"], color=RED, lw=1.4)
ytop = a1.get_ylim()[1]
a1.text(R["sizes"]["median_ha"] * 1.12, ytop * 0.95, f"median {R['sizes']['median_ha']:.1f} ha", color=RED, fontproperties=FELLIT, fontsize=12, va="top")
pal = next(x for x in R["strip"] if x["name"] == "Palmanova"); mch = next(x for x in R["strip"] if x["name"] == "Fort McHenry")
a1.annotate("Palmanova and Naarden", (pal["area_ha"], 1.5), xytext=(pal["area_ha"] * 0.9, ytop * 0.55), ha="right", fontproperties=FELLIT, fontsize=10.5,
            arrowprops=dict(arrowstyle="-", color=INKC, lw=0.6))
a1.annotate("Fort McHenry", (mch["area_ha"], ytop * 0.35), xytext=(0.12, ytop * 0.75), ha="left", fontproperties=FELLIT, fontsize=10.5,
            arrowprops=dict(arrowstyle="-", color=INKC, lw=0.6))
a1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:g}"))
a1.set_xlabel("area inside the outline (hectares, log scale)", fontproperties=FELL, fontsize=12); a1.set_ylabel("forts", fontproperties=FELL, fontsize=12)
ks = [k for k in sorted(P_, key=int) if int(k) <= 12]
a2.bar([int(k) for k in ks], [P_[k] for k in ks], color=[RED if int(k) == R["sizes"]["points_mode"] else "#5A4A3A" for k in ks], ec=INKC, lw=0.5)
a2.set_xlabel("salient points (bastions)", fontproperties=FELL, fontsize=12); a2.set_xticks(range(2, 13, 2))
for a in (a1, a2):
    for s in ("top", "right"): a.spines[s].set_visible(False)
    for t in a.get_xticklabels() + a.get_yticklabels(): t.set_fontproperties(FELL); t.set_fontsize(11)
title(fig, "Mostly small, mostly four or five points", f"{R['sizes']['n']:,} outlines traced in OpenStreetMap", y=0.93)
credit(fig, "Area: inside the outline found by the shape test (sometimes the rampart, sometimes the moat). Points: sharp salient corners.")
out(fig, "sizes")

# ---------------------------------------------------------------- 7. distance from Florence against the first date
fc = R["first_by_country"]
fig = plt.figure(figsize=(9, 5.4)); parchment(fig)
ax = fig.add_axes([0.1, 0.13, 0.86, 0.66])
eu = [c for c in fc if c["region"] in EUROPE]; nb = [c for c in fc if c["region"] not in EUROPE]
ax.scatter([c["first_year"] for c in eu], [c["km_from_florence"] for c in eu], s=110, marker=STAR, fc="#5A4A3A", ec=INKC, lw=0.6, label="Europe", zorder=4)
ax.scatter([c["first_year"] for c in nb], [c["km_from_florence"] for c in nb], s=110, marker=STAR, fc=RED, ec=INKC, lw=0.6, label="Beyond Europe", zorder=4)
LAB = {"Italy", "Indonesia", "India", "Puerto Rico", "Morocco", "Mozambique", "Philippines", "Japan",
       "Taiwan", "South Africa", "Kenya", "Russia", "Canada", "Finland", "Peru", "Cuba"}
for c in fc:
    if c["country"] in LAB or c["country"].startswith("Macao"):
        ax.annotate(c["country"].replace("United States of America", "USA").replace("Macao S.A.R", "Macau"), (c["first_year"], c["km_from_florence"]), xytext=(6, 4),
                    textcoords="offset points", fontproperties=FELLIT, fontsize=10, color=INKC)
ax.set_xlabel("year of the country's first dated star fort", fontproperties=FELL, fontsize=12)
ax.set_ylabel("km from Florence", fontproperties=FELL, fontsize=12)
for s in ("top", "right"): ax.spines[s].set_visible(False)
for t in ax.get_xticklabels() + ax.get_yticklabels(): t.set_fontproperties(FELL); t.set_fontsize(11)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
lg = ax.legend(frameon=False, loc="center right")
for t in lg.get_texts(): t.set_fontproperties(FELL); t.set_fontsize(12)
title(fig, "It went by sea", f"distance hardly predicts the date: rank correlation {R['diffusion']['rho']} across {R['diffusion']['n']} countries", y=0.94)
credit(fig, "Each star: the first dated fort of one country in this data. Great-circle distance from Florence.")
out(fig, "distance")

# ---------------------------------------------------------------- header card, 1200 x 630
fig = plt.figure(figsize=(12, 6.3)); parchment(fig, seed=7)
fig.text(0.04, 0.82, "The star fort", fontproperties=HAND, fontsize=54, color=INKC)
fig.text(0.04, 0.70, "belt", fontproperties=HAND, fontsize=54, color=RED)
fig.text(0.04, 0.585, "How the bastion spread\naround the world, 1500 to 1900", fontproperties=FELLIT, fontsize=18, color=INKC, va="bottom", linespacing=1.1)
fig.text(0.04, 0.47, f"{R['counts']['main']:,}", fontproperties=HAND, fontsize=40, color=RED)
fig.text(0.04, 0.415, "star forts on one ink map", fontproperties=FELL, fontsize=15, color=INKC)
fig.text(0.04, 0.31, f"{R['colonial_span'][0]} to {R['colonial_span'][1]}", fontproperties=HAND, fontsize=40, color=RED)
fig.text(0.04, 0.255, "from Diu in India to Hakodate in Japan", fontproperties=FELL, fontsize=15, color=INKC)
fig.text(0.04, 0.06, "Dr Tristan Hotham · maps.tristanhotham.com/star-forts", fontproperties=FELLIT, fontsize=12, color=MUT)
ax = fig.add_axes([0.47, 0.33, 0.52, 0.64]); world_first(ax, ms=4, ripple=(80e3,)); ax.patch.set_alpha(0)
ax2 = fig.add_axes([0.45, 0.02, 0.53, 0.27])
sub = [s for s in R["strip"] if s["name"] in ("Palmanova", "Naarden", "Neuf-Brisach", "Alba Carolina Fortress", "Goryōkaku")]
for i, s in enumerate(sub):
    ct = OL[s["id"]].centroid; draw_detail(ax2, s["id"], (ct.x, ct.y), i * 1750, 0, clip=OL[s["id"]].buffer(0.0014))
    ax2.text(i * 1750, -820, s["name"], ha="center", va="top", fontproperties=FELLSC, fontsize=11, color=RED)
ax2.set_xlim(-900, 4 * 1750 + 900); ax2.set_ylim(-1050, 800); ax2.set_aspect("equal"); ax2.axis("off")
fig.savefig(os.path.join(ROOT, "header.png"), dpi=100, facecolor=fig.get_facecolor()); plt.close(fig)
assert Image.open(os.path.join(ROOT, "header.png")).size == (1200, 630)
print("figures:", sorted(os.listdir(BL)), sorted(os.listdir(IMG)))
