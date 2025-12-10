import os 
import shutil

import torch
from torch import nn
import numpy as np 
import torch.optim as optim

from config import Config



class ConvBlock(nn.Module):
    
    def __init__(self , in_channels :int, out_channels :int):
        super().__init__()
        
        self.conv_block = nn.Sequential(
            nn.Conv2d(in_channels , out_channels , kernel_size = 3 , padding = 1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),

            nn.MaxPool2d(2),
        )
        
        
    def forward(self , x):
        return self.conv_block(x)
    
    


class EmotionCNN (nn.Module):
    def __init__(self , num_classes :int =7):
        super().__init__()
        
        self.features = nn.Sequential(
            ConvBlock(1 , 32),
            ConvBlock(32 , 64),
            ConvBlock(64 , 128),
            ConvBlock(128 , 256),
        )
        
        self.global_pool = nn.AdaptiveAvgPool2d((1,1))
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.5),
            nn.Linear(256 , num_classes)
        )
        
    def forward(self , x):
        x = self.features(x)
        x = self.global_pool(x)
        x = self.classifier(x)
        return x




        
        
        