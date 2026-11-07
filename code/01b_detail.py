"""Step 1b: the drawn detail of each traced star fort, at full resolution, from the raw OpenStreetMap pieces.

The outline rings of step 1 (from The Inked World) are good for finding forts and measuring them, but where a fort's walls
or moats are mapped as many short pieces the rings were made by buffering the pieces with round joins, which rounds off the
bastion points (Naarden, Palmanova, Neuf-Brisach). For drawing, this step keeps the real lines instead: every wall or
rampart way (barrier=city_wall, historic=citywalls, historic=fort, fortification_type) within 80 m of the outline, cut to
250 m round it, and the moat water (water=moat polygons, joined) within 300 m, simplified only to 0.5 m.
Writes data/forts_detail.geojson (LineString k=w for walls and ramparts, Polygon k=m for moats) and flags in WORK/detail.json
which forts have enough wall to draw (at least 60% of the outline's perimeter)."""
import csv, math
import numpy as np
from shapely.geometry import shape, Polygon, LineString, mapping
from shapely.ops import unary_union, polygonize, transform
from common import *
from outline_refine import Refiner, proj, polys

RF = Refiner(os.path.join(WORK, "raw_segs.pkl"), OSM_FORTS, os.environ.get("SF_WALLS", "/home/claude/newdata/raw12"))
OUT = jload(f"{DATA}/forts_outlines.geojson")["features"]
feats, flags = [], {}


def r6(a): return [[round(x, 6), round(y, 6)] for x, y in a]


for o in OUT:
    fid = o["properties"]["id"]
    g = shape(o["geometry"]); c = g.centroid
    f, inv = proj(c.y, c.x)
    P = transform(f, g)
    if not P.is_valid: P = P.buffer(0)
    if P.geom_type == "MultiPolygon": P = max(P.geoms, key=lambda q: q.area)
    near, far = P.buffer(80), P.buffer(250)
    from shapely.geometry import box
    idx = RF.tree.query(box(*g.bounds).buffer(400 / 110574))
    wl, moats, inner, mlines = [], [], [], []
    for i in idx:
        kind, cs = RF.segs[i]
        L = transform(f, RF.lines[i])
        if kind.startswith("moat"):
            if not L.intersects(P.buffer(300)): continue
            closed = len(cs) >= 4 and cs[0] == cs[-1]
            if closed:
                (inner if kind == "moat_inner" else moats).append(Polygon(L.coords))
            else:
                mlines.append(L)
        elif L.intersects(near):
            wl.append(L.intersection(far))
    W = unary_union([w for w in wl if not w.is_empty]) if wl else None
    wlen = W.length if W is not None else 0
    flags[fid] = {"wall_m": round(wlen), "perim_m": round(P.exterior.length), "walls": bool(wlen >= 0.6 * P.exterior.length)}
    if W is not None and not W.is_empty:
        W = W.simplify(0.5)
        for ln in (W.geoms if hasattr(W, "geoms") else [W]):
            if ln.geom_type != "LineString" or ln.length < 3: continue
            ll = transform(inv, ln)
            feats.append({"type": "Feature", "properties": {"id": fid, "k": "w"}, "geometry": {"type": "LineString", "coordinates": r6(ll.coords)}})
    # moat water: closed rings filled, minus the islands of moat relations; moats mapped as open lines drawn as lines.
    # A ring that swallows most of the fort is a riverbank or a whole moat relation outline with no island: drawn as a line.
    fill, edge = [], list(mlines)
    if moats:
        I = unary_union([q if q.is_valid else q.buffer(0) for q in inner]) if inner else None
        for q in moats:
            q = q if q.is_valid else q.buffer(0)
            if I is not None: q = q.difference(I)
            if q.intersection(P).area > 0.5 * P.area:
                edge.append(q.boundary); continue
            fill.append(q)
    if fill:
        M = unary_union(fill).intersection(P.buffer(300)).simplify(0.5)
        for p in polys(M):
            if p.area < 50: continue
            pl = transform(inv, p)
            feats.append({"type": "Feature", "properties": {"id": fid, "k": "m"},
                          "geometry": {"type": "Polygon", "coordinates": [r6(pl.exterior.coords)] + [r6(h.coords) for h in pl.interiors]}})
    if edge:
        E = unary_union(edge).intersection(P.buffer(300)).simplify(0.5)
        for ln in (E.geoms if hasattr(E, "geoms") else [E]):
            if ln.geom_type != "LineString" or ln.length < 5: continue
            feats.append({"type": "Feature", "properties": {"id": fid, "k": "e"}, "geometry": {"type": "LineString", "coordinates": r6(transform(inv, ln).coords)}})
jsave({"type": "FeatureCollection", "features": feats}, f"{DATA}/forts_detail.geojson")
jsave(flags, f"{WORK}/detail.json")
print("detail features", len(feats), "forts with drawn walls", sum(v["walls"] for v in flags.values()), "of", len(flags),
      os.path.getsize(f"{DATA}/forts_detail.geojson") // 1024, "KB")
