"""Shared settings for the ML improvement pipeline.

STATUS: NOT YET RUN. Nothing in this folder has been executed; no result from it
is claimed anywhere in the repository.

All paths are relative to the repository root or taken from environment
variables, so the same code works on a laptop and on Colab.
Override with:  BRAIN_DATA_DIR=/path/to/dataset  BRAIN_OUT_DIR=/path/to/outputs
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = Path(__file__).resolve().parent

# Dataset root containing Training/ and Testing/ (not in the repo, not downloaded here).
DATA_DIR = Path(os.environ.get("BRAIN_DATA_DIR", ROOT / "dataset"))
TRAIN_DIR = DATA_DIR / "Training"
TEST_DIR = DATA_DIR / "Testing"

# Where splits, checkpoints and evaluation outputs go (large files should stay out of git).
OUT_DIR = Path(os.environ.get("BRAIN_OUT_DIR", ML_DIR / "outputs"))
SPLIT_DIR = OUT_DIR / "splits"
CKPT_DIR = OUT_DIR / "checkpoints"
EVAL_DIR = OUT_DIR / "eval"

# Same alphabetical class order the notebook and the backend use.
CLASSES = ["glioma", "meningioma", "notumor", "pituitary"]
IMG_SIZE = (224, 224)
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# Splitting
VAL_FRACTION = 0.2
SPLIT_SEED = 42
# Near-duplicate threshold: Hamming distance between 64-bit difference hashes.
NEAR_DUP_MAX_HAMMING = 4

# Training (stage 1 = head only, stage 2 = partial unfreeze)
SEEDS = [42, 1337, 2024]
BATCH_SIZE = 32
STAGE1_EPOCHS = 8
STAGE1_LR = 1e-3
STAGE2_EPOCHS = 20
STAGE2_LR = 1e-5
# First ResNet50 layer to unfreeze for each depth option.
UNFREEZE_FROM = {"conv5": "conv5_block1_1_conv", "conv4": "conv4_block1_1_conv"}
LABEL_SMOOTHING = 0.05
EARLY_STOP_PATIENCE = 5
DROPOUT = 0.4

# Evaluation
BOOTSTRAP_ITERS = 2000
CALIBRATION_BINS = 15
