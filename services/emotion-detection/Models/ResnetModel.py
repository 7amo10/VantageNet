import os
import shutil
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
        self.data_root = "/content/processed_data"  # تأكد إن المسار صح
        self.train_dir = os.path.join(self.data_root, "train")
        self.val_dir   = os.path.join(self.data_root, "val")
        
        self.num_classes   = 7
        self.batch_size    = 32    # قللناه شوية عشان الصور كبرت (224)
        self.num_epochs    = 15    # ResNet بيتعلم بسرعة
        self.learning_rate = 1e-4  # Learning rate أهدى شوية للـ Fine-tuning
        self.weight_decay  = 1e-4
        self.num_workers   = 2
        self.device        = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.save_path     = "/content/resnet18_emotion.pt"
        self.print_every   = 1

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

# ==========================================
# 2. Data Loader (ResNet Specific)
# ==========================================
class EmotionDataModule:
    def __init__(self, cfg: Config):
        self.cfg = cfg
    
    def _build_transforms(self):
        # ResNet محتاج صور 224x224 و 3 قنوات ألوان
        train_tf = transforms.Compose([
            transforms.Grayscale(num_output_channels=3), # تكرار القناة الرمادي 3 مرات
            transforms.Resize((224, 224)),               # تكبير الصورة
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.2, contrast=0.2), # إضافة شوية "نويز" للإضاءة
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]), # تطبيع ImageNet
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
# 3. Model: Pre-trained ResNet18
# ==========================================
def get_resnet_model(num_classes=7, device='cpu'):
    print("Loading Pre-trained ResNet18...")
    # تحميل الموديل بالأوزان الجاهزة
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    
    # تجميد الطبقات الأولى (اختياري، بس خلينا ندرب كله عشان الدقة تكون أحسن للوشوش)
    # for param in model.parameters():
    #     param.requires_grad = False
    
    # تغيير آخر طبقة عشان تطلع 7 مشاعر بس
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, num_classes)
    
    return model.to(device)

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
        # AdamW usually works better for transfer learning
        self.optimizer = optim.AdamW(self.model.parameters(), lr=cfg.learning_rate, weight_decay=cfg.weight_decay)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, mode="min", factor=0.5, patience=2)
        self.best_val_acc = 0.0

    def train_epoch(self):
        self.model.train()
        running_loss, correct, total = 0.0, 0, 0
        
        for images, labels in tqdm(self.train_loader, desc="Training", leave=False):
            images, labels = images.to(self.cfg.device), labels.to(self.cfg.device)
            
            self.optimizer.zero_grad()
            outputs = self.model(images)
            loss = self.criterion(outputs, labels)
            loss.backward()
            self.optimizer.step()
            
            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
            
        return running_loss / total, correct / total

    def evaluate(self):
        self.model.eval()
        running_loss, correct, total = 0.0, 0, 0
        
        with torch.no_grad():
            for images, labels in self.val_loader:
                images, labels = images.to(self.cfg.device), labels.to(self.cfg.device)
                outputs = self.model(images)
                loss = self.criterion(outputs, labels)
                
                running_loss += loss.item() * images.size(0)
                _, preds = torch.max(outputs, 1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)
                
        return running_loss / total, correct / total

    def fit(self):
        print(f"Starting training on {self.cfg.device}...")
        for epoch in range(1, self.cfg.num_epochs + 1):
            train_loss, train_acc = self.train_epoch()
            val_loss, val_acc = self.evaluate()
            
            self.scheduler.step(val_loss)
            
            print(f"Epoch [{epoch}/{self.cfg.num_epochs}] "
                  f"Train Loss: {train_loss:.4f} | Acc: {train_acc:.1%} | "
                  f"Val Loss: {val_loss:.4f} | Acc: {val_acc:.1%}")
            
            if val_acc > self.best_val_acc:
                self.best_val_acc = val_acc
                torch.save(self.model.state_dict(), self.cfg.save_path)
                print(f">>> New Best Model Saved: {val_acc:.1%}")

# ==========================================
# 5. Main Execution
# ==========================================
if __name__ == "__main__":
    cfg = Config()
    set_seed()
    
    # Load Data
    data_module = EmotionDataModule(cfg)
    data_module.setup()
    train_loader, val_loader = data_module.get_loaders()
    
    # Load Model
    model = get_resnet_model(num_classes=cfg.num_classes, device=cfg.device)
    
    # Train
    trainer = Trainer(model, train_loader, val_loader, cfg)
    trainer.fit()