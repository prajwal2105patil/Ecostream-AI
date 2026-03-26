"""
YOLO Evaluation Script
Member 1 (AI/Vision Lead) owns this file.

Calculates mAP@50, mAP@50-95, precision, recall, F1 on test set.
Generates confusion matrix saved to runs/segment/eval/

Usage:
    python ml-models/yolo/evaluate.py --weights ml-models/yolo/weights/best.pt
"""

import argparse
from ultralytics import YOLO


def evaluate(weights: str):
    model = YOLO(weights)
    metrics = model.val(
        data="ml-models/yolo/config/dataset.yaml",
        split="test",
        iou=0.5,
        conf=0.25,
        plots=True,
        save_json=True,
    )
    print("\n=== Evaluation Results ===")
    print(f"mAP@50:     {metrics.seg.map50:.4f}")
    print(f"mAP@50-95:  {metrics.seg.map:.4f}")
    print(f"Precision:  {metrics.seg.mp:.4f}")
    print(f"Recall:     {metrics.seg.mr:.4f}")
    print("\nPer-class AP saved in runs/segment/eval/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", default="ml-models/yolo/weights/best.pt")
    args = parser.parse_args()
    evaluate(args.weights)
