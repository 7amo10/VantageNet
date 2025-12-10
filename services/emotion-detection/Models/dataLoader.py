from config import Config
import torch
from torch.utils.data import DataLoader as TorchDataLoader
from torchvision import transforms, datasets

class DataLoader :
    def __init__(self, config: Config, train=True, shuffle=True):
        self.config = config
        self.train = train
        self.shuffle = shuffle
        self.data_root = config.data_root
        self.batch_size = config.batch_size
    
    def get_transforms(self):
        train_transform = transforms.Compose([
            transforms.Grayscale(num_output_channels=1),
            transforms.Resize((48, 48)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,)),
        ])
        
        val_transform = transforms.Compose([
            transforms.Grayscale(num_output_channels=1),
            transforms.Resize((48, 48)),
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,)),
        ])
        
        return train_transform , val_transform
    
    def create_loaders(self , cfg:Config):
        train_tf , val_tf = self.get_transforms()
        
        train_dataset = datasets.ImageFolder(
            root = cfg.train_dir,
            transform=train_tf
        )
        
        val_dataset = datasets.ImageFolder(
            root= cfg.val_dir,
            transform=val_tf
        )
        
        print(f"train dataset size : {len(train_dataset)}")
        print("train classes" , train_dataset.classes)
        print(f"val dataset size : {len(val_dataset)}")
        print("val classes" , val_dataset.classes)
        
        train_loader = TorchDataLoader(
                train_dataset,
                batch_size=cfg.batch_size,
                shuffle=True,
                num_workers=cfg.num_workers,
                pin_memory=cfg.pin_memory,
                    )

        val_loader = TorchDataLoader(
            val_dataset,
            batch_size=cfg.batch_size,
            shuffle=False,
            num_workers=cfg.num_workers,
            pin_memory=cfg.pin_memory,
                )

        print("Train samples:", len(train_dataset))
        print("Val samples:", len(val_dataset))

        return train_loader, val_loader

