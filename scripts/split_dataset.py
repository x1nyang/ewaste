"""将 dataset/discription.json 按条数拆分为多个 batch，便于并行跑标注

用法示例:
    python scripts/split_dataset.py --batch-size 200
    拆分结果保存至 dataset/batches/batch_01.json, batch_02.json, ...
"""

import argparse
import json
import math
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")
DESCRIPTION_FILE = os.path.join(DATASET_DIR, "discription.json")
BATCH_DIR = os.path.join(DATASET_DIR, "batches")


def main():
    parser = argparse.ArgumentParser(description="拆分 discription.json 为多个 batch")
    parser.add_argument("--batch-size", type=int, default=200,
                        help="每个 batch 的条数（默认 200）")
    parser.add_argument("--input", default=DESCRIPTION_FILE,
                        help="输入文件，默认 dataset/discription.json")
    parser.add_argument("--output-dir", default=BATCH_DIR,
                        help="输出目录，默认 dataset/batches")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    num_batches = math.ceil(len(data) / args.batch_size)
    os.makedirs(args.output_dir, exist_ok=True)

    for i in range(num_batches):
        batch = data[i * args.batch_size:(i + 1) * args.batch_size]
        out_file = os.path.join(args.output_dir, f"batch_{i + 1:02d}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(batch, f, ensure_ascii=False, indent=4)
        print(f"{out_file}: {len(batch)} 条")

    print(f"拆分完成: 共 {len(data)} 条, 分为 {num_batches} 个 batch")


if __name__ == "__main__":
    main()
