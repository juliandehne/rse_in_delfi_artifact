"""
Step 3 — Descriptive analysis (figures).

Ported from the source study's analysis/data_analysis/data_visualizations_paper.py.
Only the I/O paths are rewired to the artifact's ``data/`` layout and a headless
matplotlib backend is forced; the plotting logic is unchanged.

Produces:
  1. Bubble chart: research-paradigm distribution
     (reference 2014–2016 human vs LLM replication, and full 2003–2025 LLM set)
  2. Line plots: mean binary & ordinal label scores per year (2003–2025)

Reads:  data/reference_paper/Evaluationen3.xlsx, data/inter_LLM/<final>.csv
Writes: data/descriptive/figures/{research_paradigm_distribution,line_plots_binary_ordinal_labels}.png

Run standalone:
    python -m pipeline.step3_descriptive_analysis
"""

from __future__ import annotations

from collections import Counter
from difflib import get_close_matches

import matplotlib
matplotlib.use("Agg")  # headless: never open a window
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from pipeline import config

REFERENCE_EXCEL = config.REFERENCE_EXCEL
REPLICATION_CSV = config.FINAL_CSV
FIGURES_DIR = config.DESCRIPTIVE_DIR / "figures"

REFERENCE_COL_MAPPING = {
    "Einzelne Software":            "label_forschungssoftware",
    "Evaluation durchgeführt":      "label_software_evaluation",
    "Lehr-Lernsetting":             "label_lehr_lern_setting",
    "Fokus Medialität":             "label_prozess_paradigma",
    "Fokus Akzeptanz":              "label_bildungstechnologie_paradigma",
    "Fokus Innovation":             "label_design_paradigma",
    "Fokus Empirischer Lernerfolg": "label_lernende_paradigma",
}

# (DelFI Band, Beitragstitelseite) -> title for the 2014-2016 subset.
TITLE_MAPPING_SUBSET = {
    (2014, 109): "ScratchDrone – Systematische Programmierung von Flugdrohnen für den Informatikunterricht",
    (2014, 133): "Moodle-Plug-in zur Analyse und Kennzeichnung der Barrierefreiheit von PDF-Dokumenten",
    (2014, 145): "Automatische Generierung von Übungsgruppen auf Basis der Nutzung von Online-Ressourcen",
    (2014, 193): "WARP – ein Trainingssystem für UML-Aktivitätsdiagramme mit mehrschichtigem Feedback",
    (2014, 217): "Erfahrungen mit mobile Learning in der Hochschullehre – Vergleich zwischen Massenveranstaltung und Seminar",
    (2014, 259): "ÜPS – Ein autorenfreundliches Trainingssystem für SQLAnfragen",
    (2014, 301): "Die Evaluation generischer Einbettung automatisierter Programmbewertung am Beispiel von Moodle und aSQLg",
    (2015, 81): "Mobil in und aus Situationen lernen: Erste Erfahrungen zum Studieneinstieg von Studierenden verschiedener Fachrichtungen",
    (2015, 107): "Zirkus Empathico: Eine mobile Applikation zum Training sozioemotionaler Kompetenzen bei Kindern imA utismus-Spektrum",
    (2015, 119): "5Code– Eine integrierte Entwicklungsumgebung für Programmieranfänger",
    (2015, 131): "Adaptive Lehrvideos",
    (2015, 183): "CrumbIT! – Community-basierte Lernpfade durch den Online-Wissensdschungel",
    (2015, 241): "Die Erweiterung von Lernräumen durch Augmented Reality am Beispiel des Social Augmented Learning",
    (2015, 265): "Ein Online-System zur Regionalisierung der Fahrschulausbildung",
    (2015, 277): "Multitouch-Pursuit – Ein generisches Lernspiel für Tischcomputer",
    (2016, 23): "Interest-based Recommendation in Academic Networks using Social Network Analysis",
    (2016, 35): "Adaption und Evaluation eines virtuellen Klassenzimmers für Blinde",
    (2016, 59): "Das erste Semester von Studierenden der Wirtschafts- und Sozialwissenschaften im Spiegel der Reflect-App",
    (2016, 83): "ConceptCloud: Supporting Reflection in the Online Learning Environment Go-Lab",
    (2016, 93): "Design eines Spiels zum Lernen von Informationskompetenz",
    (2016, 107): "Das Technologieakzeptanzmodell für kartenbasierte Lernspiele in der Bildauswertung",
    (2016, 155): "Ein Autorensystem zur Erstellung von adaptiven mobilen Mikrolernanwendungen",
    (2016, 179): "HardDriveExchange– Eine VR-Lernanwendung zur Durchführung von Festplattenwechseln in Speichersystemen",
    (2016, 192): "Elektronische Abstimmungssysteme in der Hochschullehre–Empirische Untersuchung zu ersten Erfahrungen mit dem Audience Response System eduVote",
    (2016, 203): "Evaluation automatisierter Ansätze für die Bewertung von Modellierungsaufgaben",
    (2016, 233): "MoodlePeers: Automatisierte Lerngruppenbildung auf Grundlage psychologischer Merkmalsausprägungen in E-Learning-Systemen",
    (2016, 257): "Anforderungen und ein Rahmenkonzept für inklusive E-Learning Software",
}

plt.rcParams.update({
    "font.family": "serif", "font.size": 11, "axes.labelsize": 12,
    "axes.titlesize": 13, "legend.fontsize": 9.5, "xtick.labelsize": 10,
    "ytick.labelsize": 10, "figure.dpi": 300, "savefig.dpi": 300,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.1,
})


# ── Data loading ──────────────────────────────────────────────────────────────

def load_reference_subset():
    df = pd.read_excel(REFERENCE_EXCEL)
    df = df[df["DelFI Band"].isin([2014, 2015, 2016])].copy()
    unnamed = [c for c in df.columns if c.startswith("Unnamed:")]
    df = df.drop(columns=unnamed).rename(columns=REFERENCE_COL_MAPPING)
    df = df[(df["label_forschungssoftware"] == 1) &
            (df["label_software_evaluation"] == 1) &
            (df["label_lehr_lern_setting"] == 1)].copy()
    df["title"] = df.apply(
        lambda row: TITLE_MAPPING_SUBSET.get((row["DelFI Band"], row["Beitragstitelseite"])), axis=1)
    return df.dropna(subset=["title"]).reset_index(drop=True)


def load_replication_data():
    return pd.read_csv(REPLICATION_CSV)


def find_paper_in_llm_df(title, df, cutoff=0.85):
    exact = df[df["title"] == title]
    if not exact.empty:
        return exact
    ci = df[df["title"].str.lower() == title.lower()]
    if not ci.empty:
        return ci
    matches = get_close_matches(title, df["title"].dropna().tolist(), n=1, cutoff=cutoff)
    return df[df["title"] == matches[0]] if matches else pd.DataFrame()


def get_replication_subset(df_reference, df_replication):
    ids = []
    for title in df_reference["title"]:
        result = find_paper_in_llm_df(title, df_replication)
        if result.empty:
            raise ValueError(f"No match for: {title!r}")
        ids.append(int(result["id"].iloc[0]))
    return df_replication[df_replication["id"].isin(ids)].copy().reset_index(drop=True)


def get_replication_all_binary1(df_replication):
    mask = ((df_replication["label_forschungssoftware_final"] == 1) &
            (df_replication["label_software_evaluation_final"] == 1) &
            (df_replication["label_lehr_lern_setting_final"] == 1))
    return df_replication[mask].copy().reset_index(drop=True)


# ── Coordinate formula ──────────────────────────────────────────────────────────

def paradigm_contrast(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    result = np.zeros_like(a)
    mask2 = (a == -b) & (a != b)
    result[mask2] = -b[mask2]
    mask3 = (a + b == -1) & ~mask2 & (a != b)
    result[mask3] = 0.5 + a[mask3]
    mask4 = (a != b) & ~mask2 & ~mask3
    result[mask4] = a[mask4] - b[mask4]
    return result


def compute_paradigm_coordinates(df, design_col, outcome_col, process_col):
    return (paradigm_contrast(df[design_col].values, df[outcome_col].values),
            paradigm_contrast(df[process_col].values, df[design_col].values))


# ── Plot helpers ─────────────────────────────────────────────────────────────

def _apply_paradigm_axes(ax, title):
    ax.set_xlim(-1.25, 1.25); ax.set_ylim(-1.25, 1.25); ax.set_aspect("equal")
    ax.axhline(0, color="grey", linewidth=0.5, linestyle="--")
    ax.axvline(0, color="grey", linewidth=0.5, linestyle="--")
    ax.set_xticks([-1, -0.5, 0, 0.5, 1]); ax.set_yticks([-1, -0.5, 0, 0.5, 1])
    ax.set_xticklabels(["-1", "", "0", "", "+1"], fontsize=9)
    ax.set_yticklabels(["-1", "", "0", "", "+1"], fontsize=9)
    ax.grid(True, alpha=0.2); ax.set_title(title, fontweight="bold")
    ax.set_xlabel(""); ax.set_ylabel("")
    kw = dict(fontsize=10, fontstyle="italic", va="center")
    ax.text(-1.00, 1.15, "Process", ha="center", **kw)
    ax.text(1.00, 1.15, "Acceptance", ha="center", **kw)
    ax.text(-1.00, -1.15, "Outcome", ha="center", **kw)
    ax.text(1.00, -1.15, "Design", ha="center", **kw)


def plot_bubble_chart_improved(x, y, ax, title, max_count=None, size_scale=400, min_size=30):
    coords = list(zip(np.round(x, 2), np.round(y, 2)))
    counts = Counter(coords)
    xs = np.array([c[0] for c in counts]); ys = np.array([c[1] for c in counts])
    ns = np.array([counts[c] for c in counts])
    if max_count is None:
        max_count = max(ns)
    sizes = (ns / max_count) * size_scale + min_size
    norm = mcolors.PowerNorm(gamma=0.5, vmin=1, vmax=max_count)
    scatter = ax.scatter(xs, ys, s=sizes, c=ns, cmap="YlGnBu", norm=norm,
                         edgecolors="black", linewidths=0.5, alpha=0.85)
    for xi, yi, n in zip(xs, ys, ns):
        ax.text(xi, yi, str(n), ha="center", va="center", fontsize=7, fontweight="bold",
                color="white" if n > max_count * 0.6 else "black")
    _apply_paradigm_axes(ax, title)
    return scatter, ns


def add_unified_legend(ax, max_count, legend_ns, size_scale, min_size,
                       gamma=0.5, cmap_name="YlGnBu", legend_scale=0.6):
    norm = mcolors.PowerNorm(gamma=gamma, vmin=1, vmax=max_count)
    cmap = plt.cm.get_cmap(cmap_name)
    box = FancyBboxPatch((0.02, 0.02), 0.96, 0.96, boxstyle="round,pad=0.02",
                         facecolor="white", edgecolor="grey", linewidth=0.5, alpha=0.9,
                         transform=ax.transAxes, zorder=1)
    ax.add_patch(box)
    ax.text(0.5, 0.88, "Legend", fontsize=12, fontweight="bold", ha="center", va="top",
            transform=ax.transAxes, zorder=6)
    x_positions = np.linspace(0.15, 0.85, len(legend_ns))
    for n, xp in zip(legend_ns, x_positions):
        color = cmap(norm(n))
        area = (n / max_count) * size_scale + min_size
        ax.scatter([xp], [0.60], s=area * legend_scale ** 2, c=[color], edgecolors="black",
                   linewidths=0.5, transform=ax.transAxes, clip_on=False, zorder=4)
    ax.text(0.5, 0.32,
            "Larger bubbles and darker\ncolors indicate higher case\n"
            "numbers. The number of\n DELFI papers is\n represented within each bubble.",
            ha="center", va="center", fontsize=10, fontstyle="italic",
            transform=ax.transAxes, zorder=6)


def plot_line_charts(df_final):
    years = range(2003, 2026)
    binary_label_names = {
        "label_forschungssoftware_final": "Research Software",
        "label_software_evaluation_final": "Software Evaluation",
        "label_lehr_lern_setting_final": "Teaching-Learning Setting",
    }
    binary_colors = {"Research Software": "#E6007E", "Software Evaluation": "#FF9800",
                     "Teaching-Learning Setting": "#4CAF50"}
    proportions = {}
    for col, name in binary_label_names.items():
        proportions[name] = df_final.groupby("year")[col].mean().reindex(years, fill_value=None)

    ordinal_label_names = {
        "label_prozess_paradigma_final": "Process",
        "label_lernende_paradigma_final": "Outcome",
        "label_design_paradigma_final": "Design",
        "label_bildungstechnologie_paradigma_final": "Acceptance",
    }
    ordinal_colors = {"Process": "#00B4D8", "Outcome": "#6B8E23",
                      "Design": "#9B0058", "Acceptance": "#6B6B6B"}
    ordinal_proportions = {}
    for col, name in ordinal_label_names.items():
        ordinal_proportions[name] = df_final.groupby("year")[col].mean().reindex(years, fill_value=None)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8), sharex=True,
                                   gridspec_kw={"hspace": 0.35})
    for name, props in proportions.items():
        m, sd = props.mean(), props.std(ddof=0)
        ax1.plot(props.index, props.values, marker="o",
                 label=f"{name} ($\\mu$={m:.2f}, $\\sigma$={sd:.2f})",
                 color=binary_colors[name], linewidth=1.8, markersize=4)
    ax1.set_ylabel("Proportion"); ax1.set_ylim(0, 1.08); ax1.set_yticks(np.arange(0, 1.1, 0.2))
    ax1.legend(loc="lower left", framealpha=0.95, edgecolor="0.7", fancybox=True)
    ax1.set_title("(a) Binary Labels", loc="left", fontweight="bold", pad=12)
    ax1.grid(True, alpha=0.2, linewidth=0.5)
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

    for name, means in ordinal_proportions.items():
        m, sd = means.mean(), means.std(ddof=0)
        ax2.plot(means.index, means.values, marker="o",
                 label=f"{name} ($\\mu$={m:.2f}, $\\sigma$={sd:.2f})",
                 color=ordinal_colors[name], linewidth=1.8, markersize=4)
    ax2.set_ylabel("Mean Score"); ax2.set_xlabel("Year")
    ax2.set_ylim(-1.1, 1.1); ax2.set_yticks(np.arange(-1.0, 1.1, 0.2))
    ax2.axhline(y=0, color="grey", linewidth=0.6, linestyle="--", alpha=0.4)
    ax2.legend(loc="lower left", framealpha=0.95, edgecolor="0.7", fancybox=True)
    ax2.set_title("(b) Ordinal Labels", loc="left", fontweight="bold", pad=12)
    ax2.grid(True, alpha=0.2, linewidth=0.5)
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    odd_years = [y for y in years if y % 2 != 0]
    even_years = [y for y in years if y % 2 == 0]
    ax2.set_xlim(2002.5, 2025.5); ax2.set_xticks(odd_years)
    ax2.set_xticklabels(odd_years, rotation=45, ha="right")
    ax2.set_xticks(even_years, minor=True)
    ax2.tick_params(axis="x", which="minor", length=3, color="0.5")

    out_png = FIGURES_DIR / "line_plots_binary_ordinal_labels.png"
    plt.savefig(out_png, dpi=300); plt.close(fig)
    print(f"  Saved: {out_png}")


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    df_reference = load_reference_subset()
    df_replication = load_replication_data()
    df_replication_subset = get_replication_subset(df_reference, df_replication)
    df_replication_all_b1 = get_replication_all_binary1(df_replication)

    print(f"  Reference (2014-2016 subset):    n={len(df_reference)}")
    print(f"  Replication (same papers, LLM):  n={len(df_replication_subset)}")
    print(f"  Replication (all binary=1, LLM): n={len(df_replication_all_b1)}")

    x_ref, y_ref = compute_paradigm_coordinates(
        df_reference, "label_design_paradigma", "label_lernende_paradigma", "label_prozess_paradigma")
    x_rep_sub, y_rep_sub = compute_paradigm_coordinates(
        df_replication_subset, "label_design_paradigma_final",
        "label_lernende_paradigma_final", "label_prozess_paradigma_final")
    x_rep_all, y_rep_all = compute_paradigm_coordinates(
        df_replication_all_b1, "label_design_paradigma_final",
        "label_lernende_paradigma_final", "label_prozess_paradigma_final")

    subset_coords = [list(zip(np.round(x_ref, 2), np.round(y_ref, 2))),
                     list(zip(np.round(x_rep_sub, 2), np.round(y_rep_sub, 2)))]
    subset_max = max(max(Counter(c).values()) for c in subset_coords)
    all_max = max(Counter(list(zip(np.round(x_rep_all, 2), np.round(y_rep_all, 2)))).values())

    top_ss, top_ms = 1400, 150
    bot_ss, bot_ms = 1800, 200
    fig = plt.figure(figsize=(15, 12))
    ax1 = fig.add_axes([0.05, 0.53, 0.42, 0.40])
    ax2 = fig.add_axes([0.53, 0.53, 0.42, 0.40])
    plot_bubble_chart_improved(x_ref, y_ref, ax1,
        f"Reference Study\n(2014–2016, Human Annotations, n={len(x_ref)})",
        max_count=subset_max, size_scale=top_ss, min_size=top_ms)
    plot_bubble_chart_improved(x_rep_sub, y_rep_sub, ax2,
        f"Replication Study\n(2014–2016, LLM Annotations, n={len(x_rep_sub)})",
        max_count=subset_max, size_scale=top_ss, min_size=top_ms)
    bot_width = 0.42; bot_left = 0.5 - bot_width / 2
    ax3 = fig.add_axes([bot_left, 0.04, bot_width, 0.42])
    plot_bubble_chart_improved(x_rep_all, y_rep_all, ax3,
        f"Replication Study\n(2003–2025, LLM Annotations, n={len(x_rep_all)})",
        max_count=all_max, size_scale=bot_ss, min_size=bot_ms)
    ax_leg = fig.add_axes([0.75, 0.06, 0.16, 0.30]); ax_leg.axis("off")
    add_unified_legend(ax_leg, all_max, [1, 25, 50, 100, 150], bot_ss, bot_ms, legend_scale=0.35)
    out_png = FIGURES_DIR / "research_paradigm_distribution.png"
    plt.savefig(out_png, dpi=300); plt.close(fig)
    print(f"  Saved: {out_png}")

    plot_line_charts(df_replication)
    print("Step 3 done.")


if __name__ == "__main__":
    main()
