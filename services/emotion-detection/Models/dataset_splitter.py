# import os
# import shutil
# import random
# from tqdm import tqdm


# class DataSplitter :
#     def __init__(self ,dataset_root , train_ratio =0.8 , seed = 42 ):
#         self.dataset_root = dataset_root
#         self.train_ratio = train_ratio
#         self.seed = seed
        
#         random.seed(self.seed)
        
#         self.train_dir = os.path.join(self.dataset_root , "train")
#         self.val_dir = os.path.join(self.dataset_root , "val") 
        
#     def _list_classes(self):
#         classes = []
        
#         for name in os.listdir(self.dataset_root):
#             path = os.path.join(self.dataset_root , name)
            
#             if os.path.isdir(path) and name not in ["train" , "val"]:
#                 classes.append(name)

#         return classes
    
#     def _create_dir(self,classes):
#         for cls in classes :
#             os.makedirs(os.path.join(self.train_dir , cls) , exist_ok=True)
#             os.makedirs(os.path.join(self.val_dir , cls) , exist_ok=True)
        
#     def split(self):
#         classes = self._list_classes()
#         print("classes" , classes)
        
#         self._create_dir(classes)
        
        
#         for cls in classes :
#             class_path = os.path.join(self.dataset_root , cls)
            
#             images = [
#                 f for f in os.listdir(class_path) if os.path.isfile(os.path.join(class_path , f))
#             ]
            
#             print("images" , images)
            
            
#             random.shuffle(images)
            
            
#             train_count = int(len(images) * self.train_ratio)
#             train_imgs = images[:train_count]
#             val_imgs = images[train_count:]
            
            
#             for img in tqdm(train_imgs,desc=f"train {cls}" ,ncols=60):
#                 src = os.path.join(class_path , img)
#                 dst = os.path.join(self.train_dir , cls , img)
#                 shutil.copy(src , dst)


# if __name__ == "__main__":
#     splitter = DataSplitter("services\emotion-detection\Models\Data\processed_data")
#     splitter.split()


import os
import shutil
import random
from tqdm import tqdm


class DataSplitter:
    def __init__(self, dataset_root, train_ratio=0.8, seed=42):
        self.dataset_root = dataset_root
        self.train_ratio = train_ratio
        self.seed = seed

        random.seed(self.seed)

        self.train_dir = os.path.join(self.dataset_root, "train")
        self.val_dir = os.path.join(self.dataset_root, "val")

    def _list_classes(self):
        classes = []
        for name in os.listdir(self.dataset_root):
            path = os.path.join(self.dataset_root, name)
            # استثني train/val
            if os.path.isdir(path) and name not in ["train", "val"]:
                classes.append(name)
        return classes

    def _create_dir(self, classes):
        for cls in classes:
            os.makedirs(os.path.join(self.train_dir, cls), exist_ok=True)
            os.makedirs(os.path.join(self.val_dir, cls), exist_ok=True)

    def split(self):
        classes = self._list_classes()
        print("classes:", classes)

        self._create_dir(classes)

        for cls in classes:
            class_path = os.path.join(self.dataset_root, cls)

            images = [
                f for f in os.listdir(class_path)
                if os.path.isfile(os.path.join(class_path, f))
            ]

            print(f"\nClass {cls} - {len(images)} images")

            random.shuffle(images)

            train_count = int(len(images) * self.train_ratio)
            train_imgs = images[:train_count]
            val_imgs = images[train_count:]

            # نسخ صور الـ train
            for img in tqdm(train_imgs, desc=f"train {cls}", ncols=60):
                src = os.path.join(class_path, img)
                dst = os.path.join(self.train_dir, cls, img)
                shutil.copy2(src, dst)

            # نسخ صور الـ val
            for img in tqdm(val_imgs, desc=f"val   {cls}", ncols=60):
                src = os.path.join(class_path, img)
                dst = os.path.join(self.val_dir, cls, img)
                shutil.copy2(src, dst)

        print("\n>>> Done splitting dataset!")


if __name__ == "__main__":
    # خليك حريص مع الـ backslashes في ويندوز
    # يا إمّا تستخدم raw string:
    # splitter = DataSplitter(r"services\emotion-detection\Models\Data\processed_data")
    # أو الأفضل:
    base_path = os.path.join(
        "services", "emotion-detection", "Models", "Data", "processed_data"
    )
    splitter = DataSplitter(base_path)
    splitter.split()
