"""
EfficientNet Model Definition for Emotion Detection.

This module defines the EmotionEfficientNet architecture based on EfficientNet-B0.
It replaces the default ImageNet classifier with a custom head for 7 emotion classes.

Usage:
    from services.emotion_detection.Models.efficientNetModel import EmotionEfficientNet
    model = EmotionEfficientNet(num_classes=7, pretrained=True)
"""

import torch
import torch.nn as nn
from torchvision import models

class EmotionEfficientNet(nn.Module):
    def __init__(self, num_classes=7, pretrained=True):
        """
        Args:
            num_classes (int): Number of emotion categories (default: 7).
            pretrained (bool): If True, loads ImageNet weights.
        """
        super(EmotionEfficientNet, self).__init__()

        # 1. Load the Base Model (EfficientNet-B0)
        # B0 is chosen for its balance between speed and accuracy.
        if pretrained:
            weights = models.EfficientNet_B0_Weights.DEFAULT
        else:
            weights = None
            
        self.base_model = models.efficientnet_b0(weights=weights)

        # 2. (Optional) Freeze Feature Extractor
        # Uncomment the loop below if you want to freeze the early layers
        # for param in self.base_model.features.parameters():
        #     param.requires_grad = False

        # 3. Replace the Classifier Head
        # The original classifier is: Sequential(Dropout, Linear(1280, 1000))
        # We need to change the last Linear layer to output 'num_classes'
        
        # Get the input features of the final linear layer (usually 1280 for B0)
        in_features = self.base_model.classifier[1].in_features

        self.base_model.classifier[1] = nn.Sequential(
            nn.Dropout(p=0.3),                 # Dropout to prevent overfitting
            nn.Linear(in_features, num_classes)
        )

    def forward(self, x):
        """
        Forward pass of the network.
        
        Args:
            x (Tensor): Input batch of images [Batch_Size, 3, 224, 224]
            
        Returns:
            Tensor: Raw logits [Batch_Size, num_classes]
        """
        return self.base_model(x)

# ==========================================
# Sanity Check (Test Block)
# ==========================================
if __name__ == "__main__":
    # This block only runs if you execute this file directly
    print("Testing EmotionEfficientNet model...")
    
    # 1. Create Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = EmotionEfficientNet(num_classes=7).to(device)
    
    # 2. Create Dummy Input (Batch Size=2, Channels=3, Height=224, Width=224)
    dummy_input = torch.randn(2, 3, 224, 224).to(device)
    
    # 3. Forward Pass
    try:
        output = model(dummy_input)
        print(f"✅ Forward pass successful!")
        print(f"Input shape:  {dummy_input.shape}")
        print(f"Output shape: {output.shape}") # Should be [2, 7]
    except Exception as e:
        print(f"❌ Error during forward pass: {e}")