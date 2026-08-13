"""Generate the two conceptual figures for thesis section 4.1."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts" / "figures" / "chapter4"

COLORS = {
    "ink": "#263238",
    "muted": "#68757D",
    "line": "#8A969D",
    "navy": "#4A708B",
    "teal": "#65A6A1",
    "green": "#80AD86",
    "green_light": "#E9F1E6",
    "yellow": "#E8C66A",
    "orange": "#D69A55",
    "red": "#C66A62",
    "red_light": "#F5E8E5",
    "blue_light": "#E6EEF3",
    "teal_light": "#E4F0EF",
    "gray_light": "#F2F4F5",
    "road": "#CBD2D6",
    "white": "#FFFFFF",
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        # Microsoft YaHei supplies Chinese glyphs; mathtext and Latin labels remain sans-serif.
        "font.sans-serif": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
        "font.size": 7,
        "axes.linewidth": 0.8,
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    }
)


def export(fig: plt.Figure, stem: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUT_DIR / stem
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    fig.savefig(base.with_suffix(".png"), dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(base.with_suffix(".tiff"), dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def arrow(
    ax,
    start,
    end,
    *,
    color=COLORS["ink"],
    lw=1.2,
    dashed=False,
    rad=0.0,
    mutation_scale=9,
    zorder=5,
):
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=mutation_scale,
        linewidth=lw,
        color=color,
        linestyle=(0, (3, 2)) if dashed else "solid",
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=1,
        shrinkB=1,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def rounded_box(
    ax,
    xy,
    width,
    height,
    text,
    *,
    facecolor=COLORS["white"],
    edgecolor=COLORS["line"],
    fontsize=6.5,
    fontweight="normal",
    radius=0.03,
    zorder=3,
):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=0.9,
        zorder=zorder,
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=COLORS["ink"],
        fontweight=fontweight,
        linespacing=1.25,
        zorder=zorder + 1,
    )
    return box


def draw_uav(ax, x, y, scale=1.0, color=COLORS["navy"], zorder=8):
    ax.add_patch(Rectangle((x - 0.018 * scale, y - 0.010 * scale), 0.036 * scale, 0.020 * scale,
                           facecolor=color, edgecolor="white", linewidth=0.5, zorder=zorder))
    for dx, dy in [(-0.038, -0.024), (-0.038, 0.024), (0.038, -0.024), (0.038, 0.024)]:
        ax.plot([x, x + dx * scale], [y, y + dy * scale], color=color, lw=1.0, zorder=zorder)
        ax.add_patch(Circle((x + dx * scale, y + dy * scale), 0.012 * scale,
                            facecolor="white", edgecolor=color, linewidth=0.9, zorder=zorder))


def draw_vehicle(ax, x, y, scale=1.0, color=COLORS["orange"], zorder=8):
    ax.add_patch(FancyBboxPatch(
        (x - 0.042 * scale, y - 0.022 * scale),
        0.084 * scale,
        0.044 * scale,
        boxstyle="round,pad=0.003,rounding_size=0.008",
        facecolor=color,
        edgecolor="white",
        linewidth=0.6,
        zorder=zorder,
    ))
    ax.add_patch(Rectangle((x - 0.035 * scale, y - 0.010 * scale), 0.040 * scale, 0.020 * scale,
                           facecolor="white", edgecolor="none", alpha=0.75, zorder=zorder + 1))
    ax.add_patch(Circle((x - 0.026 * scale, y - 0.026 * scale), 0.009 * scale,
                        facecolor=COLORS["ink"], edgecolor="white", linewidth=0.4, zorder=zorder + 1))
    ax.add_patch(Circle((x + 0.026 * scale, y - 0.026 * scale), 0.009 * scale,
                        facecolor=COLORS["ink"], edgecolor="white", linewidth=0.4, zorder=zorder + 1))


def draw_hotspot(ax, x, y, scale=1.0):
    for radius, color in [(0.068, COLORS["yellow"]), (0.045, COLORS["orange"]), (0.022, COLORS["red"])]:
        ax.add_patch(Circle((x, y), radius * scale, facecolor=color, edgecolor="none", alpha=0.82, zorder=2))


def figure_air_ground_system() -> None:
    # 155 mm thesis text-block width; fonts are specified at final physical size.
    fig = plt.figure(figsize=(6.10, 3.52), constrained_layout=False)
    ax = fig.add_axes([0.025, 0.06, 0.95, 0.90])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.015, 0.965, "a", fontsize=8, fontweight="bold", ha="left", va="top", color=COLORS["ink"])
    ax.text(0.585, 0.965, "b", fontsize=8, fontweight="bold", ha="left", va="top", color=COLORS["ink"])

    # Panel a: physical scene.
    field = FancyBboxPatch(
        (0.035, 0.14), 0.515, 0.76,
        boxstyle="round,pad=0.008,rounding_size=0.018",
        facecolor=COLORS["green_light"], edgecolor=COLORS["green"], linewidth=1.0, zorder=0,
    )
    ax.add_patch(field)
    for x in np.linspace(0.075, 0.515, 9):
        ax.plot([x, x], [0.17, 0.87], color="#D5E2D2", lw=0.45, zorder=1)
    for y in np.linspace(0.19, 0.85, 7):
        ax.plot([0.055, 0.53], [y, y], color="#D5E2D2", lw=0.45, zorder=1)

    ax.text(0.055, 0.865, "动态虫害农田", fontsize=7, fontweight="bold", color=COLORS["ink"], va="top")
    ax.text(0.055, 0.825, "虫害增长 · 扩散 · 风场迁移 · 药效衰减", fontsize=5.6, color=COLORS["muted"], va="top")
    draw_hotspot(ax, 0.18, 0.63, 0.9)
    draw_hotspot(ax, 0.39, 0.43, 1.0)
    draw_hotspot(ax, 0.25, 0.28, 0.72)

    draw_uav(ax, 0.16, 0.47, 0.88)
    draw_uav(ax, 0.36, 0.64, 0.88)
    draw_uav(ax, 0.43, 0.27, 0.88)
    ax.text(0.16, 0.418, "UAV 1", fontsize=5.4, ha="center", color=COLORS["navy"])
    ax.text(0.36, 0.588, "UAV 2", fontsize=5.4, ha="center", color=COLORS["navy"])
    ax.text(0.427, 0.218, "UAV N", fontsize=5.4, ha="center", color=COLORS["navy"])
    ax.text(0.454, 0.213, "u", fontsize=5.0, ha="left", va="center", color=COLORS["navy"])

    # Road graph is visually distinct from the field grid.
    road_pts = np.array([[0.04, 0.10], [0.20, 0.12], [0.31, 0.09], [0.46, 0.12], [0.56, 0.20],
                         [0.56, 0.42], [0.54, 0.66], [0.57, 0.88]])
    ax.plot(road_pts[:, 0], road_pts[:, 1], color="white", lw=7.5, solid_capstyle="round", zorder=4)
    ax.plot(road_pts[:, 0], road_pts[:, 1], color=COLORS["road"], lw=5.0, solid_capstyle="round", zorder=5)
    ax.plot(road_pts[:, 0], road_pts[:, 1], color=COLORS["white"], lw=0.6, linestyle=(0, (5, 4)), zorder=6)
    ax.text(0.311, 0.055, "道路网络 G", fontsize=5.8, ha="center", color=COLORS["muted"])
    ax.text(0.354, 0.062, "r", fontsize=5.0, ha="left", va="center", color=COLORS["muted"])

    draw_vehicle(ax, 0.29, 0.10, 0.90)
    ax.text(0.29, 0.155, "移动药液补给车", fontsize=5.6, ha="center", color=COLORS["orange"])
    rendezvous = (0.545, 0.42)
    ax.add_patch(Circle(rendezvous, 0.025, facecolor="white", edgecolor=COLORS["teal"], linewidth=1.3, zorder=9))
    ax.add_patch(Circle(rendezvous, 0.008, facecolor=COLORS["teal"], edgecolor="none", zorder=10))
    ax.text(0.514, 0.472, "候选接驳点", fontsize=5.6, ha="center", color=COLORS["teal"])

    arrow(ax, (0.33, 0.11), (0.52, 0.39), color=COLORS["orange"], lw=1.4, rad=0.08)
    arrow(ax, (0.36, 0.61), (0.525, 0.435), color=COLORS["navy"], lw=1.3, rad=-0.05)
    arrow(ax, (0.47, 0.41), (0.53, 0.42), color=COLORS["red"], lw=1.5)
    ax.text(0.462, 0.452, "药液", fontsize=5.3, color=COLORS["red"], ha="center")
    arrow(ax, (0.355, 0.68), (0.31, 0.145), color=COLORS["navy"], lw=1.0, dashed=True, rad=0.28)
    ax.text(0.205, 0.405, "补给请求", fontsize=5.3, color=COLORS["navy"], rotation=78,
            rotation_mode="anchor", ha="center")

    # Panel b: information and resource interaction.
    rounded_box(ax, (0.625, 0.72), 0.28, 0.12, "无人机群 U\n位置 · 虫害观测 · 剩余药液",
                facecolor=COLORS["blue_light"], edgecolor=COLORS["navy"], fontsize=6.3)
    rounded_box(ax, (0.625, 0.43), 0.28, 0.12, "请求—候选接驳点集合 P(t)\n紧迫度 · 车机 ETA · 可达性",
                facecolor=COLORS["teal_light"], edgecolor=COLORS["teal"], fontsize=6.3)
    rounded_box(ax, (0.625, 0.14), 0.28, 0.12, "移动药液补给车 V\n道路位置 · 库存 · 服务状态",
                facecolor="#F6EEE4", edgecolor=COLORS["orange"], fontsize=6.3)

    arrow(ax, (0.69, 0.715), (0.69, 0.565), color=COLORS["navy"], dashed=True, lw=1.1)
    arrow(ax, (0.84, 0.565), (0.84, 0.715), color=COLORS["teal"], dashed=True, lw=1.1)
    ax.text(0.655, 0.64, "请求", fontsize=5.4, color=COLORS["navy"], ha="center")
    ax.text(0.875, 0.64, "接驳指引", fontsize=5.4, color=COLORS["teal"], ha="center")

    arrow(ax, (0.69, 0.425), (0.69, 0.275), color=COLORS["teal"], dashed=True, lw=1.1)
    arrow(ax, (0.84, 0.275), (0.84, 0.425), color=COLORS["orange"], dashed=True, lw=1.1)
    ax.text(0.65, 0.35, "服务分配", fontsize=5.4, color=COLORS["teal"], ha="center")
    ax.text(0.88, 0.35, "ETA/库存", fontsize=5.4, color=COLORS["orange"], ha="center")

    arrow(ax, (0.615, 0.20), (0.59, 0.74), color=COLORS["red"], lw=1.4, rad=-0.48)
    ax.text(0.572, 0.48, "接驳后药液转移", fontsize=5.5, color=COLORS["red"], rotation=90,
            rotation_mode="anchor", va="center", ha="center")

    # Compact legend.
    ax.plot([0.625, 0.70], [0.075, 0.075], color=COLORS["ink"], lw=1.2)
    ax.text(0.715, 0.075, "物理运动/药液流", fontsize=5.3, va="center", color=COLORS["muted"])
    ax.plot([0.815, 0.89], [0.075, 0.075], color=COLORS["ink"], lw=1.1, linestyle=(0, (3, 2)))
    ax.text(0.905, 0.075, "信息流", fontsize=5.3, va="center", color=COLORS["muted"], ha="left")

    export(fig, "fig4-1_air_ground_system")


def figure_service_process() -> None:
    fig = plt.figure(figsize=(6.10, 3.98), constrained_layout=False)
    ax = fig.add_axes([0.025, 0.035, 0.95, 0.94])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.015, 0.965, "a", fontsize=8, fontweight="bold", ha="left", va="top", color=COLORS["ink"])
    ax.text(0.015, 0.925, "动态请求触发", fontsize=7, fontweight="bold", color=COLORS["ink"], va="top")

    rounded_box(ax, (0.05, 0.72), 0.22, 0.105, "估计剩余作业时间\nT_remain(i,t)",
                facecolor=COLORS["blue_light"], edgecolor=COLORS["navy"], fontsize=6.3)
    rounded_box(ax, (0.38, 0.72), 0.25, 0.105, "估计接驳与服务时间\nT_rv(i,t) + T_svc(i,t) + ΔT_safe",
                facecolor=COLORS["teal_light"], edgecolor=COLORS["teal"], fontsize=6.0)
    rounded_box(ax, (0.74, 0.70), 0.20, 0.145, "是否满足\n时间触发条件？",
                facecolor="#F7F0DD", edgecolor=COLORS["yellow"], fontsize=6.5, fontweight="bold")
    arrow(ax, (0.275, 0.772), (0.37, 0.772), color=COLORS["line"])
    arrow(ax, (0.635, 0.772), (0.73, 0.772), color=COLORS["line"])
    ax.text(0.835, 0.665, "否：下一决策步重新评估", fontsize=5.4, ha="center", color=COLORS["muted"])
    arrow(ax, (0.92, 0.70), (0.27, 0.825), color=COLORS["line"], lw=0.9, dashed=True, rad=0.12)

    ax.text(0.015, 0.60, "b", fontsize=8, fontweight="bold", ha="left", va="top", color=COLORS["ink"])
    ax.text(0.015, 0.56, "请求调度与联合到达", fontsize=7, fontweight="bold", color=COLORS["ink"], va="top")

    y_top = 0.44
    nodes = [
        (0.04, "开放请求\nrequest-open", COLORS["red_light"], COLORS["red"]),
        (0.22, "分配/预约\nassigned", COLORS["teal_light"], COLORS["teal"]),
        (0.40, "车辆沿路网行驶\nvehicle-enroute", "#F6EEE4", COLORS["orange"]),
        (0.58, "车机接驳等待\nwaiting", COLORS["gray_light"], COLORS["line"]),
        (0.76, "联合到达判定\nco-arrival", COLORS["blue_light"], COLORS["navy"]),
    ]
    for x, label, fc, ec in nodes:
        rounded_box(ax, (x, y_top), 0.15, 0.095, label, facecolor=fc, edgecolor=ec, fontsize=5.8)
    for x1, x2 in zip([0.19, 0.37, 0.55, 0.73], [0.215, 0.395, 0.575, 0.755]):
        arrow(ax, (x1, y_top + 0.048), (x2, y_top + 0.048), color=COLORS["line"], lw=1.1)
    ax.text(0.835, 0.555, "是：生成请求", fontsize=5.5, color=COLORS["red"], ha="center")
    arrow(ax, (0.835, 0.698), (0.115, 0.54), color=COLORS["red"], lw=1.1, rad=-0.18)

    ax.text(0.29, 0.405, "车辆：确定性最短路执行", fontsize=5.2, color=COLORS["orange"], ha="center")
    ax.text(0.655, 0.405, "无人机：前往同一候选接驳点", fontsize=5.2, color=COLORS["navy"], ha="center")
    arrow(ax, (0.48, 0.435), (0.66, 0.435), color=COLORS["navy"], dashed=True, lw=0.9, rad=-0.26)

    ax.text(0.015, 0.325, "c", fontsize=8, fontweight="bold", ha="left", va="top", color=COLORS["ink"])
    ax.text(0.015, 0.285, "服务锁定、部分补给与状态恢复", fontsize=7, fontweight="bold", color=COLORS["ink"], va="top")

    rounded_box(ax, (0.055, 0.115), 0.16, 0.095, "服务前置条件\n全部满足", facecolor=COLORS["gray_light"],
                edgecolor=COLORS["line"], fontsize=5.8)
    rounded_box(ax, (0.275, 0.115), 0.16, 0.095, "显式服务锁定\nservicing", facecolor=COLORS["red_light"],
                edgecolor=COLORS["red"], fontsize=5.8, fontweight="bold")
    rounded_box(ax, (0.495, 0.115), 0.18, 0.095, "计算实际转移量\nΔq = min{容量缺口, 库存, 单次上限}",
                facecolor="#F7F0DD", edgecolor=COLORS["yellow"], fontsize=5.7)
    rounded_box(ax, (0.735, 0.115), 0.20, 0.095, "更新双方库存并解锁\n恢复施药/重新调度",
                facecolor=COLORS["green_light"], edgecolor=COLORS["green"], fontsize=5.8)
    for x1, x2 in [(0.215, 0.27), (0.435, 0.49), (0.675, 0.73)]:
        arrow(ax, (x1, 0.162), (x2, 0.162), color=COLORS["line"], lw=1.1)
    arrow(ax, (0.835, 0.44), (0.135, 0.215), color=COLORS["navy"], lw=1.1, rad=-0.14)

    # Transfer outcomes and failure branch.
    ax.text(0.585, 0.078, "库存充足：按需求补给  |  库存不足：部分补给  |  库存为零：记录未满足需求",
            fontsize=5.3, color=COLORS["muted"], ha="center")
    ax.text(0.135, 0.075, "条件不满足", fontsize=5.2, color=COLORS["red"], ha="center")
    arrow(ax, (0.105, 0.112), (0.105, 0.065), color=COLORS["red"], dashed=True, lw=0.9)
    ax.text(0.105, 0.035, "继续等待 / 取消 / 失败并记录原因", fontsize=5.0, color=COLORS["muted"], ha="center")

    # State feedback and legend.
    arrow(ax, (0.835, 0.11), (0.12, 0.435), color=COLORS["green"], dashed=True, lw=0.9, rad=-0.22)
    ax.text(0.47, 0.27, "服务完成事件反馈至任务与状态更新", fontsize=5.2, color=COLORS["green"], ha="center")
    ax.plot([0.73, 0.79], [0.035, 0.035], color=COLORS["ink"], lw=1.2)
    ax.text(0.80, 0.035, "激活的状态转移", fontsize=5.1, va="center", color=COLORS["muted"])
    ax.plot([0.89, 0.94], [0.035, 0.035], color=COLORS["ink"], lw=1.0, linestyle=(0, (3, 2)))
    ax.text(0.95, 0.035, "反馈/异常分支", fontsize=5.1, va="center", ha="left", color=COLORS["muted"])

    export(fig, "fig4-2_service_process")


if __name__ == "__main__":
    figure_air_ground_system()
    figure_service_process()
