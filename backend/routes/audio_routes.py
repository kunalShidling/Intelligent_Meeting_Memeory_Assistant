"""
Audio Processing API Routes
Handles audio recording, transcription, and summarization.
"""

from flask import Blueprint, request, jsonify
import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from audio_to_text.mic_transcriber import MicrophoneTranscriber
from audio_to_text.audio_transcriber import AudioTranscriber
from audio_to_text.text_summarizer import TextSummarizer
from backend.services.audio_jobs import AudioJobManager
from pipeline_config import (
    WHISPER_MODEL,
    WHISPER_DEVICE,
    WHISPER_LANGUAGE,
    WHISPER_CHUNK_SECONDS,
    WHISPER_MAX_WORKERS,
    GROQ_MODEL
)

logger = logging.getLogger(__name__)

# Create blueprint
audio_bp = Blueprint('audio', __name__, url_prefix='/api/audio')

MINIMUM_AUDIO_BYTES = 1024

# Global instances
mic_transcriber = None
audio_transcriber = None
text_summarizer = None
job_manager = None
recording_data = {}  # Store recording sessions

import threading
init_lock = threading.Lock()

def init_components():
    """Initialize audio processing components."""
    global mic_transcriber, audio_transcriber, text_summarizer, job_manager

    if mic_transcriber is not None and audio_transcriber is not None and text_summarizer is not None and job_manager is not None:
        return

    with init_lock:
        if mic_transcriber is not None and audio_transcriber is not None and text_summarizer is not None and job_manager is not None:
            return
            
        logger.info("Initializing audio components...")
        mic_t = MicrophoneTranscriber(model_name=WHISPER_MODEL, device=WHISPER_DEVICE)
        audio_t = AudioTranscriber(
            model_name=WHISPER_MODEL,
            device=WHISPER_DEVICE,
            language=WHISPER_LANGUAGE,
            task='transcribe',
            chunk_seconds=WHISPER_CHUNK_SECONDS,
            max_workers=WHISPER_MAX_WORKERS
        )
        text_s = TextSummarizer(model=GROQ_MODEL)
        
        mic_transcriber = mic_t
        audio_transcriber = audio_t
        text_summarizer = text_s
        job_manager = AudioJobManager(audio_transcriber, text_summarizer)
        logger.info("Audio components initialized successfully")

@audio_bp.route('/record', methods=['POST'])
def record_audio():
    """Record audio from microphone."""
    try:
        init_components()

        data = request.json
        duration = data.get('duration', 30)  # Default 30 seconds
        person_id = data.get('person_id')

        logger.info(f"Recording audio for {duration} seconds...")

        # Record audio
        audio_data = mic_transcriber.record_audio(
            duration=duration,
            show_progress=True
        )

        # Save audio file
        audio_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'meeting_data', 'audio')
        os.makedirs(audio_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f'meeting_{timestamp}.wav'
        audio_path = os.path.join(audio_dir, audio_filename)

        mic_transcriber.save_audio_to_file(audio_data, audio_path)

        logger.info(f"Audio saved to: {audio_path}")

        return jsonify({
            'success': True,
            'audio_path': audio_path,
            'duration': len(audio_data) / mic_transcriber.sample_rate,
            'filename': audio_filename
        })

    except Exception as e:
        logger.error(f"Error recording audio: {e}")
        return jsonify({'error': str(e)}), 500

@audio_bp.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio file to text."""
    try:
        init_components()

        data = request.json
        audio_path = data.get('audio_path')

        if not audio_path or not os.path.exists(audio_path):
            return jsonify({'error': 'Invalid audio path'}), 400

        logger.info(f"Transcribing audio: {audio_path}")

        # Transcribe
        text = audio_transcriber.transcribe_audio(
            file_path=audio_path,
            task='transcribe',
            language='en',
            include_timestamps=False,
            verbose=True
        )

        logger.info(f"Transcription complete: {len(text)} characters")

        return jsonify({
            'success': True,
            'transcript': text,
            'length': len(text)
        })

    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return jsonify({'error': str(e)}), 500

@audio_bp.route('/summarize', methods=['POST'])
def summarize_text():
    """Summarize text using Groq AI."""
    try:
        init_components()

        data = request.json
        text = data.get('text')
        max_bullets = data.get('max_bullets', 10)

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        logger.info(f"Summarizing text: {len(text)} characters")

        # Summarize
        summary = text_summarizer.summarize_to_bullets(
            text=text,
            max_bullets=max_bullets,
            verbose=True
        )

        logger.info("Summarization complete")

        return jsonify({
            'success': True,
            'summary': summary
        })

    except Exception as e:
        logger.error(f"Error summarizing text: {e}")
        return jsonify({'error': str(e)}), 500

@audio_bp.route('/record-and-transcribe', methods=['POST'])
def record_and_transcribe():
    """Record audio and transcribe in one step."""
    try:
        init_components()

        data = request.json
        duration = data.get('duration', 30)

        logger.info(f"Recording and transcribing for {duration} seconds...")

        # Record audio
        audio_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'meeting_data', 'audio')
        os.makedirs(audio_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f'meeting_{timestamp}.wav'
        audio_path = os.path.join(audio_dir, audio_filename)

        # Use transcribe_from_mic which does both
        text = mic_transcriber.transcribe_from_mic(
            duration=duration,
            save_audio=True,
            output_audio_path=audio_path,
            verbose=True
        )

        logger.info(f"Recording and transcription complete")

        return jsonify({
            'success': True,
            'transcript': text,
            'audio_path': audio_path,
            'filename': audio_filename
        })

    except Exception as e:
        logger.error(f"Error in record and transcribe: {e}")
        return jsonify({'error': str(e)}), 500

@audio_bp.route('/process-file', methods=['POST'])
def process_audio_file():
    """Process an uploaded audio file (transcribe + summarize)."""
    try:
        init_components()

        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = request.files['audio']

        # Save uploaded file
        audio_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'meeting_data', 'audio')
        os.makedirs(audio_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_suffix = Path(audio_file.filename or '').suffix.lower()
        if original_suffix not in AudioTranscriber.SUPPORTED_FORMATS:
            original_suffix = '.webm'

        audio_path = os.path.join(audio_dir, f'upload_{timestamp}{original_suffix}')
        audio_file.save(audio_path)

        file_size = os.path.getsize(audio_path)
        if file_size < MINIMUM_AUDIO_BYTES:
            return jsonify({
                'error': 'Uploaded audio file is too short or empty. Please record a longer clip and try again.',
                'file_size': file_size
            }), 400

        sync_mode = request.args.get('sync', 'false').lower() == 'true'
        if sync_mode:
            text = audio_transcriber.transcribe_audio(
                file_path=audio_path,
                task='transcribe',
                language='en',
                include_timestamps=False,
                verbose=True
            )

            summary = text_summarizer.summarize_to_bullets(
                text=text,
                max_bullets=10,
                verbose=True
            )

            return jsonify({
                'success': True,
                'status': 'completed',
                'transcript': text,
                'summary': summary,
                'audio_path': audio_path
            })

        job_id = job_manager.submit(audio_path, max_bullets=10)
        return jsonify({
            'success': True,
            'status': 'queued',
            'job_id': job_id,
            'audio_path': audio_path
        })

    except Exception as e:
        logger.error(f"Error processing audio file: {e}")
        return jsonify({'error': str(e)}), 500

@audio_bp.route('/job/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Check status of an async audio processing job."""
    try:
        init_components()

        job = job_manager.get(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404

        response = {
            'success': True,
            'job_id': job_id,
            'status': job.get('status'),
            'audio_path': job.get('audio_path'),
            'error': job.get('error')
        }

        if job.get('status') == 'completed':
            response.update({
                'transcript': job.get('transcript'),
                'summary': job.get('summary')
            })

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error fetching job status: {e}")
        return jsonify({'error': str(e)}), 500

@audio_bp.route('/devices', methods=['GET'])
def list_audio_devices():
    """List available audio input devices."""
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        input_devices = []

        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append({
                    'id': idx,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                })

        return jsonify({
            'success': True,
            'devices': input_devices
        })

    except Exception as e:
        logger.error(f"Error listing audio devices: {e}")
        return jsonify({'error': str(e)}), 500
