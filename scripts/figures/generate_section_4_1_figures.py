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
    """Show the physical scene and its notation-consistent interaction graph."""
    # 155 mm thesis text-block width; fonts are specified at final physical size.
    fig = plt.figure(figsize=(6.10, 3.62), constrained_layout=False)
    ax = fig.add_axes([0.025, 0.055, 0.95, 0.91])
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
    ax.text(0.055, 0.825, "虫害增长 · 扩散 · 风场迁移 · 药效衰减", fontsize=6.2, color=COLORS["muted"], va="top")
    draw_hotspot(ax, 0.18, 0.63, 0.9)
    draw_hotspot(ax, 0.39, 0.43, 1.0)
    draw_hotspot(ax, 0.25, 0.28, 0.72)

    draw_uav(ax, 0.16, 0.47, 0.88)
    draw_uav(ax, 0.36, 0.64, 0.88)
    draw_uav(ax, 0.43, 0.27, 0.88)
    ax.text(0.16, 0.412, "$i=1$", fontsize=7.2, ha="center", color=COLORS["navy"])
    ax.text(0.36, 0.582, "$i=2$", fontsize=7.2, ha="center", color=COLORS["navy"])
    ax.text(0.43, 0.208, "$i=N_u$", fontsize=8.2, ha="center", color=COLORS["navy"])

    # Road graph is visually distinct from the field grid.
    road_pts = np.array([[0.04, 0.10], [0.20, 0.12], [0.31, 0.09], [0.46, 0.12], [0.56, 0.20],
                         [0.56, 0.42], [0.54, 0.66], [0.57, 0.88]])
    ax.plot(road_pts[:, 0], road_pts[:, 1], color="white", lw=7.5, solid_capstyle="round", zorder=4)
    ax.plot(road_pts[:, 0], road_pts[:, 1], color=COLORS["road"], lw=5.0, solid_capstyle="round", zorder=5)
    ax.plot(road_pts[:, 0], road_pts[:, 1], color=COLORS["white"], lw=0.6, linestyle=(0, (5, 4)), zorder=6)
    ax.text(0.145, 0.052, r"道路网络 $\mathcal{G}^{r}$", fontsize=7.2, ha="center", color=COLORS["muted"])

    draw_vehicle(ax, 0.29, 0.10, 0.90)
    ax.text(0.29, 0.155, "移动药液补给车", fontsize=6.2, ha="center", color=COLORS["orange"])
    rendezvous = (0.545, 0.42)
    ax.add_patch(Circle(rendezvous, 0.025, facecolor="white", edgecolor=COLORS["teal"], linewidth=1.3, zorder=9))
    ax.add_patch(Circle(rendezvous, 0.008, facecolor=COLORS["teal"], edgecolor="none", zorder=10))
    ax.text(0.49, 0.565, "候选接驳点\n" + r"$p\in\mathcal{P}_t$", fontsize=7.2, ha="center",
            va="bottom", color=COLORS["teal"], linespacing=1.15)

    arrow(ax, (0.33, 0.11), (0.52, 0.39), color=COLORS["orange"], lw=1.4, rad=0.08)
    arrow(ax, (0.36, 0.61), (0.525, 0.435), color=COLORS["navy"], lw=1.3, rad=-0.05)
    # The transfer arrow starts at the road-side rendezvous and ends at the UAV.
    arrow(ax, (0.535, 0.43), (0.385, 0.605), color=COLORS["red"], lw=1.6, rad=-0.20)
    arrow(ax, (0.355, 0.68), (0.31, 0.145), color=COLORS["navy"], lw=1.0, dashed=True, rad=0.28)
    ax.text(0.205, 0.405, "补给请求", fontsize=6.2, color=COLORS["navy"], rotation=78,
            rotation_mode="anchor", ha="center")

    # Panel b: information and resource interaction.
    rounded_box(ax, (0.625, 0.72), 0.28, 0.12, r"无人机集合 $\mathcal{U}$" + "\n位置 · 虫害观测 · 剩余药液",
                facecolor=COLORS["blue_light"], edgecolor=COLORS["navy"], fontsize=7.2)
    rounded_box(ax, (0.625, 0.43), 0.28, 0.12, r"请求—接驳点集合 $\mathcal{P}_t$" + "\n紧迫度 · 车机 ETA · 可达性",
                facecolor=COLORS["teal_light"], edgecolor=COLORS["teal"], fontsize=7.2)
    rounded_box(ax, (0.625, 0.14), 0.28, 0.12, r"补给车集合 $\mathcal{V}$" + "\n道路位置 · 库存 · 服务状态",
                facecolor="#F6EEE4", edgecolor=COLORS["orange"], fontsize=7.2)

    arrow(ax, (0.69, 0.715), (0.69, 0.565), color=COLORS["navy"], dashed=True, lw=1.1)
    arrow(ax, (0.84, 0.565), (0.84, 0.715), color=COLORS["teal"], dashed=True, lw=1.1)
    ax.text(0.655, 0.64, "请求", fontsize=6.2, color=COLORS["navy"], ha="center")
    ax.text(0.875, 0.64, "接驳指引", fontsize=6.2, color=COLORS["teal"], ha="center")

    arrow(ax, (0.69, 0.425), (0.69, 0.275), color=COLORS["teal"], dashed=True, lw=1.1)
    arrow(ax, (0.84, 0.275), (0.84, 0.425), color=COLORS["orange"], dashed=True, lw=1.1)
    ax.text(0.65, 0.35, "服务分配", fontsize=6.2, color=COLORS["teal"], ha="center")
    ax.text(0.88, 0.35, "ETA / 库存", fontsize=6.2, color=COLORS["orange"], ha="center")

    arrow(ax, (0.625, 0.20), (0.625, 0.75), color=COLORS["red"], lw=1.4, rad=-0.30)
    ax.text(0.572, 0.48, "接驳后药液转移", fontsize=6.2, color=COLORS["red"], rotation=90,
            rotation_mode="anchor", va="center", ha="center")

    # Compact legend.
    ax.plot([0.625, 0.70], [0.075, 0.075], color=COLORS["ink"], lw=1.2)
    ax.text(0.715, 0.075, "物理运动 / 药液流", fontsize=6.2, va="center", color=COLORS["muted"])
    ax.plot([0.815, 0.89], [0.075, 0.075], color=COLORS["ink"], lw=1.1, linestyle=(0, (3, 2)))
    ax.text(0.905, 0.075, "信息流", fontsize=6.2, va="center", color=COLORS["muted"], ha="left")

    export(fig, "fig4-1_air_ground_system")


def figure_service_process() -> None:
    """Render a deterministic event flow with parallel travel and conditional waiting."""
    fig = plt.figure(figsize=(6.10, 4.72), constrained_layout=False)
    ax = fig.add_axes([0.025, 0.025, 0.95, 0.96])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Panel a: request trigger, read from left to right.
    ax.text(0.015, 0.965, "a", fontsize=8, fontweight="bold", ha="left", va="top", color=COLORS["ink"])
    ax.text(0.015, 0.925, "动态请求触发", fontsize=7.2, fontweight="bold", color=COLORS["ink"], va="top")
    rounded_box(
        ax, (0.04, 0.745), 0.23, 0.105,
        r"剩余作业时间" + "\n" + r"$\hat{T}^{\mathrm{remain}}_{i,t}$",
        facecolor=COLORS["blue_light"], edgecolor=COLORS["navy"], fontsize=7.4,
    )
    rounded_box(
        ax, (0.36, 0.745), 0.29, 0.105,
        r"接驳、服务与安全余量" + "\n"
        + r"$\hat{T}^{\mathrm{rv}}_{i,t}+T^{\mathrm{svc}}_{i,t}+\Delta T^{\mathrm{safe}}$",
        facecolor=COLORS["teal_light"], edgecolor=COLORS["teal"], fontsize=7.4,
    )
    rounded_box(
        ax, (0.75, 0.735), 0.20, 0.125, "满足式（4.2）？",
        facecolor="#F7F0DD", edgecolor=COLORS["yellow"], fontsize=7.0, fontweight="bold",
    )
    arrow(ax, (0.275, 0.798), (0.35, 0.798), color=COLORS["line"])
    arrow(ax, (0.655, 0.798), (0.74, 0.798), color=COLORS["line"])
    ax.text(0.55, 0.70, "否：下一决策步重新评估", fontsize=6.2, ha="center", color=COLORS["muted"])
    arrow(ax, (0.83, 0.735), (0.58, 0.715), color=COLORS["line"], dashed=True, lw=0.9, rad=-0.08)

    # Panel b: snake layout, read from right to left after the request is triggered.
    ax.text(0.015, 0.655, "b", fontsize=8, fontweight="bold", ha="left", va="top", color=COLORS["ink"])
    ax.text(0.015, 0.615, "请求调度、并行行进与条件等待", fontsize=7.2, fontweight="bold",
            color=COLORS["ink"], va="top")

    rounded_box(ax, (0.82, 0.47), 0.14, 0.075, "开放请求",
                facecolor=COLORS["red_light"], edgecolor=COLORS["red"], fontsize=6.4)
    rounded_box(ax, (0.62, 0.45), 0.16, 0.115, "库存大于0且\n存在可行接驳点？",
                facecolor="#F7F0DD", edgecolor=COLORS["yellow"], fontsize=6.4, fontweight="bold")
    rounded_box(ax, (0.43, 0.47), 0.15, 0.075, "唯一预约\n请求—车—点",
                facecolor=COLORS["teal_light"], edgecolor=COLORS["teal"], fontsize=6.4)
    rounded_box(ax, (0.205, 0.515), 0.17, 0.070, "无人机前往接驳点",
                facecolor=COLORS["blue_light"], edgecolor=COLORS["navy"], fontsize=6.2)
    rounded_box(ax, (0.205, 0.415), 0.17, 0.075, "车辆释放后沿\n确定性最短路行驶",
                facecolor="#F6EEE4", edgecolor=COLORS["orange"], fontsize=6.2)
    rounded_box(ax, (0.025, 0.45), 0.14, 0.115, "双方均到达？",
                facecolor=COLORS["gray_light"], edgecolor=COLORS["line"], fontsize=6.5, fontweight="bold")

    ax.text(0.89, 0.585, "是：生成请求", fontsize=6.2, color=COLORS["red"], ha="center")
    arrow(ax, (0.85, 0.735), (0.89, 0.55), color=COLORS["red"], lw=1.1, rad=0.05)
    arrow(ax, (0.815, 0.507), (0.785, 0.507), color=COLORS["line"])
    arrow(ax, (0.615, 0.507), (0.585, 0.507), color=COLORS["line"])
    arrow(ax, (0.425, 0.507), (0.38, 0.55), color=COLORS["navy"], rad=-0.08)
    arrow(ax, (0.425, 0.507), (0.38, 0.452), color=COLORS["orange"], rad=0.08)
    arrow(ax, (0.20, 0.55), (0.17, 0.52), color=COLORS["navy"])
    arrow(ax, (0.20, 0.452), (0.17, 0.485), color=COLORS["orange"])
    ax.text(0.29, 0.505, "并行行进", fontsize=6.2, color=COLORS["muted"], ha="center")

    ax.text(0.70, 0.415, "否：取消 / 失败并记录原因", fontsize=6.2, color=COLORS["red"], ha="center")
    arrow(ax, (0.70, 0.45), (0.70, 0.422), color=COLORS["red"], dashed=True, lw=0.9)
    ax.text(0.095, 0.405, "否：仅早到方条件等待", fontsize=6.2, color=COLORS["muted"], ha="center")
    arrow(ax, (0.095, 0.45), (0.095, 0.415), color=COLORS["line"], dashed=True, lw=0.9)
    arrow(ax, (0.04, 0.415), (0.045, 0.45), color=COLORS["line"], dashed=True, lw=0.9, rad=-0.25)

    # Panel c: service starts only after the two parallel branches converge.
    ax.text(0.015, 0.365, "c", fontsize=8, fontweight="bold", ha="left", va="top", color=COLORS["ink"])
    ax.text(0.015, 0.325, "服务判定、转移与恢复", fontsize=7.2, fontweight="bold",
            color=COLORS["ink"], va="top")

    rounded_box(ax, (0.025, 0.17), 0.18, 0.095, "接驳半径、归属\n状态均满足",
                facecolor=COLORS["gray_light"], edgecolor=COLORS["line"], fontsize=6.2)
    rounded_box(ax, (0.255, 0.17), 0.16, 0.095, "显式服务锁定\n同步动作掩码",
                facecolor=COLORS["red_light"], edgecolor=COLORS["red"], fontsize=6.2, fontweight="bold")
    rounded_box(
        ax, (0.465, 0.17), 0.20, 0.095,
        r"冻结 $q^{\mathrm{alloc}}$ 并逐步转移" + "\n" + r"$\delta q_{i,v,t}$",
        facecolor="#F7F0DD", edgecolor=COLORS["yellow"], fontsize=7.2,
    )
    rounded_box(ax, (0.715, 0.17), 0.22, 0.095, "更新双方库存并解锁\n恢复施药 / 重新调度",
                facecolor=COLORS["green_light"], edgecolor=COLORS["green"], fontsize=6.2)

    # Route the convergence connector through whitespace so it does not cross the panel-c heading.
    ax.plot([0.025, 0.008, 0.008], [0.507, 0.507, 0.217],
            color=COLORS["navy"], lw=1.1, solid_capstyle="round")
    arrow(ax, (0.008, 0.217), (0.023, 0.217), color=COLORS["navy"], lw=1.1)
    ax.text(0.115, 0.285, "是：进入服务资格判定", fontsize=6.2,
            color=COLORS["navy"], ha="center", va="center")
    for x1, x2 in [(0.205, 0.25), (0.415, 0.46), (0.665, 0.71)]:
        arrow(ax, (x1, 0.217), (x2, 0.217), color=COLORS["line"], lw=1.1)

    ax.text(0.12, 0.135, "条件失效：取消 / 失败并记录原因", fontsize=6.2,
            color=COLORS["red"], ha="center")
    arrow(ax, (0.105, 0.168), (0.105, 0.142), color=COLORS["red"], dashed=True, lw=0.9)
    ax.text(0.585, 0.135, "库存充足：按目标补给  |  库存不足：部分补给  |  完成与未满足量分别记录",
            fontsize=6.2, color=COLORS["muted"], ha="center")
    ax.text(0.54, 0.085, "完成事件反馈至任务、请求与状态更新；车辆库存耗尽不终止回合",
            fontsize=6.2, color=COLORS["green"], ha="center")

    ax.plot([0.63, 0.69], [0.045, 0.045], color=COLORS["ink"], lw=1.2)
    ax.text(0.70, 0.045, "激活状态转移", fontsize=6.2, va="center", color=COLORS["muted"])
    ax.plot([0.84, 0.89], [0.045, 0.045], color=COLORS["ink"], lw=1.0, linestyle=(0, (3, 2)))
    ax.text(0.90, 0.045, "反馈 / 异常", fontsize=6.2, va="center", ha="left", color=COLORS["muted"])

    export(fig, "fig4-2_service_process")

if __name__ == "__main__":
    figure_air_ground_system()
    figure_service_process()
