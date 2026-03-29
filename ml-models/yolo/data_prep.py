"""
Dataset Preparation Script
Member 1 (AI/Vision Lead) owns this file.

Converts COCO-format annotations (TACO dataset) to YOLO segmentation format.
Maps TACO's 60 categories -> EcoStream AI's 20 Indian waste classes.
Also handles train/val/test split.

Usage:
    python ml-models/yolo/data_prep.py \
        --coco_json data/raw/annotations/instances.json \
        --images_dir data/raw/images \
        --output_dir data/processed

References:
    TACO Dataset : http://tacodataset.org/
    TACO GitHub  : https://github.com/pedropro/TACO
"""

import argparse
import json
import shutil
import random
from pathlib import Path


# -----------------------------------------------------------------------------
# EcoStream AI class index reference (matches dataset.yaml)
# -----------------------------------------------------------------------------
# 0  plastic_pet_bottle
# 1  plastic_bag
# 2  plastic_wrapper
# 3  glass_bottle
# 4  glass_broken
# 5  paper_newspaper
# 6  paper_cardboard
# 7  metal_can
# 8  metal_scrap
# 9  organic_food_waste
# 10 organic_leaves
# 11 e_waste_phone
# 12 e_waste_battery
# 13 textile_cloth
# 14 rubber_tire
# 15 construction_debris
# 16 medical_waste_mask
# 17 thermocol
# 18 tetra_pak
# 19 mixed_waste
# -----------------------------------------------------------------------------

# Maps TACO category name (lowercase, stripped) -> our 0-indexed class ID
# Classes with no TACO equivalent are omitted (organic_leaves=10, e_waste_phone=11,
# rubber_tire=14, construction_debris=15 -- supplement from other datasets later)
TACO_TO_ECOSTREAM: dict[str, int] = {
    # -- Plastics ----------------------------------------------------------
    "clear plastic bottle":          0,   # plastic_pet_bottle
    "other plastic bottle":          0,
    "milk bottle":                   0,
    "plastic bottle":                0,
    "plastic bag & wrapper":         1,   # plastic_bag
    "plastic bag":                   1,
    "other plastic bag":             1,
    "single-use carrier bag":        1,
    "shopping bag":                  1,
    "garbage bag":                   1,
    "polypropylene bag":             1,
    "other plastic wrapper":         2,   # plastic_wrapper
    "plastic film":                  2,
    "plastic wrapper":               2,
    "cling wrap":                    2,
    "crisp packet":                  2,
    "plastic straw":                 2,
    "six pack rings":                2,
    "squeezable tube":               2,
    "blister pack":                  2,
    "aluminium blister pack":        2,   # close enough to wrapper category
    "other plastic":                 2,
    "other plastic container":       2,
    # -- Glass -------------------------------------------------------------
    "glass bottle":                  3,   # glass_bottle
    "glass jar":                     3,
    "other glass":                   3,
    "broken glass":                  4,   # glass_broken
    "glass cup":                     4,
    # -- Paper -------------------------------------------------------------
    "newspaper":                     5,   # paper_newspaper
    "normal paper":                  5,
    "magazine":                      5,
    "wrapping paper":                5,
    "paper bag":                     5,
    "book":                          5,
    "cardboard":                     6,   # paper_cardboard
    "corrugated carton":             6,
    "other carton":                  6,
    "meal carton":                   6,
    "egg carton":                    6,
    "box":                           6,
    "paper cup":                     6,
    # -- Metal -------------------------------------------------------------
    "drink can":                     7,   # metal_can
    "food can":                      7,
    "cans":                          7,
    "tin can":                       7,
    "metal can":                     7,
    "aluminium foil":                7,
    "metal bottle cap":              7,
    "metal lid":                     7,
    "pop tab":                       7,
    "lid (metal, not for bottle)":   7,
    "scrap metal":                   8,   # metal_scrap
    "other metal":                   8,
    # -- Organic -----------------------------------------------------------
    "food waste":                    9,   # organic_food_waste
    "food":                          9,
    # -- E-waste -----------------------------------------------------------
    "battery":                       12,  # e_waste_battery
    # -- Textile -----------------------------------------------------------
    "clothing":                      13,  # textile_cloth
    "shoe":                          13,
    "rope & strings":                13,
    "rope":                          13,
    # -- Medical / PPE -----------------------------------------------------
    "plastic gloves":                16,  # medical_waste_mask
    "disposable glove":              16,
    "gloves":                        16,
    # -- Thermocol / Styrofoam ---------------------------------------------
    "styrofoam piece":               17,  # thermocol
    "expanded polystyrene":          17,
    # -- Tetra Pak ---------------------------------------------------------
    "drink carton":                  18,  # tetra_pak
    "milk carton":                   18,
    "juice carton":                  18,
    # -- Mixed / Unclassified ----------------------------------------------
    "unlabeled litter":              19,  # mixed_waste
    "cigarette":                     19,
    "cup":                           19,
    "disposable food container":     19,
    "disposable plastic cup":        19,
    "other plastic cup":             19,
    "plastic bottle cap":            19,
    "plastic lid":                   19,
    "plastic utensils":              19,
    "spread tub":                    19,
    "spread tub (plastic)":          19,
    "tissues":                       19,
    "tissue paper":                  19,
    "bottle cap":                    19,
    "lid":                           19,
}


def _normalize_cat_name(name: str) -> str:
    """Lowercase and strip for consistent lookup."""
    return name.lower().strip()


def build_cat_id_to_class(categories: list[dict]) -> dict[int, int]:
    """
    Build mapping: TACO category_id (int) -> EcoStream class_id (0-indexed int).
    Categories not in TACO_TO_ECOSTREAM are mapped to mixed_waste (19) as fallback.
    """
    mapping = {}
    unmapped = []
    for cat in categories:
        name = _normalize_cat_name(cat["name"])
        eco_cls = TACO_TO_ECOSTREAM.get(name)
        if eco_cls is not None:
            mapping[cat["id"]] = eco_cls
        else:
            mapping[cat["id"]] = 19  # mixed_waste fallback
            unmapped.append(cat["name"])

    if unmapped:
        print(f"  [INFO] {len(unmapped)} TACO categories -> mixed_waste (19): {unmapped[:8]}{'...' if len(unmapped)>8 else ''}")

    # Print class distribution summary
    from collections import Counter
    dist = Counter(mapping.values())
    print("  Class distribution from TACO mapping:")
    class_names = [
        "plastic_pet_bottle","plastic_bag","plastic_wrapper","glass_bottle","glass_broken",
        "paper_newspaper","paper_cardboard","metal_can","metal_scrap","organic_food_waste",
        "organic_leaves","e_waste_phone","e_waste_battery","textile_cloth","rubber_tire",
        "construction_debris","medical_waste_mask","thermocol","tetra_pak","mixed_waste"
    ]
    for cls_id in sorted(dist):
        print(f"    {cls_id:2d} {class_names[cls_id]:<25} <- {dist[cls_id]} TACO categories")

    return mapping


def coco_to_yolo_seg(
    coco_json: str,
    images_dir: str,
    output_dir: str,
    train_ratio: float = 0.70,
    val_ratio: float = 0.20,
    seed: int = 42,
):
    """Convert COCO segmentation annotations to YOLO format with TACO mapping."""
    print(f"\nLoading annotations from {coco_json} ...")
    with open(coco_json) as f:
        data = json.load(f)

    # Build category mapping
    print(f"Building TACO -> EcoStream category mapping ({len(data['categories'])} categories)...")
    cat_id_to_class = build_cat_id_to_class(data["categories"])

    # Build image lookup
    img_map = {img["id"]: img for img in data["images"]}

    # Group annotations by image; skip annotations with no segmentation mask
    ann_by_img: dict[int, list] = {}
    skipped_no_seg = 0
    for ann in data["annotations"]:
        if not ann.get("segmentation") or len(ann["segmentation"]) == 0:
            skipped_no_seg += 1
            continue
        ann_by_img.setdefault(ann["image_id"], []).append(ann)

    if skipped_no_seg:
        print(f"  Skipped {skipped_no_seg} annotations without segmentation masks.")

    # Only include images that exist on disk AND have annotations
    images_path = Path(images_dir)
    valid_ids = []
    for img_id, anns in ann_by_img.items():
        img_info = img_map.get(img_id)
        if not img_info:
            continue
        img_file = images_path / img_info["file_name"]
        if img_file.exists():
            valid_ids.append(img_id)

    print(f"\n  Total annotated images: {len(ann_by_img)}")
    print(f"  Images found on disk  : {len(valid_ids)}")

    if not valid_ids:
        print("\n[ERROR] No images found on disk. Run download_dataset.py first.")
        return

    # Reproducible split
    random.seed(seed)
    random.shuffle(valid_ids)
    n = len(valid_ids)
    n_train = int(n * train_ratio)
    n_val   = int(n * val_ratio)
    splits = {
        "train": valid_ids[:n_train],
        "val":   valid_ids[n_train: n_train + n_val],
        "test":  valid_ids[n_train + n_val:],
    }
    print(f"\n  Split: train={len(splits['train'])} | val={len(splits['val'])} | test={len(splits['test'])}")

    out = Path(output_dir)
    for split, ids in splits.items():
        img_out = out / split / "images"
        lbl_out = out / split / "labels"
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        written = 0
        for img_id in ids:
            img_info = img_map[img_id]
            src = images_path / img_info["file_name"]
            # Flatten batch subdirectory into flat filename
            flat_name = img_info["file_name"].replace("/", "_").replace("\\", "_")
            dst = img_out / flat_name

            if not dst.exists():
                shutil.copy(src, dst)

            W, H = img_info["width"], img_info["height"]
            label_lines = []

            for ann in ann_by_img.get(img_id, []):
                eco_cls = cat_id_to_class.get(ann["category_id"], 19)
                for seg in ann["segmentation"]:
                    if len(seg) < 6:          # need at least 3 points
                        continue
                    pts = []
                    for k in range(0, len(seg), 2):
                        x_norm = max(0.0, min(1.0, seg[k]     / W))
                        y_norm = max(0.0, min(1.0, seg[k + 1] / H))
                        pts.extend([x_norm, y_norm])
                    label_lines.append(f"{eco_cls} " + " ".join(f"{p:.6f}" for p in pts))

            if label_lines:
                lbl_file = lbl_out / (Path(flat_name).stem + ".txt")
                lbl_file.write_text("\n".join(label_lines))
                written += 1

        print(f"  [{split:<5}] {written} label files written -> {lbl_out}")

    print(f"\n[OK] Dataset prepared at {out}")
    print(f"\nNext step -- start training:")
    print("  python ml-models/yolo/train.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert TACO COCO annotations to YOLO seg format"
    )
    parser.add_argument("--coco_json",   required=True, help="Path to instances.json")
    parser.add_argument("--images_dir",  required=True, help="Directory with TACO images")
    parser.add_argument("--output_dir",  default="data/processed", help="Output directory")
    parser.add_argument("--train_ratio", type=float, default=0.70)
    parser.add_argument("--val_ratio",   type=float, default=0.20)
    parser.add_argument("--seed",        type=int,   default=42)
    args = parser.parse_args()

    coco_to_yolo_seg(
        coco_json=args.coco_json,
        images_dir=args.images_dir,
        output_dir=args.output_dir,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )
