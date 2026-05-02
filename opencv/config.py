"""
Configuration settings for the facial recognition system.
"""

import os

# ==================== Camera Settings ====================
CAMERA_INDEX = 0  # Default webcam index
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAPTURE_KEY = 'c'  # Key to capture frame
QUIT_KEY = 'q'  # Key to quit

# ==================== Face Detection Settings ====================
# MTCNN settings
MTCNN_MIN_FACE_SIZE = 20  # Reduced to detect smaller faces (further away)
MTCNN_THRESHOLDS = [0.6, 0.7, 0.7]  # Confidence thresholds for P-Net, R-Net, O-Net
MTCNN_DEVICE = 'cpu'  # Use 'cuda' if GPU available

# Face detection confidence threshold
MIN_DETECTION_CONFIDENCE = 0.75  # Lowered to accept faces from further away

# ==================== Face Embedding Settings ====================
# FaceNet settings
FACENET_INPUT_SIZE = 160  # FaceNet expects 160x160 input
EMBEDDING_SIZE = 512  # FaceNet generates 512-dimensional embeddings
FACENET_DEVICE = 'cpu'  # Use 'cuda' if GPU available

# Normalization settings (for FaceNet preprocessing)
PIXEL_MEAN = 127.5
PIXEL_STD = 128.0

# ==================== Recognition Settings ====================
# Cosine similarity thresholds
RECOGNITION_THRESHOLD = 0.75  # If similarity >= this, person is recognized
DUPLICATE_THRESHOLD = 0.98  # If similarity >= this, considered duplicate
UPDATE_THRESHOLD = 0.75  # Update profile if similarity is >= this (but < DUPLICATE_THRESHOLD)
UPDATE_COOLDOWN_HOURS = 24  # Wait 24 hours before updating same person again

# ==================== Database Settings ====================
# MongoDB connection - Choose one:

# Option 1: Local MongoDB
MONGODB_URI ="mongodb+srv://kunalshidling_db_user:7oVEGpDYgJF63mQW@cluster0.57skn49.mongodb.net/?appName=Cluster0"

# Option 2: MongoDB Atlas (Cloud) - Replace with your connection string
# MONGODB_URI = "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
# Example: MONGODB_URI = "mongodb+srv://myuser:mypass123@cluster0.abc123.mongodb.net/?retryWrites=true&w=majority"

MONGODB_DATABASE = "meeting_assistant"
MONGODB_COLLECTION = "face_embeddings"

# MongoDB SSL/TLS settings (for Atlas)
MONGODB_TLS = True
MONGODB_TLS_ALLOW_INVALID_CERTIFICATES = True  # Set to False in production with valid certs

# ==================== Storage Settings ====================
# Temporary storage
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
TEMP_IMAGE_NAME = "captured_face.jpg"

# ==================== Logging Settings ====================
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# ==================== Debug Settings ====================
DEBUG_MODE = True  # Enable debug visualizations
SHOW_DEBUG_WINDOW = True  # Show debug windows during processing
SAVE_DEBUG_IMAGES = False  # Save debug images to disk

# ==================== Privacy Settings ====================
DELETE_TEMP_IMAGES = True  # Delete temporary images after processing
AUTO_CLEANUP = True  # Automatically cleanup temp directory on exit

# ==================== Validation Settings ====================
MAX_NAME_LENGTH = 100
MIN_NAME_LENGTH = 1
ALLOWED_NAME_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_."
