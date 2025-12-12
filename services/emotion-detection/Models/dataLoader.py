"""
Data Loading Module for Emotion Detection.

This module handles the loading and preprocessing of image data.
It prepares PyTorch DataLoaders for training and validation sets.
"""

from config import Config
import torch
from torch.utils.data import DataLoader as TorchDataLoader
from torchvision import transforms, datasets

class EmotionDataLoader:
    """
    Wrapper class to create PyTorch DataLoaders with specific transformations
    compatible with models like EfficientNet.
    """
    def __init__(self, config: Config):
        """
        Args:
            config (Config): Configuration object containing paths and hyperparameters.
        """
        self.config = config
    
    def get_transforms(self):
        """
        Defines image transformations (Augmentation & Normalization).
        
        NOTE:
        - EfficientNet requires 3 input channels (RGB).
        - Standard input size is 224x224.
        """
        train_transform = transforms.Compose([
            # Convert to Grayscale but keep 3 channels for Model compatibility
            transforms.Grayscale(num_output_channels=3), 
            transforms.Resize((224, 224)),
            
            # Augmentations to prevent overfitting
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            
            # Convert to Tensor and Normalize
            transforms.ToTensor(),
            # Normalization (values typically used for pre-trained models)
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        val_transform = transforms.Compose([
            transforms.Grayscale(num_output_channels=3),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        return train_transform, val_transform
    
    def create_loaders(self):
        """
        Creates and returns the training and validation DataLoaders.
        
        Returns:
            train_loader, val_loader
        """
        train_tf, val_tf = self.get_transforms()
        
        # Load datasets from folders
        train_dataset = datasets.ImageFolder(
            root=self.config.train_dir,
            transform=train_tf
        )
        
        val_dataset = datasets.ImageFolder(
            root=self.config.val_dir,
            transform=val_tf
        )
        
        # Logging dataset details
        print(f"Train dataset size : {len(train_dataset)}")
        print(f"Train classes      : {train_dataset.classes}")
        print(f"Val dataset size   : {len(val_dataset)}")
        print(f"Val classes        : {val_dataset.classes}")
        
        # Create DataLoaders
        train_loader = TorchDataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=self.config.num_workers,
            pin_memory=self.config.pin_memory,
        )

        val_loader = TorchDataLoader(
            val_dataset,
            batch_size=self.config.batch_size,
            shuffle=False,
            num_workers=self.config.num_workers,
            pin_memory=self.config.pin_memory,
        )

        return train_loader, val_loader