"""
Configuration settings for the integrated meeting pipeline.
"""

import os
from pathlib import Path

# ==================== Pipeline Settings ====================
PROJECT_ROOT = Path(__file__).parent
MEETING_DATA_DIR = PROJECT_ROOT / "meeting_data"
IMAGES_DIR = MEETING_DATA_DIR / "images"
AUDIO_DIR = MEETING_DATA_DIR / "audio"
TRANSCRIPTS_DIR = MEETING_DATA_DIR / "transcripts"

# ==================== Audio Settings ====================
# Whisper model for transcription (smaller models reduce latency)
WHISPER_MODEL = 'tiny'  # Options: tiny, base, small, medium, large
WHISPER_DEVICE = 'auto'  # Use 'auto' to select GPU when available
WHISPER_LANGUAGE = 'en'  # Force English-only transcription
WHISPER_TASK = 'transcribe'  # Translate mode disabled
WHISPER_CHUNK_SECONDS = 15  # Chunk size for faster streaming
WHISPER_MAX_WORKERS = 2  # Parallel chunk workers on CPU

# Audio recording settings
SAMPLE_RATE = 16000  # Hz
AUDIO_CHANNELS = 1  # Mono
DEFAULT_RECORDING_DURATION = 30  # seconds

# ==================== Summarization Settings ====================
# Groq API settings
GROQ_MODEL = 'llama-3.3-70b-versatile'
MAX_SUMMARY_BULLETS = 10

# ==================== Face Recognition Settings ====================
# Import from opencv config
try:
    from opencv import config as opencv_config
    RECOGNITION_THRESHOLD = opencv_config.RECOGNITION_THRESHOLD
    MONGODB_URI = opencv_config.MONGODB_URI
    MONGODB_DATABASE = opencv_config.MONGODB_DATABASE
except ImportError:
    # Fallback defaults
    RECOGNITION_THRESHOLD = 0.85
    MONGODB_URI = "mongodb://localhost:27017/"
    MONGODB_DATABASE = "meeting_assistant"

# ==================== Display Settings ====================
SHOW_FACE_WINDOW = True
SHOW_TRANSCRIPT_PREVIEW = True
TRANSCRIPT_PREVIEW_LENGTH = 500  # characters

# ==================== Logging Settings ====================
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
