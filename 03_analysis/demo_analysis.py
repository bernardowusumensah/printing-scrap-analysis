"""
Demo analysis of the simulated printing job cards.

Run from anywhere:  python 03_analysis/demo_analysis.py

It cleans the raw job card files, works out where scrap comes from,
saves three charts to 04_output/charts/ and builds the interactive
dashboard page at docs/index.html (published with GitHub Pages).

All data is simulated.
"""
import json
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "01_raw" / "job_cards"
CLEAN = ROOT / "02_clean"
CHARTS = ROOT / "04_output" / "charts"
DOCS = ROOT / "docs"
TEMPLATE = Path(__file__).resolve().parent / "dashboard_template.html"
COST_PER_CUP = 0.06          # assumption: replace with the real cost of a blank cup
LAST_FULL_WEEK = "2026-09-28"  # the week after holds only one job's last shift

# ---------------------------------------------------------------- load
jobs = pd.read_csv(RAW / "job_cards.csv", dtype={"order": str, "work_center": str, "material": str})
shifts = pd.read_csv(RAW / "job_card_shifts.csv", dtype={"order": str})
printers = pd.read_csv(RAW / "work_centers.csv", dtype={"work_center": str})

# ---------------------------------------------------------------- clean
checks = []
n = len(shifts)
shifts = shifts.drop_duplicates()
checks.append(("Duplicate shift lines removed", n - len(shifts)))

shifts["counter_diff"] = shifts.counter_end - shifts.counter_start
blank = shifts.run_scrap.isna()
shifts.loc[blank, "run_scrap"] = shifts.loc[blank, "counter_diff"] - shifts.loc[blank, "total_printed"]
checks.append(("Blank run scrap filled from counters", int(blank.sum())))

gap = shifts.counter_diff - (shifts.total_printed + shifts.run_scrap)
checks.append(("Shift lines where counters don't match", int((gap.abs() > 5).sum())))

blank = jobs.setup_scrap.isna()
jobs.loc[blank, "setup_scrap"] = jobs.loc[blank, "setup_counter_end"] - jobs.loc[blank, "setup_counter_start"]
checks.append(("Blank setup scrap filled from counters", int(blank.sum())))

# a new artwork version = higher than the last job for the same product
jobs = jobs.sort_values(["setup_date", "setup_shift", "order"])
v = jobs.artwork_version.astype(int)
jobs["new_artwork"] = v > v.groupby(jobs.material).shift()

totals = shifts.groupby("order").agg(printed=("total_printed", "sum"), run_scrap=("run_scrap", "sum"))
jobs = jobs.join(totals, on="order").merge(printers[["work_center", "name"]], on="work_center")
jobs = jobs.rename(columns={"name": "printer"})
shifts = shifts.merge(jobs[["order", "printer"]], on="order")
d = pd.to_datetime(shifts.date)
shifts["week"] = (d - pd.to_timedelta(d.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")

CLEAN.mkdir(exist_ok=True)
jobs.to_csv(CLEAN / "job_cards_clean.csv", index=False)
shifts.to_csv(CLEAN / "job_card_shifts_clean.csv", index=False)

# ---------------------------------------------------------------- summarise
def rate(scrap, good):
    return scrap / (good + scrap)

groups = ["All"] + sorted(jobs.printer.unique())
def pick(df, p):
    return df if p == "All" else df[df.printer == p]

data = {"printers": groups, "summary": {}, "size": {}, "shift": {}, "artwork": {}, "weekly": {}, "checks": checks,
        "cost_per_cup": COST_PER_CUP}
for p in groups:
    j, s = pick(jobs, p), pick(shifts, p)
    setup, run, good = j.setup_scrap.sum(), j.run_scrap.sum(), j.printed.sum()
    data["summary"][p] = dict(jobs=len(j), printed=int(good), setup=int(setup), run=int(run),
                              scrap_rate=rate(setup + run, good), setup_share=setup / (setup + run),
                              avg_setup=setup / len(j), cost=(setup + run) * COST_PER_CUP)
    by = j.groupby("pallets").agg(good=("printed", "sum"), setup=("setup_scrap", "sum"), run=("run_scrap", "sum"))
    data["size"][p] = [dict(pallets=int(k), setup_rate=r.setup / (r.good + r.setup + r.run),
                            run_rate=r.run / (r.good + r.setup + r.run)) for k, r in by.iterrows()]
    by = s.groupby("shift").agg(good=("total_printed", "sum"), run=("run_scrap", "sum"))
    data["shift"][p] = [dict(shift=int(k), run_rate=rate(r.run, r.good)) for k, r in by.iterrows()]
    by = j.groupby("new_artwork").setup_scrap.mean()
    data["artwork"][p] = {"Repeat": by.get(False), "New": by.get(True)}
wk = shifts[shifts.week <= LAST_FULL_WEEK].groupby(["printer", "week"]).agg(good=("total_printed", "sum"), run=("run_scrap", "sum"))
for p in groups[1:]:
    data["weekly"][p] = [dict(week=w, run_rate=rate(r.run, r.good)) for (_, w), r in wk.loc[[p]].iterrows()]

# ---------------------------------------------------------------- charts
CHARTS.mkdir(parents=True, exist_ok=True)
BLUE, GREY, TEXT, MUTED = "#2563a8", "#c9ccd1", "#1f2328", "#59636e"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GREY,
                     "axes.spines.top": False, "axes.spines.right": False, "text.color": TEXT,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED})

def finish(fig, title, sub, name):
    fig.suptitle(title, x=0.02, y=0.98, ha="left", fontsize=14, fontweight="bold")
    fig.text(0.02, 0.905, sub, ha="left", color=MUTED, fontsize=10.5)
    fig.text(0.02, 0.015, "Simulated data · 1,765 job cards, Jul 6 – Oct 3, 2026", color=MUTED, fontsize=8.5)
    fig.savefig(CHARTS / name, dpi=150)
    plt.close(fig)

# 1 scrap by printer
fig, ax = plt.subplots(figsize=(8, 4.4)); fig.subplots_adjust(top=0.74, bottom=0.2, left=0.14, right=0.95)
ps = groups[1:]
setup = [data["summary"][p]["setup"] / 1000 for p in ps]
run = [data["summary"][p]["run"] / 1000 for p in ps]
worst = max(ps, key=lambda p: data["summary"][p]["avg_setup"])
ax.barh(ps, setup, color=[BLUE if p == worst else "#7ea6d3" for p in ps], label="Setup scrap")
ax.barh(ps, run, left=setup, color=GREY, label="Run scrap")
for i, p in enumerate(ps):
    ax.text(setup[i] + run[i] + 4, i, f"{setup[i] + run[i]:.0f}k", va="center", color=TEXT)
ax.invert_yaxis(); ax.set_xlabel("Cups scrapped (thousands)")
ax.set_xlim(0, max(a + b for a, b in zip(setup, run)) * 1.12)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=BLUE, label="Setup scrap"), Patch(color=GREY, label="Run scrap")],
          frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
ax.spines["left"].set_visible(False); ax.tick_params(left=False)
o = [data["summary"][p]["avg_setup"] for p in ps if p != worst]
finish(fig, f"{worst} wastes the most cups on setup",
       f"{data['summary'][worst]['avg_setup']:.0f} cups per setup vs about {sum(o) / len(o):.0f} on the other printers",
       "scrap_by_printer.png")

# 2 job size
fig, ax = plt.subplots(figsize=(8, 4.2)); fig.subplots_adjust(top=0.8, bottom=0.14, left=0.09, right=0.97)
sz = data["size"]["All"]
lab = [f"{r['pallets']} pallet{'s' if r['pallets'] > 1 else ''}" for r in sz]
sr = [r["setup_rate"] * 100 for r in sz]; rr = [r["run_rate"] * 100 for r in sz]
ax.bar(lab, sr, color=BLUE, width=0.55, label="Setup scrap")
ax.bar(lab, rr, bottom=sr, color=GREY, width=0.55, label="Run scrap")
for i in range(len(sz)):
    ax.text(i, sr[i] + rr[i] + 0.08, f"{sr[i] + rr[i]:.1f}%", ha="center", color=TEXT)
ax.set_ylabel("Scrap rate (%)"); ax.legend(frameon=False); ax.set_ylim(0, max(a + b for a, b in zip(sr, rr)) * 1.2)
finish(fig, "Small jobs scrap more, mostly from setup waste",
       f"{sr[0] + rr[0]:.1f}% of cups scrapped on {sz[0]['pallets']}-pallet jobs vs {sr[-1] + rr[-1]:.1f}% on {sz[-1]['pallets']}-pallet jobs",
       "scrap_by_job_size.png")

# 3 weekly run scrap
fig, ax = plt.subplots(figsize=(8, 4.2)); fig.subplots_adjust(top=0.8, bottom=0.14, left=0.09, right=0.84)
peak_p = max(ps, key=lambda p: max(r["run_rate"] for r in data["weekly"][p]))
for p in ps:
    rows = data["weekly"][p]
    x = pd.to_datetime([r["week"] for r in rows]); y = [r["run_rate"] * 100 for r in rows]
    hi = p == peak_p
    ax.plot(x, y, color=BLUE if hi else GREY, lw=2.5 if hi else 1.6, zorder=3 if hi else 2, marker="o", ms=3.5 if hi else 0)
    if hi:
        ax.text(x[-1], y[-1], f"  {p}", va="center", color=BLUE, fontweight="bold")
ax.text(x[-1], 0.75, "  Other printers", va="center", color=MUTED)
ax.set_ylabel("Run scrap rate (%)"); ax.set_ylim(0, None)
ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %d"))
top = max(r["run_rate"] for r in data["weekly"][peak_p]) * 100
finish(fig, f"{peak_p}'s run scrap tripled for four weeks, then recovered",
       f"Weekly run scrap rate peaked at {top:.1f}%; the other printers stayed near 1%", "weekly_run_scrap.png")

# ---------------------------------------------------------------- dashboard page
DOCS.mkdir(exist_ok=True)
html = TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", json.dumps(data, default=float))
(DOCS / "index.html").write_text(html, encoding="utf-8")
print("Saved charts to", CHARTS)
print("Saved dashboard to", DOCS / "index.html")
