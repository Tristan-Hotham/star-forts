"""Step 6: README.md, LICENSE and the Reddit post text, from data/results.json."""
from common import *

R = jload(f"{DATA}/results.json")
c, d, s, v, df = R["counts"], R["dates"], R["sizes"], R["survival"], R["diffusion"]
fam = "; ".join(f"{f['name']} {f['area_ha']:.1f} ha, {f['points']} points ({f['year']})" for f in R["famous"])
readme = f"""# The star fort belt: how the bastion spread around the world

Every star fort (bastion fort, trace italienne) I could find in open data, {c['main']:,} in {c['countries']} countries, drawn on The Inked World's hand-inked basemap: {c['outlines']:,} by their real outlines from OpenStreetMap, the rest as pen-drawn stars, with a decade slider from 1480 to today, the source of every date, sizes from the outlines, and an honest count of how few can be dated.

Interactive page: {PAGE}
Paper: https://doi.org/{{10.5281/zenodo.24043680}}
Blog post: {{https://blog.tristanhotham.com/2026/10/31/star-forts/}}
Code and data: {REPO}

## Headline results

- Catalogue: {c['main']:,} star forts ({c['outlines']:,} traced outlines, {c['catalogue']:,} Wikidata points, {c['hand_added']} added from Wikipedia); {c['europe_pct']:.0f}% in Europe. Kept out of the counts: {c['lookalike']} shape look-alikes (towered walls of other traditions) and {c['bavarian']} Bavarian listed earthworks of uncertain form.
- Dates: only {d['dated']} forts ({d['dated_pct']:.1f}%) can be dated: {d['hand']} by hand from English Wikipedia, {d['wikidata']} from Wikidata, {d['osm']} from OpenStreetMap. Without the hand dates, {d['nonhand_pct']:.1f}%.
- Spread: the earliest dated works are Italian, but distance from Florence barely predicts a country's first dated fort (Spearman rho {df['rho']}, {df['n']} countries). Median first date beyond Europe {df['median_first_beyond']}, in Europe {df['median_first_europe']}: the bastion went by sea, Diu {R['colonial_span'][0]} to Hakodate {R['colonial_span'][1]}.
- Size: median {s['median_ha']:.1f} ha inside the outline (about {s['median_diameter_m']} m across); {s['points_mode_pct']:.0f}% have four points; no trend in size with date (rho {R['size_year']['rho']}).
- Great fortress towns: {fam}.
- Survival: {v['outline_pct']:.0f}% of forts still have an outline the shape test recognises ({v['europe_outline_pct']:.0f}% in Europe, {v['beyond_outline_pct']:.0f}% beyond); {v['hand_vanished']} hand-dated forts are known to be largely demolished.

## Files

| File | What it is |
|---|---|
| `index.html`, `js/page.js` | The interactive page (built by `code/03_build_site.py`). The base map is The Inked World engine, loaded from `../ink-map/` on the same site (maps.tristanhotham.com/ink-map/), so its scripts, data and fonts are not copied here. |
| `header.png` | Social card, 1200 x 630. |
| `img/` | Figures for the page. |
| `data/forts.csv` | One row per fort ({c['records']:,} rows incl. look-alikes and Bavarian entries): id, name and where the name came from, kind, main flag, coordinates, country, region, Wikidata id, OpenStreetMap ids, area, perimeter, diameter, points, year with source and precision, raw Wikidata and OpenStreetMap dates, builder, fate, Wikipedia link. ODbL. |
| `data/forts_outlines.geojson` | The {c['outline_in']:,} outlines (clockwise rings) with id, name and year. ODbL. |
| `data/forts_detail.geojson` | The walls, ramparts and moats of each traced fort as mapped in OpenStreetMap, at full detail (code/01b_detail.py), drawn on the page from zoom 11 and in the outline figures. ODbL. |
| `data/forts_points.geojson`, `data/search.json` | Page data. |
| `data/hand_dates.csv` | Input: {d['hand_rows']} forts dated by hand from English Wikipedia, with builder, fate, note and article link. |
| `data/countries.csv`, `data/regions.csv`, `data/decades.csv`, `data/famous.csv` | Tables. |
| `data/results.json` | Every number quoted anywhere. |
| `code/` | Scripts, run in order, templates and `qa.js`. |
| `release/` | Paper (`paper/`), blog post and figures (`blog/`), Zenodo files (`zenodo/`). |
| `reddit/` | Collage (`collage.py`, PNG) and post text. |

## Method in brief

- Outlines: The Inked World searched OpenStreetMap (historic=fort, fortification_type, town walls, moats; walls and moats joined into rings) and kept rings that look bastioned: perimeter 250 m to 20 km, 45% to 93% of the convex hull, at least four salient corners sharper than 100 degrees at similar distances from the centre, with re-entrant corners between (three if named or catalogued as a star fort or sconce). Points = salients.
- Drawing: the outline rings join broken walls and moats with round buffers, which rounds the bastion points, so the page and figures draw each fort from its own wall, rampart and moat pieces instead (within 80 to 300 m of the outline, simplified only to 0.5 m); the rings are used for finding and measuring.
- Catalogue: Wikidata star forts, sconces and polygonal forts without an outline added; catalogue points on an outline merged; Wikidata fortified towns inside an outline give it a name; unnamed outlines named after the nearest Natural Earth town.
- Left out of the counts: Bavarian monument-list sconces (uncertain form and age) and outlines in countries where the shape test mostly finds other traditions (China, Korea, India, Pakistan, the Middle East, Central Asia, North Africa) unless dated by hand as a European work; Maginot ouvrages and Smolensk's wall.
- Dates: hand date (English Wikipedia) > Wikidata start time or opening > Wikidata inception (year or decade precision) > OpenStreetMap start_date. Before 1450 = medieval origin, set aside; monastery inceptions and decade-precision inceptions before 1550 set aside.
- Diffusion: first dated fort per country, great-circle distance from Florence, Spearman rank correlation.
- Caveats: the catalogue reflects mapping and cataloguing (Sweden's sconce register, Bavaria, OpenStreetMap's European depth); the shape test misses forts and finds look-alikes; few forts are dated and the hand-dated ones are famous; inceptions may date a site, not its bastions; areas are inside whichever line the test found.

## How to rerun

Needs Python 3 with numpy, scipy, shapely, pyproj, matplotlib and Pillow, xelatex and pdftotext; node with Playwright for `code/qa.js`. Step 1 reads The Inked World's `data/forts.geojson`, the OpenStreetMap extracts, the Wikidata query results and Natural Earth (paths in `code/common.py`); later steps need only `data/`.

```
python3 code/01_forts.py        # forts, outlines, names, countries, dates
python3 code/01b_detail.py      # walls and moats of each fort for drawing
python3 code/02_results.py      # results.json, tables, page data
python3 code/03_build_site.py   # index.html
python3 code/04_figures.py      # figures and header
python3 code/05_paper.py        # paper PDF
python3 reddit/collage.py       # collage
python3 code/06_readme.py       # README, LICENSE, Reddit post
python3 code/07_release.py      # blog post, Zenodo files
```

## Sources and licences

- OpenStreetMap contributors, (c) OpenStreetMap, ODbL 1.0: outlines, names, start dates. `data/forts.csv` and `data/forts_outlines.geojson` are derived databases released under the ODbL 1.0.
- Wikidata (CC0): star forts, sconces, polygonal forts and fortified towns, with dates, queried with QLever in 2026.
- English Wikipedia (CC BY-SA 4.0): dates, builders and fates of {d['hand_rows']} forts (facts only; one article each, linked in `data/hand_dates.csv`).
- Natural Earth (public domain): countries, land, populated places.
- Base map: The Inked World ({INKPAGE}), OpenStreetMap vector tiles by OpenFreeMap, AWS Terrain Tiles, RESOLVE Ecoregions 2017 (CC BY 4.0). Fonts: MedievalSharp, IM Fell (SIL OFL).

## Citation

Hotham, T. (2026) The star fort belt: how the bastion spread around the world. Zenodo. https://doi.org/{{10.5281/zenodo.24043680}}

Dr Tristan Hotham, Independent researcher. ORCID 0000-0003-4931-9349.

{AI}
"""
open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(readme)
lic = """MIT License (code)

Copyright (c) 2026 Tristan Hotham

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Text, figures, the paper and the collage: Creative Commons Attribution 4.0 International (CC BY 4.0).

Data: data/forts.csv and data/forts_outlines.geojson (and the page data built from them) are derived from OpenStreetMap and are made available under the Open Database License 1.0 (https://opendatacommons.org/licenses/odbl/1-0/), (c) OpenStreetMap contributors. Wikidata content is CC0. data/hand_dates.csv records facts (years, builders) from English Wikipedia, with links to the articles (CC BY-SA 4.0), and is released under CC BY 4.0.
"""
open(os.path.join(ROOT, "LICENSE"), "w", encoding="utf-8").write(lic)
post = f"""## Title

[OC] I mapped {c['main']:,} star forts in ink. The bastion reached India, Morocco and the Caribbean in the same decades it reached Germany and England

## Body

Star forts (bastion forts, the "trace italienne") were Italy's answer to cannon around 1500. I put every one I could find in open data on a hand-inked world map: {c['outlines']:,} found by their star-shaped outlines in OpenStreetMap, plus forts catalogued in Wikidata and {d['hand']} famous ones I dated by hand from Wikipedia. {c['europe_pct']:.0f}% are in Europe, in a belt along the old war zones. Only {d['dated_pct']:.0f}% can be dated, but the dates say the idea did not creep out of Italy: Diu in India ({R['colonial_span'][0]}), San Juan (1539) and Mazagan (1541) come as early as Jülich (1548) or Berwick (1558), and distance from Florence barely predicts when a country got its first dated fort. The last link is Goryōkaku in Japan ({R['colonial_span'][1]}). The median fort is small, {s['median_ha']:.1f} ha, usually with four points. Caveats: it shows what has been mapped and catalogued; most forts have no date; the shape test misses some forts and catches some look-alikes (left out). Interactive map with a decade slider: {PAGE}

## Source comment

Sources: OpenStreetMap contributors (ODbL) for the outlines, names and start dates; Wikidata (CC0) for star forts, sconces, fortified towns and dates; English Wikipedia for the dates and builders of {d['hand_rows']} forts; Natural Earth. Base map: my hand-inked Inked World map.

Tools: Python (shapely, pandas, scipy, matplotlib); MapLibre for the interactive map.

Interactive version: {PAGE}
Paper: https://doi.org/{{10.5281/zenodo.24043680}}
Blog post: {{https://blog.tristanhotham.com/2026/10/31/star-forts/}}
"""
open(os.path.join(ROOT, "reddit", "post.md"), "w", encoding="utf-8").write(post)
for t in (readme, lic, post):
    for bad in ("—", "–", "--", "DSIT", "DCMS"):
        assert bad not in t.replace("|---|---|", ""), bad
print("README", len(readme.split()), "words")
