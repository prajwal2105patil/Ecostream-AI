"""
YOLO Training Script — EcoStream AI
Member 1 (AI/Vision Lead) owns this file.

Usage (run from project root: d:/Smart Waste Management/):
    python ml-models/yolo/train.py

Prerequisites:
    1. pip install ultralytics
    2. Download dataset:  python ml-models/yolo/download_dataset.py --subset 600
    3. Prepare dataset:   python ml-models/yolo/data_prep.py \
                              --coco_json data/raw/annotations/instances.json \
                              --images_dir data/raw/images \
                              --output_dir data/processed

Expected time (CPU, ~600 images, 50 epochs, imgsz=416):
    ~3–5 hours — run overnight, then pick up best.pt in the morning.

After training:
    best.pt is auto-copied to ml-models/yolo/weights/best.pt
    The inference pipeline (inference.py) detects this automatically.
"""

import shutil
import sys
import time
from pathlib import Path

# ── Paths (project root assumed as CWD) ────────────────────────────────────
PROJECT_ROOT   = Path(__file__).resolve().parents[2]
WEIGHTS_DIR    = PROJECT_ROOT / "ml-models" / "yolo" / "weights"
TRAIN_CFG      = PROJECT_ROOT / "ml-models" / "yolo" / "config" / "train_config.yaml"
DATASET_YAML   = PROJECT_ROOT / "ml-models" / "yolo" / "config" / "dataset.yaml"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"


def check_dataset() -> bool:
    """Verify that processed dataset exists before training."""
    train_imgs = DATA_PROCESSED / "train" / "images"
    val_imgs   = DATA_PROCESSED / "val"   / "images"

    if not train_imgs.exists() or not any(train_imgs.iterdir()):
        print("[ERROR] Training images not found at data/processed/train/images/")
        print("\nRun these steps first:")
        print("  python ml-models/yolo/download_dataset.py --subset 600")
        print("  python ml-models/yolo/data_prep.py \\")
        print("      --coco_json data/raw/annotations/instances.json \\")
        print("      --images_dir data/raw/images \\")
        print("      --output_dir data/processed")
        return False

    n_train = len(list(train_imgs.glob("*")))
    n_val   = len(list(val_imgs.glob("*"))) if val_imgs.exists() else 0
    print(f"[✓] Dataset ready: {n_train} train images, {n_val} val images")
    return True


def train():
    from ultralytics import YOLO

    if not check_dataset():
        sys.exit(1)

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print("  EcoStream AI — YOLOv11-seg Training")
    print("="*60)
    print(f"  Config   : {TRAIN_CFG}")
    print(f"  Dataset  : {DATASET_YAML}")
    print(f"  Output   : runs/segment/ecostream_waste/")
    print("="*60 + "\n")

    # Load pretrained YOLOv11-nano-seg (auto-downloads ~6 MB if not cached)
    model = YOLO("yolo11n-seg.pt")

    start = time.time()
    results = model.train(
        cfg=str(TRAIN_CFG),
        data=str(DATASET_YAML),
    )
    elapsed = time.time() - start
    hours, rem = divmod(int(elapsed), 3600)
    mins = rem // 60

    best_src = Path(results.save_dir) / "weights" / "best.pt"
    dest     = WEIGHTS_DIR / "best.pt"

    print("\n" + "="*60)
    print(f"  Training complete in {hours}h {mins}m")
    print(f"  Best weights : {best_src}")
    print("="*60)

    if best_src.exists():
        shutil.copy(best_src, dest)
        print(f"[✓] Copied best.pt → {dest}")
        print("\n  Inference pipeline will use these weights automatically.")
        print("  To test: python ml-models/yolo/evaluate.py")
    else:
        print(f"[WARN] best.pt not found at {best_src}")
        print("  Check runs/segment/ecostream_waste/weights/ manually.")

    # Print key metrics if available
    try:
        metrics = results.results_dict
        map50   = metrics.get("metrics/mAP50(M)", metrics.get("metrics/mAP50(B)", "N/A"))
        map5095 = metrics.get("metrics/mAP50-95(M)", "N/A")
        print(f"\n  mAP@0.5      : {map50}")
        print(f"  mAP@0.5:0.95 : {map5095}")
        if isinstance(map50, float):
            if map50 >= 0.70:
                print("  → Publication-ready (IEEE paper quality)")
            elif map50 >= 0.55:
                print("  → Good for IEEE paper submission")
            elif map50 >= 0.45:
                print("  → Acceptable for demo; consider more epochs/data")
            else:
                print("  → Below target — try: more data, more epochs, or GPU training")
    except Exception:
        pass


if __name__ == "__main__":
    train()
