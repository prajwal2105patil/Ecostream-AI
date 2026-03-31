"""
dataset/gan_mix.py  --  EcoStream AI Composite Augmentation Pipeline
=====================================================================
Generates 2 000+ synthetic training images by compositing real waste
item crops (TACO / TrashNet) onto bin-area backgrounds.

For each output image:
  1. Sample a random bin background from dataset/raw/backgrounds/
  2. Paste 3-5 randomly chosen waste crops at random position, scale,
     and rotation using alpha compositing.
  3. Compute a per-object polygon mask (cv2.findContours on alpha / binary).
  4. Write YOLO segmentation annotation to dataset/annotations/
     Format: {class_id} x1 y1 x2 y2 ... xN yN  (all normalised 0-1)
  5. Write composited image to dataset/augmented/images/

After all images are generated the script writes dataset/augmented/dataset.yaml
with a 70 / 15 / 15 train/val/test split pointing at the augmented folder.

Prerequisites
-------------
  dataset/raw/<class_name>/*.jpg   -- real crop images per class
  dataset/raw/backgrounds/*.jpg    -- bin / urban-scene backgrounds

Usage:
    python dataset/gan_mix.py

Target output: 2 000 composited images (deletable + regenerable at any time).

Owned by: M1a Prajwal Patil (AI/Vision Lead)
"""

import math
import os
import random
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT   = Path(__file__).resolve().parent.parent
RAW_DIR        = PROJECT_ROOT / "dataset" / "raw"
BACKGROUNDS_DIR = RAW_DIR / "backgrounds"
OUTPUT_IMAGES  = PROJECT_ROOT / "dataset" / "augmented" / "images"
OUTPUT_LABELS  = PROJECT_ROOT / "dataset" / "annotations"
DATASET_YAML   = PROJECT_ROOT / "dataset" / "augmented" / "dataset.yaml"

TARGET_IMAGES  = 2000
IMAGE_SIZE     = 416     # YOLO input resolution
ITEMS_PER_IMG  = (3, 5)  # min / max objects to paste

# Scale range for each pasted object (fraction of background width)
SCALE_MIN, SCALE_MAX = 0.15, 0.45
# Rotation range (degrees)
ROT_MIN,   ROT_MAX   = -30, 30
# Minimum object overlap with background (IoU with full frame)
MIN_VISIBILITY = 0.30

# 20 Indian waste classes -- LOCKED (must match dataset.yaml / serve.py)
CLASS_NAMES = [
    "plastic_pet_bottle", "plastic_bag",      "plastic_wrapper",
    "glass_bottle",       "glass_broken",     "paper_newspaper",
    "paper_cardboard",    "metal_can",         "metal_scrap",
    "organic_food_waste", "organic_leaves",    "e_waste_phone",
    "e_waste_battery",    "textile_cloth",     "rubber_tire",
    "construction_debris","medical_waste_mask","thermocol",
    "tetra_pak",          "mixed_waste",
]
CLASS_ID = {name: idx for idx, name in enumerate(CLASS_NAMES)}

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
try:
    import cv2
    import numpy as np
    _CV2 = True
except ImportError:
    _CV2 = False


# ---------------------------------------------------------------------------
# Helper: rotate image (with alpha if present)
# ---------------------------------------------------------------------------
def _rotate(img: "np.ndarray", angle_deg: float) -> "np.ndarray":
    """Rotate img (BGRA or BGR) around its centre; expands canvas to avoid clipping."""
    h, w = img.shape[:2]
    cx, cy = w / 2, h / 2
    M = cv2.getRotationMatrix2D((cx, cy), angle_deg, 1.0)
    cos_a = abs(M[0, 0])
    sin_a = abs(M[0, 1])
    new_w = int(h * sin_a + w * cos_a)
    new_h = int(h * cos_a + w * sin_a)
    M[0, 2] += (new_w / 2) - cx
    M[1, 2] += (new_h / 2) - cy
    flags = cv2.INTER_LINEAR
    border = cv2.BORDER_CONSTANT
    if img.shape[2] == 4:
        return cv2.warpAffine(img, M, (new_w, new_h), flags=flags,
                              borderMode=border, borderValue=(0, 0, 0, 0))
    return cv2.warpAffine(img, M, (new_w, new_h), flags=flags,
                          borderMode=border, borderValue=(0, 0, 0))


# ---------------------------------------------------------------------------
# Helper: alpha-composite one BGRA patch onto a BGR canvas
# ---------------------------------------------------------------------------
def _paste(canvas: "np.ndarray", patch: "np.ndarray",
           x: int, y: int) -> "np.ndarray":
    """
    Paste `patch` (BGRA) onto `canvas` (BGR) at top-left corner (x, y).
    Clips to canvas boundaries.
    Returns (canvas, actual_mask_bin) where mask_bin is a boolean HxW array
    covering the full canvas, True where the object alpha > 128.
    """
    ch, cw = canvas.shape[:2]
    ph, pw = patch.shape[:2]

    # clipping
    x0 = max(x, 0);   y0 = max(y, 0)
    x1 = min(x + pw, cw);  y1 = min(y + ph, ch)
    px0 = x0 - x;  py0 = y0 - y
    px1 = px0 + (x1 - x0);  py1 = py0 + (y1 - y0)

    if x1 <= x0 or y1 <= y0:
        return canvas, np.zeros((ch, cw), dtype=bool)

    roi = canvas[y0:y1, x0:x1]
    src = patch[py0:py1, px0:px1]

    alpha = src[:, :, 3:4].astype(np.float32) / 255.0
    blended = (src[:, :, :3].astype(np.float32) * alpha
               + roi.astype(np.float32) * (1 - alpha)).astype(np.uint8)
    canvas[y0:y1, x0:x1] = blended

    mask_bin = np.zeros((ch, cw), dtype=bool)
    mask_bin[y0:y1, x0:x1] = (src[:, :, 3] > 128)
    return canvas, mask_bin


# ---------------------------------------------------------------------------
# Helper: binary mask -> YOLO polygon string (largest contour, normalised)
# ---------------------------------------------------------------------------
def _mask_to_yolo_polygon(mask_bin: "np.ndarray", class_id: int,
                           img_h: int, img_w: int) -> str | None:
    """
    Given a boolean mask (H x W) extract the largest contour and return
    a YOLO segmentation label line:
        class_id x1 y1 x2 y2 ... xN yN   (all normalised to [0,1])
    Returns None if no valid contour found.
    """
    m = mask_bin.astype(np.uint8)
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    # pick largest contour
    cnt = max(contours, key=cv2.contourArea)
    if cv2.contourArea(cnt) < 100:
        return None
    pts = cnt.squeeze()
    if pts.ndim != 2 or len(pts) < 3:
        return None
    coords = []
    for p in pts.tolist():
        coords.append(round(p[0] / img_w, 6))
        coords.append(round(p[1] / img_h, 6))
    return f"{class_id} " + " ".join(map(str, coords)) + "\n"


# ---------------------------------------------------------------------------
# Helper: load crop images for all classes found in dataset/raw/
# ---------------------------------------------------------------------------
def _load_crop_index() -> dict[int, list[Path]]:
    """Returns {class_id: [list of image paths]}."""
    index: dict[int, list[Path]] = {}
    if not RAW_DIR.exists():
        return index
    for sub in sorted(RAW_DIR.iterdir()):
        if not sub.is_dir() or sub.name == "backgrounds":
            continue
        cid = CLASS_ID.get(sub.name)
        if cid is None:
            continue
        imgs = [p for p in sub.iterdir()
                if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
        if imgs:
            index[cid] = imgs
    return index


# ---------------------------------------------------------------------------
# Helper: load one crop as BGRA (add alpha channel from grayscale mask if needed)
# ---------------------------------------------------------------------------
def _load_bgra(path: Path) -> "np.ndarray | None":
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 3:
        # No alpha channel -- create one via GrabCut or simple background removal
        # Simple approach: treat near-white/near-black pixels as background
        b, g, r = cv2.split(img)
        # Build alpha: pixels that are not near-white background
        brightness = img.mean(axis=2)
        alpha = np.where(brightness > 240, 0, 255).astype(np.uint8)
        # Optionally erode alpha to remove fringing
        kernel = np.ones((3, 3), np.uint8)
        alpha = cv2.erode(alpha, kernel, iterations=1)
        img = cv2.merge([b, g, r, alpha])
    return img


# ---------------------------------------------------------------------------
# Helper: generate a blank grey background if none exist
# ---------------------------------------------------------------------------
def _get_backgrounds() -> list[Path]:
    bgs = []
    if BACKGROUNDS_DIR.exists():
        bgs = [p for p in BACKGROUNDS_DIR.iterdir()
               if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    return bgs


def _make_synthetic_bg(size: int) -> "np.ndarray":
    """Create a plausible grey concrete / road background when no real BGs exist."""
    base = np.random.randint(80, 160, (size, size, 3), dtype=np.uint8)
    noise = np.random.randint(-20, 20, (size, size, 3), dtype=np.int16)
    bg = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return bg


# ---------------------------------------------------------------------------
# Helper: create a fallback ellipse polygon label (when no cv2 contour works)
# ---------------------------------------------------------------------------
def _ellipse_label(class_id: int) -> str:
    cx, cy, rx, ry = 0.5, 0.5, 0.20, 0.20
    points = []
    for i in range(16):
        theta = 2 * math.pi * i / 16
        x = round(cx + rx * math.cos(theta), 6)
        y = round(cy + ry * math.sin(theta), 6)
        points.extend([x, y])
    return f"{class_id} " + " ".join(map(str, points)) + "\n"


# ---------------------------------------------------------------------------
# Main compositing loop
# ---------------------------------------------------------------------------
def main():
    if not _CV2:
        print("[ERROR] opencv-python not installed.")
        print("  Run: pip install opencv-python-headless")
        sys.exit(1)

    OUTPUT_IMAGES.mkdir(parents=True, exist_ok=True)
    OUTPUT_LABELS.mkdir(parents=True, exist_ok=True)

    crop_index = _load_crop_index()
    if not crop_index:
        print(f"[WARN] No crop images found under {RAW_DIR}/")
        print("       Falling back to solid-colour placeholder crops.")

    bg_paths = _get_backgrounds()
    if not bg_paths:
        print(f"[WARN] No backgrounds found at {BACKGROUNDS_DIR}/")
        print("       Generating synthetic grey backgrounds.")

    print("=" * 60)
    print("  EcoStream AI -- Composite Augmentation")
    print("=" * 60)
    print(f"  Classes with crops : {len(crop_index)}")
    print(f"  Backgrounds found  : {len(bg_paths)}")
    print(f"  Target images      : {TARGET_IMAGES}")
    print(f"  Output images      : {OUTPUT_IMAGES}")
    print(f"  Output labels      : {OUTPUT_LABELS}")
    print("=" * 60)

    # Available class ids for sampling
    available_classes = list(crop_index.keys()) if crop_index else list(range(20))

    generated = 0
    while generated < TARGET_IMAGES:
        # 1. Load / generate background
        if bg_paths:
            bg_raw = cv2.imread(str(random.choice(bg_paths)))
        else:
            bg_raw = None

        if bg_raw is None:
            bg = _make_synthetic_bg(IMAGE_SIZE)
        else:
            bg = cv2.resize(bg_raw, (IMAGE_SIZE, IMAGE_SIZE),
                            interpolation=cv2.INTER_LINEAR)

        canvas = bg.copy()
        img_h, img_w = canvas.shape[:2]
        label_lines = []

        # 2. Paste 3-5 objects
        n_items = random.randint(*ITEMS_PER_IMG)
        sampled_classes = random.choices(available_classes, k=n_items)

        for cid in sampled_classes:
            # Load a crop
            if cid in crop_index:
                crop_path = random.choice(crop_index[cid])
                patch = _load_bgra(crop_path)
            else:
                patch = None

            if patch is None:
                # Fallback: solid colour rectangle with full alpha
                color = [random.randint(30, 220) for _ in range(3)]
                ph = pw = random.randint(40, 100)
                patch = np.zeros((ph, pw, 4), dtype=np.uint8)
                patch[:, :, :3] = color
                patch[:, :, 3] = 255

            # 3. Scale
            scale = random.uniform(SCALE_MIN, SCALE_MAX)
            new_w = max(20, int(img_w * scale))
            aspect = patch.shape[0] / max(patch.shape[1], 1)
            new_h = max(20, int(new_w * aspect))
            patch = cv2.resize(patch, (new_w, new_h),
                               interpolation=cv2.INTER_LINEAR)

            # 4. Rotate
            angle = random.uniform(ROT_MIN, ROT_MAX)
            patch = _rotate(patch, angle)

            ph, pw = patch.shape[:2]

            # 5. Random position (allow partial occlusion at edges)
            x = random.randint(-pw // 4, img_w - pw // 4 * 3)
            y = random.randint(-ph // 4, img_h - ph // 4 * 3)

            # 6. Alpha composite
            canvas, mask_bin = _paste(canvas, patch, x, y)

            if not mask_bin.any():
                continue

            # Check visibility
            visible_px = mask_bin.sum()
            total_px   = img_h * img_w
            if visible_px / total_px < MIN_VISIBILITY * scale:
                label_line = _ellipse_label(cid)
            else:
                label_line = _mask_to_yolo_polygon(mask_bin, cid, img_h, img_w)
                if label_line is None:
                    label_line = _ellipse_label(cid)

            label_lines.append(label_line)

        if not label_lines:
            continue  # nothing pasted, skip

        # 7. Save image + label
        stem = f"composite_{generated:05d}"
        img_path = OUTPUT_IMAGES / f"{stem}.jpg"
        lbl_path = OUTPUT_LABELS / f"{stem}.txt"

        cv2.imwrite(str(img_path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 90])
        lbl_path.write_text("".join(label_lines))

        generated += 1
        if generated % 200 == 0:
            print(f"  [{generated}/{TARGET_IMAGES}] images generated ...")

    print(f"\n[DONE] Generated {generated} composited images.")
    print(f"       Images : {OUTPUT_IMAGES}")
    print(f"       Labels : {OUTPUT_LABELS}")

    # -----------------------------------------------------------------------
    # Write dataset.yaml with 70/15/15 split
    # -----------------------------------------------------------------------
    _write_dataset_yaml(generated)
    print(f"       dataset.yaml -> {DATASET_YAML}")
    print("\n  Next: python vision/train.py")


# ---------------------------------------------------------------------------
# dataset.yaml writer -- creates symlinked train/val/test splits
# ---------------------------------------------------------------------------
def _write_dataset_yaml(n_total: int):
    """
    Shuffle all generated images and write dataset.yaml pointing to
    dataset/augmented/{train,val,test}/ sub-folders with 70/15/15 split.
    Copies (hard-links where possible) images + labels into split dirs.
    """
    all_imgs = sorted(OUTPUT_IMAGES.glob("*.jpg"))
    random.shuffle(all_imgs)

    n_train = int(n_total * 0.70)
    n_val   = int(n_total * 0.15)
    # test gets the rest

    splits = {
        "train": all_imgs[:n_train],
        "val":   all_imgs[n_train:n_train + n_val],
        "test":  all_imgs[n_train + n_val:],
    }

    aug_root = OUTPUT_IMAGES.parent
    for split, imgs in splits.items():
        (aug_root / split / "images").mkdir(parents=True, exist_ok=True)
        (aug_root / split / "labels").mkdir(parents=True, exist_ok=True)
        for img_p in imgs:
            lbl_p = OUTPUT_LABELS / (img_p.stem + ".txt")
            dst_img = aug_root / split / "images" / img_p.name
            dst_lbl = aug_root / split / "labels" / (img_p.stem + ".txt")
            # copy (safe on Windows + cross-device)
            shutil.copy2(str(img_p), str(dst_img))
            if lbl_p.exists():
                shutil.copy2(str(lbl_p), str(dst_lbl))

    yaml_content = f"""\
# EcoStream AI -- Composite Augmented Dataset
# Generated by dataset/gan_mix.py
# {n_total} total images, 70/15/15 split

path: {aug_root.as_posix()}
train: train/images
val:   val/images
test:  test/images

nc: {len(CLASS_NAMES)}
names: {CLASS_NAMES}
"""
    DATASET_YAML.parent.mkdir(parents=True, exist_ok=True)
    DATASET_YAML.write_text(yaml_content)


if __name__ == "__main__":
    main()
