"""
GAN Seed Image Downloader
Member 1 (AI/Vision Lead) -- Mahantesh owns this file.

Downloads ~30 real images per zero-instance waste class using Bing image search.
These seed images train the DCGAN to generate realistic synthetic samples.

Zero-instance classes (confirmed from TACO dataset analysis):
  10  organic_leaves
  11  e_waste_phone
  14  rubber_tire
  15  construction_debris
  16  medical_waste_mask

Usage:
    python ml-models/gan/download_seeds.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEEDS_DIR = PROJECT_ROOT / "data" / "gan_seeds"

# Search queries tuned for Indian urban waste context
MISSING_CLASSES = {
    10: ("organic_leaves",       "dry dead leaves pile garbage outdoor"),
    11: ("e_waste_phone",        "broken old mobile phone discarded e-waste"),
    14: ("rubber_tire",          "old rubber tire dumped waste"),
    15: ("construction_debris",  "construction rubble concrete debris waste pile"),
    16: ("medical_waste_mask",   "used disposable face mask waste discarded"),
}

NUM_SEEDS = 30  # per class


def download_class(class_id: int, class_name: str, query: str):
    out_dir = SEEDS_DIR / class_name
    out_dir.mkdir(parents=True, exist_ok=True)

    existing = list(out_dir.glob("*.jpg")) + list(out_dir.glob("*.png"))
    if len(existing) >= NUM_SEEDS:
        print(f"  [{class_name}] Already have {len(existing)} seeds -- skipping download")
        return len(existing)

    print(f"  [{class_name}] Downloading ~{NUM_SEEDS} images for: '{query}'")
    try:
        from icrawler.builtin import BingImageCrawler
        crawler = BingImageCrawler(
            storage={"root_dir": str(out_dir)},
            feeder_threads=1,
            parser_threads=1,
            downloader_threads=4,
        )
        crawler.crawl(keyword=query, max_num=NUM_SEEDS, min_size=(64, 64))
        found = list(out_dir.glob("*.jpg")) + list(out_dir.glob("*.png"))
        print(f"  [{class_name}] Downloaded {len(found)} images -> {out_dir}")
        return len(found)
    except Exception as e:
        print(f"  [{class_name}] Download failed: {e}")
        return 0


def main():
    print("=" * 60)
    print("  EcoStream AI -- GAN Seed Downloader")
    print("=" * 60)
    print(f"  Seeds dir: {SEEDS_DIR}")
    print(f"  Target: {NUM_SEEDS} images per class\n")

    total = 0
    for class_id, (class_name, query) in MISSING_CLASSES.items():
        n = download_class(class_id, class_name, query)
        total += n

    print(f"\n  Done. Total seed images: {total}")
    print("  Next: python ml-models/gan/train_gan.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
