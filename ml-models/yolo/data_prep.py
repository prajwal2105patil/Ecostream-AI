"""
Dataset Preparation Script
Member 1 (AI/Vision Lead) owns this file.

Converts COCO-format annotations (e.g. TACO dataset) to YOLO segmentation format.
Also handles train/val/test split.

Usage:
    python ml-models/yolo/data_prep.py --coco_json data/raw/annotations/instances.json \
        --images_dir data/raw/images --output_dir data/processed

References:
    TACO Dataset: http://tacodataset.org/
    TrashNet: https://github.com/garythung/trashnet
"""

import argparse
import json
import os
import shutil
import random
from pathlib import Path


def coco_to_yolo_seg(coco_json: str, images_dir: str, output_dir: str,
                     train_ratio=0.7, val_ratio=0.2):
    with open(coco_json) as f:
        data = json.load(f)

    cat_map = {cat["id"]: cat["name"] for cat in data["categories"]}
    img_map = {img["id"]: img for img in data["images"]}

    # Group annotations by image
    ann_by_img = {}
    for ann in data["annotations"]:
        ann_by_img.setdefault(ann["image_id"], []).append(ann)

    image_ids = list(ann_by_img.keys())
    random.shuffle(image_ids)
    n = len(image_ids)
    splits = {
        "train": image_ids[: int(n * train_ratio)],
        "val": image_ids[int(n * train_ratio): int(n * (train_ratio + val_ratio))],
        "test": image_ids[int(n * (train_ratio + val_ratio)):],
    }

    for split, ids in splits.items():
        img_out = Path(output_dir) / split / "images"
        lbl_out = Path(output_dir) / split / "labels"
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        for img_id in ids:
            img_info = img_map[img_id]
            src = Path(images_dir) / img_info["file_name"]
            dst = img_out / img_info["file_name"]
            if src.exists():
                shutil.copy(src, dst)

            w, h = img_info["width"], img_info["height"]
            label_lines = []
            for ann in ann_by_img.get(img_id, []):
                if not ann.get("segmentation"):
                    continue
                cls_id = ann["category_id"] - 1  # 0-indexed
                for seg in ann["segmentation"]:
                    # Normalize polygon coordinates
                    pts = []
                    for i in range(0, len(seg), 2):
                        pts.extend([seg[i] / w, seg[i + 1] / h])
                    label_lines.append(f"{cls_id} " + " ".join(f"{p:.6f}" for p in pts))

            lbl_file = lbl_out / (Path(img_info["file_name"]).stem + ".txt")
            lbl_file.write_text("\n".join(label_lines))

    print(f"Done. Train: {len(splits['train'])}, Val: {len(splits['val'])}, Test: {len(splits['test'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--coco_json", required=True)
    parser.add_argument("--images_dir", required=True)
    parser.add_argument("--output_dir", default="data/processed")
    args = parser.parse_args()
    coco_to_yolo_seg(args.coco_json, args.images_dir, args.output_dir)
