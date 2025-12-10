import os
import shutil
import random
from tqdm import tqdm
import torch

# class Config :
#     def __init__(self):
#         self.data_root = "services\emotion-detection\Models\Data\processed_data"
        
#         self.train_dir = os.path.join(self.data_root , "train")
#         self.val_dir = os.path.join(self.data_root , "val")
        
#         self.num_classes = 7    
#         self.batch_size = 64 
#         self.num_epochs = 30
#         self.learning_rate = 1e-3
#         self.weight_decay = 1e-4
#         self.num_workers = 2
#         self.pin_memory = True 
#         self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#         self.seed = 42 
        
#         self.save_path = "emotion_model_best.pt"
#         self.print_every = 1
        
        
#         self.emotion_labels = {
#             0: "Angry",
#             1: "Disgust",
#             2: "Fear",
#             3: "Happy",
#             4: "Sad",
#             5: "Surprise",
#             6: "Neutral",
#         }
        
#     def set_seed(self ,seed:int = 42):
#         random.seed(seed)
#         torch.manual_seed(seed)
#         torch.cuda.manual_seed(seed)
        

import os
import random
import torch

class Config:
    def __init__(self):
        # ======= تحديد Base Dir للمشروع =======
        # مكان ملف config.py -> Models/
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        # processed_data جوه Models/Data/processed_data
        self.data_root = os.path.join(BASE_DIR, "Data", "processed_data")

        self.train_dir = os.path.join(self.data_root, "train")
        self.val_dir   = os.path.join(self.data_root, "val")

        self.num_classes   = 7
        self.batch_size    = 64
        self.num_epochs    = 30
        self.learning_rate = 1e-3
        self.weight_decay  = 1e-4
        self.num_workers   = 2
        self.pin_memory    = True
        self.device        = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.seed          = 42

        self.save_path     = os.path.join(BASE_DIR, "emotion_model_best.pt")
        self.print_every   = 1

        self.emotion_labels = {
            0: "Angry",
            1: "Disgust",
            2: "Fear",
            3: "Happy",
            4: "Sad",
            5: "Surprise",
            6: "Neutral",
        }

    def set_seed(self, seed: int = 42):
        random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed(seed)
