"""
GAN Synthetic Image Generator -- EcoStream AI
Member 1 (AI/Vision Lead) -- Mahantesh owns this file.

Loads trained DCGAN weights and generates 100 synthetic images per zero-instance
class, then injects them directly into the YOLO training dataset with correct
segmentation labels.

Output per class:
  data/processed/train/images/gan_{class_name}_{i:03d}.jpg  (416x416 JPEG)
  data/processed/train/labels/gan_{class_name}_{i:03d}.txt  (YOLO seg format)

YOLO segmentation label format (per line):
  {class_id} x1 y1 x2 y2 ... xn yn   (normalised polygon, 16 points, ellipse)

Usage:
    python ml-models/gan/generate.py
    # Then re-run: python ml-models/yolo/train.py
"""

import math
import sys
from pathlib import Path

import torch
from torchvision.utils import save_image
from PIL import Image
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "ml-models" / "gan"))

from dcgan import Generator, LATENT_DIM, IMAGE_SIZE

WEIGHTS_DIR = PROJECT_ROOT / "ml-models" / "gan" / "weights"
TRAIN_IMGS  = PROJECT_ROOT / "data" / "processed" / "train" / "images"
TRAIN_LBLS  = PROJECT_ROOT / "data" / "processed" / "train" / "labels"
YOLO_IMGSZ  = 416   # must match train.py IMGSZ
N_GENERATE  = 100   # synthetic images per class

MISSING_CLASSES = {
    10: "organic_leaves",
    11: "e_waste_phone",
    14: "rubber_tire",
    15: "construction_debris",
    16: "medical_waste_mask",
}


def make_ellipse_label(class_id: int, n_points: int = 16) -> str:
    """
    Generate a YOLO segmentation label: ellipse polygon centred at image centre.
    Covers ~60% of image width/height (realistic for a full-frame GAN output).
    """
    cx, cy = 0.5, 0.5
    rx, ry = 0.40, 0.40   # semi-axes (normalised)
    coords = []
    for i in range(n_points):
        angle = 2 * math.pi * i / n_points
        x = cx + rx * math.cos(angle)
        y = cy + ry * math.sin(angle)
        # Clamp to [0.01, 0.99]
        coords.extend([max(0.01, min(0.99, x)), max(0.01, min(0.99, y))])
    coord_str = " ".join(f"{v:.6f}" for v in coords)
    return f"{class_id} {coord_str}\n"


def generate_class(class_id: int, class_name: str) -> int:
    weights_path = WEIGHTS_DIR / f"{class_name}_G.pt"
    if not weights_path.exists():
        print(f"  [{class_name}] No weights found at {weights_path}. Run train_gan.py first.")
        return 0

    G = Generator()
    G.load_state_dict(torch.load(weights_path, map_location="cpu"))
    G.eval()

    generated = 0
    with torch.no_grad():
        for i in range(N_GENERATE):
            img_name = f"gan_{class_name}_{i:03d}"
            img_path = TRAIN_IMGS / f"{img_name}.jpg"
            lbl_path = TRAIN_LBLS / f"{img_name}.txt"

            if img_path.exists():
                generated += 1
                continue

            # Generate 64x64 image from noise
            noise = torch.randn(1, LATENT_DIM, 1, 1)
            fake = G(noise).squeeze(0)          # (3, 64, 64) in [-1, 1]

            # Denormalise to [0, 255] and resize to YOLO_IMGSZ x YOLO_IMGSZ
            fake_np = ((fake.permute(1, 2, 0).numpy() + 1) * 127.5).astype(np.uint8)
            pil_img = Image.fromarray(fake_np).resize(
                (YOLO_IMGSZ, YOLO_IMGSZ), Image.BILINEAR
            )
            pil_img.save(str(img_path), "JPEG", quality=90)

            # Write YOLO segmentation label
            lbl_path.write_text(make_ellipse_label(class_id), encoding="utf-8")
            generated += 1

    print(f"  [{class_name}] Generated {generated} images -> {TRAIN_IMGS}")
    return generated


def verify_injection():
    """Re-count class instances after injection to confirm zero classes are fixed."""
    label_dir = TRAIN_LBLS
    class_counts = {}
    for lf in label_dir.glob("*.txt"):
        for line in lf.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                try:
                    cls = int(line.split()[0])
                    class_counts[cls] = class_counts.get(cls, 0) + 1
                except (ValueError, IndexError):
                    pass

    print("\n  Class instance counts after GAN injection:")
    classes = [
        "plastic_pet_bottle", "plastic_bag", "plastic_wrapper", "glass_bottle",
        "glass_broken", "paper_newspaper", "paper_cardboard", "metal_can",
        "metal_scrap", "organic_food_waste", "organic_leaves", "e_waste_phone",
        "e_waste_battery", "textile_cloth", "rubber_tire", "construction_debris",
        "medical_waste_mask", "thermocol", "tetra_pak", "mixed_waste"
    ]
    zero_remaining = 0
    for i, name in enumerate(classes):
        count = class_counts.get(i, 0)
        flag = " <-- STILL ZERO" if count == 0 else (" [GAN]" if "gan" in name.lower() else "")
        if count == 0:
            zero_remaining += 1
        if i in MISSING_CLASSES or count > 0:
            print(f"    {i:2d} {name:<25} {count:4d}{flag}")
    print(f"\n  Zero-instance classes remaining: {zero_remaining}/20")


def main():
    print("=" * 60)
    print("  EcoStream AI -- GAN Image Generation")
    print("=" * 60)
    print(f"  Generating {N_GENERATE} images per class")
    print(f"  Output size: {YOLO_IMGSZ}x{YOLO_IMGSZ}")
    print(f"  Target: {TRAIN_IMGS}")
    print("=" * 60 + "\n")

    total = 0
    for class_id, class_name in MISSING_CLASSES.items():
        n = generate_class(class_id, class_name)
        total += n

    print(f"\n  Total synthetic images injected: {total}")
    verify_injection()

    print("\n  Re-run YOLO training to benefit from synthetic data:")
    print("    python ml-models/yolo/train.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
