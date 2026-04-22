"""
WallE3 VLM — Mission KPI Analysis
===================================
Reads sample CSV telemetry, computes KPIs, and generates a dashboard PNG.

Usage:
    python analytics/python/mission_kpi_analysis.py

Output:
    analytics/dashboard/kpi_dashboard.png

Data:
    analytics/sample_data/fact_missions.csv
    analytics/sample_data/fact_safety_events.csv
    analytics/sample_data/fact_inference_events.csv

KPIs computed (maps to docs/product/08_kpi_dashboard_spec.md):
    KPI-001  Mission Success Rate        (target ≥70% R0)
    KPI-002  Mean Mission Duration       (target ≤120s)
    KPI-003  Safety Intervention Rate    (target ≤1 per mission R0)
    KPI-004  Stuck Abort Rate            (target ≤20% R0)
    KPI-005  VLM Latency p50/p95         (target p50≤10s, p95≤15s)
    KPI-006  Target Not Found Rate       (inference-level)
    KPI-007  Operator Onboarding         (manual/hardcoded)
    KPI-008  System Uptime               (manual/hardcoded)
"""

import pathlib
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

BASE = pathlib.Path(__file__).parent.parent

# ── Load data ─────────────────────────────────────────────────────────────────
missions   = pd.read_csv(BASE / "sample_data/fact_missions.csv")
safety     = pd.read_csv(BASE / "sample_data/fact_safety_events.csv")
inference  = pd.read_csv(BASE / "sample_data/fact_inference_events.csv")

missions["start_ts"] = pd.to_datetime(missions["start_ts"])
missions["date"]     = missions["start_ts"].dt.date

# ── KPI calculations ───────────────────────────────────────────────────────────
success_rate   = (missions["outcome"] == "SUCCESS").mean() * 100
avg_duration   = missions["duration_s"].mean()
stuck_rate     = (missions["reason"] == "stuck_timeout_60s").mean() * 100

# Safety interventions per mission
collision_events = safety[safety["event_type"] == "collision_risk"]
interventions_per_mission = len(collision_events) / len(missions)

# VLM latency
valid_inf = inference[inference["output_valid"] == True]
latency_p50 = np.percentile(valid_inf["latency_ms"], 50) / 1000
latency_p95 = np.percentile(valid_inf["latency_ms"], 95) / 1000

# Target not found rate (per inference call)
target_not_found_rate = (inference["target_found"] == False).mean() * 100

# Daily success rate trend
daily = missions.groupby("date").apply(
    lambda x: (x["outcome"] == "SUCCESS").mean() * 100
).reset_index()
daily.columns = ["date", "success_rate"]

# Per-site summary
site_summary = missions.groupby("site_id").agg(
    total      = ("mission_id", "count"),
    successful = ("outcome", lambda x: (x == "SUCCESS").sum()),
    avg_dur    = ("duration_s", "mean"),
    avg_interventions = ("intervention_count", "mean"),
).reset_index()
site_summary["success_rate"] = site_summary["successful"] / site_summary["total"] * 100

# Safety severity distribution
sev_counts = safety["severity"].value_counts()

# ── Build dashboard figure ─────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 10), facecolor="#0f1117")
fig.suptitle("WallE3 VLM — KPI Dashboard\n(Sample Data: 2026-04-20 to 2026-04-22)",
             fontsize=15, color="white", y=0.98)

DARK   = "#0f1117"
PANEL  = "#1a1d2e"
GREEN  = "#22c55e"
YELLOW = "#eab308"
RED    = "#ef4444"
BLUE   = "#3b82f6"
CYAN   = "#06b6d4"
GRAY   = "#6b7280"
WHITE  = "#f3f4f6"

ax_color   = {"facecolor": PANEL}
text_kw    = {"color": WHITE, "fontsize": 10}

def kpi_color(val, green_thresh, yellow_thresh, higher_is_better=True):
    if higher_is_better:
        return GREEN if val >= green_thresh else (YELLOW if val >= yellow_thresh else RED)
    else:
        return GREEN if val <= green_thresh else (YELLOW if val <= yellow_thresh else RED)

gs = fig.add_gridspec(3, 4, hspace=0.55, wspace=0.4,
                      left=0.05, right=0.97, top=0.90, bottom=0.06)

# ── Row 0: KPI scorecards ──────────────────────────────────────────────────────
kpis = [
    ("Mission\nSuccess Rate",  f"{success_rate:.1f}%",   "target ≥70%",
     kpi_color(success_rate, 70, 50)),
    ("Mean Mission\nDuration", f"{avg_duration:.0f}s",   "target ≤120s",
     kpi_color(avg_duration, 120, 150, higher_is_better=False)),
    ("Stuck Abort\nRate",      f"{stuck_rate:.1f}%",     "target ≤20%",
     kpi_color(stuck_rate, 20, 30, higher_is_better=False)),
    ("Safety Events\n/Mission",f"{interventions_per_mission:.2f}", "target ≤1.0",
     kpi_color(interventions_per_mission, 1.0, 1.5, higher_is_better=False)),
]
for col, (title, value, target, color) in enumerate(kpis):
    ax = fig.add_subplot(gs[0, col], **ax_color)
    ax.set_xticks([]); ax.set_yticks([])
    ax.text(0.5, 0.72, value,  transform=ax.transAxes, ha="center", va="center",
            fontsize=26, fontweight="bold", color=color)
    ax.text(0.5, 0.38, title,  transform=ax.transAxes, ha="center", va="center",
            fontsize=10, color=WHITE)
    ax.text(0.5, 0.12, target, transform=ax.transAxes, ha="center", va="center",
            fontsize=8,  color=GRAY)
    for spine in ax.spines.values():
        spine.set_edgecolor(color)
        spine.set_linewidth(2)

# ── Row 1 left: Daily success rate trend ──────────────────────────────────────
ax1 = fig.add_subplot(gs[1, :2], **ax_color)
x = range(len(daily))
bars = ax1.bar(x, daily["success_rate"],
               color=[kpi_color(v, 70, 50) for v in daily["success_rate"]],
               width=0.5, zorder=2)
ax1.axhline(70, color=GREEN,  linestyle="--", linewidth=1, alpha=0.7, label="Target 70%")
ax1.axhline(50, color=YELLOW, linestyle=":",  linewidth=1, alpha=0.7, label="Warning 50%")
ax1.set_xticks(list(x)); ax1.set_xticklabels([str(d) for d in daily["date"]], color=WHITE, fontsize=8)
ax1.set_ylabel("Success Rate %", color=WHITE); ax1.tick_params(colors=WHITE)
ax1.set_ylim(0, 110); ax1.set_title("Daily Mission Success Rate", color=WHITE, fontsize=10)
ax1.legend(fontsize=7, loc="upper right", facecolor=PANEL, labelcolor=WHITE, framealpha=0.8)
ax1.yaxis.label.set_color(WHITE)
for spine in ax1.spines.values(): spine.set_edgecolor(GRAY)
ax1.set_facecolor(PANEL)

# ── Row 1 right: Safety severity distribution ──────────────────────────────────
ax2 = fig.add_subplot(gs[1, 2], **ax_color)
sev_labels = sev_counts.index.tolist()
sev_vals   = sev_counts.values
sev_colors = [RED if s == "CRITICAL" else YELLOW if s == "HIGH"
              else BLUE if s == "MEDIUM" else GRAY for s in sev_labels]
wedges, texts, autotexts = ax2.pie(
    sev_vals, labels=sev_labels, colors=sev_colors,
    autopct="%1.0f%%", pctdistance=0.75,
    textprops={"color": WHITE, "fontsize": 8},
    wedgeprops={"edgecolor": DARK, "linewidth": 2}
)
for at in autotexts: at.set_fontsize(8); at.set_color(DARK)
ax2.set_title("Safety Events\nby Severity", color=WHITE, fontsize=10)
ax2.set_facecolor(PANEL)

# ── Row 1 far right: VLM latency box ──────────────────────────────────────────
ax3 = fig.add_subplot(gs[1, 3], **ax_color)
ax3.set_xticks([]); ax3.set_yticks([])
ax3.text(0.5, 0.80, "VLM Latency",  transform=ax3.transAxes, ha="center",
         fontsize=10, color=WHITE)
ax3.text(0.5, 0.60, f"p50: {latency_p50:.1f}s", transform=ax3.transAxes, ha="center",
         fontsize=18, fontweight="bold",
         color=kpi_color(latency_p50, 10, 12, higher_is_better=False))
ax3.text(0.5, 0.38, f"p95: {latency_p95:.1f}s", transform=ax3.transAxes, ha="center",
         fontsize=16, fontweight="bold",
         color=kpi_color(latency_p95, 15, 18, higher_is_better=False))
ax3.text(0.5, 0.14, "target p50≤10s p95≤15s", transform=ax3.transAxes, ha="center",
         fontsize=7, color=GRAY)
for spine in ax3.spines.values(): spine.set_edgecolor(CYAN); spine.set_linewidth(2)

# ── Row 2 left: Per-site success rate ─────────────────────────────────────────
ax4 = fig.add_subplot(gs[2, :2], **ax_color)
sites = site_summary["site_id"].str.replace("_", "\n")
bars4 = ax4.bar(range(len(site_summary)), site_summary["success_rate"],
                color=[kpi_color(v, 70, 50) for v in site_summary["success_rate"]],
                width=0.5, zorder=2)
ax4.set_xticks(range(len(site_summary))); ax4.set_xticklabels(sites, color=WHITE, fontsize=7)
ax4.axhline(70, color=GREEN, linestyle="--", linewidth=1, alpha=0.7)
ax4.set_ylabel("Success Rate %", color=WHITE); ax4.tick_params(colors=WHITE)
ax4.set_ylim(0, 110); ax4.set_title("Success Rate by Site", color=WHITE, fontsize=10)
for spine in ax4.spines.values(): spine.set_edgecolor(GRAY)
ax4.set_facecolor(PANEL)

for bar, row in zip(bars4, site_summary.itertuples()):
    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
             f"n={row.total}", ha="center", va="bottom", fontsize=7, color=GRAY)

# ── Row 2 right: ROI summary ──────────────────────────────────────────────────
ax5 = fig.add_subplot(gs[2, 2:], **ax_color)
ax5.set_xticks([]); ax5.set_yticks([])
ax5.set_title("ROI Snapshot (portfolio assumptions)", color=WHITE, fontsize=10)

roi_lines = [
    ("Manual task time (baseline)",    "8 min / task"),
    ("Robot mission time (avg)",        f"{avg_duration:.0f}s / task"),
    ("Time saved per task",             f"{max(0, 480 - avg_duration):.0f}s ({max(0, (480-avg_duration)/480*100):.0f}%)"),
    ("Labor rate assumption",           "$6 USD/hr (VN warehouse)"),
    ("Successful missions (sample)",    f"{int(site_summary['successful'].sum())} / {int(site_summary['total'].sum())}"),
    ("Est. daily savings (sample)",     "~$3.60 USD / day"),
    ("Projected annual savings",        "~$900 USD / robot"),
    ("Break-even (robot cost $12k)",    "~13 months"),
]
for i, (label, value) in enumerate(roi_lines):
    y = 0.90 - i * 0.105
    ax5.text(0.02, y, label,  transform=ax5.transAxes, ha="left",  fontsize=8, color=GRAY)
    ax5.text(0.98, y, value,  transform=ax5.transAxes, ha="right", fontsize=8, color=WHITE,
             fontweight="bold")
for spine in ax5.spines.values(): spine.set_edgecolor(GREEN); spine.set_linewidth(1.5)

# ── Footer ────────────────────────────────────────────────────────────────────
fig.text(0.5, 0.01,
         "Data: analytics/sample_data/ | Telemetry schema: docs/product/09_event_contract_v1.md | "
         "KPI spec: docs/product/08_kpi_dashboard_spec.md",
         ha="center", fontsize=7, color=GRAY)

# ── Save ──────────────────────────────────────────────────────────────────────
out = BASE / "dashboard/kpi_dashboard.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=DARK)
print(f"Saved: {out}")
print(f"\nKPI Summary:")
print(f"  Mission Success Rate : {success_rate:.1f}%  (target ≥70%)")
print(f"  Mean Duration        : {avg_duration:.0f}s  (target ≤120s)")
print(f"  Stuck Abort Rate     : {stuck_rate:.1f}%  (target ≤20%)")
print(f"  Interventions/Mission: {interventions_per_mission:.2f}  (target ≤1.0)")
print(f"  VLM Latency p50      : {latency_p50:.1f}s  (target ≤10s)")
print(f"  VLM Latency p95      : {latency_p95:.1f}s  (target ≤15s)")
print(f"  Target Not Found     : {target_not_found_rate:.1f}% of inference calls")
