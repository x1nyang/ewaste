"""筛选 dataset 中相同或相似的图像，重复图像与 discription.json 中对应描述一起删除"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "dataset" / "raw"
DESCRIPTION_PATH = PROJECT_ROOT / "dataset" / "discription.json"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def dhash(image_path: Path, hash_size: int = 8) -> int:
    """计算 64 位 dHash 感知哈希，相似图像哈希值汉明距离小"""
    with Image.open(image_path) as img:
        gray = img.convert("L").resize(
            (hash_size + 1, hash_size), Image.Resampling.LANCZOS
        )
        pixels = list(gray.getdata())
    h = 0
    for row in range(hash_size):
        base = row * (hash_size + 1)
        for col in range(hash_size):
            h = (h << 1) | (pixels[base + col] > pixels[base + col + 1])
    return h


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def main():
    parser = argparse.ArgumentParser(description="删除 dataset 中相同或相似的图像及其描述")
    parser.add_argument("--raw-dir", default=str(RAW_DIR), help="图像目录")
    parser.add_argument("--json", dest="json_path", default=str(DESCRIPTION_PATH), help="描述文件路径")
    parser.add_argument(
        "--threshold",
        type=int,
        default=5,
        help="dHash 汉明距离阈值，<= 该值视为相似图像（默认 5）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印结果，不删除任何文件")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    json_path = Path(args.json_path)

    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            description = json.load(f)
    else:
        description = []

    image_files = sorted(
        p for p in raw_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )
    desc_uuids = {entry["image_uuid"] for entry in description}

    # 1. 完全相同：按 MD5 分组
    md5_groups: dict[str, list[Path]] = {}
    for path in image_files:
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        md5_groups.setdefault(digest, []).append(path)

    # 2. 相似：每个 MD5 组取第一个作为代表，贪心保留第一个，后续相似的标记为重复
    kept: list[tuple[Path, int]] = []
    dup_reason: dict[Path, tuple[str, Path]] = {}

    for path in (files[0] for files in md5_groups.values()):
        try:
            h = dhash(path)
        except Exception as e:
            print(f"[警告] 无法读取图像，跳过：{path.name}（{e}）")
            continue
        for kept_path, kept_h in kept:
            dist = hamming(h, kept_h)
            if dist <= args.threshold:
                dup_reason[path] = (f"相似（汉明距离 {dist}）", kept_path)
                break
        else:
            kept.append((path, h))

    for files in md5_groups.values():
        for dup in files[1:]:
            dup_reason[dup] = ("完全相同（MD5）", files[0])

    duplicates = sorted(dup_reason)
    removed_uuids = {p.stem for p in duplicates}

    # 将重复链解析到最终保留的图像，避免报告中"保留"的文件本身也是重复
    def kept_ancestor(p: Path) -> Path:
        seen = set()
        while p in dup_reason:
            if p in seen:
                break
            seen.add(p)
            p = dup_reason[p][1]
        return p

    print(f"图像总数：{len(image_files)}")
    print(f"完全相同组：{sum(1 for f in md5_groups.values() if len(f) > 1)}")
    print(f"将删除图像：{len(duplicates)}，将删除描述条目："
          f"{sum(1 for e in description if e['image_uuid'] in removed_uuids)}")
    print("-" * 60)
    for dup in duplicates:
        reason, _ = dup_reason[dup]
        print(f"[重复] {dup.name}  ->  保留 {kept_ancestor(dup).name}（{reason}）")

    # 孤儿条目：描述存在但图像缺失，或图像存在但无描述，仅报告不删除
    orphan_entries = [e for e in description if e["image_uuid"] not in {p.stem for p in image_files}]
    orphan_images = [p for p in image_files if p.stem not in desc_uuids]
    if orphan_entries:
        print("-" * 60)
        print(f"[提示] {len(orphan_entries)} 条描述没有对应图像文件，未处理")
        for e in orphan_entries[:10]:
            print(f"  {e['image_uuid']}")
        if len(orphan_entries) > 10:
            print(f"  ... 共 {len(orphan_entries)} 条")
    if orphan_images:
        print(f"[提示] {len(orphan_images)} 个图像在描述文件中无条目，未处理")

    if args.dry_run:
        print("-" * 60)
        print("dry-run 模式，未删除任何文件。去掉 --dry-run 参数实际执行删除。")
        return

    for dup in duplicates:
        dup.unlink()
    if duplicates:
        kept_description = [e for e in description if e["image_uuid"] not in removed_uuids]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(kept_description, f, ensure_ascii=False, indent=4)
    print(f"完成：已删除 {len(duplicates)} 个图像及对应描述条目")


if __name__ == "__main__":
    main()
