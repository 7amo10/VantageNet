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
        # Change this path to your data location
        self.data_root = "/content/drive/MyDrive/cv project/processed_data - Copy"
        self.train_dir = os.path.join(self.data_root, "train")
        self.val_dir   = os.path.join(self.data_root, "val")

        self.num_classes   = 7
        self.batch_size    = 32    # 32 is safe for 224x224 images on Colab
        self.num_epochs    = 20    # EfficientNet needs time to fine-tune
        self.learning_rate = 3e-4  # Good starting point for pre-trained models
        self.weight_decay  = 1e-4
        self.num_workers   = 2
        self.device        = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.save_path     = "/content/efficientnet_emotion.pt"

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

# ==========================================
# 2. Data Module (Updated for EfficientNet)
# ==========================================
class EmotionDataModule:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def _build_transforms(self):
        # EfficientNet requires 224x224 and 3 Channels (RGB)
        train_tf = transforms.Compose([
            transforms.Grayscale(num_output_channels=3),
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
        self.train_dataset = datasets.ImageFolder(root=self.cfg.train_dir, transform=train_tf)
        self.val_dataset = datasets.ImageFolder(root=self.cfg.val_dir, transform=val_tf)

        print(f"Train samples: {len(self.train_dataset)}")
        print(f"Val samples:   {len(self.val_dataset)}")

    def get_loaders(self):
        train_loader = TorchDataLoader(self.train_dataset, batch_size=self.cfg.batch_size, shuffle=True, num_workers=self.cfg.num_workers)
        val_loader = TorchDataLoader(self.val_dataset, batch_size=self.cfg.batch_size, shuffle=False, num_workers=self.cfg.num_workers)
        return train_loader, val_loader

# ==========================================
# 3. Model: EfficientNet-B0
# ==========================================
class EmotionEfficientNet(nn.Module):
    def __init__(self, num_classes=7, pretrained=True):
        super(EmotionEfficientNet, self).__init__()

        print("Loading EfficientNet-B0...")
        weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        self.base_model = models.efficientnet_b0(weights=weights)

        # Modify the classifier head
        # The classifier in EfficientNet is a Sequential block, index 1 is the Linear layer
        in_features = self.base_model.classifier[1].in_features

        self.base_model.classifier[1] = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, num_classes)
        )

    def forward(self, x):
        return self.base_model(x)

# ==========================================
# 4. Trainer
# ==========================================
class Trainer:
    def __init__(self, model, train_loader, val_loader, cfg: Config):
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.cfg = cfg

        self.criterion = nn.CrossEntropyLoss()

        # AdamW is generally better for Transfer Learning than standard Adam
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=cfg.learning_rate,
            weight_decay=cfg.weight_decay
        )

        # Scheduler to reduce LR when validation loss plateaus
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode="min", factor=0.5, patience=2
        )

        self.best_val_acc = 0.0

    def train_epoch(self):
        self.model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        loop = tqdm(self.train_loader, desc="Training", leave=False)

        for images, labels in loop:
            images = images.to(self.cfg.device)
            labels = labels.to(self.cfg.device)

            # Forward pass
            self.optimizer.zero_grad()
            outputs = self.model(images)
            loss = self.criterion(outputs, labels)

            # Backward pass
            loss.backward()
            self.optimizer.step()

            # Metrics
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

            # Step the scheduler
            self.scheduler.step(val_loss)

            print(f"Epoch [{epoch}/{self.cfg.num_epochs}] "
                  f"Train Loss: {train_loss:.4f} | Acc: {train_acc:.2%} | "
                  f"Val Loss: {val_loss:.4f} | Acc: {val_acc:.2%}")

            # Save best model
            if val_acc > self.best_val_acc:
                self.best_val_acc = val_acc
                torch.save(self.model.state_dict(), self.cfg.save_path)
                print(f"🔥 New Best Model Saved! ({val_acc:.2%}) -> {self.cfg.save_path}")

        print("\n✅ Training Complete.")
        print(f"🏆 Best Validation Accuracy: {self.best_val_acc:.2%}")

# ==========================================
# 5. Main Execution
# ==========================================
if __name__ == "__main__":
    # 1. Setup Config & Seed
    cfg = Config()
    set_seed()

    # 2. Setup Data
    if not os.path.exists(cfg.train_dir):
        print("❌ Error: Data not found. Please upload and unzip data first.")
    else:
        data_module = EmotionDataModule(cfg)
        data_module.setup()
        train_loader, val_loader = data_module.get_loaders()

        # 3. Setup Model
        model = EmotionEfficientNet(num_classes=cfg.num_classes).to(cfg.device)

        # 4. Train
        trainer = Trainer(model, train_loader, val_loader, cfg)
        trainer.fit()