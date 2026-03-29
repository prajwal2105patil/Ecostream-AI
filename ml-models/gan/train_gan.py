"""
GAN Training Script -- EcoStream AI
Member 1 (AI/Vision Lead) -- Mahantesh owns this file.

Trains one DCGAN per zero-instance waste class using downloaded seed images.
Saves Generator weights to ml-models/gan/weights/{class_name}_G.pt

Training details:
  - 200 epochs per class on ~30 seed images
  - Adam (lr=0.0002, betas=(0.5, 0.999)) for both G and D
  - BCELoss with label smoothing (real=0.9, fake=0.1) for stability
  - CPU training: ~3-5 min per class, ~20-25 min total

Usage:
    python ml-models/gan/train_gan.py
"""

import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "ml-models" / "gan"))

from dcgan import build_models, LATENT_DIM, IMAGE_SIZE

SEEDS_DIR    = PROJECT_ROOT / "data" / "gan_seeds"
WEIGHTS_DIR  = PROJECT_ROOT / "ml-models" / "gan" / "weights"
WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

EPOCHS       = 200
BATCH_SIZE   = 8
LR           = 0.0002
BETAS        = (0.5, 0.999)
REAL_LABEL   = 0.9   # label smoothing
FAKE_LABEL   = 0.1

MISSING_CLASSES = {
    10: "organic_leaves",
    11: "e_waste_phone",
    14: "rubber_tire",
    15: "construction_debris",
    16: "medical_waste_mask",
}


class SeedDataset(Dataset):
    """Loads seed images from a directory, resizes to 64x64, normalises to [-1,1]."""

    def __init__(self, folder: Path):
        self.paths = (
            list(folder.glob("*.jpg")) +
            list(folder.glob("*.jpeg")) +
            list(folder.glob("*.png"))
        )
        if not self.paths:
            raise RuntimeError(f"No images found in {folder}. Run download_seeds.py first.")
        self.transform = transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.CenterCrop(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
        ])

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        return self.transform(img)


def train_class(class_id: int, class_name: str) -> bool:
    """Train DCGAN for one class. Returns True if successful."""
    weights_path = WEIGHTS_DIR / f"{class_name}_G.pt"
    if weights_path.exists():
        print(f"  [{class_name}] Weights already exist at {weights_path} -- skipping")
        return True

    seed_dir = SEEDS_DIR / class_name
    try:
        dataset = SeedDataset(seed_dir)
    except RuntimeError as e:
        print(f"  [{class_name}] ERROR: {e}")
        return False

    print(f"  [{class_name}] {len(dataset)} seed images, training {EPOCHS} epochs...")

    # Oversample small datasets so each epoch has at least 64 samples
    repeat = max(1, 64 // len(dataset))
    from torch.utils.data import ConcatDataset
    dataset_rep = ConcatDataset([dataset] * repeat)
    loader = DataLoader(dataset_rep, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)

    G, D = build_models()
    criterion = nn.BCELoss()
    opt_G = optim.Adam(G.parameters(), lr=LR, betas=BETAS)
    opt_D = optim.Adam(D.parameters(), lr=LR, betas=BETAS)

    t0 = time.monotonic()
    for epoch in range(1, EPOCHS + 1):
        g_losses, d_losses = [], []

        for real_imgs in loader:
            bs = real_imgs.size(0)

            # ----- Train Discriminator -----
            D.zero_grad()
            real_labels = torch.full((bs,), REAL_LABEL)
            fake_labels = torch.full((bs,), FAKE_LABEL)

            out_real = D(real_imgs)
            loss_real = criterion(out_real, real_labels)

            noise = torch.randn(bs, LATENT_DIM, 1, 1)
            fake_imgs = G(noise).detach()
            out_fake = D(fake_imgs)
            loss_fake = criterion(out_fake, fake_labels)

            loss_D = loss_real + loss_fake
            loss_D.backward()
            opt_D.step()

            # ----- Train Generator -----
            G.zero_grad()
            noise = torch.randn(bs, LATENT_DIM, 1, 1)
            fake_imgs = G(noise)
            out = D(fake_imgs)
            # Generator wants D to output REAL_LABEL for its fakes
            loss_G = criterion(out, torch.full((bs,), REAL_LABEL))
            loss_G.backward()
            opt_G.step()

            g_losses.append(loss_G.item())
            d_losses.append(loss_D.item())

        if epoch % 50 == 0 or epoch == EPOCHS:
            elapsed = time.monotonic() - t0
            avg_g = sum(g_losses) / len(g_losses)
            avg_d = sum(d_losses) / len(d_losses)
            print(f"    Epoch {epoch:3d}/{EPOCHS}  "
                  f"G={avg_g:.4f}  D={avg_d:.4f}  ({elapsed:.0f}s)")

    torch.save(G.state_dict(), weights_path)
    elapsed = time.monotonic() - t0
    print(f"  [{class_name}] Done in {elapsed:.0f}s -> {weights_path}")
    return True


def main():
    print("=" * 60)
    print("  EcoStream AI -- DCGAN Training")
    print("=" * 60)
    print(f"  Classes : {list(MISSING_CLASSES.values())}")
    print(f"  Epochs  : {EPOCHS}")
    print(f"  Device  : CPU")
    print("=" * 60 + "\n")

    t_total = time.monotonic()
    success = 0
    for class_id, class_name in MISSING_CLASSES.items():
        ok = train_class(class_id, class_name)
        if ok:
            success += 1

    elapsed = time.monotonic() - t_total
    print(f"\n  Trained {success}/{len(MISSING_CLASSES)} classes in {elapsed:.0f}s")
    print("  Next: python ml-models/gan/generate.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
