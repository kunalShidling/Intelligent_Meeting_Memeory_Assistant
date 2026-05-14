"""
Face detection module using MTCNN.
Detects and extracts faces from images.
"""

import cv2
import numpy as np
from mtcnn import MTCNN
from typing import Optional, Tuple, Dict
import logging
import config

# Configure logging
logger = logging.getLogger(__name__)


class FaceDetector:
    """Face detector using MTCNN."""
    
    # Minimum image dimension accepted by MTCNN without producing empty Conv2D batches
    MIN_IMAGE_DIM = 80

    def __init__(self):
        """Initialize MTCNN face detector."""
        import threading
        self.inference_lock = threading.Lock()
        try:
            # MTCNN 1.0.0+ has simplified API
            self.detector = MTCNN()
            logger.info("MTCNN face detector initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MTCNN: {e}")
            raise
    
    def detect_faces(self, image: np.ndarray) -> list:
        """
        Detect all faces in image.
        
        Args:
            image: Input image (BGR format from OpenCV)
            
        Returns:
            list: List of detected faces with bounding boxes and confidence
        """
        import gc
        try:
            h, w = image.shape[:2]

            # Guard: MTCNN's image pyramid creates zero-size batches on very small
            # images, causing a TF Conv2D crash. Reject them early.
            if h < self.MIN_IMAGE_DIM or w < self.MIN_IMAGE_DIM:
                logger.debug(
                    f"Image too small for MTCNN ({w}x{h}), "
                    f"minimum is {self.MIN_IMAGE_DIM}px on each side"
                )
                return []

            # Convert BGR to RGB (MTCNN expects RGB)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect faces — wrap in its own try/except to catch TF/Keras
            # version-mismatch errors (Conv2D empty batch, PNet positional-arg)
            # without crashing the whole request.
            with self.inference_lock:
                try:
                    detections = self.detector.detect_faces(rgb_image)
                except Exception as tf_err:
                    err_str = str(tf_err)
                    # Known compat errors between mtcnn and newer TensorFlow/Keras
                    if any(kw in err_str for kw in [
                        'Conv2D', 'PNet', 'positional arguments',
                        'empty output', 'DefaultCPUAllocator'
                    ]):
                        logger.debug(
                            f"MTCNN TF-compat issue (no faces returned): {err_str[:120]}"
                        )
                        return []
                    raise  # re-raise unexpected errors
            
            logger.debug(f"Detected {len(detections)} face(s)")
            
            # Explicitly collect garbage after detection to prevent memory leaks in TF loop
            gc.collect()
            
            return detections
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []
    
    def get_largest_face(self, detections: list) -> Optional[Dict]:
        """
        Get the largest face from detections.
        
        Args:
            detections: List of face detections
            
        Returns:
            Optional[Dict]: Largest face detection, or None if no faces
        """
        if not detections:
            return None
        
        # Find largest face by area
        largest_face = max(
            detections,
            key=lambda d: d['box'][2] * d['box'][3]  # width * height
        )
        
        box = largest_face['box']
        confidence = largest_face['confidence']
        
        logger.debug(f"Largest face - Box: {box}, Confidence: {confidence:.3f}")
        
        return largest_face
    
    def validate_detection(self, detection: Dict) -> bool:
        """
        Validate face detection meets confidence threshold.
        
        Args:
            detection: Face detection dictionary
            
        Returns:
            bool: True if detection is valid, False otherwise
        """
        if detection is None:
            logger.warning("No face detection to validate")
            return False
        
        confidence = detection.get('confidence', 0.0)
        
        if confidence < config.MIN_DETECTION_CONFIDENCE:
            logger.warning(
                f"Face detection confidence {confidence:.3f} below threshold "
                f"{config.MIN_DETECTION_CONFIDENCE}"
            )
            return False
        
        logger.debug(f"Face detection validated - Confidence: {confidence:.3f}")
        return True
    
    def crop_face(self, image: np.ndarray, detection: Dict, padding: int = 0) -> Optional[np.ndarray]:
        """
        Crop face region from image.
        
        Args:
            image: Input image
            detection: Face detection dictionary
            padding: Additional padding around face (in pixels)
            
        Returns:
            Optional[np.ndarray]: Cropped face image, or None if failed
        """
        try:
            box = detection['box']
            x, y, w, h = box
            
            # Add padding
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = w + 2 * padding
            h = h + 2 * padding
            
            # Ensure coordinates are within image bounds
            x2 = min(image.shape[1], x + w)
            y2 = min(image.shape[0], y + h)
            
            # Crop face
            face = image[y:y2, x:x2]
            
            if face.size == 0:
                logger.error("Cropped face is empty")
                return None
            
            logger.debug(f"Face cropped - Region: ({x}, {y}, {w}, {h}), Shape: {face.shape}")
            return face
            
        except Exception as e:
            logger.error(f"Error cropping face: {e}")
            return None
    
    def detect_and_extract_largest_face(
        self,
        image_path: str,
        padding: int = 20
    ) -> Tuple[bool, Optional[np.ndarray], Optional[Dict]]:
        """
        Detect and extract the largest face from an image file.
        
        Args:
            image_path: Path to image file
            padding: Padding around face in pixels
            
        Returns:
            Tuple[bool, Optional[np.ndarray], Optional[Dict]]:
                - success: True if face detected and extracted successfully
                - face: Cropped face image (BGR format)
                - detection_info: Detection metadata (box, confidence, keypoints)
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to read image: {image_path}")
                return False, None, None
            
            logger.info(f"Processing image: {image_path}, Shape: {image.shape}")
            
            # Detect faces
            detections = self.detect_faces(image)
            
            if not detections:
                logger.warning("No faces detected in image")
                return False, None, None
            
            # Get largest face
            largest_face = self.get_largest_face(detections)
            
            # Validate detection
            if not self.validate_detection(largest_face):
                logger.warning("Face detection failed validation")
                return False, None, None
            
            # Crop face
            face = self.crop_face(image, largest_face, padding)
            
            if face is None:
                logger.error("Failed to crop face")
                return False, None, None
            
            # Prepare detection info
            detection_info = {
                'box': largest_face['box'],
                'confidence': largest_face['confidence'],
                'keypoints': largest_face.get('keypoints', {}),
                'image_shape': image.shape,
                'face_shape': face.shape
            }
            
            logger.info(
                f"Face extracted successfully - "
                f"Confidence: {detection_info['confidence']:.3f}, "
                f"Shape: {face.shape}"
            )
            
            return True, face, detection_info
            
        except Exception as e:
            logger.error(f"Error in detect_and_extract_largest_face: {e}")
            return False, None, None
            
    def detect_and_extract_all_faces(
        self,
        image_path: str,
        padding: int = 20
    ) -> list:
        """
        Detect and extract all faces from an image file.
        
        Args:
            image_path: Path to image file
            padding: Padding around face in pixels
            
        Returns:
            list: List of tuples (face_img, detection_info) for valid faces
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to read image: {image_path}")
                return []
            
            logger.info(f"Processing image: {image_path}, Shape: {image.shape}")
            
            # Detect faces
            detections = self.detect_faces(image)
            
            if not detections:
                logger.warning("No faces detected in image")
                return []
            
            valid_faces = []
            for det in detections:
                # Validate detection
                if not self.validate_detection(det):
                    continue
                
                # Crop face
                face = self.crop_face(image, det, padding)
                if face is None:
                    continue
                
                # Prepare detection info
                detection_info = {
                    'box': det['box'],
                    'confidence': det['confidence'],
                    'keypoints': det.get('keypoints', {}),
                    'image_shape': image.shape,
                    'face_shape': face.shape
                }
                
                valid_faces.append((face, detection_info))
                
            logger.info(f"Extracted {len(valid_faces)} valid faces successfully.")
            return valid_faces
            
        except Exception as e:
            logger.error(f"Error in detect_and_extract_all_faces: {e}")
            return []
    
    def visualize_detection(
        self,
        image_path: str,
        detection_info: Dict,
        window_name: str = "Face Detection"
    ):
        """
        Visualize face detection on image.
        
        Args:
            image_path: Path to original image
            detection_info: Detection metadata
            window_name: Name of display window
        """
        if not config.SHOW_DEBUG_WINDOW:
            return
        
        try:
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to read image for visualization: {image_path}")
                return
            
            # Draw bounding box
            box = detection_info['box']
            x, y, w, h = box
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Draw confidence
            confidence = detection_info['confidence']
            label = f"Confidence: {confidence:.3f}"
            cv2.putText(
                image,
                label,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )
            
            # Draw keypoints if available
            keypoints = detection_info.get('keypoints', {})
            for key, point in keypoints.items():
                if point:
                    cv2.circle(image, tuple(point), 3, (0, 0, 255), -1)
            
            # Display
            cv2.imshow(window_name, image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
        except Exception as e:
            logger.error(f"Error visualizing detection: {e}")


def main():
    """Test face detector."""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT
    )
    
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python detector.py <image_path>")
        return
    
    image_path = sys.argv[1]
    
    detector = FaceDetector()
    success, face, detection_info = detector.detect_and_extract_largest_face(image_path)
    
    if success:
        print(f"Face detected successfully!")
        print(f"Confidence: {detection_info['confidence']:.3f}")
        print(f"Face shape: {detection_info['face_shape']}")
        
        # Show detected face
        if config.SHOW_DEBUG_WINDOW:
            detector.visualize_detection(image_path, detection_info)
            cv2.imshow("Extracted Face", face)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    else:
        print("Failed to detect face")


if __name__ == "__main__":
    main()
