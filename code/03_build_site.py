"""Step 3: index.html from code/page_template.html and data/results.json, with the facts written in words checked.
10.5281/zenodo.24043680, https://doi.org/10.5281/zenodo.24043680 and https://blog.tristanhotham.com/2026/10/31/star-forts/ stay as placeholders for the publisher."""
import re, time
from common import *

R = jload(f"{DATA}/results.json")
KEEP = {"DOI", "DOI_URL", "BLOG_URL"}

# ---- facts stated in words on the page (and in the blog, paper and collage)
H = {f["name"]: f for f in R["strip"] + R["famous"]}
hand = {}
import csv
for r in csv.DictReader(open(f"{DATA}/hand_dates.csv", encoding="utf-8")):
    hand[r["name"]] = int(r["year"])
for n, y in {"Fortezza da Basso": 1534, "Citadel of Jülich": 1548, "Berwick-upon-Tweed walls": 1558, "Diu Fort": 1535, "Mazagan": 1541,
             "Castillo San Felipe del Morro": 1539, "Fort São Sebastião": 1558, "Moti Daman Fort": 1559, "Fort Jesus": 1593, "Morro Castle": 1589,
             "Fort Santiago": 1590, "Fort Belgica": 1611, "Fort Zeelandia": 1624, "Castle of Good Hope": 1666, "Fort St George": 1640,
             "Fort Christiansvaern": 1738, "Fortress of Louisbourg": 1720, "Goryōkaku": 1857, "Palmanova": 1593, "Naarden": 1673}.items():
    assert hand[n] == y, (n, hand[n], y)
first = {r["region"]: r for r in R["regions"]}
assert first["Low Countries"]["first_name"] == "Fort Rammekens" and first["Low Countries"]["first_year"] == 1547
assert first["Scandinavia and the Baltic"]["first_name"] == "Landskrona Citadel" and first["Scandinavia and the Baltic"]["first_year"] == 1559
assert first["Italy and Malta"]["first_year"] < 1534
assert R["colonial"][0]["builder"] == "Portugal" and R["colonial"][0]["first_name"] == "Diu Fort"
assert R["colonial_span"] == [1535, 1857]
assert R["density"][0]["iso"] == "MLT" and R["density"][1]["iso"] == "NLD" and R["density"][2]["iso"] == "BEL"
assert R["regions"][10]["region"] == "Asia and Oceania" and R["regions"][9]["region"] == "Americas" and R["regions"][5]["region"] == "Scandinavia and the Baltic"
assert R["sizes"]["under_2ha_pct"] > 50                                     # "half are under 2 ha"
assert abs(R["diffusion"]["rho"]) < 0.3 and R["diffusion"]["p"] > 0.05        # "hardly predicts"
assert abs(R["size_year"]["rho"]) < 0.1 and R["size_year"]["p"] > 0.05        # "no rank correlation"
assert sorted(R["survival"]["hand_vanished_names"]) == sorted(["Fortress of Louisbourg", "Citadel of Antwerp", "Saarlouis", "Citadel of Turin", "Fort Amsterdam"])
assert [f["name"] for f in R["famous"]][:2] == ["Palmanova", "Naarden"] and R["famous"][5]["name"] == "Elvas"
dec = {d["decade"]: d["n"] for d in R["decades"]}
assert max(dec, key=lambda d: dec[d] if d < 1650 else -1) == 1590 and max(dec, key=lambda d: dec[d] if 1650 <= d < 1700 else -1) == 1670
assert max(dec, key=lambda d: dec[d]) == 1870                              # the alt text of the decades chart

regions_rows = ""
for r in R["regions"]:
    fy = f"{r['first_name']} ({r['first_country']}), {r['first_year']}" if r["first_year"] else ""
    regions_rows += f"<tr><td>{r['region']}</td><td class=\"r\">{r['n']:,}</td><td class=\"r\">{r['dated']:,}</td><td>{fy}</td></tr>"
fam_rows = ""
for f in R["famous"]:
    fam_rows += (f"<tr><td><a href=\"{f['wikipedia']}\">{f['name']}</a> ({f['country']})</td><td class=\"r\">{f['year']}</td>"
                 f"<td class=\"r\">{f['area_ha']:.1f}</td><td class=\"r\">{f['points']}</td><td class=\"r\">{f['diameter_m']:,}</td></tr>")

t = open(os.path.join(ROOT, "code", "page_template.html"), encoding="utf-8").read()
fs = open(os.path.join(ROOT, "code", "fullscreen_snippet.html"), encoding="utf-8").read()
t = t.replace("{{TABLE_REGIONS}}", regions_rows).replace("{{TABLE_FAMOUS}}", fam_rows).replace("{{FULLSCREEN}}", fs)
t = t.replace("{{BYLINE}}", BYLINE).replace("{{AI}}", AI).replace("{{VERSION}}", time.strftime("%Y%m%d"))
t = re.sub(r"\{\{([^}|]+)(\|(\w+))?\}\}", lambda m: m.group(0) if m.group(1) in KEEP else fmt(get(R, m.group(1)), m.group(3)), t)
assert set(re.findall(r"\{\{([^}]+)\}\}", t)) <= KEEP, set(re.findall(r"\{\{([^}]+)\}\}", t))
vis = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", t, flags=re.S)
for bad in ("—", "–", "--", "DSIT", "DCMS", "civil serv"):
    assert bad not in vis, bad
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(t)
js = open(os.path.join(ROOT, "js", "page.js"), encoding="utf-8").read()
assert "—" not in js and "–" not in js
print("index.html", len(t) // 1024, "KB")
