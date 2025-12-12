"""
Training Script for Emotion Detection (EfficientNet-B0).

This script handles the entire training pipeline:
1. Loads the dataset with correct transforms (224x224, RGB).
2. Initializes the EfficientNet-B0 model (Pre-trained).
3. Trains the model using AdamW optimizer and CrossEntropyLoss.
4. Saves the best model weights based on validation accuracy.

Usage:
    Adjust the 'Config' class paths to match your environment.
    Run: python train.py
"""

import os
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader as TorchDataLoader
from torchvision import transforms, datasets, models
from tqdm import tqdm

# ==========================================
# 1. Configuration
# ==========================================
class Config:
    def __init__(self):
        # ---------------------------------------------------------
        # ⚠️ CRITICAL: Update this path to your actual data folder
        # ---------------------------------------------------------
        # For Colab: "/content/drive/MyDrive/..."
        # For Local: "processed_data" or absolute path
        self.data_root = "processed_data" 
        
        self.train_dir = os.path.join(self.data_root, "train")
        self.val_dir   = os.path.join(self.data_root, "val")

        # Hyperparameters
        self.num_classes   = 7
        self.batch_size    = 32    # 16 or 32 is safe for most GPUs
        self.num_epochs    = 20    # 15-20 is usually enough for Transfer Learning
        self.learning_rate = 3e-4  # 0.0003 is standard for fine-tuning
        self.weight_decay  = 1e-4  # Regularization
        self.num_workers   = 2     # Set to 0 if you get errors on Windows
        
        # Hardware
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Output Path
        self.save_path = "efficientnet_emotion_best.pt"

def set_seed(seed=42):
    """Sets random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

# ==========================================
# 2. Data Module
# ==========================================
class EmotionDataModule:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def _build_transforms(self):
        # EfficientNet Expectations: 224x224 size, 3 Channels, Normalized
        train_tf = transforms.Compose([
            transforms.Grayscale(num_output_channels=3), # Convert 1 ch -> 3 ch
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        val_tf = transforms.Compose([
            transforms.Grayscale(num_output_channels=3),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        return train_tf, val_tf

    def setup(self):
        train_tf, val_tf = self._build_transforms()
        
        # Load datasets using ImageFolder structure
        self.train_dataset = datasets.ImageFolder(root=self.cfg.train_dir, transform=train_tf)
        self.val_dataset = datasets.ImageFolder(root=self.cfg.val_dir, transform=val_tf)

        print(f"✅ Data Loaded:")
        print(f"   - Train samples: {len(self.train_dataset)}")
        print(f"   - Val samples:   {len(self.val_dataset)}")
        print(f"   - Classes:       {self.train_dataset.classes}")

    def get_loaders(self):
        train_loader = TorchDataLoader(
            self.train_dataset, 
            batch_size=self.cfg.batch_size, 
            shuffle=True, 
            num_workers=self.cfg.num_workers,
            pin_memory=True
        )
        val_loader = TorchDataLoader(
            self.val_dataset, 
            batch_size=self.cfg.batch_size, 
            shuffle=False, 
            num_workers=self.cfg.num_workers,
            pin_memory=True
        )
        return train_loader, val_loader

# ==========================================
# 3. Model: EfficientNet-B0
# ==========================================
class EmotionEfficientNet(nn.Module):
    def __init__(self, num_classes=7, pretrained=True):
        super(EmotionEfficientNet, self).__init__()

        print("🏗️  Initializing EfficientNet-B0...")
        weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        self.base_model = models.efficientnet_b0(weights=weights)

        # Modify the classifier head to match our 7 emotion classes
        # The original classifier is: Sequential(Dropout, Linear(1280, 1000))
        in_features = self.base_model.classifier[1].in_features

        self.base_model.classifier[1] = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, num_classes)
        )

    def forward(self, x):
        return self.base_model(x)

# ==========================================
# 4. Trainer Engine
# ==========================================
class Trainer:
    def __init__(self, model, train_loader, val_loader, cfg: Config):
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.cfg = cfg

        self.criterion = nn.CrossEntropyLoss()

        # Optimizer: AdamW is robust for Transfer Learning
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=cfg.learning_rate,
            weight_decay=cfg.weight_decay
        )

        # Scheduler: Drops Learning Rate if validation loss stops improving
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode="min", factor=0.5, patience=3, verbose=True
        )

        self.best_val_acc = 0.0

    def train_epoch(self):
        self.model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        # Tqdm loop for progress bar
        loop = tqdm(self.train_loader, desc="Training", leave=False)

        for images, labels in loop:
            images = images.to(self.cfg.device)
            labels = labels.to(self.cfg.device)

            # Forward
            self.optimizer.zero_grad()
            outputs = self.model(images)
            loss = self.criterion(outputs, labels)

            # Backward
            loss.backward()
            self.optimizer.step()

            # Stats
            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

            # Update progress bar
            loop.set_postfix(loss=loss.item())

        return running_loss / total, correct / total

    def evaluate(self):
        self.model.eval()
        running_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for images, labels in self.val_loader:
                images = images.to(self.cfg.device)
                labels = labels.to(self.cfg.device)

                outputs = self.model(images)
                loss = self.criterion(outputs, labels)

                running_loss += loss.item() * images.size(0)
                _, preds = torch.max(outputs, 1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)

        return running_loss / total, correct / total

    def fit(self):
        print(f"🚀 Starting training on {self.cfg.device}...")

        for epoch in range(1, self.cfg.num_epochs + 1):
            train_loss, train_acc = self.train_epoch()
            val_loss, val_acc = self.evaluate()

            # Step the scheduler based on validation loss
            self.scheduler.step(val_loss)

            print(f"Epoch [{epoch}/{self.cfg.num_epochs}] "
                  f"Train Loss: {train_loss:.4f} | Acc: {train_acc:.2%} | "
                  f"Val Loss: {val_loss:.4f} | Acc: {val_acc:.2%}")

            # Save Model Checkpoint
            if val_acc > self.best_val_acc:
                self.best_val_acc = val_acc
                torch.save(self.model.state_dict(), self.cfg.save_path)
                print(f"🔥 New Best Model Saved! ({val_acc:.2%}) -> {self.cfg.save_path}")

        print("\n✅ Training Complete.")
        print(f"🏆 Best Validation Accuracy: {self.best_val_acc:.2%}")

# ==========================================
# 5. Main Execution Block
# ==========================================
if __name__ == "__main__":
    # 1. Setup Config & Seed
    cfg = Config()
    set_seed()

    # 2. Check Data
    if not os.path.exists(cfg.train_dir):
        print(f"❌ Error: Train directory not found at: {cfg.train_dir}")
        print("Please check 'self.data_root' in Config class.")
    else:
        # 3. Prepare Data
        data_module = EmotionDataModule(cfg)
        data_module.setup()
        train_loader, val_loader = data_module.get_loaders()

        # 4. Prepare Model
        model = EmotionEfficientNet(num_classes=cfg.num_classes).to(cfg.device)

        # 5. Start Training
        trainer = Trainer(model, train_loader, val_loader, cfg)
        trainer.fit()