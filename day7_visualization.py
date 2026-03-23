import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

df = pd.read_csv("data/clean_analysis_dataset.csv")

STRESS     = ["Nigeria", "Argentina", "Turkey", "Egypt", "Venezuela"]
BENCHMARKS = ["United States", "India"]
ALL        = STRESS + BENCHMARKS

COLORS = {
    "Nigeria":       "#E63946",
    "Argentina":     "#457B9D",
    "Turkey":        "#F4A261",
    "Egypt":         "#2A9D8F",
    "Venezuela":     "#9B2226",
    "United States": "#606C38",
    "India":         "#BC6C25",
}
MARKERS = {c: m for c, m in zip(ALL, ["o","s","^","D","v","P","*"])}
df_viz = df[df["country"].isin(ALL)].copy()

fig = plt.figure(figsize=(20, 16))
fig.patch.set_facecolor("#0F1117")
gs = gridspec.GridSpec(3, 4, figure=fig,
    hspace=0.55, wspace=0.4, height_ratios=[1.2, 1.2, 0.08])

# Chart 1: Small multiples
small_countries = ["Nigeria", "Egypt", "United States", "India"]
small_labels = {
    "Nigeria":       "Nigeria (stress economy)",
    "Egypt":         "Egypt (stress economy)",
    "United States": "United States (benchmark)",
    "India":         "India (benchmark)",
}
for idx, country in enumerate(small_countries):
    ax = fig.add_subplot(gs[0, idx])
    ax.set_facecolor("#1A1D27")
    sub = df_viz[
        (df_viz["country"] == country) &
        df_viz["inflation_pct"].notna() &
        df_viz["crypto_demand_score"].notna()
    ]
    color = COLORS[country]
    ax.scatter(sub["inflation_pct"], sub["crypto_demand_score"],
               color=color, s=90, edgecolors="white",
               linewidths=0.5, zorder=3)
    for _, row in sub.iterrows():
        ax.annotate(str(int(row["year"])),
            (row["inflation_pct"], row["crypto_demand_score"]),
            fontsize=6, color="#AAAAAA",
            xytext=(3, 3), textcoords="offset points")
    if len(sub) >= 3:
        z = np.polyfit(sub["inflation_pct"],
                       sub["crypto_demand_score"], 1)
        p = np.poly1d(z)
        x_line = np.linspace(sub["inflation_pct"].min(),
                             sub["inflation_pct"].max(), 50)
        ax.plot(x_line, p(x_line), "--",
                color="white", alpha=0.3, linewidth=1)
        r, pval = stats.pearsonr(sub["inflation_pct"],
                                 sub["crypto_demand_score"])
        ax.text(0.05, 0.92, f"r={r:+.2f} (n={len(sub)})",
                transform=ax.transAxes, fontsize=7,
                color="#AAAAAA", va="top")
    ax.set_title(small_labels[country],
                 color="white", fontsize=9, fontweight="bold")
    ax.set_xlabel("Inflation (%)", color="#AAAAAA", fontsize=8)
    if idx == 0:
        ax.set_ylabel("Within-country normalized\nsearch demand",
                      color="#AAAAAA", fontsize=7)
    ax.tick_params(colors="#AAAAAA", labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333344")

# Chart 2: Inflation Timeline
ax2 = fig.add_subplot(gs[1, 0:2])
ax2.set_facecolor("#1A1D27")
for country in ALL:
    if country == "Venezuela":
        continue
    sub = df_viz[df_viz["country"] == country].sort_values("year")
    if sub.empty:
        continue
    style = "--" if country in BENCHMARKS else "-"
    lw    = 1.5 if country in BENCHMARKS else 2.5
    ax2.plot(sub["year"], sub["inflation_pct"],
             color=COLORS[country], label=country,
             linewidth=lw, linestyle=style,
             marker=MARKERS[country], markersize=5)
ax2.axhline(y=20, color="#FF6B6B", linestyle=":",
            alpha=0.6, linewidth=1)
ax2.text(2019.1, 21, "High stress threshold (20%)",
         color="#FF6B6B", fontsize=7, alpha=0.8)
ax2.set_title("Inflation Timeline — Stress vs Benchmark Economies\n"
              "(Venezuela excluded: 19,906% peak 2019)",
              color="white", fontsize=10, fontweight="bold")
ax2.set_xlabel("Year", color="#AAAAAA", fontsize=9)
ax2.set_ylabel("Inflation Rate (%)", color="#AAAAAA", fontsize=9)
ax2.tick_params(colors="#AAAAAA")
for spine in ax2.spines.values():
    spine.set_edgecolor("#333344")
legend_elements = (
    [Line2D([0],[0], color=COLORS[c], linewidth=2,
             marker=MARKERS[c], markersize=5, label=c)
     for c in STRESS if c != "Venezuela"] +
    [Line2D([0],[0], color=COLORS[c], linewidth=1.5,
             linestyle="--", marker=MARKERS[c], markersize=5,
             label=f"{c} (benchmark)")
     for c in BENCHMARKS]
)
ax2.legend(handles=legend_elements, fontsize=7,
           facecolor="#1A1D27", labelcolor="white",
           framealpha=0.8, ncol=2)

# Chart 3: Heatmap
ax3 = fig.add_subplot(gs[1, 2])
ax3.set_facecolor("#1A1D27")
heatmap_order = ["Nigeria","Argentina","Turkey",
                 "Egypt","Venezuela","United States","India"]
df_heat = df_viz[df_viz["country"].isin(heatmap_order)].copy()
pivot = df_heat.pivot_table(index="country", columns="year",
    values="crypto_demand_score", aggfunc="mean")
pivot = pivot.reindex(heatmap_order)
im = ax3.imshow(pivot.values, cmap="YlOrRd",
                aspect="auto", vmin=0, vmax=1)
ax3.set_xticks(range(len(pivot.columns)))
ax3.set_xticklabels(pivot.columns, color="#AAAAAA", fontsize=8)
ax3.set_yticks(range(len(pivot.index)))
ax3.set_yticklabels(pivot.index, color="#AAAAAA", fontsize=8)
for i in range(len(pivot.index)):
    for j in range(len(pivot.columns)):
        val = pivot.values[i, j]
        if not np.isnan(val):
            ax3.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=7,
                    color="black" if val > 0.6 else "white")
cb = plt.colorbar(im, ax=ax3, fraction=0.046, pad=0.04)
cb.ax.tick_params(colors="#AAAAAA", labelsize=7)
cb.set_label("Within-country normalized",
             color="#AAAAAA", fontsize=7)
ax3.set_title("Crypto Search Demand Heatmap\n"
              "(Venezuela: descriptive only)",
              color="white", fontsize=10, fontweight="bold")

# Chart 4: Nigeria Deep-Dive
ax4 = fig.add_subplot(gs[1, 3])
ax4.set_facecolor("#1A1D27")
nga = df_viz[df_viz["iso3"] == "NGA"].sort_values("year")
ax4_twin = ax4.twinx()
line1, = ax4.plot(nga["year"], nga["inflation_pct"],
    color="#F4A261", linewidth=2.5,
    marker="o", markersize=5, label="Inflation (%)")
line2, = ax4_twin.plot(nga["year"], nga["crypto_demand_score"],
    color="#E63946", linewidth=2.5,
    marker="s", markersize=5,
    linestyle="--", label="Search Demand (normalized)")
ax4.set_title("Nigeria Case Study\nInflation & search demand moved\ntogether most clearly (n=6, exploratory)",
              color="white", fontsize=9, fontweight="bold")
ax4.set_xlabel("Year", color="#AAAAAA", fontsize=9)
ax4.set_ylabel("Inflation Rate (%)", color="#F4A261", fontsize=9)
ax4_twin.set_ylabel("Within-country\nnormalized demand",
                    color="#E63946", fontsize=8)
ax4.tick_params(colors="#AAAAAA")
ax4_twin.tick_params(colors="#E63946")
for spine in ax4.spines.values():
    spine.set_edgecolor("#333344")
lines  = [line1, line2]
labels = [l.get_label() for l in lines]
ax4.legend(lines, labels, fontsize=7, facecolor="#1A1D27",
           labelcolor="white", framealpha=0.8)
ax4.text(0.05, 0.05,
         "Exploratory association only\nNot a causal claim",
         transform=ax4.transAxes, fontsize=7,
         color="#888888", va="bottom")

# Footer
ax_footer = fig.add_subplot(gs[2, :])
ax_footer.axis("off")
ax_footer.text(0.5, 0.5,
    "Sources: IMF World Economic Outlook, World Bank, Google Trends, "
    "Chainalysis Global Crypto Adoption Index  |  Annual country-level "
    "view, 2019–2024  |  Search demand normalized within country  |  "
    "Venezuela in heatmap only (hyperinflation scale distortion)  |  "
    "Findings exploratory and non-causal",
    ha="center", va="center",
    transform=ax_footer.transAxes,
    fontsize=7, color="#666666")

fig.suptitle(
    "Tracking Currency Stress with Alternative Data\n"
    "A Cross-Country Macro Monitoring Framework  |  "
    "Stress economies vs benchmark controls  |  2019–2024",
    color="white", fontsize=13, fontweight="bold", y=0.99)

plt.savefig("data/dashboard_v2.png", dpi=150,
            bbox_inches="tight", facecolor="#0F1117")
plt.show()
print("✓ Saved → data/dashboard_v2.png")