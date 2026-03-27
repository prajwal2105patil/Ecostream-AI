# -*- coding: utf-8 -*-
"""
TACO Dataset Downloader for EcoStream AI
Member 1 (AI/Vision Lead) owns this file.

Downloads TACO (Trash Annotations in Context) dataset:
  - annotations.json from GitHub (COCO format, ~1500 images, 60 categories)
  - Images from Flickr via URLs listed in annotations

Usage:
    # Download all ~1500 images (recommended, runs overnight on CPU)
    python ml-models/yolo/download_dataset.py

    # Download first 600 images (good for demo/testing)
    python ml-models/yolo/download_dataset.py --subset 600

After download, run:
    python ml-models/yolo/data_prep.py \
        --coco_json data/raw/annotations/instances.json \
        --images_dir data/raw/images \
        --output_dir data/processed
"""

import sys
import time
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

ANNOTATIONS_URL = (
    "https://raw.githubusercontent.com/pedropro/TACO/master/data/annotations.json"
)


def download_file(url, dest):
    """Download a single file with up to 3 retries."""
    headers = {"User-Agent": "Mozilla/5.0 (EcoStream-AI)"}
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                dest.write_bytes(resp.read())
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            if attempt < 2:
                time.sleep(2 ** attempt)
        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)
    return False


def download_annotations(output_dir):
    """Download TACO annotations.json from GitHub."""
    ann_dir = output_dir / "annotations"
    ann_dir.mkdir(parents=True, exist_ok=True)
    ann_file = ann_dir / "instances.json"

    if ann_file.exists() and ann_file.stat().st_size > 10_000:
        print("[OK] Annotations already at {}".format(ann_file))
        with open(ann_file, encoding="utf-8") as f:
            return json.load(f)

    print("Downloading TACO annotations.json from GitHub ...")
    ok = download_file(ANNOTATIONS_URL, ann_file)
    if not ok or not ann_file.exists():
        print("[ERROR] Failed to download annotations.json")
        print("  Manual: https://github.com/pedropro/TACO/blob/master/data/annotations.json")
        sys.exit(1)

    print("[OK] Annotations saved -> {}".format(ann_file))
    with open(ann_file, encoding="utf-8") as f:
        return json.load(f)


def download_images(data, images_dir, subset=None):
    """Download images from Flickr URLs listed in TACO annotations."""
    images_dir.mkdir(parents=True, exist_ok=True)
    images = data["images"]
    if subset:
        images = images[:subset]

    total = len(images)
    downloaded = skipped = failed = 0

    print("\nDownloading {} images to {} ...".format(total, images_dir))
    print("(Ctrl+C to stop -- partial datasets still train fine)\n")

    for i, img in enumerate(images, 1):
        filename = img.get("file_name", "{}.jpg".format(img["id"]))
        dest = images_dir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists() and dest.stat().st_size > 1_000:
            skipped += 1
            if i % 100 == 0:
                _print_progress(i, total, downloaded, skipped, failed)
            continue

        url = img.get("flickr_url") or img.get("coco_url") or ""
        if not url:
            failed += 1
            continue

        ok = download_file(url, dest)
        if ok:
            downloaded += 1
        else:
            failed += 1
            if dest.exists() and dest.stat().st_size == 0:
                dest.unlink()

        if i % 50 == 0 or i == total:
            _print_progress(i, total, downloaded, skipped, failed)

        time.sleep(0.15)  # polite rate-limiting for Flickr

    print("\n" + "=" * 50)
    print("  Downloaded : {}".format(downloaded))
    print("  Skipped    : {} (already existed)".format(skipped))
    print("  Failed     : {} (URL gone / timeout)".format(failed))
    print("  Total ready: {}".format(downloaded + skipped))
    print("=" * 50)
    return downloaded + skipped


def _print_progress(i, total, downloaded, skipped, failed):
    pct = i / total * 100
    bar_filled = int(pct / 5)
    bar = "#" * bar_filled + "." * (20 - bar_filled)
    print("  [{}] {:5.1f}%  {}/{}  (+{} new | ={} skip | x{} fail)".format(
        bar, pct, i, total, downloaded, skipped, failed), end="\r")


def print_category_summary(data):
    """Print TACO categories to verify mapping."""
    cats = sorted(data["categories"], key=lambda c: c["id"])
    print("\nTACO has {} categories:".format(len(cats)))
    for c in cats:
        print("  {:3d}: {}".format(c["id"], c["name"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download TACO trash dataset for EcoStream AI YOLO training"
    )
    parser.add_argument(
        "--subset", type=int, default=None,
        help="Download only first N images (default: all ~1500)"
    )
    parser.add_argument(
        "--output", default="data/raw",
        help="Root output directory (default: data/raw)"
    )
    parser.add_argument(
        "--list-categories", action="store_true",
        help="Print TACO categories and exit"
    )
    args = parser.parse_args()

    output = Path(args.output)
    data = download_annotations(output)

    print("\nTACO dataset summary:")
    print("  Images      : {}".format(len(data["images"])))
    print("  Categories  : {}".format(len(data["categories"])))
    print("  Annotations : {}".format(len(data["annotations"])))

    if args.list_categories:
        print_category_summary(data)
        sys.exit(0)

    subset_label = "first {}".format(args.subset) if args.subset else "all"
    print("\nWill download {} images.".format(subset_label))

    ready = download_images(data, output / "images", subset=args.subset)

    ann_file = output / "annotations" / "instances.json"
    print("\n[NEXT STEP] Run data preparation:")
    print("  python ml-models/yolo/data_prep.py \\")
    print("    --coco_json {} \\".format(ann_file))
    print("    --images_dir {} \\".format(output / "images"))
    print("    --output_dir data/processed")
