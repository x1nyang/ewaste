"""统计 dataset/label 下 sift 和 classify 的标注结果，输出结构化文本

用法示例:
    python scripts/stats_labels.py                              # 打印统计结果
    python scripts/stats_labels.py --save-stats outputs/stats/stats.json   # 同时保存结构化统计

再用 scripts/plot_stats.py 读取结构化统计生成图表，两步可分开执行:
    python scripts/plot_stats.py --stats outputs/stats/stats.json

sift 统计: is_real_pcb / is_match_discription / condition / is_multi_pcb / usable
classify 统计: type / completeness / component_density（不统计 name 和 model）
"""

import argparse
import glob
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABEL_DIR = os.path.join(PROJECT_ROOT, "dataset", "label")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "stats")
STATS_FILE = os.path.join(OUTPUT_DIR, "stats.json")

SIFT_FIELDS = ["is_real_pcb", "is_match_discription", "condition", "is_multi_pcb", "usable"]
CLASSIFY_FIELDS = ["type", "completeness", "component_density"]


def load_batches(label_dir, kind):
    files = sorted(glob.glob(os.path.join(label_dir, kind, "batch_*.json")))
    batches = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            batches.append((os.path.basename(f), json.load(fp)))
    return batches


def normalize(value):
    # 数据里存在字符串 "true"/"false" 的笔误，统一归一化为布尔值
    if isinstance(value, str):
        lower = value.lower()
        if lower == "true":
            return True
        if lower == "false":
            return False
    return value


def count_sift(batches):
    counters = {field: Counter() for field in SIFT_FIELDS}
    for _, records in batches:
        for rec in records:
            for field in SIFT_FIELDS:
                counters[field][normalize(rec.get(field))] += 1
    return counters


def count_classify(batches):
    counters = {field: Counter() for field in CLASSIFY_FIELDS}
    for _, records in batches:
        for rec in records:
            for field in CLASSIFY_FIELDS:
                counters[field][rec.get(field)] += 1
    return counters


def print_field(title, counter):
    total = sum(counter.values())
    print(f"  {title}:")
    for value, count in sorted(counter.items(), key=lambda kv: str(kv[0])):
        pct = count / total * 100 if total else 0
        print(f"    {str(value):<24} {count:>6}  ({pct:5.1f}%)")


def counters_to_dict(counters):
    return {
        field: {("None" if k is None else str(k)): v for k, v in counter.items()}
        for field, counter in counters.items()
    }


def main():
    parser = argparse.ArgumentParser(description="统计 dataset/label 下 sift 和 classify 标注结果")
    parser.add_argument("--label-dir", default=LABEL_DIR,
                        help="标注目录，默认 dataset/label")
    parser.add_argument("--save-stats", nargs="?", const=STATS_FILE, default=None,
                        help="保存结构化统计到指定 JSON 文件（默认 outputs/stats/stats.json）")
    args = parser.parse_args()

    stats = {}
    for kind, fields, counter_func in [
        ("sift", SIFT_FIELDS, count_sift),
        ("classify", CLASSIFY_FIELDS, count_classify),
    ]:
        files = sorted(glob.glob(os.path.join(args.label_dir, kind, "batch_*.json")))
        if not files:
            print(f"[{kind}] 未找到 batch_*.json，跳过")
            continue
        batches = load_batches(args.label_dir, kind)
        total = sum(len(records) for _, records in batches)

        print(f"== {kind} ({len(batches)} 个文件, 共 {total} 条) ==")
        for name, records in batches:
            print(f"  {name}: {len(records)} 条")
        counters = counter_func(batches)
        for field in fields:
            print_field(field, counters[field])
        print()

        stats[kind] = {
            "total": total,
            "files": [{"file": name, "count": len(records)} for name, records in batches],
            "fields": counters_to_dict(counters),
        }

    if args.save_stats:
        out_file = args.save_stats
        os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"结构化统计已保存: {out_file}")


if __name__ == "__main__":
    main()
