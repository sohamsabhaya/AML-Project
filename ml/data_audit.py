"""Duplicate audit and duplicate-aware train/validation split.

STATUS: NOT YET RUN. Needs the Kaggle dataset locally (not included in this repo).

What it does
  1. Hashes every image in Training/ and Testing/ (exact MD5 + 64-bit difference hash).
  2. Reports exact duplicates and near-duplicates (within Training and train vs test).
  3. Groups duplicates/near-duplicates (same class) into connected components, then
     splits whole groups into train/validation so the same slice never lands on both
     sides. (The original notebook used a random per-file 20% split; its cell 6 found
     138 duplicate hashes inside Training.)
  4. Writes manifests: train.csv, val.csv, test.csv and audit_report.json.

Usage:  python ml/data_audit.py [--data-dir PATH] [--out-dir PATH]
Needs only numpy, pillow and pandas (no TensorFlow).
"""
import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

import config


def list_images(root: Path):
    """Yield (path, class_name) for every image under root/<class>/."""
    for cls in config.CLASSES:
        folder = root / cls
        if not folder.is_dir():
            raise FileNotFoundError(f"Missing folder: {folder}")
        for p in sorted(folder.iterdir()):
            if p.suffix.lower() in config.IMAGE_EXTS:
                yield p, cls


def dhash(path: Path, size: int = 8) -> int:
    """64-bit difference hash: robust to re-encoding and small resizes."""
    with Image.open(path) as im:
        g = im.convert("L").resize((size + 1, size), Image.BILINEAR)
    a = np.asarray(g, dtype=np.int16)
    bits = (a[:, 1:] > a[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def build_table(root: Path, split: str, rel_to: Path) -> pd.DataFrame:
    """One row per readable image: relative path, label, md5, dhash."""
    rows = []
    for p, cls in list_images(root):
        try:
            rows.append({
                "path": str(p.relative_to(rel_to)).replace("\\", "/"),
                "label": cls, "split": split,
                "md5": md5(p), "dhash": dhash(p),
            })
        except Exception as exc:  # unreadable file: report it, do not crash
            print(f"WARNING unreadable {p}: {exc}")
    return pd.DataFrame(rows)


class UnionFind:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def near_duplicate_pairs(hashes, max_hamming):
    """Brute-force index pairs whose hashes differ by <= max_hamming bits.

    O(n^2) but vectorised; fine for a few thousand images.
    """
    arr = np.array([h & 0xFFFFFFFFFFFFFFFF for h in hashes], dtype=np.uint64)
    pairs = []
    for i in range(len(arr) - 1):
        x = arr[i] ^ arr[i + 1:]
        counts = np.unpackbits(x.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)
        for j in np.nonzero(counts <= max_hamming)[0]:
            pairs.append((i, i + 1 + int(j)))
    return pairs


def grouped_split(train_df: pd.DataFrame, val_fraction: float, seed: int):
    """Class-stratified split of duplicate groups (a group never straddles train/val)."""
    uf = UnionFind(len(train_df))
    by_md5 = defaultdict(list)
    for i, h in enumerate(train_df["md5"]):
        by_md5[h].append(i)
    for idxs in by_md5.values():
        for k in idxs[1:]:
            uf.union(idxs[0], k)
    labels = train_df["label"].tolist()
    for i, j in near_duplicate_pairs(train_df["dhash"].tolist(), config.NEAR_DUP_MAX_HAMMING):
        if labels[i] == labels[j]:  # keep groups inside one class
            uf.union(i, j)
    train_df = train_df.copy()
    train_df["group"] = [uf.find(i) for i in range(len(train_df))]

    rng = random.Random(seed)
    val_groups = set()
    for _, sub in train_df.groupby("label"):
        sizes = sub.groupby("group").size().to_dict()
        groups = sorted(sizes)
        rng.shuffle(groups)
        target, got = val_fraction * len(sub), 0
        for g in groups:
            if got >= target:
                break
            val_groups.add(g)
            got += sizes[g]
    is_val = train_df["group"].isin(val_groups)
    return train_df[~is_val].reset_index(drop=True), train_df[is_val].reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=str(config.DATA_DIR))
    ap.add_argument("--out-dir", default=str(config.SPLIT_DIR))
    args = ap.parse_args()
    data_dir, out_dir = Path(args.data_dir), Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train = build_table(data_dir / "Training", "train_pool", data_dir)
    test = build_table(data_dir / "Testing", "test", data_dir)

    dup = train.groupby("md5").size()
    dup = dup[dup > 1]
    cross_exact = set(train["md5"]) & set(test["md5"])

    n_train = len(train)
    all_h = train["dhash"].tolist() + test["dhash"].tolist()
    cross_near = [(i, j - n_train) for i, j in near_duplicate_pairs(all_h, config.NEAR_DUP_MAX_HAMMING)
                  if i < n_train <= j]

    tr, va = grouped_split(train, config.VAL_FRACTION, config.SPLIT_SEED)

    cols = ["path", "label", "md5", "dhash"]
    tr[cols].to_csv(out_dir / "train.csv", index=False)
    va[cols].to_csv(out_dir / "val.csv", index=False)
    test[cols].to_csv(out_dir / "test.csv", index=False)

    report = {
        "note": "Generated by data_audit.py; values describe the data actually scanned.",
        "n_train_pool": n_train, "n_test": len(test),
        "exact_duplicate_hashes_in_training": int(len(dup)),
        "exact_duplicate_extra_copies_in_training": int((dup - 1).sum()),
        "exact_cross_split_duplicates": len(cross_exact),
        "near_duplicate_pairs_train_vs_test": len(cross_near),
        "near_duplicate_hamming_threshold": config.NEAR_DUP_MAX_HAMMING,
        "n_train_after_split": len(tr), "n_val_after_split": len(va),
        "val_class_counts": {k: int(v) for k, v in va["label"].value_counts().items()},
        "seed": config.SPLIT_SEED,
        "cross_near_examples": [[train["path"].iat[i], test["path"].iat[j]] for i, j in cross_near[:20]],
    }
    (out_dir / "audit_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
