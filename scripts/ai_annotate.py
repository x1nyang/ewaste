"""调用 OpenAI 格式 API 对 PCB 图像进行 AI 自动标注

用法示例:
    python scripts/ai_annotate.py --task sift -d E:\project\wpcbs\dataset\disciption\batch_06.json -o E:\project\wpcbs\dataset\label\sift\batch_06.json
    python scripts/ai_annotate.py --task classify --limit 10
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from schema import prompts

DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")
IMAGE_DIR = os.path.join(DATASET_DIR, "raw")
DESCRIPTION_FILE = os.path.join(DATASET_DIR, "discription")
LABEL_DIR = os.path.join(DATASET_DIR, "label")

client = OpenAI(
    base_url="https://token-plan.maas.qianwenaiapi.com/compatible-mode/v1",
    api_key="sk-sp-H.DYXMPE.iWlQ.MEQCIGzHJ7zvhjYOLhvmCfwrKM5W4EMov09JCuzhTPHIeTA3AiA5BUc1Ujb6IXOBSp9erzq9ow7QqJ0U5RHGyuqSpqr2XQ",
)

def extract_json(text):
    """从模型输出中提取 JSON 对象，兼容 markdown 代码块包裹的情况"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError("无法从模型输出中解析 JSON")


def call_api(client, model, prompt, image_path):
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    completion = client.chat.completions.create(
        extra_body={},
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        temperature=0.1
    )
    return completion.choices[0].message.content

def main():
    tasks = [
        name for name, fn in vars(prompts).items()
        if callable(fn) and not name.startswith("_")
    ]
    parser = argparse.ArgumentParser(description="AI 自动标注 PCB 图像")
    parser.add_argument("-t", "--task", required=True, choices=tasks,
                        help=f"选择 schema/prompts.py 中的提示词函数: {tasks}")
    parser.add_argument("-m", "--model", default="qwen3.8-flash",
                        help="模型名称，默认取环境变量 OPENAI_MODEL")
    parser.add_argument("--max-retries", type=int, default=2,
                        help="失败后的重试次数，不含首次尝试（默认 2）")
    parser.add_argument("-l", "--limit", type=int, default=None,
                        help="最多处理 N 条（默认处理全部）")
    parser.add_argument("-d", "--description-file", default=DESCRIPTION_FILE)
    parser.add_argument("-s", "--sift-file")
    parser.add_argument("-i", "--image-dir", default=IMAGE_DIR)
    parser.add_argument("-o", "--output", default=None,
                        help="输出文件，默认为 LABEL_DIR/{task}.json")
    args = parser.parse_args()

    prompt_fn = getattr(prompts, args.task)
    output_file = args.output or os.path.join(LABEL_DIR, f"{args.task}.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(args.description_file, "r", encoding="utf-8") as f:
        descriptions = json.load(f)
    detail_map = {item["image_uuid"]: item["detail"] for item in descriptions}
    
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            results = json.load(f)
        done = {r["image_uuid"] for r in results}
    else:
        results, done = [], set()
    
    todo = [u for u in detail_map if u not in done]
    if args.task == "classify":
        with open(args.sift_file,"r",encoding='utf-8') as f:
            sift = json.load(f)
        usable_map_single = {item["image_uuid"]: item["usable"] and not item["is_multi_pcb"] for item in sift}
        todo = [u for u in todo if usable_map_single[u]]
    if args.limit is not None:
        todo = todo[:args.limit]
    total = len(todo)
    if total == 0:
        print("没有待处理的数据")
        return

    print(f"task={args.task}, model={args.model}, 待处理 {total} 条, 输出 {output_file}")
    failed = 0
    for idx, uuid in enumerate(todo, 1):
        detail = detail_map[uuid]
        image_path = os.path.join(args.image_dir, f"{uuid}.jpg")
        if not os.path.exists(image_path):
            print(f"[{idx}/{total}] {uuid} 图像文件不存在，跳过")
            failed += 1
            continue

        prompt = prompt_fn(detail)
        if not prompt or not prompt.strip():
            print(f"[{idx}/{total}] {uuid} 提示词为空，跳过")
            failed += 1
            continue

        content = None
        for attempt in range(args.max_retries + 1):
            try:
                content = call_api(client, args.model,
                                   prompt, image_path)
                parsed = extract_json(content)
                break
            except Exception as e:
                if attempt < args.max_retries:
                    wait = 2 ** (attempt + 1)
                    print(f"[{idx}/{total}] {uuid} 第 {attempt + 1} 次失败({e})，{wait}s 后重试")
                    time.sleep(wait)
                else:
                    print(f"[{idx}/{total}] {uuid} 重试 {args.max_retries} 次后仍失败: {e}")
                    failed += 1
                    continue

        record = {"image_uuid": uuid, **parsed}
        results.append(record)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"[{idx}/{total}] {uuid} 完成: {json.dumps(record, ensure_ascii=False)}")

    print(f"处理完成: 成功 {len(results) - len(done)} 条, 失败 {failed} 条, 结果已保存至 {output_file}")


if __name__ == "__main__":
    main()
