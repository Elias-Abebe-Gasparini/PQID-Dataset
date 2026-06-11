from __future__ import annotations

import os
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.path import Path as MplPath
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, PathPatch, Rectangle
import numpy as np


ROOT = Path(__file__).resolve().parents[2]

_figure_dir_override = os.environ.get("PQID_SCI_DATA_FIGURE_DIR")
if _figure_dir_override:
    _figure_dir_path = Path(_figure_dir_override)
    FIGURE_DIR = (
        _figure_dir_path
        if _figure_dir_path.is_absolute()
        else ROOT / "submissions" / "scientific_data" / _figure_dir_path
    )
else:
    FIGURE_DIR = ROOT / "submissions" / "scientific_data" / "figures"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

_font_override = os.environ.get("PQID_SCI_DATA_FIGURE_FONT")
if _font_override:
    FONT_FAMILY = "sans-serif"
    FONT_STACK = [_font_override, "Calibri", "Arial", "Liberation Sans", "DejaVu Sans"]
else:
    FONT_FAMILY = "serif"
    FONT_STACK = ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"]
AVAILABLE_FONTS = {font.name for font in font_manager.fontManager.ttflist}
MANUSCRIPT_FONT = next((font for font in FONT_STACK if font in AVAILABLE_FONTS), "DejaVu Sans" if _font_override else "DejaVu Serif")

COLORS = {
    "ink": "#111827",
    "muted": "#5b6472",
    "hairline": "#d8dee8",
    "panel": "#f6f7f9",
    "navy": "#243b53",
    "blue": "#356da8",
    "teal": "#2a9d8f",
    "green": "#3f8f5f",
    "mint": "#cfeee1",
    "gold": "#e9c46a",
    "amber": "#c9852b",
    "coral": "#e76f51",
    "red": "#b94a48",
    "rose": "#f0c7c7",
    "violet": "#7b61a8",
    "slate": "#536276",
}

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.family": FONT_FAMILY,
        "font.serif": [MANUSCRIPT_FONT, "Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"],
        "font.sans-serif": [MANUSCRIPT_FONT, "Calibri", "Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 8.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def save(fig: plt.Figure, stem: str, pad_inches: float = 0.045) -> None:
    outputs = {
        "svg": FIGURE_DIR / f"{stem}.svg",
        "png": FIGURE_DIR / f"{stem}.png",
        "pdf": FIGURE_DIR / f"{stem}.pdf",
    }
    fig.savefig(outputs["svg"], bbox_inches="tight", pad_inches=pad_inches)
    fig.savefig(outputs["png"], dpi=450, bbox_inches="tight", pad_inches=pad_inches)
    fig.savefig(outputs["pdf"], bbox_inches="tight", pad_inches=pad_inches)
    plt.close(fig)
    for path in outputs.values():
        print(f"saved {path}")


def add_label(
    ax,
    x,
    y,
    text,
    size=8.5,
    weight="normal",
    color=None,
    ha="center",
    va="center",
    linespacing=1.1,
    zorder=5,
):
    ax.text(
        x,
        y,
        text,
        fontsize=size,
        fontweight=weight,
        color=color or COLORS["ink"],
        ha=ha,
        va=va,
        linespacing=linespacing,
        zorder=zorder,
    )


def panel_label(ax, label, x, y, text=None):
    ax.text(x, y, label, fontsize=12, fontweight="bold", ha="left", va="center", color=COLORS["ink"])
    if text:
        ax.text(x + 0.032, y, text, fontsize=8.5, fontweight="bold", ha="left", va="center", color=COLORS["ink"])


def rounded_box(ax, xy, width, height, fc, ec=None, radius=0.025, lw=0.9, alpha=1.0, zorder=2):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        linewidth=lw,
        edgecolor=ec or fc,
        facecolor=fc,
        alpha=alpha,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def ribbon(ax, x0, y0a, y0b, x1, y1a, y1b, color, alpha=0.62, curve=0.46, zorder=1):
    dx = x1 - x0
    verts = [
        (x0, y0a),
        (x0 + curve * dx, y0a),
        (x1 - curve * dx, y1a),
        (x1, y1a),
        (x1, y1b),
        (x1 - curve * dx, y1b),
        (x0 + curve * dx, y0b),
        (x0, y0b),
        (x0, y0a),
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.LINETO,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CLOSEPOLY,
    ]
    ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color, edgecolor="none", alpha=alpha, zorder=zorder))


def stack_positions(counts: list[float], y_min=0.14, y_max=0.86, gap=0.014):
    total = sum(counts)
    available = y_max - y_min - gap * (len(counts) - 1)
    heights = [available * count / total for count in counts]
    positions = []
    y = y_max
    for height in heights:
        positions.append((y - height, y))
        y -= height + gap
    return positions


def stack_positions_min_visible(counts: list[float], y_min=0.14, y_max=0.86, gap=0.014, min_height=0.0):
    total = sum(counts)
    available = y_max - y_min - gap * (len(counts) - 1)
    raw_heights = [available * count / total for count in counts]
    small = [idx for idx, height in enumerate(raw_heights) if height < min_height]
    large = [idx for idx in range(len(counts)) if idx not in small]
    heights = raw_heights[:]
    if small and large:
        remaining = max(available - min_height * len(small), available * 0.5)
        large_total = sum(counts[idx] for idx in large)
        for idx in small:
            heights[idx] = min_height
        for idx in large:
            heights[idx] = remaining * counts[idx] / large_total
    positions = []
    y = y_max
    for height in heights:
        positions.append((y - height, y))
        y -= height + gap
    return positions


def draw_bar(ax, x, y0, y1, color, width=0.018):
    ax.add_patch(Rectangle((x - width / 2, y0), width, y1 - y0, facecolor=color, edgecolor="white", lw=0.8, zorder=3))


def callout(ax, x, y, text, color=COLORS["muted"], ha="left"):
    rounded_box(ax, (x - 0.008, y - 0.028), 0.18, 0.056, "#ffffff", COLORS["hairline"], radius=0.013, lw=0.7, zorder=4)
    add_label(ax, x + 0.006, y, text, size=7.6, color=color, ha=ha, linespacing=1.05, zorder=6)


def flow_arrow(ax, start, end, color, lw=6.0, rad=0.0, alpha=0.55, zorder=1):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=6 + lw * 0.25,
            linewidth=lw,
            color=color,
            alpha=alpha,
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=0,
            shrinkB=0,
            capstyle="round",
            joinstyle="round",
            zorder=zorder,
        )
    )


def draw_figure_1():
    fig, ax = plt.subplots(figsize=(8.6, 2.45))
    ax.set_xlim(0, 1)
    ax.set_ylim(0.218, 0.805)
    ax.axis("off")

    panel_label(ax, "a", 0.035, 0.780, "construction stages")
    panel_label(ax, "b", 0.035, 0.320, "row-level evidence retained")

    stages = [
        ("GitHub API\nacquisition", "91,719\nsource records", "repository metadata\nand raw artifacts", COLORS["blue"]),
        ("Execution\nvalidation", "Qiskit + OpenQASM\n146 source keys", "runtime evidence\nand circuit structure", COLORS["teal"]),
        ("Instruction\nconstruction", "91,719 seeds\n458,595 paraphrases", "seed lineage and\nprompt policy", COLORS["gold"]),
        ("Human review\nand remediation", "209 accept / 47 rewrite\n282 remediations", "acceptance gate\nand rewrite closeout", COLORS["violet"]),
        ("Semantic and\nlanguage audit", "550,300 English\nsemantic metrics", "BERTScore, BLEU,\nROUGE-L, edit distance", COLORS["coral"]),
        ("License-filtered\nrelease", "422,580 license-valid\n414,522 permissive-only", "release bucket and\nrestriction evidence", COLORS["green"]),
    ]

    xs = np.linspace(0.095, 0.905, len(stages))
    ax.add_patch(FancyArrowPatch((0.055, 0.575), (0.945, 0.575), arrowstyle="-|>", mutation_scale=13, lw=1.5, color=COLORS["hairline"], zorder=0))

    for i, (x, (title, count, evidence, color)) in enumerate(zip(xs, stages), start=1):
        card_w, card_h = 0.128, 0.32
        x0, y0 = x - card_w / 2, 0.405
        rounded_box(ax, (x0, y0), card_w, card_h, "#ffffff", COLORS["hairline"], radius=0.018, lw=0.9)
        ax.add_patch(Rectangle((x0, y0 + card_h - 0.026), card_w, 0.026, facecolor=color, edgecolor="none", zorder=3))
        ax.add_patch(Circle((x, y0 + card_h - 0.026), 0.025, facecolor="white", edgecolor=color, linewidth=1.4, zorder=4))
        add_label(ax, x, y0 + card_h - 0.026, str(i), size=8.5, weight="bold", color=color)
        add_label(ax, x, y0 + 0.238, title, size=7.7, weight="bold", linespacing=1.0)
        add_label(ax, x, y0 + 0.142, count, size=6.6, color=COLORS["muted"], linespacing=1.05)
        add_label(ax, x, y0 + 0.058, evidence, size=6.25, color=COLORS["muted"], linespacing=1.05)

    evidence_items = [
        ("provenance", COLORS["blue"]),
        ("execution", COLORS["teal"]),
        ("generation", COLORS["gold"]),
        ("review", COLORS["violet"]),
        ("semantics", COLORS["coral"]),
        ("release", COLORS["green"]),
    ]
    ax.add_patch(Rectangle((0.08, 0.235), 0.84, 0.055, facecolor=COLORS["panel"], edgecolor="none", zorder=0))
    for i, (label, color) in enumerate(evidence_items):
        x = 0.105 + i * 0.139
        rounded_box(ax, (x, 0.246), 0.105, 0.032, "#ffffff", color, radius=0.012, lw=0.8)
        ax.add_patch(Circle((x + 0.014, 0.262), 0.0055, facecolor=color, edgecolor="none", zorder=5))
        add_label(ax, x + 0.027, 0.262, label, size=7.0, ha="left", color=COLORS["ink"])
    save(fig, "fig1_pqid_construction_pipeline_designed", pad_inches=0.018)


def draw_figure_2():
    fig, ax = plt.subplots(figsize=(8.6, 5.05))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    panel_label(ax, "a", 0.035, 0.94, "release stratification")
    panel_label(ax, "b", 0.035, 0.21, "license evidence classes")

    categories = [
        ("permissive", 414_522, COLORS["green"], "permissive\n414,522"),
        ("copyleft", 7_356, COLORS["amber"], "copyleft\n7,356"),
        ("reviewed other", 702, COLORS["violet"], "reviewed other\n702"),
        ("internal-only", 127_734, COLORS["red"], "no detected public license\n127,734"),
    ]
    counts = [item[1] for item in categories]
    left_pos = [(0.27, 0.84)]
    mid_pos = stack_positions_min_visible(counts, 0.27, 0.84, gap=0.018, min_height=0.026)
    right_pos = mid_pos
    x_left, x_mid, x_right = 0.12, 0.50, 0.86

    draw_bar(ax, x_left, *left_pos[0], COLORS["slate"], width=0.022)
    add_label(ax, x_left, 0.885, "internal object\n550,314 rows", size=8.6, weight="bold", linespacing=1.05)
    add_label(ax, x_mid, 0.885, "release evidence", size=8.6, weight="bold")
    add_label(ax, x_right, 0.885, "distribution treatment", size=8.6, weight="bold")

    for (_, _, color, _), pos in zip(categories, mid_pos):
        ribbon(ax, x_left + 0.012, left_pos[0][0], left_pos[0][1], x_mid - 0.014, pos[0], pos[1], color, alpha=0.25)
        draw_bar(ax, x_mid, *pos, color, width=0.024)

    for (label, _, color, annotation), src, dst in zip(categories, mid_pos, right_pos):
        ribbon(ax, x_mid + 0.014, src[0], src[1], x_right - 0.014, dst[0], dst[1], color, alpha=0.56)
        draw_bar(ax, x_right, *dst, color, width=0.024)
        y = (dst[0] + dst[1]) / 2
        label_size = 7.2 if label in {"copyleft", "reviewed other"} else 7.8
        display_annotation = annotation.replace("\n", " ") if label in {"copyleft", "reviewed other"} else annotation
        add_label(ax, x_mid + 0.04, y, display_annotation, size=label_size, ha="left", linespacing=1.0)
        if label == "permissive":
            add_label(ax, x_right + 0.04, y, "public-open", size=7.8, ha="left", linespacing=1.0)
        elif label == "internal-only":
            add_label(ax, x_right + 0.04, y, "internal-only", size=7.8, ha="left", linespacing=1.0)

    obligation_y = (mid_pos[1][0] + mid_pos[2][1]) / 2
    add_label(ax, x_right + 0.04, obligation_y, "license-valid\nwith obligations", size=7.35, ha="left", linespacing=1.0)

    detail = [
        ("permissive", "414,522", COLORS["green"]),
        ("copyleft", "7,356", COLORS["amber"]),
        ("reviewed\nother", "702", COLORS["violet"]),
        ("internal-only\nno detected public license", "127,734", COLORS["red"]),
    ]
    x0, y0 = 0.10, 0.075
    widths = [0.118, 0.112, 0.130, 0.205]
    for (label, count, color), width in zip(detail, widths):
        rounded_box(ax, (x0, y0), width, 0.074, "#ffffff", COLORS["hairline"], radius=0.014, lw=0.8)
        ax.add_patch(Rectangle((x0, y0), 0.014, 0.074, facecolor=color, edgecolor="none", zorder=4))
        add_label(ax, x0 + 0.025, y0 + 0.050, label, size=6.45, ha="left", linespacing=0.95)
        add_label(ax, x0 + 0.025, y0 + 0.021, count, size=6.55, ha="left", color=COLORS["muted"])
        x0 += width + 0.008

    add_label(ax, 0.735, 0.137, "license-valid view:\n422,580 rows", size=7.1, ha="left", color=COLORS["green"], linespacing=1.05)
    add_label(ax, 0.735, 0.080, "public-open view:\n414,522 permissive rows", size=7.1, ha="left", color=COLORS["muted"], linespacing=1.05)
    add_label(ax, 0.735, 0.025, "thin bands expanded for visibility;\ncounts are printed explicitly", size=6.45, ha="left", color=COLORS["muted"], linespacing=1.05)

    save(fig, "fig2_release_stratification_designed")


def draw_figure_3():
    fig, ax = plt.subplots(figsize=(8.7, 4.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    panel_label(ax, "a", 0.035, 0.935, "branching generation flow")
    panel_label(ax, "b", 0.035, 0.205, "quality controls")

    x0, x1, x2, x3 = 0.11, 0.40, 0.68, 0.89
    source_pos = (0.29, 0.82)
    branch_counts = [88_717, 3_002]
    branch_pos = stack_positions(branch_counts, 0.29, 0.82, gap=0.045)
    final_counts = [532_302, 18_012]
    final_pos = stack_positions(final_counts, 0.29, 0.82, gap=0.045)

    teacher_color = COLORS["blue"]
    source_color = COLORS["gold"]

    ribbon(ax, x0 + 0.012, source_pos[0], source_pos[1], x1 - 0.014, branch_pos[0][0], branch_pos[0][1], teacher_color, alpha=0.30)
    ribbon(ax, x0 + 0.012, source_pos[0], source_pos[1], x1 - 0.014, branch_pos[1][0], branch_pos[1][1], source_color, alpha=0.38)
    ribbon(ax, x1 + 0.014, branch_pos[0][0], branch_pos[0][1], x2 - 0.014, final_pos[0][0], final_pos[0][1], teacher_color, alpha=0.58)
    ribbon(ax, x1 + 0.014, branch_pos[1][0], branch_pos[1][1], x2 - 0.014, final_pos[1][0], final_pos[1][1], source_color, alpha=0.70)
    ribbon(ax, x2 + 0.014, final_pos[0][0], final_pos[0][1], x3 - 0.012, 0.31, 0.80, COLORS["teal"], alpha=0.22)
    ribbon(ax, x2 + 0.014, final_pos[1][0], final_pos[1][1], x3 - 0.012, 0.29, 0.31, COLORS["teal"], alpha=0.22)
    ax.add_patch(
        FancyArrowPatch(
            (x2 - 0.005, 0.835),
            (x1 + 0.020, 0.835),
            arrowstyle="-|>",
            mutation_scale=10,
            lw=1.1,
            color=COLORS["coral"],
            connectionstyle="arc3,rad=0.22",
            zorder=5,
        )
    )
    add_label(
        ax,
        (x1 + x2) / 2,
        0.910,
        "residual similarity retry loop",
        size=6.45,
        color=COLORS["coral"],
        linespacing=1.0,
    )

    for x, y0, y1, color in [
        (x0, *source_pos, COLORS["slate"]),
        (x1, *branch_pos[0], teacher_color),
        (x1, *branch_pos[1], source_color),
        (x2, *final_pos[0], teacher_color),
        (x2, *final_pos[1], source_color),
        (x3, 0.29, 0.80, COLORS["teal"]),
    ]:
        draw_bar(ax, x, y0, y1, color, width=0.024)

    add_label(ax, x0, 0.86, "seed-role manifest\n91,719 records", size=8.3, weight="bold", linespacing=1.05)
    add_label(ax, x3, 0.86, "canonical instruction object\n550,314 rows", size=8.3, weight="bold", linespacing=1.05)

    add_label(ax, x1 + 0.035, np.mean(branch_pos[0]), "teacher-text branch\n88,717 seeds", size=7.5, ha="left", linespacing=1.05)
    add_label(ax, x1 + 0.035, 0.258, "source-code branch\n3,002 seeds", size=7.1, ha="left", linespacing=1.0)
    add_label(ax, x2 + 0.035, np.mean(final_pos[0]), "teacher-text instructions\n532,302 rows", size=7.5, ha="left", linespacing=1.05)
    add_label(ax, x2 + 0.035, 0.248, "source-code instructions\n18,012 rows", size=7.1, ha="left", linespacing=1.0)

    controls = [
        ("teacher-text\nBatch API branch", COLORS["blue"]),
        ("source-code\nBatch API branch", COLORS["gold"]),
        ("progressive temperature\nretry loop", COLORS["coral"]),
        ("semantic diagnostics\nBERTScore / BLEU / ROUGE-L", COLORS["teal"]),
    ]
    x = 0.10
    for label, color in controls:
        rounded_box(ax, (x, 0.075), 0.19, 0.075, "#ffffff", COLORS["hairline"], radius=0.014, lw=0.8)
        ax.add_patch(Rectangle((x, 0.075), 0.012, 0.075, facecolor=color, edgecolor="none", zorder=4))
        add_label(ax, x + 0.025, 0.112, label, size=7.0, ha="left", linespacing=1.05)
        x += 0.205

    save(fig, "fig3_seed_generation_workflow_designed")


def draw_figure_4():
    fig, ax = plt.subplots(figsize=(8.7, 4.85))
    ax.set_xlim(0, 1)
    ax.set_ylim(0.035, 0.86)
    ax.axis("off")

    rows = [
        ("Execution validation", [3, 1, 0, 1], "Qiskit execution; materialized circuits; OpenQASM export"),
        ("Benchmark readiness", [3, 1, 0, 1], "n/7 and n/8 readiness gates"),
        ("Metadata design", [3, 2, 2, 3], "27 additive governance and split fields"),
        ("Acceptance gate", [0, 3, 3, 2], "209 accept / 47 rewrite pilot adjudication"),
        ("Remediation", [0, 2, 3, 2], "282 rewrite-tail and lineage-neighbor results"),
        ("Semantic diversity", [0, 1, 3, 2], "BERTScore, BLEU, ROUGE-L, edit distance"),
        ("Language audit", [0, 2, 3, 2], "550,300 / 550,314 inputs resolved as English"),
        ("Release integrity", [1, 2, 2, 3], "no no-license or missing-license rows in public views"),
    ]
    cols = ["source\ncorpus", "seed\nlayer", "paraphrase\nlayer", "release\nviews"]
    palette = {0: "#f3f4f6", 1: "#d8e7f8", 2: "#fff1bd", 3: "#cef2dd"}
    labels = {0: "n/a", 1: "source", 2: "audit", 3: "gate"}

    left, bottom = 0.235, 0.225
    cell_w, cell_h = 0.118, 0.066

    for j, col in enumerate(cols):
        add_label(ax, left + j * cell_w + cell_w / 2, bottom + len(rows) * cell_h + 0.048, col, size=7.7, weight="bold", linespacing=1.0)

    for i, (row_name, values, note) in enumerate(rows):
        y = bottom + (len(rows) - 1 - i) * cell_h
        add_label(ax, left - 0.020, y + cell_h / 2, row_name, size=7.7, ha="right", weight="bold")
        add_label(ax, left + len(cols) * cell_w + 0.028, y + cell_h / 2, note, size=7.05, ha="left", color=COLORS["muted"])
        for j, value in enumerate(values):
            x = left + j * cell_w
            ax.add_patch(Rectangle((x, y), cell_w - 0.005, cell_h - 0.005, facecolor=palette[value], edgecolor="white", lw=0.9, zorder=2))
            add_label(ax, x + cell_w / 2, y + cell_h / 2, labels[value], size=6.9, color=COLORS["ink"])

    add_label(
        ax,
        left,
        0.158,
        "Layers are shown by where they annotate or constrain the dataset object;\nhard gates control public-release eligibility.",
        size=7.2,
        color=COLORS["muted"],
        ha="left",
        linespacing=1.05,
    )

    legend_items = [("n/a", palette[0]), ("source evidence", palette[1]), ("audit evidence", palette[2]), ("hard gate", palette[3])]
    for k, (label, color) in enumerate(legend_items):
        x = 0.25 + k * 0.16
        y = 0.070
        ax.add_patch(Rectangle((x, y), 0.024, 0.024, facecolor=color, edgecolor="white", lw=0.8))
        add_label(ax, x + 0.031, y + 0.012, label, size=7.3, ha="left", color=COLORS["muted"])

    save(fig, "fig4_validation_audit_layers_designed", pad_inches=0.018)


def main():
    print(f"Using plot font: {MANUSCRIPT_FONT}")
    draw_figure_1()
    draw_figure_2()
    draw_figure_3()
    draw_figure_4()

    from sync_manuscript_figure_labels import sync_manuscript_figure_labels

    for target in sync_manuscript_figure_labels():
        print(f"synced {target}")


if __name__ == "__main__":
    main()
