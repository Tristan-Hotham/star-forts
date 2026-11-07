"""House style for the static figures: the ink look of The Inked World on parchment. Black coasts with blue ripple lines,
red and black lettering in IM Fell and MedievalSharp, pen-drawn star fort marks, Natural Earth outlines."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly, PathPatch
from matplotlib.path import Path
import numpy as np
from pyproj import Transformer
from shapely.geometry import shape, box, mapping
from shapely.ops import transform as stransform, unary_union
from common import *

for f in ("IMFeENrm28P.ttf", "IMFeENsc28P.ttf", "IMFeGPit28P.ttf", "MedievalSharp.ttf"):
    fm.fontManager.addfont(f"{INKFONTS}/{f}")
for f in ("IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf"):
    fm.fontManager.addfont(f"{FONTS}/{f}")
FELL = fm.FontProperties(fname=f"{INKFONTS}/IMFeENrm28P.ttf")
FELLSC = fm.FontProperties(fname=f"{INKFONTS}/IMFeENsc28P.ttf")
FELLIT = fm.FontProperties(fname=f"{INKFONTS}/IMFeGPit28P.ttf")
HAND = fm.FontProperties(fname=f"{INKFONTS}/MedievalSharp.ttf")
MONO = "IBM Plex Mono"
plt.rcParams.update({"font.family": "IM FELL English PRO", "font.size": 13, "axes.edgecolor": "#6E604E", "axes.labelcolor": "#2B2119",
                     "xtick.color": "#6E604E", "ytick.color": "#6E604E", "axes.facecolor": "none"})
try:
    plt.rcParams["font.family"] = FELL.get_name()
except Exception:
    pass
PAPER, PAPER2, INKC, MUT, RED, BLUE, RIPPLE, LANDC = "#F6EED8", "#F3E5BF", "#2B2119", "#6E604E", "#A3261B", "#3D6E9E", "#6F9DC6", "#F1E2B8"
SEPIA = "#8C6A43"
# periods of the first dated fort (for the world maps)
PERIODS = [(1450, 1550, "before 1550", "#7E1810"), (1550, 1600, "1550 to 1599", "#A3261B"), (1600, 1650, "1600 to 1649", "#C8553D"),
           (1650, 1700, "1650 to 1699", "#DE8B5F"), (1700, 1800, "1700 to 1799", "#E9B98B"), (1800, 1950, "1800 and after", "#F0D8B4")]


def period_col(y):
    for a, b, lab, c in PERIODS:
        if a <= y < b:
            return c
    return None


NE_LAND = jload(f"{GEO}/ne_50m_land.geojson")["features"]
NE_C50 = jload(f"{GEO}/ne_50m_admin_0_countries.geojson")["features"]


def projector(crs):
    tr = Transformer.from_crs(4326, crs, always_xy=True)
    return lambda x, y, z=None: tr.transform(x, y)


def project_geoms(feats, crs, clip=None):
    f = projector(crs)
    out = []
    for ft in feats:
        g = shape(ft["geometry"])
        if clip is not None:
            g = g.intersection(clip)
            if g.is_empty: continue
        pg = stransform(f, g)
        if not pg.is_valid: pg = pg.buffer(0)
        out.append((ft["properties"], pg))
    return out


def patches(ax, g, **kw):
    polys = g.geoms if g.geom_type == "MultiPolygon" else [g] if g.geom_type == "Polygon" else []
    for p in polys:
        verts, codes = [], []
        for ring in [p.exterior] + list(p.interiors):
            cs = np.asarray(ring.coords)
            verts += cs.tolist(); codes += [Path.MOVETO] + [Path.LINETO] * (len(cs) - 2) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), **kw))


def lines(ax, g, **kw):
    if g.is_empty: return
    gs = g.geoms if hasattr(g, "geoms") else [g]
    for x in gs:
        if x.geom_type == "Polygon":
            for ring in [x.exterior] + list(x.interiors):
                cs = np.asarray(ring.coords); ax.plot(cs[:, 0], cs[:, 1], **kw)
        elif x.geom_type in ("LineString", "LinearRing"):
            cs = np.asarray(x.coords); ax.plot(cs[:, 0], cs[:, 1], **kw)
        elif hasattr(x, "geoms"):
            lines(ax, x, **kw)


def ink_base(ax, crs, extent_ll, ripple_m=(9e3, 22e3, 40e3), land_fc=LANDC, coast_lw=0.9, countries=True, country_fc=None, simplify=None,
             min_area=0):
    """Parchment sea, land with a black coast and blue ripple lines out to sea, country borders as fine dashes.
    country_fc: function(iso) -> colour or None. Returns the projected extent."""
    lon0, lon1, lat0, lat1 = extent_ll
    clip = box(max(-180, lon0 - 30), max(-89, lat0 - 15), min(180, lon1 + 30), min(89, lat1 + 15))
    land = [g for _, g in project_geoms(NE_LAND, crs, clip)]
    land = unary_union(land)
    if not land.is_valid: land = land.buffer(0)
    if simplify: land = land.simplify(simplify)
    if min_area:
        land = unary_union([p for p in (land.geoms if hasattr(land, "geoms") else [land]) if p.area >= min_area])
    f = projector(crs)
    xs, ys = f(np.array([lon0, lon1, lon0, lon1, (lon0 + lon1) / 2, (lon0 + lon1) / 2]), np.array([lat0, lat0, lat1, lat1, lat0, lat1]))
    ext = (min(xs), max(xs), min(ys), max(ys))
    ax.set_facecolor(PAPER)
    for k, d in enumerate(ripple_m):
        lines(ax, land.buffer(d, resolution=4).boundary, color=RIPPLE, lw=0.55 - 0.12 * k, alpha=0.75 - 0.2 * k, zorder=1)
    patches(ax, land, fc=land_fc, ec="none", zorder=2)
    if countries:
        for p, g in project_geoms(NE_C50, crs, clip):
            iso = p["ADM0_A3"]
            c = country_fc(iso) if country_fc else None
            if c:
                patches(ax, g, fc=c, ec="none", zorder=2.5, alpha=0.85)
            lines(ax, g.boundary if hasattr(g, "boundary") else g, color=INKC, lw=0.25, alpha=0.45, ls=(0, (3, 2)), zorder=3)
    lines(ax, land, color=INKC, lw=coast_lw, zorder=4)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    return ext, f


def star_marker(n=5):
    """a bastioned trace seen from above, as a matplotlib marker path"""
    pts = []
    for i in range(n):
        a = -np.pi / 2 + 2 * np.pi * i / n
        a0, a1 = a - np.pi / n * 0.55, a + np.pi / n * 0.55
        pts += [(0.55 * np.cos(a0), 0.55 * np.sin(a0)), (1.0 * np.cos(a), 1.0 * np.sin(a)), (0.55 * np.cos(a1), 0.55 * np.sin(a1))]
        b = a + np.pi / n
        pts.append((0.42 * np.cos(b), 0.42 * np.sin(b)))
    pts.append(pts[0])
    return Path(pts, [Path.MOVETO] + [Path.LINETO] * (len(pts) - 2) + [Path.CLOSEPOLY])


STAR = star_marker()


def parchment(fig, seed=3, alpha=0.06):
    """faint mottling over the whole sheet, as on old paper"""
    rng = np.random.default_rng(seed)
    n = 48
    z = rng.normal(size=(n, int(n * fig.get_figwidth() / fig.get_figheight()) + 1))
    from scipy.ndimage import gaussian_filter
    z = gaussian_filter(z, 2.5)
    ax = fig.add_axes([0, 0, 1, 1], zorder=-10); ax.axis("off")
    ax.imshow(z, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("p", ["#E9D9AE", PAPER]), alpha=1, aspect="auto", interpolation="bicubic")
    fig.patch.set_facecolor(PAPER)
    return ax


def save(fig, path, dpi=200):
    fig.savefig(path, dpi=dpi, facecolor=fig.get_facecolor())
    plt.close(fig)


# ---- a fort drawn from its real OpenStreetMap lines (data/forts_detail.geojson, code/01b_detail.py): moat water in blue,
# walls and ramparts in black ink, centred on its outline and set at (cx, cy) in metres
_DET = None


def draw_detail(ax, fid, centre_ll, cx, cy, lw=1.1, zorder=3, clip=None):
    global _DET
    if _DET is None:
        _DET = {}
        for ft in jload(f"{DATA}/forts_detail.geojson")["features"]:
            _DET.setdefault(ft["properties"]["id"], []).append(ft)
    lon0, lat0 = centre_ll
    k = 111320 * np.cos(np.radians(lat0))
    tf = lambda x, y, z=None: ((np.asarray(x) - lon0) * k + cx, (np.asarray(y) - lat0) * 110574 + cy)
    for ft in sorted(_DET.get(fid, []), key=lambda f: f["properties"]["k"] != "m"):
        g0 = shape(ft["geometry"])
        if clip is not None:
            g0 = g0.intersection(clip)
            if g0.is_empty: continue
        g = stransform(tf, g0); kd = ft["properties"]["k"]
        if kd == "m":
            patches(ax, g, fc="#B9CFE0", ec=BLUE, lw=0.35, zorder=zorder)
        elif kd == "e":
            lines(ax, g, color=BLUE, lw=0.6, zorder=zorder + 0.5)
        else:
            lines(ax, g, color=INKC, lw=lw, zorder=zorder + 1, solid_capstyle="round", solid_joinstyle="miter")
