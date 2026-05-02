"""
Continuous Face Monitoring Module
Real-time multi-face detection and recognition with bounding boxes
"""

import cv2
import numpy as np
import logging
import time
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from detector import FaceDetector
from embedder import FaceEmbedder
from database import FaceDatabase
from recognizer import FaceRecognizer
import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    datefmt=config.LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)


class ContinuousMonitor:
    """
    Continuous face monitoring system with real-time multi-face detection
    """
    
    def __init__(self):
        """Initialize continuous monitoring system"""
        logger.info("Initializing Continuous Face Monitor...")
        
        try:
            # Initialize components
            self.detector = FaceDetector()
            self.embedder = FaceEmbedder()
            
            # Initialize database
            self.database = FaceDatabase()
            if not self.database.connect():
                raise Exception("Failed to connect to database")
            
            self.recognizer = FaceRecognizer(self.database)
            
            # Camera
            self.camera = None
            self.camera_index = config.CAMERA_INDEX
            
            # Performance settings
            self.process_every_n_frames = 3  # Process every 3rd frame for better performance
            self.frame_count = 0
            
            # Face cache (avoid re-processing same faces)
            self.face_cache = {}
            self.cache_timeout = 5.0  # seconds
            
            # Display settings
            self.box_color_known = (0, 255, 0)      # Green for recognized
            self.box_color_unknown = (0, 0, 255)    # Red for unknown
            self.box_thickness = 2
            self.font = cv2.FONT_HERSHEY_SIMPLEX
            self.font_scale = 0.6
            self.font_thickness = 2
            
            logger.info("✓ Continuous Monitor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitor: {e}")
            raise
    
    def start_camera(self) -> bool:
        """Start camera capture"""
        try:
            self.camera = cv2.VideoCapture(self.camera_index)
            
            if not self.camera.isOpened():
                logger.error(f"Failed to open camera at index {self.camera_index}")
                return False
            
            # Set camera properties
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            
            logger.info(f"✓ Camera opened successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            return False
    
    def stop_camera(self):
        """Stop camera and cleanup"""
        if self.camera is not None:
            self.camera.release()
        cv2.destroyAllWindows()
        logger.info("Camera stopped")
    
    def detect_all_faces(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect all faces in frame
        
        Args:
            frame: Video frame (BGR format)
            
        Returns:
            List of face dictionaries with 'face', 'box', 'confidence'
        """
        try:
            # Convert BGR to RGB for MTCNN
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces using MTCNN
            detections = self.detector.detect_faces(rgb_frame)
            
            if not detections:
                return []
            
            faces = []
            for detection in detections:
                confidence = detection.get('confidence', 0.0)
                
                # Filter by confidence
                if confidence < config.MIN_DETECTION_CONFIDENCE:
                    continue
                
                # Get bounding box
                box = detection['box']
                x, y, w, h = box
                
                # Add padding
                padding = 20
                x1 = max(0, x - padding)
                y1 = max(0, y - padding)
                x2 = min(frame.shape[1], x + w + padding)
                y2 = min(frame.shape[0], y + h + padding)
                
                # Crop face
                face_crop = frame[y1:y2, x1:x2]
                
                if face_crop.size == 0:
                    continue
                
                faces.append({
                    'face': face_crop,
                    'box': (x1, y1, x2 - x1, y2 - y1),
                    'confidence': confidence
                })
            
            return faces
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []
    
    def process_face(self, face_img: np.ndarray) -> Dict:
        """
        Process and recognize a face
        
        Args:
            face_img: Cropped face image
            
        Returns:
            Dictionary with recognition results
        """
        try:
            # Generate embedding
            success, embedding = self.embedder.embed_face(face_img)
            
            if not success or embedding is None:
                return {
                    'status': 'error',
                    'name': 'Unknown',
                    'confidence': 0.0
                }
            
            # Recognize face
            recognized, name, confidence = self.recognizer.recognize(embedding)
            
            if recognized:
                return {
                    'status': 'recognized',
                    'name': name,
                    'confidence': confidence
                }
            else:
                return {
                    'status': 'unknown',
                    'name': 'Unknown Person',
                    'confidence': confidence
                }
                
        except Exception as e:
            logger.error(f"Error processing face: {e}")
            return {
                'status': 'error',
                'name': 'Error',
                'confidence': 0.0
            }
    
    def get_cache_key(self, box: Tuple[int, int, int, int]) -> str:
        """Generate cache key from bounding box"""
        x, y, w, h = box
        # Round to nearest 30 pixels to handle small jitters especially for faraway faces
        return f"{x//30}_{y//30}_{w//30}_{h//30}"
    
    def get_cached_result(self, box: Tuple[int, int, int, int]) -> Optional[Dict]:
        """Get cached recognition result if available and not expired"""
        cache_key = self.get_cache_key(box)
        
        if cache_key in self.face_cache:
            cached = self.face_cache[cache_key]
            age = time.time() - cached['timestamp']
            
            if age < self.cache_timeout:
                return cached['result']
        
        return None
    
    def cache_result(self, box: Tuple[int, int, int, int], result: Dict):
        """Cache recognition result"""
        cache_key = self.get_cache_key(box)
        self.face_cache[cache_key] = {
            'timestamp': time.time(),
            'result': result
        }
    
    def clean_cache(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, data in self.face_cache.items()
            if current_time - data['timestamp'] > self.cache_timeout
        ]
        for key in expired_keys:
            del self.face_cache[key]
    
    def draw_face_box(self, frame: np.ndarray, box: Tuple[int, int, int, int],
                     result: Dict):
        """
        Draw bounding box and label on frame
        
        Args:
            frame: Video frame
            box: Bounding box (x, y, w, h)
            result: Recognition result dictionary
        """
        x, y, w, h = box
        status = result['status']
        name = result['name']
        confidence = result['confidence']
        
        # Choose color based on status
        if status == 'recognized':
            color = self.box_color_known
            label = f"{name} ({confidence:.0%})"
        else:
            color = self.box_color_unknown
            label = "Unknown"
        
        # Draw rectangle
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, self.box_thickness)
        
        # Calculate text size
        (text_width, text_height), baseline = cv2.getTextSize(
            label, self.font, self.font_scale, self.font_thickness
        )
        
        # Draw text background
        cv2.rectangle(
            frame,
            (x, y - text_height - 10),
            (x + text_width + 10, y),
            color,
            -1
        )
        
        # Draw text
        cv2.putText(
            frame,
            label,
            (x + 5, y - 5),
            self.font,
            self.font_scale,
            (255, 255, 255),
            self.font_thickness
        )
    
    def draw_info(self, frame: np.ndarray, fps: float, face_count: int):
        """Draw information overlay"""
        info_lines = [
            f"FPS: {fps:.1f}",
            f"Faces: {face_count}",
            f"Registered: {self.database.count_embeddings()}",
            "Press 'q' to quit"
        ]
        
        y_offset = 30
        for line in info_lines:
            cv2.putText(
                frame,
                line,
                (10, y_offset),
                self.font,
                0.5,
                (0, 255, 255),
                1
            )
            y_offset += 25
    
    def run(self):
        """
        Run continuous monitoring loop
        """
        print("\n" + "=" * 70)
        print("CONTINUOUS FACE MONITORING - REAL-TIME RECOGNITION")
        print("=" * 70)
        print("Features:")
        print("  🎥 Camera stays on continuously")
        print("  👥 Detects multiple faces simultaneously")
        print("  🟢 Green box = Recognized person (with name)")
        print("  🔴 Red box = Unknown person")
        print("  ⚡ Real-time processing")
        print("\nControls:")
        print("  Press 'q' to quit")
        print("=" * 70 + "\n")
        
        if not self.start_camera():
            print("✗ Failed to start camera")
            return
        
        # FPS calculation
        fps_start_time = time.time()
        fps_counter = 0
        fps = 0.0
        
        # Last processed results (for smooth display between processing frames)
        last_results = []
        
        try:
            while True:
                # Read frame
                ret, frame = self.camera.read()
                if not ret:
                    logger.error("Failed to read frame")
                    break
                
                self.frame_count += 1
                fps_counter += 1
                
                # Calculate FPS
                elapsed = time.time() - fps_start_time
                if elapsed > 1.0:
                    fps = fps_counter / elapsed
                    fps_start_time = time.time()
                    fps_counter = 0
                
                # Process faces every N frames
                if self.frame_count % self.process_every_n_frames == 0:
                    # Detect all faces
                    detected_faces = self.detect_all_faces(frame)
                    
                    if detected_faces:
                        logger.debug(f"Processing {len(detected_faces)} face(s)")
                        
                        results = []
                        for face_data in detected_faces:
                            face_img = face_data['face']
                            box = face_data['box']
                            
                            # Check cache first
                            cached_result = self.get_cached_result(box)
                            
                            if cached_result:
                                result = cached_result
                            else:
                                # Process face
                                result = self.process_face(face_img)
                                # Cache result
                                self.cache_result(box, result)
                            
                            results.append({
                                'box': box,
                                'result': result
                            })
                        
                        last_results = results
                        
                        # Clean cache periodically
                        if self.frame_count % 30 == 0:
                            self.clean_cache()
                
                # Draw boxes (use last results for smooth display)
                for item in last_results:
                    self.draw_face_box(frame, item['box'], item['result'])
                
                # Draw info overlay
                self.draw_info(frame, fps, len(last_results))
                
                # Display frame
                cv2.imshow('Continuous Face Monitor', frame)
                
                # Handle key press
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    logger.info("Quit requested")
                    break
        
        except KeyboardInterrupt:
            logger.info("\nInterrupted by user")
        
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.stop_camera()
            self.database.disconnect()
            print("\n✓ Continuous monitoring stopped")


def main():
    """Main entry point"""
    try:
        monitor = ContinuousMonitor()
        monitor.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n✗ Error: {e}")
        print("Please check:")
        print("  1. Camera is available")
        print("  2. Database is connected")
        print("  3. Dependencies are installed")


if __name__ == "__main__":
    main()
