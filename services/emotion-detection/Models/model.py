"""
Custom CNN Model Definition for Emotion Detection.

This is a lightweight alternative to EfficientNet. It is a standard Convolutional 
Neural Network built from scratch, useful for faster training on simpler datasets 
or lower-end hardware.

Architecture:
    Input (3, H, W) -> [ConvBlock x 4] -> AdaptiveAvgPool -> Classifier -> Output (7)
"""

import torch
import torch.nn as nn

class ConvBlock(nn.Module):
    """
    A reusable block consisting of:
    2x Convolution -> BatchNorm -> ReLU -> MaxPool
    """
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        
        self.conv_block = nn.Sequential(
            # First Conv Layer
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            
            # Second Conv Layer
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),

            # Downsampling
            nn.MaxPool2d(kernel_size=2),
        )
        
    def forward(self, x):
        return self.conv_block(x)


class EmotionCNN(nn.Module):
    def __init__(self, num_classes: int = 7):
        super().__init__()
        
        self.features = nn.Sequential(
            # Input Channels: 3 (RGB) to match the DataLoader
            ConvBlock(in_channels=3, out_channels=32),
            ConvBlock(in_channels=32, out_channels=64),
            ConvBlock(in_channels=64, out_channels=128),
            ConvBlock(in_channels=128, out_channels=256),
        )
        
        # Adaptive Pooling ensures output is always (256, 1, 1) regardless of input size
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes)
        )
        
    def forward(self, x):
        x = self.features(x)
        x = self.global_pool(x)
        x = self.classifier(x)
        return x

# ==========================================
# Sanity Check (Test Block)
# ==========================================
if __name__ == "__main__":
    print("Testing Custom EmotionCNN model...")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = EmotionCNN(num_classes=7).to(device)
    
    # Create dummy input: Batch=2, Channels=3, Height=48, Width=48 (or 224)
    # Note: This model works with 48x48 OR 224x224 thanks to AdaptiveAvgPool
    dummy_input = torch.randn(2, 3, 48, 48).to(device)
    
    try:
        output = model(dummy_input)
        print(f"✅ Forward pass successful!")
        print(f"Input shape:  {dummy_input.shape}")
        print(f"Output shape: {output.shape}") # Should be [2, 7]
    except Exception as e:
        print(f"❌ Error during forward pass: {e}")