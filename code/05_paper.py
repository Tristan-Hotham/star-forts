"""Step 5: the paper. Fills code/paper_template.tex from data/results.json, adds tables, compiles with xelatex.
Output: release/paper/<NAME>.pdf and .tex beside the f_*.png figures. The DOI stays as a 10.5281/zenodo.24043680 placeholder."""
import csv, subprocess, shutil
from common import *

R = jload(f"{DATA}/results.json")
OUT = os.path.join(ROOT, "release", "paper"); NAME = "Hotham_Star_Fort_Belt"
tex = lambda s: str(s).replace("\\", "").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#").replace("$", "\\$")

# statements made in words in the paper only
dec = {d["decade"]: d for d in R["decades"]}
assert max(dec[d]["beyond"] for d in dec) == dec[1750]["beyond"] == dec[1760]["beyond"]
assert dec[1590]["n"] > max(dec[1580]["n"], dec[1600]["n"]) and dec[1670]["n"] > max(dec[1660]["n"], dec[1680]["n"]) and dec[1870]["n"] > dec[1860]["n"]
assert 38 < R["survival"]["no_outline_pct"] < 43                     # "two in five"
assert R["countries_top"][0]["iso"] == "SWE"
assert 15 < R["dates"]["dated_pct"] < 25                              # "only a fifth"


def tfmt(v, f):
    if f == "int": return f"{int(round(float(v))):,}"
    if f == "pc": return f"{round(float(v))}\\%"
    if f == "f1": return f"{float(v):.1f}"
    if f == "f2": return f"{float(v):.2f}"
    return tex(str(v))


rows = "".join(f"{tex(c['country'])} & {c['n']:,} & {c['outlines']:,} & {c['dated']:,}\\\\\n" for c in R["countries_top"])
TC = ("\\begin{table}[tbp]\\centering\\small\\caption{The twelve countries with most star forts: all forts, those with a traced outline, and those with a date.}\\label{tab:countries}"
      "\\begin{tabular}{lrrr}\\toprule Country & Forts & Outlines & Dated\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
rows = "".join(f"{tex(r['region'])} & {r['n']:,} & {r['dated']:,} & {r['dated_pct']:.0f} & {tex(r['first_name'])} & {r['first_year']} & {r['median_year']}\\\\\n" for r in R["regions"])
TR = ("\\begin{table}[tbp]\\centering\\footnotesize\\caption{Regions: forts, dated forts and their share (\\%), the earliest dated fort in the data and the median year of the dated forts.}\\label{tab:regions}"
      "\\begin{tabular}{p{3.6cm}rrrp{4.2cm}rr}\\toprule Region & Forts & Dated & \\% & Earliest dated & Year & Median\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
rows = "".join(f"{tex(f['name'])} & {tex(f['country'])} & {f['area_ha']:.1f} & {f['points']} & {f['year'] or ''}\\\\\n" for f in R["largest"])
TL = ("\\begin{table}[tbp]\\centering\\small\\caption{The twelve largest traced outlines (unnamed ones carry the name of the nearest town).}\\label{tab:largest}"
      "\\begin{tabular}{llrrr}\\toprule Fort & Country & Area (ha) & Points & Begun\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
H = sorted(csv.DictReader(open(f"{DATA}/hand_dates.csv", encoding="utf-8")), key=lambda h: (int(h["year"]), h["name"]))
F = {f["name"]: f for f in csv.DictReader(open(f"{DATA}/forts.csv", encoding="utf-8")) if f["year_src"] == "Wikipedia"}
rows = "".join(f"{tex(h['name'])} & {tex(F[h['name']]['country'])} & {h['year']} & {tex(h['builder'])} & {'yes' if F[h['name']]['outline'] == 'True' else 'no'} & {h['status']}\\\\\n" for h in H)
TH = ("{\\footnotesize\\setlength{\\tabcolsep}{4pt}\\begin{longtable}{p{4.6cm}p{3.2cm}rp{3.2cm}ll}\\caption{The " + str(len(H)) + " forts dated by hand from English Wikipedia: year the bastioned works were begun, builder, whether an outline is traced, and fate. Article links are in data/hand\\_dates.csv.}\\label{tab:hand}\\\\"
      "\\toprule Fort & Country & Begun & Builder & Outline & Today\\\\\\midrule\\endfirsthead\\toprule Fort & Country & Begun & Builder & Outline & Today\\\\\\midrule\\endhead\n" + rows + "\\bottomrule\\end{longtable}}")
t = open(os.path.join(ROOT, "code", "paper_template.tex"), encoding="utf-8").read()
for k in ("page", "repo"):
    t = t.replace("\\url{{{meta.%s}}}" % k, "\\url{%s}" % R["meta"][k])
t = t.replace("{{AI}}", AI)
for k, v in (("COUNTRIES", TC), ("REGIONS", TR), ("LARGEST", TL), ("HAND", TH)):
    t = t.replace("{{TABLE_%s}}" % k, v)
t = re.sub(r"\{\{(?!TABLE_)([^}|]+)(\|(\w+))?\}\}", lambda m: tfmt(get(R, m.group(1)), m.group(3) or "raw"), t)
assert "{{" not in t.replace("\\{\\{DOI\\}\\}", "") and "--" not in t and "—" not in t and "–" not in t
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, NAME + ".tex"), "w", encoding="utf-8").write(t)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", NAME + ".tex"], cwd=OUT, capture_output=True, text=True)
log = open(os.path.join(OUT, NAME + ".log"), encoding="utf-8", errors="ignore").read()
print([l for l in log.splitlines() if "Missing character" in l or "undefined" in l.lower() or "Overfull" in l][:12])
for ext in (".aux", ".log", ".out"):
    q = os.path.join(OUT, NAME + ext)
    if os.path.exists(q): os.remove(q)
txt = subprocess.run(["pdftotext", os.path.join(OUT, NAME + ".pdf"), "-"], capture_output=True, text=True).stdout
pages = subprocess.run(["pdfinfo", os.path.join(OUT, NAME + ".pdf")], capture_output=True, text=True).stdout
print("paper", r.returncode, len(txt.split()), "words;", [l for l in pages.splitlines() if l.startswith("Pages")], "dashes:", txt.count("—") + txt.count("–") + txt.count("--"))
