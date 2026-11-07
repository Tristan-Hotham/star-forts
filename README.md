# The star fort belt: how the bastion spread around the world

Every star fort (bastion fort, trace italienne) I could find in open data, 1,307 in 80 countries, drawn on The Inked World's hand-inked basemap: 769 by their real outlines from OpenStreetMap, the rest as pen-drawn stars, with a decade slider from 1480 to today, the source of every date, sizes from the outlines, and an honest count of how few can be dated.

Interactive page: https://maps.tristanhotham.com/star-forts/
Paper: https://doi.org/10.5281/zenodo.24043680
Blog post: https://blog.tristanhotham.com/2026/10/31/star-forts/
Code and data: https://github.com/Tristan-Hotham/star-forts

## Headline results

- Catalogue: 1,307 star forts (769 traced outlines, 498 Wikidata points, 40 added from Wikipedia); 89% in Europe. Kept out of the counts: 253 shape look-alikes (towered walls of other traditions) and 560 Bavarian listed earthworks of uncertain form.
- Dates: only 251 forts (19.2%) can be dated: 84 by hand from English Wikipedia, 127 from Wikidata, 40 from OpenStreetMap. Without the hand dates, 12.8%.
- Spread: the earliest dated works are Italian, but distance from Florence barely predicts a country's first dated fort (Spearman rho 0.15, 49 countries). Median first date beyond Europe 1623, in Europe 1626: the bastion went by sea, Diu 1535 to Hakodate 1857.
- Size: median 1.9 ha inside the outline (about 228 m across); 42% have four points; no trend in size with date (rho -0.02).
- Great fortress towns: Palmanova 113.8 ha, 8 points (1593); Naarden 103.5 ha, 5 points (1673); Bourtange 28.5 ha, 10 points (1593); Neuf-Brisach 48.6 ha, 8 points (1698); Valletta 66.5 ha, 12 points (1566); Elvas 68.1 ha, 17 points (1643); Goryōkaku 11.9 ha, 5 points (1857).
- Survival: 59% of forts still have an outline the shape test recognises (56% in Europe, 82% beyond); 5 hand-dated forts are known to be largely demolished.

## Files

| File | What it is |
|---|---|
| `index.html`, `js/page.js` | The interactive page (built by `code/03_build_site.py`). The base map is The Inked World engine, loaded from `../ink-map/` on the same site (maps.tristanhotham.com/ink-map/), so its scripts, data and fonts are not copied here. |
| `header.png` | Social card, 1200 x 630. |
| `img/` | Figures for the page. |
| `data/forts.csv` | One row per fort (2,120 rows incl. look-alikes and Bavarian entries): id, name and where the name came from, kind, main flag, coordinates, country, region, Wikidata id, OpenStreetMap ids, area, perimeter, diameter, points, year with source and precision, raw Wikidata and OpenStreetMap dates, builder, fate, Wikipedia link. ODbL. |
| `data/forts_outlines.geojson` | The 1,022 outlines (clockwise rings) with id, name and year. ODbL. |
| `data/forts_detail.geojson` | The walls, ramparts and moats of each traced fort as mapped in OpenStreetMap, at full detail (code/01b_detail.py), drawn on the page from zoom 11 and in the outline figures. ODbL. |
| `data/forts_points.geojson`, `data/search.json` | Page data. |
| `data/hand_dates.csv` | Input: 84 forts dated by hand from English Wikipedia, with builder, fate, note and article link. |
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
- English Wikipedia (CC BY-SA 4.0): dates, builders and fates of 84 forts (facts only; one article each, linked in `data/hand_dates.csv`).
- Natural Earth (public domain): countries, land, populated places.
- Base map: The Inked World (https://maps.tristanhotham.com/ink-map/), OpenStreetMap vector tiles by OpenFreeMap, AWS Terrain Tiles, RESOLVE Ecoregions 2017 (CC BY 4.0). Fonts: MedievalSharp, IM Fell (SIL OFL).

## Citation

Hotham, T. (2026) The star fort belt: how the bastion spread around the world. Zenodo. https://doi.org/10.5281/zenodo.24043680

Dr Tristan Hotham, Independent researcher. ORCID 0000-0003-4931-9349.

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
