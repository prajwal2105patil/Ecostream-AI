"""
EcoStream AI -- YOLO Autoresearch Train Script
===========================================================================

Agent contract:
  - This is the ONLY file the autoresearch agent may edit.
  - Run: python ml-models/yolo/train.py
  - Budget: 5-minute wall-clock maximum (enforced by callback).
  - Output: Final line of stdout is a JSON metrics dict.
  - Prerequisites: Run prepare.py first to populate data/processed/.

The agent experiments by modifying the EXPERIMENT KNOBS section below.
Everything below the FIXED CONSTANTS section must not be changed.
"""

import json
import shutil
import sys
import time
from pathlib import Path

# ==========================================================================
# EXPERIMENT KNOBS -- The autoresearch agent modifies ONLY these constants
# ==========================================================================

# Model architecture
MODEL_VARIANT = "yolo11s-seg.pt"      # yolo11n-seg | yolo11s-seg | yolo11m-seg

# Image & batch
IMGSZ      = 416                       # 416 balances speed vs accuracy on CPU
BATCH_SIZE = 8                         # 8 for faster epochs on CPU

# Optimizer -- Full paper run: AdamW + progressive unfreeze + copy-paste
OPTIMIZER    = "AdamW"                 # Best for transfer learning
LR0          = 0.001                   # Standard AdamW LR for fine-tuning
LRF          = 0.01                    # Cosine decay to 1% of LR0
MOMENTUM     = 0.937                   # Adam beta1
WEIGHT_DECAY = 0.0005                  # L2 regularization

# Schedule -- full run with proper warmup
WARMUP_EPOCHS = 3.0                    # 3-epoch warmup for stable convergence
PATIENCE      = 20                     # Generous -- let the model converge fully

# Transfer learning -- progressive unfreeze (ULMFiT for YOLO)
FREEZE_LAYERS = 10                     # Freeze backbone epoch 0
PROGRESSIVE_UNFREEZE = True            # Unfreeze all at epoch 1, LR /= 10

# Augmentation -- full augmentation suite for paper
HSV_H     = 0.015                      # Hue jitter
HSV_S     = 0.7                        # Saturation jitter
HSV_V     = 0.4                        # Value jitter
DEGREES   = 10.0                       # Rotation degrees
TRANSLATE = 0.1                        # Translation fraction
SCALE     = 0.5                        # Scale gain
FLIPLR    = 0.5                        # Horizontal flip probability
MOSAIC    = 1.0                        # Full mosaic -- enough epochs to benefit
MIXUP     = 0.1                        # Light mixup for regularization
COPY_PASTE = 0.5                       # Copy-paste masks for class imbalance
CLOSE_MOSAIC = 10                      # Disable mosaic last 10 epochs for clean convergence

# Validation thresholds
CONF_THRESHOLD = 0.25                  # Confidence threshold for NMS
IOU_THRESHOLD  = 0.45                  # IoU threshold for NMS


# ==========================================================================
# FIXED CONSTANTS -- Agent must NOT change anything below this line
# ==========================================================================

WALL_CLOCK_BUDGET_SEC = 18000           # 5 hours -- full paper run

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_YAML = PROJECT_ROOT / "data" / "processed" / "dataset.yaml"
WEIGHTS_DIR  = PROJECT_ROOT / "ml-models" / "yolo" / "weights"
NC           = 20                      # 20 Indian waste classes -- LOCKED


def main():
    # -- Pre-flight checks ------------------------------------------------
    if not DATASET_YAML.exists():
        print(f"[ERROR] {DATASET_YAML} not found. Run prepare.py first.")
        sys.exit(1)

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  EcoStream AI -- YOLO Autoresearch Training")
    print("=" * 60)
    print(f"  Model     : {MODEL_VARIANT}")
    print(f"  ImgSz     : {IMGSZ}")
    print(f"  Batch     : {BATCH_SIZE}")
    print(f"  Optimizer : {OPTIMIZER} (lr={LR0})")
    print(f"  Patience  : {PATIENCE}")
    print(f"  Freeze    : {FREEZE_LAYERS} layers")
    print(f"  Budget    : {WALL_CLOCK_BUDGET_SEC}s")
    print(f"  Dataset   : {DATASET_YAML}")
    print("=" * 60)

    from ultralytics import YOLO

    model = YOLO(MODEL_VARIANT)

    # -- 5-minute wall-clock guard (callback, Windows-safe) ---------------
    _start = time.monotonic()
    _epoch_end_times = []  # wall-clock timestamp at end of each epoch

    def _time_guard(trainer):
        now = time.monotonic()
        _epoch_end_times.append(now)
        elapsed = now - _start

        # Use the LAST epoch's duration (not the average) because epoch 0
        # includes one-time setup costs (model download, dataset scan, cache build)
        # that inflate the average and cause premature stopping.
        if len(_epoch_end_times) >= 2:
            last_epoch_dur = _epoch_end_times[-1] - _epoch_end_times[-2]
        else:
            last_epoch_dur = elapsed  # only have epoch 0

        remaining = WALL_CLOCK_BUDGET_SEC - elapsed
        if remaining < last_epoch_dur * 1.3:  # 30% safety margin
            epoch = getattr(trainer, "epoch", 0)
            print(f"\n[BUDGET] Stopping at epoch {epoch} -- "
                  f"{elapsed:.0f}s elapsed, last epoch ~{last_epoch_dur:.0f}s, "
                  f"{remaining:.0f}s remaining")
            trainer.stop = True

    model.add_callback("on_train_epoch_end", _time_guard)

    # -- Freeze backbone layers if requested ------------------------------
    if FREEZE_LAYERS > 0:
        frozen = 0
        for i, (name, param) in enumerate(model.model.named_parameters()):
            if i < FREEZE_LAYERS:
                param.requires_grad = False
                frozen += 1
        print(f"  Froze {frozen} parameter tensors")

    # -- Progressive unfreeze (ULMFiT pattern adapted for YOLO) ---------
    # Epoch 0: train head only (fast class assignment learning)
    # Epoch 1+: unfreeze all layers, drop LR 10x (fine-tune backbone)
    _unfrozen = [False]

    if FREEZE_LAYERS > 0 and PROGRESSIVE_UNFREEZE:
        def _progressive_unfreeze_cb(trainer):
            if not _unfrozen[0] and getattr(trainer, "epoch", 0) >= 1:
                for param in trainer.model.parameters():
                    param.requires_grad = True
                for pg in trainer.optimizer.param_groups:
                    pg["lr"] *= 0.1
                _unfrozen[0] = True
                print(f"\n[UNFREEZE] All layers unfrozen at epoch {trainer.epoch}, "
                      f"LR reduced 10x -> {pg['lr']:.6f}")

        model.add_callback("on_train_epoch_start", _progressive_unfreeze_cb)
        print("  Progressive unfreeze enabled: will unfreeze at epoch 1")

    # -- Train ------------------------------------------------------------
    results = model.train(
        data=str(DATASET_YAML),
        epochs=70,                     # full paper run
        patience=PATIENCE,
        imgsz=IMGSZ,
        batch=BATCH_SIZE,
        device="cpu",
        workers=0,                     # Windows requirement
        optimizer=OPTIMIZER,
        lr0=LR0,
        lrf=LRF,
        momentum=MOMENTUM,
        weight_decay=WEIGHT_DECAY,
        warmup_epochs=WARMUP_EPOCHS,
        hsv_h=HSV_H,
        hsv_s=HSV_S,
        hsv_v=HSV_V,
        degrees=DEGREES,
        translate=TRANSLATE,
        scale=SCALE,
        fliplr=FLIPLR,
        mosaic=MOSAIC,
        mixup=MIXUP,
        copy_paste=COPY_PASTE,
        close_mosaic=CLOSE_MOSAIC,
        conf=CONF_THRESHOLD,
        iou=IOU_THRESHOLD,
        project=str(PROJECT_ROOT / "runs" / "segment"),
        name="autoresearch",
        exist_ok=True,
        plots=False,                   # save time during experiments
        save_period=-1,                # only save best/last
        cache=True,                    # load all images into RAM once (~90 MB for 420 imgs)
    )

    elapsed = time.monotonic() - _start

    # -- Copy best weights ------------------------------------------------
    best_src = Path(results.save_dir) / "weights" / "best.pt"
    if best_src.exists():
        shutil.copy(best_src, WEIGHTS_DIR / "best.pt")
        print(f"\n[OK] best.pt -> {WEIGHTS_DIR / 'best.pt'}")

    # -- Extract metrics --------------------------------------------------
    try:
        m = results.results_dict
    except Exception:
        m = {}

    output = {
        "experiment": "yolo",
        "wall_clock_sec": round(elapsed, 1),
        "epochs_completed": getattr(results, "epoch", 0),
        "map50_seg": round(m.get("metrics/mAP50(M)", 0.0), 4),
        "map50_95_seg": round(m.get("metrics/mAP50-95(M)", 0.0), 4),
        "map50_box": round(m.get("metrics/mAP50(B)", 0.0), 4),
        "precision_seg": round(m.get("metrics/precision(M)", 0.0), 4),
        "recall_seg": round(m.get("metrics/recall(M)", 0.0), 4),
        "val_loss_seg": round(m.get("val/seg_loss", 0.0), 4),
        "val_loss_box": round(m.get("val/box_loss", 0.0), 4),
        "val_loss_cls": round(m.get("val/cls_loss", 0.0), 4),
        "model_variant": MODEL_VARIANT,
        "imgsz": IMGSZ,
        "batch_size": BATCH_SIZE,
        "optimizer": OPTIMIZER,
        "lr0": LR0,
        "freeze_layers": FREEZE_LAYERS,
        "progressive_unfreeze": PROGRESSIVE_UNFREEZE,
        "copy_paste": COPY_PASTE,
    }

    # MUST be the final line of stdout -- the autoresearch agent parses this
    print(json.dumps(output))


if __name__ == "__main__":
    main()
