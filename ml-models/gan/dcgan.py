"""
DCGAN Architecture -- EcoStream AI
Member 1 (AI/Vision Lead) -- Mahantesh owns this file.

Deep Convolutional GAN (Radford et al., 2015) adapted for 64x64 waste images.
One Generator + Discriminator pair is trained per zero-instance waste class.

Architecture:
  Generator  : 100-dim noise -> 512 -> 256 -> 128 -> 64 -> 3x64x64 (tanh)
  Discriminator: 3x64x64 -> 64 -> 128 -> 256 -> 512 -> 1 (sigmoid)

Both use BatchNorm + LeakyReLU (Discriminator) / ReLU (Generator).
"""

import torch
import torch.nn as nn

LATENT_DIM = 100   # noise vector size
IMAGE_SIZE = 64    # output image size (64x64)
NGF = 64           # generator feature map base size
NDF = 64           # discriminator feature map base size
NC = 3             # RGB channels


class Generator(nn.Module):
    """Maps latent noise z (100,) -> RGB image (3, 64, 64)."""

    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            # Input: (LATENT_DIM, 1, 1)
            nn.ConvTranspose2d(LATENT_DIM, NGF * 8, 4, 1, 0, bias=False),
            nn.BatchNorm2d(NGF * 8),
            nn.ReLU(True),
            # -> (NGF*8, 4, 4)
            nn.ConvTranspose2d(NGF * 8, NGF * 4, 4, 2, 1, bias=False),
            nn.BatchNorm2d(NGF * 4),
            nn.ReLU(True),
            # -> (NGF*4, 8, 8)
            nn.ConvTranspose2d(NGF * 4, NGF * 2, 4, 2, 1, bias=False),
            nn.BatchNorm2d(NGF * 2),
            nn.ReLU(True),
            # -> (NGF*2, 16, 16)
            nn.ConvTranspose2d(NGF * 2, NGF, 4, 2, 1, bias=False),
            nn.BatchNorm2d(NGF),
            nn.ReLU(True),
            # -> (NGF, 32, 32)
            nn.ConvTranspose2d(NGF, NC, 4, 2, 1, bias=False),
            nn.Tanh(),
            # -> (3, 64, 64)  values in [-1, 1]
        )

    def forward(self, z):
        return self.net(z)


class Discriminator(nn.Module):
    """Maps RGB image (3, 64, 64) -> real/fake probability scalar."""

    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            # Input: (3, 64, 64)
            nn.Conv2d(NC, NDF, 4, 2, 1, bias=False),
            nn.LeakyReLU(0.2, inplace=True),
            # -> (NDF, 32, 32)
            nn.Conv2d(NDF, NDF * 2, 4, 2, 1, bias=False),
            nn.BatchNorm2d(NDF * 2),
            nn.LeakyReLU(0.2, inplace=True),
            # -> (NDF*2, 16, 16)
            nn.Conv2d(NDF * 2, NDF * 4, 4, 2, 1, bias=False),
            nn.BatchNorm2d(NDF * 4),
            nn.LeakyReLU(0.2, inplace=True),
            # -> (NDF*4, 8, 8)
            nn.Conv2d(NDF * 4, NDF * 8, 4, 2, 1, bias=False),
            nn.BatchNorm2d(NDF * 8),
            nn.LeakyReLU(0.2, inplace=True),
            # -> (NDF*8, 4, 4)
            nn.Conv2d(NDF * 8, 1, 4, 1, 0, bias=False),
            nn.Sigmoid(),
            # -> (1, 1, 1)
        )

    def forward(self, x):
        return self.net(x).view(-1)


def weights_init(m):
    """DCGAN weight initialisation: Conv/ConvTranspose ~ N(0, 0.02), BN ~ N(1, 0.02)."""
    classname = m.__class__.__name__
    if "Conv" in classname:
        nn.init.normal_(m.weight.data, 0.0, 0.02)
    elif "BatchNorm" in classname:
        nn.init.normal_(m.weight.data, 1.0, 0.02)
        nn.init.constant_(m.bias.data, 0)


def build_models():
    """Instantiate and initialise Generator + Discriminator."""
    G = Generator()
    D = Discriminator()
    G.apply(weights_init)
    D.apply(weights_init)
    return G, D
