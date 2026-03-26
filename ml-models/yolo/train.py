"""
YOLO Training Script
Member 1 (AI/Vision Lead) owns this file.

Usage:
    python ml-models/yolo/train.py

Requires:
    - pip install ultralytics
    - Dataset prepared in YOLO segmentation format at data/processed/
    - See data_prep.py to convert from COCO format
"""

from ultralytics import YOLO


def train():
    model = YOLO("yolo11n-seg.pt")  # Download pretrained if not cached

    results = model.train(
        cfg="ml-models/yolo/config/train_config.yaml",
        data="ml-models/yolo/config/dataset.yaml",
    )
    print(f"\nTraining complete. Best weights: {results.save_dir}/weights/best.pt")
    print("Copy best.pt to: ml-models/yolo/weights/best.pt")


if __name__ == "__main__":
    train()
