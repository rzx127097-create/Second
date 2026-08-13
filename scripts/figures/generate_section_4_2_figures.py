"""Generate the Section 4.2 heterogeneous decision-model schematic."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts" / "figures" / "chapter4"
STEM = "fig4-3_heterogeneous_decision_model"

COLORS = {
    "ink": "#263238",
    "muted": "#66747C",
    "line": "#8B979E",
    "navy": "#4A708B",
    "navy_light": "#E7EEF3",
    "teal": "#5E9D98",
    "teal_light": "#E5F0EF",
    "green": "#7CA27E",
    "green_light": "#E9F1E7",
    "gold": "#D6B65E",
    "gold_light": "#F7F1DE",
    "orange": "#C98D52",
    "orange_light": "#F6EDE4",
    "red": "#B9655F",
    "red_light": "#F4E7E5",
    "gray": "#E9ECEE",
    "white": "#FFFFFF",
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        # Arial does not contain Chinese glyphs. Put the thesis-safe CJK font
        # first and retain Arial/DejaVu Sans as Latin and math fallbacks.
        "font.sans-serif": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
        "font.size": 7.2,
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    }
)


def box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    face: str,
    edge: str,
    size: float = 7.2,
    weight: str = "normal",
    zorder: int = 3,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.009,rounding_size=0.014",
        facecolor=face,
        edgecolor=edge,
        linewidth=0.9,
        zorder=zorder,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=size,
        fontweight=weight,
        color=COLORS["ink"],
        linespacing=1.22,
        zorder=zorder + 1,
    )
    return patch


def arrow(
    ax,
    start,
    end,
    *,
    color: str = COLORS["line"],
    lw: float = 1.1,
    dashed: bool = False,
    rad: float = 0.0,
    mutation_scale: float = 8.5,
    zorder: int = 5,
):
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=mutation_scale,
        color=color,
        linewidth=lw,
        linestyle=(0, (3, 2)) if dashed else "solid",
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=1.5,
        shrinkB=1.5,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def build_figure() -> plt.Figure:
    """Build a two-panel schematic at final thesis-column proportions."""
    fig = plt.figure(figsize=(7.2, 5.2), constrained_layout=False)
    ax = fig.add_axes([0.025, 0.025, 0.95, 0.95])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Panel a: one complete decision-step sequence.
    ax.text(0.012, 0.975, "a", fontsize=8.5, fontweight="bold", va="top", color=COLORS["ink"])
    ax.text(0.050, 0.973, "单决策步的状态转移时序", fontsize=8.0, fontweight="bold", va="top", color=COLORS["ink"])
    ax.text(0.985, 0.973, r"状态  $t$  →  状态  $t+1$", fontsize=7.4, ha="right", va="top", color=COLORS["muted"])

    top = [
        ("状态读取与\n掩码生成", COLORS["gray"], COLORS["line"]),
        ("空地角色\n联合采样", COLORS["navy_light"], COLORS["navy"]),
        ("目标解码、预约\n与最短路构造", COLORS["teal_light"], COLORS["teal"]),
        ("无人机动作与\n车辆路网推进", COLORS["orange_light"], COLORS["orange"]),
        ("准备计时或\n药液转移", COLORS["red_light"], COLORS["red"]),
    ]
    # The second row is read from right to left after the top row drops at its
    # right edge: resources -> ecology -> requests -> arrival -> reward/log.
    bottom = [
        ("团队奖励、终止\n与完整事件日志", COLORS["gray"], COLORS["line"]),
        ("联合到达检查\n建立下一步锁定", COLORS["teal_light"], COLORS["teal"]),
        ("请求生成或更新\n候选有效性检查", COLORS["gold_light"], COLORS["gold"]),
        ("虫害、风场与\n药效状态更新", COLORS["green_light"], COLORS["green"]),
        ("资源与药剂场\n同步更新", COLORS["red_light"], COLORS["red"]),
    ]
    xs = [0.035, 0.225, 0.415, 0.605, 0.795]
    w, h = 0.155, 0.090
    y_top, y_bottom = 0.815, 0.665
    for idx, (text_value, face, edge) in enumerate(top):
        box(ax, xs[idx], y_top, w, h, text_value, face=face, edge=edge, size=7.2, weight="bold" if idx in (1, 2) else "normal")
        if idx < 4:
            arrow(ax, (xs[idx] + w, y_top + h / 2), (xs[idx + 1], y_top + h / 2))
    arrow(ax, (xs[-1] + w / 2, y_top), (xs[-1] + w / 2, y_bottom + h), color=COLORS["red"])
    for idx in range(4, -1, -1):
        text_value, face, edge = bottom[idx]
        box(ax, xs[idx], y_bottom, w, h, text_value, face=face, edge=edge, size=7.2)
        if idx > 0:
            arrow(ax, (xs[idx], y_bottom + h / 2), (xs[idx - 1] + w, y_bottom + h / 2))
    ax.text(0.505, 0.625, "本步新请求从下一决策步进入车辆候选集合；首次联合到达不在本步完成补给", ha="center", va="center", fontsize=7.2, color=COLORS["muted"])

    # Divider between the two logically independent panels.
    ax.plot([0.02, 0.98], [0.585, 0.585], color="#D8DDE0", lw=0.8)

    # Panel b: CTDE information boundary.
    ax.text(0.012, 0.555, "b", fontsize=8.5, fontweight="bold", va="top", color=COLORS["ink"])
    ax.text(0.050, 0.553, "空地异构Dec-POMDP与SR-MAPPO训练闭环", fontsize=8.0, fontweight="bold", va="top", color=COLORS["ink"])

    box(ax, 0.040, 0.405, 0.165, 0.090, "无人机局部观测\n虫害 · 资源 · 接驳", face=COLORS["navy_light"], edge=COLORS["navy"], size=7.2)
    box(ax, 0.040, 0.245, 0.165, 0.090, "车辆局部观测\n道路 · 库存 · 请求", face=COLORS["orange_light"], edge=COLORS["orange"], size=7.2)

    box(ax, 0.270, 0.405, 0.145, 0.090, "无人机actor\n共享角色参数", face=COLORS["navy_light"], edge=COLORS["navy"], size=7.2, weight="bold")
    box(ax, 0.270, 0.245, 0.145, 0.090, "车辆actor\n独立角色参数", face=COLORS["orange_light"], edge=COLORS["orange"], size=7.2, weight="bold")

    box(ax, 0.480, 0.405, 0.150, 0.090, "无人机动作与掩码\n移动 · 驻留 · 施药", face=COLORS["navy_light"], edge=COLORS["navy"], size=7.2)
    box(ax, 0.480, 0.245, 0.150, 0.090, "车辆动作与掩码\n保持 / 候选槽位", face=COLORS["orange_light"], edge=COLORS["orange"], size=7.2)

    box(ax, 0.700, 0.325, 0.185, 0.110, "统一环境转移\n道路 · 服务 · 药液\n虫害与药效演化", face=COLORS["green_light"], edge=COLORS["green"], size=7.2, weight="bold")
    box(ax, 0.700, 0.140, 0.185, 0.075, r"共享团队奖励  $r_t$", face=COLORS["red_light"], edge=COLORS["red"], size=7.4, weight="bold")
    box(ax, 0.300, 0.095, 0.215, 0.085, "结构化全局状态  $s_t$\n仅用于集中训练", face=COLORS["teal_light"], edge=COLORS["teal"], size=7.4)
    box(ax, 0.545, 0.095, 0.130, 0.085, "中央评论家\n$V(s_t)$", face=COLORS["teal_light"], edge=COLORS["teal"], size=7.4, weight="bold")

    # Solid execution path.
    for y, color in ((0.45, COLORS["navy"]), (0.29, COLORS["orange"])):
        arrow(ax, (0.205, y), (0.268, y), color=color, lw=1.25)
        arrow(ax, (0.415, y), (0.478, y), color=color, lw=1.25)
    arrow(ax, (0.630, 0.45), (0.698, 0.395), color=COLORS["navy"], lw=1.25, rad=0.04)
    arrow(ax, (0.630, 0.29), (0.698, 0.365), color=COLORS["orange"], lw=1.25, rad=-0.04)
    arrow(ax, (0.793, 0.323), (0.793, 0.217), color=COLORS["red"], lw=1.25)
    arrow(ax, (0.884, 0.365), (0.930, 0.365), color=COLORS["green"], lw=1.1)
    ax.text(0.935, 0.365, r"$s_{t+1}$", fontsize=7.4, va="center", color=COLORS["green"], fontweight="bold")

    # Dashed training-only path. No critic arrows enter actor inputs.
    arrow(ax, (0.515, 0.138), (0.543, 0.138), color=COLORS["teal"], dashed=True, lw=1.15)
    arrow(ax, (0.700, 0.177), (0.678, 0.138), color=COLORS["red"], dashed=True, lw=1.0, rad=0.10)
    arrow(ax, (0.610, 0.182), (0.345, 0.403), color=COLORS["teal"], dashed=True, lw=1.0, rad=-0.16)
    arrow(ax, (0.610, 0.182), (0.345, 0.337), color=COLORS["teal"], dashed=True, lw=1.0, rad=0.14)
    ax.text(0.585, 0.198, "团队GAE与角色策略更新", fontsize=7.2, ha="center", color=COLORS["teal"])

    # Observation feedback follows the panel boundary, avoiding title and box
    # collisions while preserving the environment-to-observation semantics.
    feedback_style = {"color": COLORS["line"], "lw": 0.85, "linestyle": "solid", "zorder": 2}
    ax.plot([0.920, 0.955, 0.955, 0.205], [0.405, 0.405, 0.515, 0.515], **feedback_style)
    arrow(ax, (0.205, 0.515), (0.205, 0.495), color=COLORS["line"], dashed=False, lw=0.85, rad=0.0)
    ax.plot([0.920, 0.955, 0.955, 0.205], [0.345, 0.345, 0.235, 0.235], **feedback_style)
    arrow(ax, (0.205, 0.235), (0.205, 0.245), color=COLORS["line"], dashed=False, lw=0.85, rad=0.0)
    ax.text(0.930, 0.300, "下一步\n局部观测", fontsize=7.2, ha="center", color=COLORS["muted"], linespacing=1.15)

    # Compact legend.
    ax.plot([0.040, 0.105], [0.050, 0.050], color=COLORS["ink"], lw=1.2)
    ax.text(0.115, 0.050, "执行阶段直接传递", fontsize=7.2, va="center", color=COLORS["muted"])
    ax.plot([0.270, 0.335], [0.050, 0.050], color=COLORS["ink"], lw=1.0, linestyle=(0, (3, 2)))
    ax.text(0.345, 0.050, "训练阶段信息连接", fontsize=7.2, va="center", color=COLORS["muted"])
    ax.text(0.975, 0.050, "actor执行时不访问全局状态或中央评论家", fontsize=7.2, ha="right", va="center", color=COLORS["muted"])

    return fig


def export(fig: plt.Figure) -> list[Path]:
    """Export editable vectors and 600 dpi raster previews."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUT_DIR / STEM
    outputs: list[Path] = []
    svg_path = base.with_suffix(".svg")
    pdf_path = base.with_suffix(".pdf")
    png_path = base.with_suffix(".png")
    tiff_path = base.with_suffix(".tiff")
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.04, facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.04, facecolor="white")
    fig.savefig(png_path, dpi=600, bbox_inches="tight", pad_inches=0.04, facecolor="white")
    fig.savefig(tiff_path, dpi=600, bbox_inches="tight", pad_inches=0.04, facecolor="white")
    outputs.extend((svg_path, pdf_path, png_path, tiff_path))
    plt.close(fig)
    return outputs


def main() -> None:
    for output in export(build_figure()):
        print(output)


if __name__ == "__main__":
    main()
