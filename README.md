# Integrated Meeting Assistant Pipeline

## Overview

This project integrate **face recognition** with **audio transcription** and **conversation summarization** to create an intelligent meeting assistant that:

1. **Recognizes people** using camera and facial recognition
2. **Displays meeting history** for returning visitors
3. **Records conversations** using microphone
4. **Transcribes audio** to text using Whisper AI
5. **Generates summaries** using Groq API
6. **Stores everything** in MongoDB for future reference

## Architecture

```
meeting_pipeline.py (Main Controller)
    ├── opencv/ (Face Recognition Module)
    │   ├── camera.py - Camera interface
    │   ├── detector.py - Face detection (MTCNN)
    │   ├── embedder.py - Face embeddings (FaceNet)
    │   ├── recognizer.py - Face matching
    │   └── database.py - MongoDB operations
    │
    └── audio_to_text/ (Audio Processing Module)
        ├── mic_transcriber.py - Audio recording
        ├── audio_transcriber.py - Speech-to-text (Whisper)
        └── text_summarizer.py - Text summarization (Groq)
```

## Features

### Face Recognition
- Real-time face detection using MTCNN
- Face recognition using FaceNet embeddings
- Automatic registration of new people
- Cosine similarity matching for identification

### Meeting Management
- Multiple meetings per person
- Chronological meeting history
- Stores transcript, summary, audio, and images
- Last meeting summary display for returning visitors

### Audio Processing
- Real-time microphone recording
- Fixed duration or manual stop recording
- High-quality audio capture (16kHz mono)

### Transcription
- Automatic speech-to-text using OpenAI Whisper
- Multiple model sizes (tiny to large)
- Language detection and translation support

### Summarization
- AI-powered summarization using Groq API
- Bullet-point format summaries
- Customizable summary length
- Key points extraction

## Prerequisites

### Hardware
- **Camera** (webcam or external)
- **Microphone** (built-in or external)

### Software
1. **Python 3.8+**
2. **MongoDB** (local or MongoDB Atlas)
3. **Groq API Key** (free at https://console.groq.com/)

### Operating System
- Windows, macOS, or Linux
- GPU (optional, for faster processing)

## Installation

### 1. Clone/Download the Project

```bash
cd d:\miniproject
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** If you encounter issues with torch/torchvision on Windows, install from official site:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### 3. Set Up MongoDB

**Option A: Local MongoDB**
```bash
# Install MongoDB from https://www.mongodb.com/try/download/community
# Start MongoDB service
# Default URI: mongodb://localhost:27017/
```

**Option B: MongoDB Atlas (Cloud - Recommended)**
1. Create free account at https://www.mongodb.com/cloud/atlas
2. Create a cluster
3. Get connection string
4. Update `opencv/config.py` with your connection string

### 4. Configure Groq API

Create a `.env` file in the project root:

```bash
GROQ_API_KEY=your_groq_api_key_here
```

Get your free API key from: https://console.groq.com/keys

### 5. Verify Setup

```bash
# Test database connection
cd opencv
python database.py

# Test audio recording
cd ../audio_to_text
python mic_transcriber.py
```

## Usage

### Quick Start

Run the integrated pipeline:

```bash
python run_pipeline.py
```

### Detailed Workflow

1. **Face Recognition Phase**
   - Position yourself in front of the camera
   - Press 'c' to capture your face
   - System will recognize you or register as new user

2. **Person Information Display**
   - Shows your name and ID
   - Displays last meeting summary (if returning)
   - Shows your captured image

3. **Meeting Recording**
   - Choose recording duration or manual stop
   - Speak into microphone
   - System records conversation

4. **Processing Phase**
   - Transcribes audio to text (Whisper)
   - Generates summary (Groq AI)
   - Stores everything in database

5. **Completion**
   - Meeting saved with transcript and summary
   - Audio and image files stored locally
   - Database updated with new meeting record

### Advanced Usage

#### Custom Pipeline Script

```python
from meeting_pipeline import MeetingPipeline

# Initialize pipeline
pipeline = MeetingPipeline()

# Run complete workflow
pipeline.run()

# Or run individual steps
person_id, name, img_path, is_new = pipeline.capture_and_recognize_face()
if person_id:
    pipeline.display_person_info(person_id, name, img_path, is_new)
    pipeline.record_and_process_meeting(person_id, name, img_path)

# Cleanup
pipeline.cleanup()
```

#### Access Meeting History

```python
from opencv.database import FaceDatabase

db = FaceDatabase()
db.connect()

# Get person record
person = db.get_person_by_name("John Doe")
person_id = str(person['_id'])

# Get all meetings
meetings = db.get_all_meetings(person_id)

for meeting in meetings:
    print(f"Date: {meeting['timestamp']}")
    print(f"Summary: {meeting['summary']}")
    print(f"Transcript: {meeting['transcript']}")
    print("-" * 80)

db.disconnect()
```

## Configuration

### Face Recognition Settings

Edit `opencv/config.py`:

```python
# Recognition threshold (0.0 - 1.0)
RECOGNITION_THRESHOLD = 0.85  # Higher = stricter matching

# Camera settings
CAMERA_INDEX = 0  # Change if using external camera
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# Database
MONGODB_URI = "your_mongodb_connection_string"
MONGODB_DATABASE = "meeting_assistant"
```

### Audio Settings

Edit `pipeline_config.py`:

```python
# Whisper model size
WHISPER_MODEL = 'base'  # Options: tiny, base, small, medium, large

# Audio quality
SAMPLE_RATE = 16000  # Hz
AUDIO_CHANNELS = 1  # Mono

# Recording
DEFAULT_RECORDING_DURATION = 30  # seconds
```

### Summarization Settings

```python
# Groq model
GROQ_MODEL = 'llama-3.3-70b-versatile'

# Summary length
MAX_SUMMARY_BULLETS = 10
```

## Project Structure

```
miniproject/
├── meeting_pipeline.py          # Main integration controller
├── run_pipeline.py              # Quick start script
├── pipeline_config.py           # Configuration settings
├── pipeline_utils.py            # Utility functions
├── requirements.txt             # Python dependencies
│
├── opencv/                      # Face recognition module
│   ├── camera.py
│   ├── detector.py
│   ├── embedder.py
│   ├── recognizer.py
│   ├── database.py              # Extended with meeting storage
│   ├── config.py
│   └── main.py
│
├── audio_to_text/              # Audio processing module
│   ├── mic_transcriber.py
│   ├── audio_transcriber.py
│   ├── text_summarizer.py
│   └── requirements.txt
│
└── meeting_data/               # Generated data directory
    ├── images/                 # Captured face images
    ├── audio/                  # Recorded audio files
    └── transcripts/            # Text transcripts
```

## Database Schema

### Persons Collection (`face_embeddings`)

```javascript
{
  _id: ObjectId,
  name: String,
  embedding: [Float],  // 512-dimensional FaceNet embedding
  date: DateTime,
  image_path: String,
  updated_at: DateTime
}
```

### Meetings Collection (`meetings`)

```javascript
{
  _id: ObjectId,
  person_id: String,    // Reference to person _id
  person_name: String,
  timestamp: DateTime,
  transcript: String,   // Full conversation text
  summary: String,      // AI-generated summary
  audio_path: String,   // Path to audio file
  image_path: String    // Path to captured image
}
```

## Troubleshooting

### Camera Issues

```bash
# Test camera
python opencv/camera.py

# Try different camera index in config.py
CAMERA_INDEX = 1  # or 2, 3...
```

### Microphone Issues

```bash
# List available microphones
python -c "import sounddevice as sd; print(sd.query_devices())"

# Test recording
cd audio_to_text
python mic_transcriber.py
```

### MongoDB Connection Issues

```bash
# Test connection
python opencv/database.py

# Check MongoDB is running
# For local: mongosh
# For Atlas: Check network access whitelist
```

### Groq API Issues

```bash
# Verify API key
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GROQ_API_KEY'))"

# Test summarizer
cd audio_to_text
python text_summarizer.py
```

### Model Download Issues

Whisper and FaceNet models download automatically on first run. If issues occur:

```bash
# Clear cache and retry
rm -rf ~/.cache/whisper
rm -rf ~/.cache/torch

# Or specify manual download location in code
```

## Performance Optimization

### Use GPU Acceleration

If you have NVIDIA GPU:

```bash
# Install CUDA-enabled PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Update configs
WHISPER_DEVICE = 'cuda'
FACENET_DEVICE = 'cuda'
MTCNN_DEVICE = 'cuda'
```

### Smaller Whisper Model

For faster transcription:

```python
WHISPER_MODEL = 'tiny'  # Fastest, less accurate
# or
WHISPER_MODEL = 'base'  # Good balance (recommended)
```

### Optimize Face Recognition

```python
# Lower image resolution
CAMERA_WIDTH = 480
CAMERA_HEIGHT = 360

# Adjust detection threshold
MIN_DETECTION_CONFIDENCE = 0.85
```

## API Reference

### MeetingPipeline Class

```python
class MeetingPipeline:
    def __init__()
    def capture_and_recognize_face() -> Tuple[str, str, str, bool]
    def display_person_info(person_id, person_name, image_path, is_new)
    def record_and_process_meeting(person_id, person_name, image_path) -> bool
    def run()
    def cleanup()
```

### Database Methods (Extended)

```python
class FaceDatabase:
    # Existing methods
    def store_embedding(name, embedding) -> bool
    def get_embedding_by_name(name) -> np.ndarray
    def get_all_embeddings() -> List[Dict]
    
    # New meeting methods
    def store_meeting(person_id, person_name, transcript, summary, ...) -> str
    def get_last_meeting(person_id) -> Dict
    def get_all_meetings(person_id) -> List[Dict]
    def get_person_by_name(name) -> Dict
    def update_person_image(person_id, image_path) -> bool
```

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Database**: Use authentication for production MongoDB
3. **Privacy**: Store audio/transcripts securely
4. **Consent**: Always get user consent before recording
5. **Data Retention**: Implement data cleanup policies

## License

This project is for educational and demonstration purposes.

## Credits

- **Face Recognition**: MTCNN + FaceNet
- **Speech Recognition**: OpenAI Whisper
- **Summarization**: Groq API (Llama 3.3)
- **Database**: MongoDB

## Support

For issues or questions:
1. Check troubleshooting section
2. Review module-specific READMEs in `opencv/` and `audio_to_text/`
3. Ensure all prerequisites are properly installed

## Future Enhancements

- [ ] Web interface
- [ ] Real-time transcription during recording
- [ ] Multiple language support
- [ ] Speaker diarization
- [ ] Action items extraction
- [ ] Calendar integration
- [ ] Email summaries
- [ ] Voice activity detection
- [ ] Noise cancellation
- [ ] Mobile app integration
