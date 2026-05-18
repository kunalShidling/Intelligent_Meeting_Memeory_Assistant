"""
Audio Transcription Module using OpenAI Whisper

This module provides a production-ready solution for converting audio files to text
using OpenAI's Whisper model with English-only, low-latency settings and chunked
inference for faster response times.

Author: Audio Transcription System
Date: 2026
"""

import os
import json
import warnings
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import torch

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

try:
    import whisper
except ImportError:
    raise ImportError(
        "Whisper is not installed. Please install it using: pip install openai-whisper"
    )


class AudioTranscriber:
    """
    A class for transcribing and translating audio files using OpenAI Whisper.
    
    Attributes:
        model_name (str): The Whisper model to use (tiny, base, small, medium, large)
        device (str): The device to run inference on ('cpu' or 'cuda')
        model: The loaded Whisper model
    """
    
    SUPPORTED_FORMATS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.wma', '.aac', '.mp4', '.webm'}
    AVAILABLE_MODELS = ['tiny', 'base', 'small', 'medium', 'large']
    
    def __init__(
        self,
        model_name: str = 'base',
        device: str = 'cpu',
        language: str = 'en',
        task: str = 'transcribe',
        chunk_seconds: int = 15,
        max_workers: Optional[int] = None
    ):
        """
        Initialize the AudioTranscriber with a specified Whisper model.
        
        Args:
            model_name (str): Model size to use. Options: 'tiny', 'base', 'small', 'medium', 'large'
                             Smaller models are faster but less accurate.
            device (str): Device to run on ('cpu' or 'cuda'). Defaults to 'cpu'.
        
        Raises:
            ValueError: If an invalid model name is provided
        """
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Invalid model name: {model_name}. "
                f"Available models: {', '.join(self.AVAILABLE_MODELS)}"
            )
        
        self.model_name = model_name
        self.device = self._resolve_device(device)
        self.language = language or 'en'
        self.task = 'transcribe' if task != 'transcribe' else task
        self.chunk_seconds = max(5, int(chunk_seconds))
        self.max_workers = max_workers
        self.model = None
        self.use_fp16 = self.device == 'cuda'
        self.inference_lock = threading.Lock()
        print(f"Initializing Whisper model '{model_name}' on {self.device}...")
        self._load_model()

    def _resolve_device(self, device: str) -> str:
        if device == 'auto':
            return 'cuda' if torch.cuda.is_available() else 'cpu'
        return device
    
    def _load_model(self) -> None:
        """Load the Whisper model into memory."""
        try:
            self.model = whisper.load_model(self.model_name, device=self.device)
            print(f"Model '{self.model_name}' loaded successfully.")
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {str(e)}")
    
    def _validate_audio_file(self, file_path: str) -> Path:
        """
        Validate that the audio file exists and has a supported format.
        
        Args:
            file_path (str): Path to the audio file
        
        Returns:
            Path: Validated Path object
        
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is not supported
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported audio format: {path.suffix}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        return path
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Convert seconds to HH:MM:SS.mmm format.
        
        Args:
            seconds (float): Time in seconds
        
        Returns:
            str: Formatted timestamp string
        """
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{milliseconds:03d}"
    
    def transcribe_audio(
        self,
        file_path: str,
        task: str = 'transcribe',
        language: Optional[str] = None,
        include_timestamps: bool = False,
        verbose: bool = False
    ) -> str:
        """
        Transcribe or translate an audio file to text.
        
        Args:
            file_path (str): Path to the audio file
            task (str): Either 'transcribe' (same language) or 'translate' (to English)
            language (str, optional): Language code (e.g., 'en', 'es', 'fr'). Auto-detected if None.
            include_timestamps (bool): Whether to include timestamps in output
            verbose (bool): Whether to print progress information
        
        Returns:
            str: Transcribed text
        
        Raises:
            FileNotFoundError: If the audio file doesn't exist
            ValueError: If the file format is unsupported or task is invalid
        """
        # Validate inputs
        audio_path = self._validate_audio_file(file_path)
        
        if task != 'transcribe':
            task = 'transcribe'
        
        if verbose:
            print(f"\nProcessing: {audio_path.name}")
            print(f"Task: {task}")
            print(f"Language: {language if language else 'en'}")
        
        try:
            language = language or self.language or 'en'

            if include_timestamps:
                result = self._transcribe_full(
                    str(audio_path),
                    task=task,
                    language=language,
                    verbose=verbose
                )
                return self._format_with_timestamps(result)

            return self._transcribe_chunked(
                str(audio_path),
                task=task,
                language=language,
                verbose=verbose
            )
        
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {str(e)}")
    
    def _format_with_timestamps(self, result: Dict[str, Any]) -> str:
        """
        Format transcription result with timestamps.
        
        Args:
            result (dict): Whisper transcription result
        
        Returns:
            str: Formatted text with timestamps
        """
        output_lines = []
        
        for segment in result.get('segments', []):
            start = self._format_timestamp(segment['start'])
            end = self._format_timestamp(segment['end'])
            text = segment['text'].strip()
            output_lines.append(f"[{start} --> {end}] {text}")
        
        return '\n'.join(output_lines)
    
    def transcribe_with_details(
        self,
        file_path: str,
        task: str = 'transcribe',
        language: Optional[str] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Transcribe audio and return detailed information including timestamps and segments.
        
        Args:
            file_path (str): Path to the audio file
            task (str): Either 'transcribe' or 'translate'
            language (str, optional): Language code. Auto-detected if None.
            verbose (bool): Whether to print progress information
        
        Returns:
            dict: Dictionary containing:
                - text (str): Full transcription
                - language (str): Detected/specified language
                - segments (list): List of segments with timestamps
                - duration (float): Audio duration in seconds
        """
        # Validate inputs
        audio_path = self._validate_audio_file(file_path)
        
        if task != 'transcribe':
            task = 'transcribe'
        
        if verbose:
            print(f"\nProcessing: {audio_path.name}")
        
        try:
            language = language or self.language or 'en'
            result = self._transcribe_full(
                str(audio_path),
                task=task,
                language=language,
                verbose=verbose
            )
            
            # Extract detailed information
            segments = []
            for segment in result.get('segments', []):
                segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'start_formatted': self._format_timestamp(segment['start']),
                    'end_formatted': self._format_timestamp(segment['end']),
                    'text': segment['text'].strip()
                })
            
            return {
                'text': result['text'].strip(),
                'language': result.get('language', language),
                'segments': segments,
                'duration': segments[-1]['end'] if segments else 0.0
            }
        
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {str(e)}")
    
    def save_transcription(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        task: str = 'transcribe',
        language: Optional[str] = None,
        include_timestamps: bool = False,
        format: str = 'txt',
        verbose: bool = False
    ) -> str:
        """
        Transcribe audio and save the result to a file.
        
        Args:
            file_path (str): Path to the audio file
            output_path (str, optional): Path for output file. Auto-generated if None.
            task (str): Either 'transcribe' or 'translate'
            language (str, optional): Language code. Auto-detected if None.
            include_timestamps (bool): Whether to include timestamps
            format (str): Output format - 'txt' or 'json'
            verbose (bool): Whether to print progress information
        
        Returns:
            str: Path to the saved output file
        """
        audio_path = self._validate_audio_file(file_path)
        
        # Generate output path if not provided
        if output_path is None:
            suffix = '.json' if format == 'json' else '.txt'
            output_path = audio_path.with_suffix(suffix)
        
        output_path = Path(output_path)
        
        if format == 'json':
            # Get detailed transcription
            result = self.transcribe_with_details(
                file_path=str(audio_path),
                task=task,
                language=language,
                verbose=verbose
            )
            
            # Save as JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        
        else:  # txt format
            # Get text transcription
            text = self.transcribe_audio(
                file_path=str(audio_path),
                task=task,
                language=language,
                include_timestamps=include_timestamps,
                verbose=verbose
            )
            
            # Save as text
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
        
        if verbose:
            print(f"\nTranscription saved to: {output_path}")
        
        return str(output_path)

    def _transcribe_full(
        self,
        file_path: str,
        task: str,
        language: str,
        verbose: bool
    ) -> Dict[str, Any]:
        """
        Full Whisper transcription (slower) with timestamps.
        """
        return self.model.transcribe(
            file_path,
            task='transcribe',
            language=language,
            verbose=verbose,
            fp16=self.use_fp16,
            temperature=0.0,
            beam_size=1,
            condition_on_previous_text=False
        )

    def _transcribe_chunked(
        self,
        file_path: str,
        task: str,
        language: str,
        verbose: bool
    ) -> str:
        """
        Chunked transcription for faster latency. English-only, no translate mode.
        """
        audio = whisper.load_audio(file_path)
        chunk_samples = int(self.chunk_seconds * whisper.audio.SAMPLE_RATE)
        if chunk_samples <= 0:
            chunk_samples = int(15 * whisper.audio.SAMPLE_RATE)

        chunks = [audio[i:i + chunk_samples] for i in range(0, len(audio), chunk_samples)]
        if not chunks:
            return ""

        options = whisper.DecodingOptions(
            language=language,
            task='transcribe',
            fp16=self.use_fp16,
            temperature=0.0,
            beam_size=1,
            without_timestamps=True
        )

        max_workers = self._resolve_max_workers()
        results: List[str] = ["" for _ in range(len(chunks))]

        def run_chunk(idx: int, chunk_audio: np.ndarray) -> None:
            text = self._decode_chunk(chunk_audio, options)
            results[idx] = text

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(run_chunk, idx, chunk): idx
                    for idx, chunk in enumerate(chunks)
                }
                for future in as_completed(futures):
                    future.result()

            return " ".join([text for text in results if text]).strip()
        except Exception:
            # Fall back to the stable full-file path if chunked decode fails.
            full = self._transcribe_full(
                file_path=file_path,
                task=task,
                language=language,
                verbose=verbose
            )
            return full.get('text', '').strip()

    def _decode_chunk(self, chunk_audio: np.ndarray, options: whisper.DecodingOptions) -> str:
        chunk_audio = whisper.pad_or_trim(chunk_audio)
        mel = whisper.log_mel_spectrogram(chunk_audio).to(self.model.device)
        # Whisper decode is not thread-safe in some environments.
        with self.inference_lock:
            result = whisper.decode(self.model, mel, options)
        return result.text.strip()

    def _resolve_max_workers(self) -> int:
        if self.max_workers is not None and self.max_workers > 0:
            return self.max_workers
        if self.device == 'cuda':
            return 1
        cpu_count = os.cpu_count() or 2
        # Use a single worker on CPU to avoid concurrent model decode issues.
        return 1


# Convenience function for simple use cases
def transcribe_audio(
    file_path: str,
    model: str = 'base',
    task: str = 'transcribe',
    language: Optional[str] = None,
    device: str = 'cpu'
) -> str:
    """
    Simple function to transcribe an audio file.
    
    Args:
        file_path (str): Path to the audio file
        model (str): Whisper model to use ('tiny', 'base', 'small', 'medium', 'large')
        task (str): Either 'transcribe' (same language) or 'translate' (to English)
        language (str, optional): Language code (e.g., 'en', 'es'). Auto-detected if None.
        device (str): Device to run on ('cpu' or 'cuda')
    
    Returns:
        str: Transcribed text
    
    Example:
        >>> text = transcribe_audio('meeting.mp3')
        >>> print(text)
        This is the transcribed text from the audio file.
    """
    transcriber = AudioTranscriber(
        model_name=model,
        device=device,
        language=language or 'en',
        task='transcribe'
    )
    return transcriber.transcribe_audio(
        file_path=file_path,
        task=task,
        language=language,
        include_timestamps=False,
        verbose=False
    )


if __name__ == "__main__":
    # Example usage
    print("Audio Transcription Module")
    print("=" * 50)
    print("\nThis module provides audio-to-text conversion using OpenAI Whisper.")
    print("\nExample usage:")
    print("  from audio_transcriber import transcribe_audio, AudioTranscriber")
    print("  text = transcribe_audio('audio.mp3')")
    print("  print(text)")
