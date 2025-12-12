"""
Dataset Splitter Module.

This script organizes a flat dataset directory into a standard Train/Validation structure 
required by PyTorch's ImageFolder or Keras's flow_from_directory.

Structure Transformation:
-------------------------
Before:
    dataset_root/
    ├── angry/
    ├── happy/
    └── sad/

After:
    dataset_root/
    ├── train/
    │   ├── angry/
    │   ├── happy/
    │   └── sad/
    ├── val/
    │   ├── angry/
    │   ├── happy/
    │   └── sad/
    ├── angry/  (Original folders remain safe)
    ├── happy/
    └── sad/
"""

import os
import shutil
import random
from tqdm import tqdm
from typing import List

class DataSplitter:
    def __init__(self, dataset_root: str, train_ratio: float = 0.8, seed: int = 42):
        """
        Args:
            dataset_root (str): Path to the folder containing class subfolders.
            train_ratio (float): Percentage of data to use for training (0.0 to 1.0).
            seed (int): Random seed for reproducibility.
        """
        self.dataset_root = dataset_root
        self.train_ratio = train_ratio
        self.seed = seed

        # Set seed for reproducible splits
        random.seed(self.seed)

        self.train_dir = os.path.join(self.dataset_root, "train")
        self.val_dir = os.path.join(self.dataset_root, "val")

    def _get_classes(self) -> List[str]:
        """Scans the root directory for class folders, ignoring 'train' and 'val'."""
        classes = []
        for name in os.listdir(self.dataset_root):
            path = os.path.join(self.dataset_root, name)
            
            # Skip non-directories and the output folders themselves
            if os.path.isdir(path) and name not in ["train", "val"]:
                classes.append(name)
        return classes

    def _create_output_dirs(self, classes: List[str]):
        """Creates the necessary train/val directory structure."""
        for cls in classes:
            os.makedirs(os.path.join(self.train_dir, cls), exist_ok=True)
            os.makedirs(os.path.join(self.val_dir, cls), exist_ok=True)

    def split(self):
        """Main method to execute the split."""
        classes = self._get_classes()
        print(f"Found classes: {classes}")

        self._create_output_dirs(classes)

        for cls in classes:
            class_path = os.path.join(self.dataset_root, cls)

            # Filter for valid image files only
            images = [
                f for f in os.listdir(class_path)
                if os.path.isfile(os.path.join(class_path, f)) 
                and f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
            ]

            print(f"\nProcessing Class: {cls} - {len(images)} images found.")

            # Shuffle to ensure random distribution
            random.shuffle(images)

            # Calculate split index
            train_count = int(len(images) * self.train_ratio)
            train_imgs = images[:train_count]
            val_imgs = images[train_count:]

            # Copy Train images
            for img in tqdm(train_imgs, desc=f"Copying Train ({cls})", ncols=80):
                src = os.path.join(class_path, img)
                dst = os.path.join(self.train_dir, cls, img)
                shutil.copy2(src, dst)

            # Copy Validation images
            for img in tqdm(val_imgs, desc=f"Copying Val   ({cls})", ncols=80):
                src = os.path.join(class_path, img)
                dst = os.path.join(self.val_dir, cls, img)
                shutil.copy2(src, dst)

        print("\n✅ Dataset splitting completed successfully!")
        print(f"Train set location: {self.train_dir}")
        print(f"Val set location:   {self.val_dir}")


if __name__ == "__main__":
    # Define the path using os.path.join for cross-platform compatibility (Windows/Mac/Linux)
    dataset_path = os.path.join(
        "services", "emotion-detection", "Models", "Data", "processed_data"
    )
    
    # Initialize and run
    # Ensure the path actually exists before running
    if os.path.exists(dataset_path):
        splitter = DataSplitter(dataset_path, train_ratio=0.8)
        splitter.split()
    else:
        print(f"❌ Error: The path '{dataset_path}' does not exist.")