"""Sharper outlines for the star forts.

The Inked World joined broken town walls and moats into rings by buffering every piece by 15 to 22 m with round joins,
filling and shrinking back. That bridges gates and gaps, but it rounds every bastion point, so fortress towns such as
Naarden and Palmanova come out as lumpy blobs. Here each fort is traced again from the raw OpenStreetMap pieces that lie on
it, at full detail, and the candidate that reads most like a bastioned trace is kept:

  a. every closed way or relation ring on its own (historic=fort, fortification_type, barrier=city_wall, water=moat);
  b. the wall pieces buffered by 4, 8, 14 or 22 m with mitred joins (which keep sharp corners), unioned: both the outside
     of the band and its inner hole (the area inside the walls), grown or shrunk back by the same amount with mitred joins;
  c. the moat pieces made into polygons and unioned: the holes inside the water (the rampart the moat runs round, which on
     a wet-ditch fort is the bastion trace) and the outer edge.

Score: the number of salients (convex corners sharper than 100 degrees that stand out from the centre) on the ring
simplified to 2 m, with no more than 40 m of wobble between them; the candidate must overlap the original outline (its
area 0.3 to 3 times, its centre within the other). The original outline is kept unless a candidate has more salients.
"""
import math, pickle, glob, json, os
import numpy as np
from shapely.geometry import LineString, Polygon, MultiPolygon, box
from shapely.ops import unary_union, polygonize, transform
from shapely.strtree import STRtree

MITRE = dict(join_style="mitre", mitre_limit=6)


def proj(lat0, lon0):
    k = 111320 * math.cos(math.radians(lat0))
    return (lambda x, y, z=None: ((np.asarray(x) - lon0) * k, (np.asarray(y) - lat0) * 110574),
            lambda x, y, z=None: (np.asarray(x) / k + lon0, np.asarray(y) / 110574 + lat0))


def salients(pm):
    """sharp convex corners standing out from the centre (bastion points) on a ring in metres"""
    pm = pm.simplify(2)
    if pm.geom_type != "Polygon" or pm.is_empty: return 0
    pts = list(pm.exterior.coords)[:-1]; n = len(pts)
    if n < 4: return 0
    cx, cy = pm.centroid.x, pm.centroid.y
    orient = 1 if pm.exterior.is_ccw else -1
    s = 0
    for j in range(n):
        ax, ay = pts[j - 1]; bx, by = pts[j]; qx, qy = pts[(j + 1) % n]
        v1 = (ax - bx, ay - by); v2 = (qx - bx, qy - by)
        l1 = math.hypot(*v1); l2 = math.hypot(*v2)
        if l1 < 4 or l2 < 4: continue
        ang = math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)))))
        cross = (bx - ax) * (qy - by) - (by - ay) * (qx - bx)
        if cross * orient > 0 and ang < 100:
            d = math.hypot(bx - cx, by - cy)
            if d >= math.hypot(ax - cx, ay - cy) and d >= math.hypot(qx - cx, qy - cy): s += 1
    return s


def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    if hasattr(g, "geoms"): return [p for x in g.geoms for p in polys(x)]
    return []


class Refiner:
    def __init__(self, cache, raw_osm, raw_walls):
        if not os.path.exists(cache):
            out = []
            files = [(f, "fort") for f in sorted(glob.glob(f"{raw_osm}/fort_*.json"))] + \
                    [(f, "wall") for f in sorted(glob.glob(f"{raw_walls}/cw[0-9]*.json")) + [f"{raw_osm}/relwalls.json"]] + \
                    [(f, "moat") for f in sorted(glob.glob(f"{raw_osm}/moat_*.json"))]
            for f, kind in files:
                if not os.path.exists(f): continue
                for el in json.load(open(f))["elements"]:
                    segs = []
                    if el["type"] == "way" and len(el.get("geometry") or []) >= 2: segs = [(kind, el["geometry"])]
                    elif el["type"] == "relation":
                        # inner rings of a moat relation are the islands the water runs round (kept apart as moat_inner)
                        segs = [(kind + "_inner" if m.get("role") == "inner" else kind, m["geometry"]) for m in el.get("members", [])
                                if m.get("type") == "way" and len(m.get("geometry") or []) >= 2 and (m.get("role") != "inner" or kind == "moat")]
                    for k, g in segs:
                        out.append((k, [(p["lon"], p["lat"]) for p in g]))
            pickle.dump(out, open(cache, "wb"))
        self.segs = pickle.load(open(cache, "rb"))
        self.lines = [LineString(c) for _, c in self.segs]
        self.tree = STRtree(self.lines)

    def refine(self, poly_ll):
        """returns (best polygon in lon/lat, its salients, the original's salients, which candidate won)"""
        c = poly_ll.centroid
        f, inv = proj(c.y, c.x)
        P = transform(f, poly_ll)
        if not P.is_valid: P = P.buffer(0)
        if P.geom_type == "MultiPolygon": P = max(P.geoms, key=lambda g: g.area)
        s0 = salients(P)
        pad = 200 / 110574
        idx = self.tree.query(box(*poly_ll.bounds).buffer(pad))
        walls, moats, rings = [], [], []
        for i in idx:
            kind, cs = self.segs[i]
            if kind == "moat_inner": continue
            L = transform(f, self.lines[i])
            if not L.intersects(P.buffer(60)): continue
            if kind == "moat": moats.append(L)
            else: walls.append(L)
            if len(cs) >= 4 and cs[0] == cs[-1]:
                rp = Polygon(L.coords)
                if rp.is_valid and rp.area > 0: rings.append(("ring_" + kind, rp))
        cands = list(rings)
        if walls:
            W = unary_union(walls)
            for d in (4, 8, 14, 22):
                band = W.buffer(d, **MITRE)
                for p in polys(band):
                    cands.append((f"wall_out_{d}", Polygon(p.exterior).buffer(-d, **MITRE)))
                    for h in p.interiors:
                        cands.append((f"wall_in_{d}", Polygon(h).buffer(d, **MITRE)))
        if moats:
            mp = [Polygon(m.coords) for m in moats if m.is_ring and len(m.coords) >= 4]
            mp = [p if p.is_valid else p.buffer(0) for p in mp]
            mp += list(polygonize(unary_union([m for m in moats])))
            M = unary_union([p for p in mp if not p.is_empty]) if mp else None
            for p in polys(M):
                cands.append(("moat_out", Polygon(p.exterior)))
                for h in p.interiors:
                    cands.append(("moat_in", Polygon(h)))
            # moats mapped as pieces that only touch: close the gaps with a small mitred buffer
            if M is not None and not M.is_empty:
                for p in polys(M.buffer(6, **MITRE)):
                    for h in p.interiors:
                        cands.append(("moat_in_6", Polygon(h).buffer(6, **MITRE)))
        best, bs, how = P, s0, "original"
        for how_c, q in cands:
            q = q if q.is_valid else q.buffer(0)
            q = max(polys(q), key=lambda g: g.area, default=None)
            if q is None or q.area <= 0: continue
            r = q.area / P.area
            if not (0.3 <= r <= 3): continue
            if not (q.contains(P.centroid) or P.contains(q.centroid)): continue
            fill = q.area / q.convex_hull.area
            if fill < 0.45 or fill > 0.95: continue
            s = salients(q)
            # more points wins; at equal points the larger (outer) trace
            if s > bs or (s == bs and how != "original" and q.area > best.area):
                best, bs, how = q, s, how_c
        return transform(inv, best), bs, s0, how
