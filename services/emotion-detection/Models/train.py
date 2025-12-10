import torch
import torch.nn as nn
import torch.optim as optim
from config import Config
from model import EmotionCNN , ConvBlock
from dataLoader import DataLoader
class Trainer:
    def __init__(self, model, train_loader, val_loader, cfg: Config):
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.cfg = cfg

        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=self.cfg.learning_rate,
            weight_decay=self.cfg.weight_decay,
        )

        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode="min", factor=0.5, patience=3, verbose=True
        )

        self.best_val_acc = 0.0

    def train_one_epoch(self, epoch: int):
        self.model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in self.train_loader:
            images = images.to(self.cfg.device)
            labels = labels.to(self.cfg.device)

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
        print("Training on:", self.cfg.device)

        for epoch in range(1, self.cfg.num_epochs + 1):
            train_loss, train_acc = self.train_one_epoch(epoch)
            val_loss, val_acc = self.evaluate()

            self.scheduler.step(val_loss)

            if epoch % self.cfg.print_every == 0:
                print(
                    f"Epoch [{epoch}/{self.cfg.num_epochs}] "
                    f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f} "
                    f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f}"
                )

            if val_acc > self.best_val_acc:
                self.best_val_acc = val_acc
                torch.save(self.model.state_dict(), self.cfg.save_path)
                print(
                    f">>> New best model saved! Val Acc = {self.best_val_acc:.4f} "
                    f"-> {self.cfg.save_path}"
                )

        print("Training finished. Best Val Acc:", self.best_val_acc)




# =========================
# 5. Main
# =========================
def main():
    cfg = Config()

    print("train dir:", cfg.train_dir)
    print("val dir  :", cfg.val_dir)

    import os
    for root in [cfg.train_dir, cfg.val_dir]:
        print(f"\nListing {root}:")
        for cls in os.listdir(root):
            cls_path = os.path.join(root, cls)
            if os.path.isdir(cls_path):
                n_files = len([
                    f for f in os.listdir(cls_path)
                    if os.path.isfile(os.path.join(cls_path, f))
                ])
                print(f"  {cls}: {n_files} files")


if __name__ == "__main__":
    main()