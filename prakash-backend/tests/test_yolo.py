"""
tests/test_yolo.py  --  EcoStream AI YOLO Ablation Study
=========================================================
Week 10 deliverable: compare YOLOv8n bbox baseline vs YOLOv11s-seg
production model on 200 held-out test images.

Outputs a side-by-side mAP table ready to copy into results.tex.

Usage:
    python tests/test_yolo.py

Both model weights must exist:
    vision/model/best.pt       -- YOLOv11s-seg production
    vision/model/baseline.pt   -- YOLOv8n bbox baseline

Owned by: M1a Prajwal Patil (AI/Vision Lead)
"""

import sys
from pathlib import Path

PROJECT_ROOT  = Path(__file__).resolve().parent.parent
MODEL_DIR     = PROJECT_ROOT / "vision" / "model"
BEST_PT       = MODEL_DIR / "best.pt"
BASELINE_PT   = MODEL_DIR / "baseline.pt"
DATASET_YAML  = PROJECT_ROOT / "dataset" / "augmented" / "dataset.yaml"

TEST_IMAGES_DIR = PROJECT_ROOT / "dataset" / "augmented" / "test" / "images"
MAX_TEST_IMAGES = 200   # evaluate on at most 200 held-out images


# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
def _check_prereqs():
    errors = []
    if not BEST_PT.exists():
        errors.append(f"  Missing production weights : {BEST_PT}")
    if not BASELINE_PT.exists():
        errors.append(f"  Missing baseline weights   : {BASELINE_PT}")
    if not DATASET_YAML.exists():
        errors.append(f"  Missing dataset.yaml       : {DATASET_YAML}")
    if errors:
        print("[ERROR] Prerequisites not met:")
        for e in errors:
            print(e)
        print("\n  Run in order:")
        print("    python dataset/gan_mix.py   # build dataset")
        print("    python vision/train.py      # train both models")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Validate on test split, return metrics dict
# ---------------------------------------------------------------------------
def _validate(model, split: str = "test") -> dict:
    """
    Run YOLO val on the test split.
    Returns a flat dict with the numeric metrics we care about.
    """
    metrics = model.val(
        data=str(DATASET_YAML),
        split=split,
        imgsz=416,
        batch=4,
        device="cpu",
        workers=0,
        verbose=False,
        plots=False,
        save_json=False,
    )
    rd = metrics.results_dict
    # Segmentation model keys use (M) suffix; bbox keys use (B)
    return {
        "mAP50":    rd.get("metrics/mAP50(M)",    rd.get("metrics/mAP50(B)",    0.0)),
        "mAP5095":  rd.get("metrics/mAP50-95(M)", rd.get("metrics/mAP50-95(B)", 0.0)),
        "precision":rd.get("metrics/precision(M)", rd.get("metrics/precision(B)",0.0)),
        "recall":   rd.get("metrics/recall(M)",    rd.get("metrics/recall(B)",   0.0)),
    }


# ---------------------------------------------------------------------------
# Pretty-print comparison table
# ---------------------------------------------------------------------------
def _print_table(box_m: dict, seg_m: dict):
    w = 60
    print()
    print("=" * w)
    print("  ABLATION STUDY — YOLOv8n bbox  vs  YOLOv11s-seg")
    print("=" * w)
    header = f"  {'Metric':<20} {'YOLOv8n bbox':>14} {'YOLOv11s-seg':>14}"
    print(header)
    print(f"  {'-'*20} {'-'*14} {'-'*14}")

    metrics_order = [
        ("mAP50",    "mAP50"),
        ("mAP5095",  "mAP50-95"),
        ("precision","Precision"),
        ("recall",   "Recall"),
    ]
    for key, label in metrics_order:
        bv = box_m[key]
        sv = seg_m[key]
        delta = sv - bv
        sign  = "+" if delta >= 0 else ""
        print(f"  {label:<20} {bv:>14.4f} {sv:>14.4f}   ({sign}{delta*100:.1f}%)")

    if box_m["mAP50"] > 0:
        pct = (seg_m["mAP50"] - box_m["mAP50"]) / box_m["mAP50"] * 100
        print(f"\n  mAP50 relative improvement : {pct:+.1f}%")

    print("=" * w)

    # LaTeX table rows for results.tex
    print()
    print("  -- LaTeX (paste into results.tex) --")
    print(r"  \begin{tabular}{lccc}")
    print(r"  \hline")
    print(r"  Model & mAP50 & mAP50-95 & Precision \\")
    print(r"  \hline")
    print(f"  YOLOv8n bbox  & {box_m['mAP50']:.4f} & "
          f"{box_m['mAP5095']:.4f} & {box_m['precision']:.4f} \\\\")
    print(f"  YOLOv11s-seg  & {seg_m['mAP50']:.4f} & "
          f"{seg_m['mAP5095']:.4f} & {seg_m['precision']:.4f} \\\\")
    print(r"  \hline")
    print(r"  \end{tabular}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    _check_prereqs()

    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics not installed.")
        print("  Run: pip install ultralytics")
        sys.exit(1)

    # How many test images are available?
    if TEST_IMAGES_DIR.exists():
        n_test = len(list(TEST_IMAGES_DIR.glob("*.jpg")))
        print(f"[INFO] Test split : {TEST_IMAGES_DIR}")
        print(f"[INFO] Test images: {n_test} (evaluating up to {MAX_TEST_IMAGES})")
    else:
        print(f"[WARN] Test images dir not found: {TEST_IMAGES_DIR}")
        print("       YOLO val will use the 'test' key from dataset.yaml")

    # -- Baseline: YOLOv8n bbox -------------------------------------------------
    print("\n[1/2] Evaluating YOLOv8n bbox baseline ...")
    baseline = YOLO(str(BASELINE_PT))
    box_metrics = _validate(baseline, split="test")
    print(f"  mAP50={box_metrics['mAP50']:.4f}  "
          f"mAP50-95={box_metrics['mAP5095']:.4f}  "
          f"P={box_metrics['precision']:.4f}  R={box_metrics['recall']:.4f}")

    # -- Production: YOLOv11s-seg -----------------------------------------------
    print("\n[2/2] Evaluating YOLOv11s-seg production model ...")
    prod = YOLO(str(BEST_PT))
    seg_metrics = _validate(prod, split="test")
    print(f"  mAP50={seg_metrics['mAP50']:.4f}  "
          f"mAP50-95={seg_metrics['mAP5095']:.4f}  "
          f"P={seg_metrics['precision']:.4f}  R={seg_metrics['recall']:.4f}")

    # -- Print table ------------------------------------------------------------
    _print_table(box_metrics, seg_metrics)


if __name__ == "__main__":
    main()
