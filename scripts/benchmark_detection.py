#!/usr/bin/env python3
"""
Benchmark script for emotion detection service performance profiling.
Tests both baseline and optimized implementations.
"""

import sys
import time
import psutil
import numpy as np
import cv2
import torch
from pathlib import Path
from typing import List, Dict
import json
import os

# Change to emotion-detection service directory for correct model paths
service_dir = Path(__file__).parent.parent / "services" / "emotion-detection"
os.chdir(service_dir)
sys.path.insert(0, str(service_dir))

from app.model_loader import model_loader
from app.config import settings
from torchvision import transforms
from PIL import Image

# ANSI colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]


class BenchmarkRunner:
    """Benchmark runner for emotion detection pipeline."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = 0
        self.peak_memory = 0
        
        # Transform for FER
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    
    def get_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / (1024 * 1024)
    
    def generate_test_frame(self, size=(640, 480)) -> np.ndarray:
        """Generate a test frame with random noise."""
        frame = np.random.randint(0, 255, (size[1], size[0], 3), dtype=np.uint8)
        # Add some structure (simulated face)
        cv2.rectangle(frame, (200, 100), (400, 300), (255, 200, 150), -1)
        return frame
    
    def compress_frame_jpeg(self, frame: np.ndarray) -> bytes:
        """Compress frame to JPEG bytes."""
        _, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return encoded.tobytes()
    
    def benchmark_decompression(self, num_frames: int = 100) -> Dict:
        """Benchmark JPEG decompression."""
        print(f"\n{BLUE}Testing JPEG decompression ({num_frames} frames)...{RESET}")
        
        # Generate test data
        test_frame = self.generate_test_frame()
        jpeg_data = self.compress_frame_jpeg(test_frame)
        
        times = []
        for i in range(num_frames):
            start = time.time()
            np_arr = np.frombuffer(jpeg_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
        
        return {
            "avg_ms": np.mean(times),
            "p50_ms": np.percentile(times, 50),
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99)
        }
    
    def benchmark_yolo(self, num_frames: int = 100) -> Dict:
        """Benchmark YOLO face detection."""
        print(f"\n{BLUE}Testing YOLO face detection ({num_frames} frames)...{RESET}")
        
        if not model_loader.yolo_model:
            return {"error": "YOLO model not loaded"}
        
        # Generate test frames
        test_frame = self.generate_test_frame()
        
        times = []
        faces_detected = []
        
        for i in range(num_frames):
            start = time.time()
            results = model_loader.yolo_model(test_frame, conf=0.5, verbose=False)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            
            if results and len(results) > 0 and results[0].boxes is not None:
                faces_detected.append(len(results[0].boxes))
            else:
                faces_detected.append(0)
        
        return {
            "avg_ms": np.mean(times),
            "p50_ms": np.percentile(times, 50),
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99),
            "avg_faces": np.mean(faces_detected)
        }
    
    def benchmark_fer(self, num_faces: int = 100) -> Dict:
        """Benchmark FER emotion classification."""
        print(f"\n{BLUE}Testing FER emotion classification ({num_faces} faces)...{RESET}")
        
        if not model_loader.fer_model:
            return {"error": "FER model not loaded"}
        
        # Generate test face crops
        test_face = self.generate_test_frame(size=(224, 224))
        test_face_rgb = cv2.cvtColor(test_face, cv2.COLOR_BGR2RGB)
        
        times = []
        device = model_loader.device
        
        for i in range(num_faces):
            start = time.time()
            
            # Convert to PIL and transform
            pil_img = Image.fromarray(test_face_rgb)
            input_tensor = self.transform(pil_img).unsqueeze(0).to(device)
            
            # Inference
            with torch.no_grad():
                outputs = model_loader.fer_model(input_tensor)
                probs = torch.nn.functional.softmax(outputs, dim=1)
                top_prob, top_idx = torch.max(probs, 1)
            
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
        
        return {
            "avg_ms": np.mean(times),
            "p50_ms": np.percentile(times, 50),
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99)
        }
    
    def benchmark_full_pipeline(self, num_frames: int = 100) -> Dict:
        """Benchmark full end-to-end pipeline."""
        print(f"\n{BLUE}Testing full pipeline ({num_frames} frames)...{RESET}")
        
        if not model_loader.yolo_model or not model_loader.fer_model:
            return {"error": "Models not loaded"}
        
        # Generate test data
        test_frame = self.generate_test_frame()
        jpeg_data = self.compress_frame_jpeg(test_frame)
        device = model_loader.device
        
        times = {
            "decompress": [],
            "yolo": [],
            "fer": [],
            "total": []
        }
        
        emotions_detected = []
        
        for i in range(num_frames):
            total_start = time.time()
            
            # 1. Decompress
            decomp_start = time.time()
            np_arr = np.frombuffer(jpeg_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            times["decompress"].append((time.time() - decomp_start) * 1000)
            
            # 2. YOLO detection
            yolo_start = time.time()
            yolo_results = model_loader.yolo_model(frame, conf=0.5, verbose=False)
            times["yolo"].append((time.time() - yolo_start) * 1000)
            
            # 3. FER for each face
            fer_start = time.time()
            emotion_count = 0
            
            if yolo_results and len(yolo_results) > 0 and yolo_results[0].boxes is not None:
                for box in yolo_results[0].boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    h, w = frame.shape[:2]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    
                    face_crop = frame[y1:y2, x1:x2]
                    if face_crop.size > 0:
                        face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(face_rgb)
                        input_tensor = self.transform(pil_img).unsqueeze(0).to(device)
                        
                        with torch.no_grad():
                            outputs = model_loader.fer_model(input_tensor)
                            probs = torch.nn.functional.softmax(outputs, dim=1)
                            top_prob, top_idx = torch.max(probs, 1)
                        
                        emotion_count += 1
            
            times["fer"].append((time.time() - fer_start) * 1000)
            emotions_detected.append(emotion_count)
            
            times["total"].append((time.time() - total_start) * 1000)
        
        return {
            "total": {
                "avg_ms": np.mean(times["total"]),
                "p50_ms": np.percentile(times["total"], 50),
                "p95_ms": np.percentile(times["total"], 95),
                "p99_ms": np.percentile(times["total"], 99),
                "avg_fps": 1000 / np.mean(times["total"])
            },
            "breakdown": {
                "decompress_avg_ms": np.mean(times["decompress"]),
                "yolo_avg_ms": np.mean(times["yolo"]),
                "fer_avg_ms": np.mean(times["fer"])
            },
            "avg_emotions": np.mean(emotions_detected)
        }
    
    def run_full_benchmark(self):
        """Run complete benchmark suite."""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}{'Emotion Detection Performance Benchmark':^70}{RESET}")
        print(f"{BLUE}{'='*70}{RESET}")
        
        # Get system info
        print(f"\n{YELLOW}System Information:{RESET}")
        print(f"  CPU: {psutil.cpu_count(logical=False)} cores ({psutil.cpu_count()} threads)")
        print(f"  CPU Freq: {psutil.cpu_freq().current:.0f} MHz")
        print(f"  RAM: {psutil.virtual_memory().total / (1024**3):.1f} GB")
        print(f"  Python: {sys.version.split()[0]}")
        print(f"  PyTorch: {torch.__version__}")
        print(f"  CUDA Available: {torch.cuda.is_available()}")
        print(f"  Device: {model_loader.device}")
        
        # Initial memory
        self.initial_memory = self.get_memory_mb()
        print(f"  Initial Memory: {self.initial_memory:.1f} MB")
        
        # Load models
        print(f"\n{YELLOW}Loading models...{RESET}")
        import asyncio
        loop = asyncio.get_event_loop()
        loaded = loop.run_until_complete(model_loader.load_models())
        
        if not loaded:
            print(f"{RED}Failed to load models{RESET}")
            return 1
        
        self.peak_memory = self.get_memory_mb()
        print(f"{GREEN}✓ Models loaded{RESET}")
        print(f"  Memory after loading: {self.peak_memory:.1f} MB (+{self.peak_memory - self.initial_memory:.1f} MB)")
        
        # Run benchmarks
        results = {}
        
        # 1. Decompression
        results["decompression"] = self.benchmark_decompression()
        print(f"  Avg: {results['decompression']['avg_ms']:.2f}ms | "
              f"P95: {results['decompression']['p95_ms']:.2f}ms")
        
        # 2. YOLO
        results["yolo"] = self.benchmark_yolo()
        if "error" not in results["yolo"]:
            print(f"  Avg: {results['yolo']['avg_ms']:.2f}ms | "
                  f"P95: {results['yolo']['p95_ms']:.2f}ms | "
                  f"Faces: {results['yolo']['avg_faces']:.1f}")
        
        # 3. FER
        results["fer"] = self.benchmark_fer()
        if "error" not in results["fer"]:
            print(f"  Avg: {results['fer']['avg_ms']:.2f}ms | "
                  f"P95: {results['fer']['p95_ms']:.2f}ms")
        
        # 4. Full Pipeline
        results["pipeline"] = self.benchmark_full_pipeline()
        if "error" not in results["pipeline"]:
            total = results["pipeline"]["total"]
            breakdown = results["pipeline"]["breakdown"]
            
            print(f"\n{BLUE}{'='*70}{RESET}")
            print(f"{BLUE}Pipeline Performance Summary{RESET}")
            print(f"{BLUE}{'='*70}{RESET}\n")
            
            print(f"Total Processing Time:")
            print(f"  Average: {total['avg_ms']:.2f}ms ({total['avg_fps']:.1f} FPS)")
            print(f"  P50: {total['p50_ms']:.2f}ms")
            print(f"  P95: {total['p95_ms']:.2f}ms")
            print(f"  P99: {total['p99_ms']:.2f}ms")
            
            print(f"\nBreakdown:")
            print(f"  Decompression: {breakdown['decompress_avg_ms']:.2f}ms ({breakdown['decompress_avg_ms']/total['avg_ms']*100:.1f}%)")
            print(f"  YOLO: {breakdown['yolo_avg_ms']:.2f}ms ({breakdown['yolo_avg_ms']/total['avg_ms']*100:.1f}%)")
            print(f"  FER: {breakdown['fer_avg_ms']:.2f}ms ({breakdown['fer_avg_ms']/total['avg_ms']*100:.1f}%)")
            
            print(f"\nMemory:")
            current_mem = self.get_memory_mb()
            print(f"  Current: {current_mem:.1f} MB")
            print(f"  Peak: {self.peak_memory:.1f} MB")
            
            # Performance assessment
            print(f"\n{BLUE}{'='*70}{RESET}")
            print(f"{BLUE}Performance Assessment{RESET}")
            print(f"{BLUE}{'='*70}{RESET}\n")
            
            target_fps = 30
            current_fps = total['avg_fps']
            
            if current_fps >= target_fps:
                print(f"{GREEN}✓ PASSED: {current_fps:.1f} FPS >= {target_fps} FPS target{RESET}")
            else:
                print(f"{YELLOW}⚠ BELOW TARGET: {current_fps:.1f} FPS < {target_fps} FPS target{RESET}")
                print(f"{YELLOW}  Improvement needed: {target_fps/current_fps:.1f}x faster{RESET}")
            
            if current_mem < 2000:
                print(f"{GREEN}✓ Memory OK: {current_mem:.1f} MB < 2GB{RESET}")
            else:
                print(f"{RED}✗ Memory HIGH: {current_mem:.1f} MB > 2GB{RESET}")
        
        # Save results to JSON
        output_file = Path(__file__).parent.parent / "benchmark_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{GREEN}Results saved to: {output_file}{RESET}\n")
        
        return 0


if __name__ == "__main__":
    benchmark = BenchmarkRunner()
    sys.exit(benchmark.run_full_benchmark())
