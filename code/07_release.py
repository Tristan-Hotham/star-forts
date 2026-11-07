"""Step 7: blog post and meta (release/blog), Zenodo files and metadata (release/zenodo).
10.5281/zenodo.24043680, https://doi.org/10.5281/zenodo.24043680 and https://blog.tristanhotham.com/2026/10/31/star-forts/ stay as placeholders for the publisher."""
import json as _json, shutil, zipfile, importlib.util
from PIL import Image
from common import *

spec = importlib.util.spec_from_file_location("b", os.path.join(ROOT, "code", "03_build_site.py"))
spec.loader.exec_module(importlib.util.module_from_spec(spec))          # shared fact checks (and rebuilds index.html)
R = jload(f"{DATA}/results.json")
REL = os.path.join(ROOT, "release"); NAME = "Hotham_Star_Fort_Belt"
KEEP = {"DOI", "DOI_URL", "BLOG_URL"}

# facts written in words in the blog and the collage
assert R["countries_top"][0]["iso"] == "SWE" and R["counts"]["europe_pct"] > 85
assert R["diffusion"]["median_first_beyond"] <= R["diffusion"]["median_first_europe"]
assert R["sizes"]["points_mode"] == 4
pts = R["sizes"]["points_counts"]; assert pts["5"] == max(v for k, v in pts.items() if k != "4")   # "then the pentagon"
dec = {d["decade"]: d for d in R["decades"]}
assert max(dec[d]["beyond"] for d in dec) in (dec[1750]["beyond"], dec[1760]["beyond"])

post = open(os.path.join(ROOT, "code", "blog_template.html"), encoding="utf-8").read()
post = re.sub(r"\{\{(?!IMG)([^}|]+)(\|(\w+))?\}\}", lambda m: m.group(0) if m.group(1) in KEEP else fmt(get(R, m.group(1)), m.group(3)), post)
used = re.findall(r"\{\{IMG\|([^|]+)\|", post)
assert 5 <= len(used) <= 8, len(used)
assert all(re.search(r"^\{\{IMG\|" + re.escape(u_), post, re.M) for u_ in used) and "wp:image" not in post
for img in used:
    assert Image.open(f"{REL}/blog/{img}").size[0] == 1800, img
for fn in os.listdir(f"{REL}/blog"):
    if fn.startswith("b_") and fn not in used:
        os.remove(f"{REL}/blog/{fn}")
assert set(re.findall(r"\{\{([^|}]+)\}\}", post)) <= KEEP, set(re.findall(r"\{\{([^|}]+)\}\}", post))
vis = re.sub(r"<!--.*?-->", "", post, flags=re.S)
for bad in ("\u2014", "\u2013", "--", "DSIT", "DCMS"):
    assert bad not in vis, bad
open(f"{REL}/blog/post.html", "w", encoding="utf-8").write(post)
words = len(re.sub(r"<[^>]+>|\{\{IMG\|[^}]*\}\}", " ", vis).split())
c, d = R["counts"], R["dates"]
meta = {"title": "The star fort belt: how the bastion spread around the world",
        "slug": "star-forts",
        "excerpt": f"I mapped {c['main']:,} star forts in ink, from Palmanova to Hakodate. Only {d['dated_pct']:.0f}% can be dated, but the dates tell a clear story: the bastion did not creep out of Italy, it sailed, reaching India, Morocco and the Caribbean as early as Germany and England.",
        "seo_description": f"{c['main']:,} star forts on a hand-inked map: how the bastioned fortress spread from Italy to India, Africa, the Americas and Japan, 1500 to 1900.",
        "tags": ["maps", "history", "star forts", "fortifications", "military history", "colonial history", "data visualisation", "OpenStreetMap", "Wikidata"],
        "header_alt": f"Title card on parchment reading 'The star fort belt' in black and red hand lettering, with a world map shading each country by its first dated star fort, the figures {c['main']:,} star forts and {R['colonial_span'][0]} to {R['colonial_span'][1]}, and the ink outlines of Palmanova, Naarden, Neuf-Brisach, Elvas and Goryokaku."}
assert len(meta["seo_description"]) < 160, len(meta["seo_description"])
jsave(meta, f"{REL}/blog/meta.json", indent=2)

# Zenodo
Z = f"{REL}/zenodo"; os.makedirs(Z, exist_ok=True)
for fn in os.listdir(Z):
    os.remove(os.path.join(Z, fn))
shutil.copy(f"{REL}/paper/{NAME}.pdf", f"{Z}/{NAME}.pdf")
zp = f"{Z}/star-forts_data_and_code.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for dd in ("code", "data", "js"):
        for fn in sorted(os.listdir(os.path.join(ROOT, dd))):
            if fn.endswith(".pyc") or fn == "__pycache__":
                continue
            z.write(os.path.join(ROOT, dd, fn), f"star-forts/{dd}/{fn}")
    for fn in ("README.md", "LICENSE", "index.html"):
        z.write(os.path.join(ROOT, fn), f"star-forts/{fn}")
    z.write(os.path.join(ROOT, "reddit", "collage.py"), "star-forts/reddit/collage.py")
tex = open(f"{REL}/paper/{NAME}.tex", encoding="utf-8").read()
ab = re.search(r"\\begin\{center\}\\textbf\{Abstract\}\\end\{center\}\n(.*?)\n\n\\textbf\{Keywords", tex, re.S).group(1)
ab = ab.replace("\\%", "%").replace("\\&", "&").replace("$\\rho$", "rho")
zmeta = {"title": "The Star Fort Belt: How the Bastion Spread Around the World",
         "upload_type": "publication", "publication_type": "workingpaper",
         "description": f"<p>{ab}</p><p>Interactive map: <a href=\"{PAGE}\">{PAGE}</a>. Data and code: <a href=\"{REPO}\">{REPO}</a>. Blog post: {{https://blog.tristanhotham.com/2026/10/31/star-forts/}}.</p><p>Sources: OpenStreetMap contributors (ODbL 1.0; the derived outline and fort tables are released under the ODbL); Wikidata (CC0); English Wikipedia (CC BY-SA 4.0; dates and builders of {d['hand_rows']} forts); Natural Earth (public domain). Base map: The Inked World.</p>",
         "creators": [{"name": "Hotham, Tristan", "affiliation": "Independent researcher", "orcid": "0000-0003-4931-9349"}],
         "keywords": ["star fort", "bastion fort", "trace italienne", "fortification", "military architecture", "diffusion", "colonial history", "OpenStreetMap", "Wikidata", "maps"],
         "license": "cc-by-4.0", "language": "eng",
         "notes": "Text and figures CC BY 4.0; code MIT; data/forts.csv and data/forts_outlines.geojson are derived from OpenStreetMap and released under the Open Database License 1.0.",
         "related_identifiers": [{"identifier": REPO, "relation": "isSupplementedBy", "resource_type": "software"},
                                 {"identifier": PAGE, "relation": "isSupplementedBy", "resource_type": "other"},
                                 {"identifier": INKPAGE, "relation": "isDerivedFrom", "resource_type": "other"},
                                 {"identifier": "https://www.openstreetmap.org/", "relation": "isDerivedFrom", "resource_type": "dataset"},
                                 {"identifier": "https://www.wikidata.org/", "relation": "isDerivedFrom", "resource_type": "dataset"},
                                 {"identifier": "https://www.naturalearthdata.com/", "relation": "isDerivedFrom", "resource_type": "dataset"}],
         "files": sorted(os.listdir(Z))}
sj = _json.dumps(zmeta, ensure_ascii=False) + _json.dumps(meta, ensure_ascii=False)
assert "\u2014" not in sj and "\u2013" not in sj and "--" not in sj and "DSIT" not in sj and "DCMS" not in sj
jsave(zmeta, f"{Z}/metadata.json", indent=2)
print("blog words", words, "figures", len(used), "; zenodo", sorted(os.listdir(Z)), os.path.getsize(zp) // 1024, "KB zip")
