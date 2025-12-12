"""
Offline Data Augmentation Script.

This script artificially increases the size of the training dataset by generating 
modified versions of existing images (rotations, flips, color jitter, etc.).
It saves the original + augmented images into a new directory.

Usage:
    Adjust INPUT_DIR and OUTPUT_DIR to match your folder structure.
    Run this script ONCE before starting the training process.
"""

import os
from PIL import Image
from torchvision import transforms
from tqdm import tqdm

# ==========================================
# 1. Configuration
# ==========================================
# Path to your original dataset (train folder containing class subfolders)
INPUT_DIR = r"processed_data/train" 

# Path where to save the augmented dataset
# (Will contain original images + new augmented ones)
OUTPUT_DIR = r"processed_data/augmented_train" 

# Augmentation Factor: How many NEW images to create per original image?
# Total images = Original + (Original * AUGMENTATION_FACTOR)
# Example: 100 images with Factor 3 => 100 + 300 = 400 total images.
AUGMENTATION_FACTOR = 3 

# ==========================================
# 2. Define Augmentation Pipeline
# ==========================================
# These transforms will be applied stochastically (randomly)
augment_pipeline = transforms.Compose([
    # Randomly rotate the image by up to 30 degrees
    transforms.RandomRotation(degrees=30),
    
    # Randomly flip the image horizontally (p=0.5)
    transforms.RandomHorizontalFlip(p=0.5),
    
    # Change brightness, contrast, saturation, and hue slightly to simulate lighting conditions
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
    
    # Randomly convert to grayscale (optional, robust against color dependency)
    transforms.RandomGrayscale(p=0.1),
    
    # Random Perspective (changes the angle of view, good for faces)
    transforms.RandomPerspective(distortion_scale=0.2, p=0.5),
])

def augment_and_save():
    """
    Iterates through class folders, augments images, and saves them to the output directory.
    """
    # Verify input directory
    if not os.path.exists(INPUT_DIR):
        print(f"❌ Error: Input directory '{INPUT_DIR}' not found.")
        return

    print(f"🚀 Starting augmentation...")
    print(f"📂 Input:  {INPUT_DIR}")
    print(f"📂 Output: {OUTPUT_DIR}")
    print(f"🔢 Factor: {AUGMENTATION_FACTOR} new images per original image")

    # Get list of classes (subfolders)
    classes = [d for d in os.listdir(INPUT_DIR) if os.path.isdir(os.path.join(INPUT_DIR, d))]
    
    for class_name in classes:
        class_input_path = os.path.join(INPUT_DIR, class_name)
        class_output_path = os.path.join(OUTPUT_DIR, class_name)
        
        # Create output directory for this class
        os.makedirs(class_output_path, exist_ok=True)
        
        # List all valid images in the class folder
        images = [f for f in os.listdir(class_input_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        print(f"\nProcessing class: '{class_name}' ({len(images)} original images)")
        
        for img_name in tqdm(images, desc=f"Augmenting {class_name}"):
            try:
                # 1. Load original image
                img_path = os.path.join(class_input_path, img_name)
                image = Image.open(img_path).convert("RGB")
                
                # 2. Save the ORIGINAL image first (to keep it in the new dataset)
                original_save_path = os.path.join(class_output_path, f"orig_{img_name}")
                image.save(original_save_path)
                
                # 3. Generate AUGMENTED versions
                for i in range(AUGMENTATION_FACTOR):
                    # Apply transforms
                    aug_img = augment_pipeline(image)
                    
                    # Construct new filename (e.g., aug_0_image.jpg)
                    filename_no_ext = os.path.splitext(img_name)[0]
                    ext = os.path.splitext(img_name)[1]
                    new_filename = f"aug_{i}_{filename_no_ext}{ext}"
                    
                    # Save augmented image
                    aug_save_path = os.path.join(class_output_path, new_filename)
                    aug_img.save(aug_save_path)
                    
            except Exception as e:
                print(f"⚠️ Error processing {img_name}: {e}")

    print("\n✅ Data Augmentation Completed Successfully!")
    print(f"Check your new dataset at: {OUTPUT_DIR}")

if __name__ == "__main__":
    augment_and_save()