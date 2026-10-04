"""从结构化统计 JSON 生成 sift / classify 统计图表

用法示例:
    python scripts/plot_stats.py                                  # 读取默认 outputs/stats/stats.json
    python scripts/plot_stats.py --stats outputs/stats/stats.json --output-dir outputs/stats

结构化统计由 scripts/stats_labels.py --save-stats 生成，两步可分开执行。
"""

import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "stats")
STATS_FILE = os.path.join(OUTPUT_DIR, "stats.json")

# 柱状图取值展示顺序（None 排在最后）
VALUE_ORDER = {
    "is_real_pcb": ["True", "False", "None"],
    "is_match_discription": ["True", "False", "None"],
    "condition": ["high", "medium", "low", "unusable", "None"],
    "is_multi_pcb": ["True", "False", "None"],
    "usable": ["True", "False", "None"],
    "completeness": ["complete", "medium", "incomplete"],
    "component_density": ["dense", "medium", "sparse"],
}


def setup_chinese_font():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    return plt


def ordered_items(field, counter):
    order = VALUE_ORDER.get(field)
    if order is None:
        # 无预设顺序（如 type）按数量降序，None 排最后
        return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return [(v, counter[v]) for v in order if v in counter] + \
        [(v, n) for v, n in sorted(counter.items(), key=lambda kv: kv[0]) if v not in order]


def bar_with_labels(ax, labels, values):
    total = sum(values)
    bars = ax.bar(labels, values)
    # 上方留出余量，避免最高柱的标注顶到图框上沿
    if values:
        ax.set_ylim(0, max(values) * 1.25)
    for bar, value in zip(bars, values):
        pct = value / total * 100 if total else 0
        ax.annotate(f"{value}\n({pct:.1f}%)", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha="center", va="bottom", fontsize=8)
    return bars


def plot_sift(fields, total, out_file):
    plt = setup_chinese_font()
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.5))
    axes = axes.flatten()
    for ax, field in zip(axes, ["is_real_pcb", "is_match_discription", "condition",
                                "is_multi_pcb", "usable"]):
        items = ordered_items(field, fields[field])
        labels = [k for k, _ in items]
        bar_with_labels(ax, labels, [n for _, n in items])
        ax.set_title(field)
        ax.tick_params(axis="x", labelsize=8)
    axes[-1].axis("off")
    fig.suptitle(f"sift 标注统计（共 {total} 条）", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_file, dpi=150)
    plt.close(fig)
    return out_file


def plot_classify(fields, total, out_file):
    plt = setup_chinese_font()
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, field in zip(axes, ["type", "completeness", "component_density"]):
        items = ordered_items(field, fields[field])
        labels = [k for k, _ in items]
        values = [n for _, n in items]
        if field == "type":
            bars = ax.barh(labels, values)
            # 右侧留出余量，避免最长柱的标注顶到图框边缘
            if values:
                ax.set_xlim(0, max(values) * 1.2)
            for bar, value in zip(bars, values):
                pct = value / sum(values) * 100 if values else 0
                ax.annotate(f"{value} ({pct:.1f}%)", (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                            ha="left", va="center", fontsize=8)
            ax.invert_yaxis()
        else:
            bar_with_labels(ax, labels, values)
        ax.set_title(field)
        ax.tick_params(axis="x", labelsize=8)
    fig.suptitle(f"classify 标注统计（共 {total} 条）", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_file, dpi=150)
    plt.close(fig)
    return out_file


def main():
    parser = argparse.ArgumentParser(description="从结构化统计 JSON 生成统计图表")
    parser.add_argument("--stats", default=STATS_FILE,
                        help=f"结构化统计 JSON 文件，默认 {STATS_FILE}")
    parser.add_argument("--output-dir", default=OUTPUT_DIR,
                        help="图表输出目录，默认 outputs/stats")
    args = parser.parse_args()

    with open(args.stats, "r", encoding="utf-8") as f:
        stats = json.load(f)

    os.makedirs(args.output_dir, exist_ok=True)
    if "sift" in stats:
        out = plot_sift(stats["sift"]["fields"], stats["sift"]["total"],
                        os.path.join(args.output_dir, "sift_stats.png"))
        print(f"sift 图表已保存: {out}")
    if "classify" in stats:
        out = plot_classify(stats["classify"]["fields"], stats["classify"]["total"],
                            os.path.join(args.output_dir, "classify_stats.png"))
        print(f"classify 图表已保存: {out}")


if __name__ == "__main__":
    main()
