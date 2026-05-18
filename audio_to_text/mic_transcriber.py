"""
Real-time Microphone Audio Transcription Module

This module captures audio from your microphone and transcribes it to text
using OpenAI Whisper. Transcription is fixed to English for low-latency output.

Author: Audio Transcription System
Date: 2026
"""

import os
import wave
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Literal

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    raise ImportError(
        "sounddevice is not installed. Please install it using: pip install sounddevice numpy"
    )

from audio_transcriber import AudioTranscriber


class MicrophoneTranscriber:
    """
    A class for recording audio from microphone and transcribing it in real-time.
    
    Attributes:
        transcriber: AudioTranscriber instance
        sample_rate (int): Audio sample rate (default: 16000 Hz)
        channels (int): Number of audio channels (default: 1 - mono)
    """
    
    def __init__(
        self,
        model_name: str = 'base',
        device: str = 'cpu',
        sample_rate: int = 16000,
        channels: int = 1
    ):
        """
        Initialize the MicrophoneTranscriber.
        
        Args:
            model_name (str): Whisper model to use ('tiny', 'base', 'small', 'medium', 'large')
            device (str): Device to run on ('cpu' or 'cuda')
            sample_rate (int): Audio sample rate in Hz (default: 16000)
            channels (int): Number of audio channels (default: 1 for mono)
        """
        self.transcriber = AudioTranscriber(model_name=model_name, device=device)
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = []
        self.is_recording = False
    
    def list_microphones(self) -> None:
        """List all available microphone devices."""
        print("\n" + "="*70)
        print("Available Audio Input Devices:")
        print("="*70)
        devices = sd.query_devices()
        
        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                print(f"[{idx}] {device['name']}")
                print(f"    Channels: {device['max_input_channels']}")
                print(f"    Sample Rate: {device['default_samplerate']} Hz")
        print("="*70)
    
    def record_audio(
        self,
        duration: Optional[int] = None,
        device_id: Optional[int] = None,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Record audio from the microphone.
        
        Args:
            duration (int, optional): Duration in seconds. If None, press Ctrl+C to stop.
            device_id (int, optional): Microphone device ID. If None, uses default.
            show_progress (bool): Show recording progress
        
        Returns:
            np.ndarray: Recorded audio data
        """
        print("\n" + "="*70)
        if duration:
            print(f"🎤 Recording for {duration} seconds...")
        else:
            print("🎤 Recording... Press Ctrl+C to stop")
        print("="*70)
        
        try:
            if duration:
                # Fixed duration recording
                audio_data = sd.rec(
                    int(duration * self.sample_rate),
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    device=device_id,
                    dtype='float32'
                )
                
                if show_progress:
                    # Show progress bar
                    import time
                    for i in range(duration):
                        print(f"Recording: {i+1}/{duration} seconds", end='\r')
                        time.sleep(1)
                    print()
                
                sd.wait()  # Wait until recording is finished
            else:
                # Continuous recording until Ctrl+C
                print("Speak into your microphone...")
                self.recording = []
                
                def callback(indata, frames, time, status):
                    if status:
                        print(f"Status: {status}")
                    self.recording.append(indata.copy())
                
                try:
                    with sd.InputStream(
                        samplerate=self.sample_rate,
                        channels=self.channels,
                        device=device_id,
                        callback=callback,
                        dtype='float32'
                    ):
                        print("Press Ctrl+C to stop recording...")
                        while True:
                            sd.sleep(100)  # Sleep in small intervals
                except KeyboardInterrupt:
                    print("\n✓ Recording stopped")
                
                # Concatenate all recorded chunks
                if len(self.recording) > 0:
                    audio_data = np.concatenate(self.recording, axis=0)
                else:
                    audio_data = np.array([]).reshape(0, self.channels)
        
        except KeyboardInterrupt:
            # Handle Ctrl+C during fixed duration recording
            print("\n✓ Recording interrupted")
            raise
        
        print(f"✓ Recorded {len(audio_data) / self.sample_rate:.2f} seconds of audio")
        return audio_data
    
    def save_audio_to_file(
        self,
        audio_data: np.ndarray,
        output_path: Optional[str] = None
    ) -> str:
        """
        Save recorded audio to a WAV file.
        
        Args:
            audio_data (np.ndarray): Audio data to save
            output_path (str, optional): Output file path. Auto-generated if None.
        
        Returns:
            str: Path to saved audio file
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"recording_{timestamp}.wav"
        
        # Convert float32 to int16
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        # Save as WAV file
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 2 bytes for int16
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())
        
        return output_path
    
    def transcribe_from_mic(
        self,
        duration: Optional[int] = None,
        device_id: Optional[int] = None,
        task: Literal['transcribe', 'translate'] = 'transcribe',
        language: Optional[str] = 'en',
        save_audio: bool = False,
        output_audio_path: Optional[str] = None,
        verbose: bool = True
    ) -> str:
        """
        Record audio from microphone and transcribe it.
        
        Args:
            duration (int, optional): Recording duration in seconds. None for manual stop.
            device_id (int, optional): Microphone device ID. None for default.
            task (str): Transcribe mode only (translate disabled).
            language (str, optional): Language code (defaults to 'en').
            save_audio (bool): Whether to save the recorded audio file
            output_audio_path (str, optional): Path to save audio. Auto-generated if None.
            verbose (bool): Show detailed progress
        
        Returns:
            str: Transcribed/translated text
        """
        # Record audio
        audio_data = self.record_audio(
            duration=duration,
            device_id=device_id,
            show_progress=verbose
        )
        
        # Save to temporary file for transcription
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Save audio data
            self.save_audio_to_file(audio_data, temp_path)
            
            # Transcribe
            if verbose:
                print(f"\n🔄 Processing audio ({task})...")
            
            text = self.transcriber.transcribe_audio(
                file_path=temp_path,
                task='transcribe',
                language=language or 'en',
                include_timestamps=False,
                verbose=verbose
            )
            
            # Save audio if requested
            if save_audio:
                if output_audio_path is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_audio_path = f"recording_{timestamp}.wav"
                
                import shutil
                shutil.copy(temp_path, output_audio_path)
                
                if verbose:
                    print(f"💾 Audio saved to: {output_audio_path}")
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return text
    
    def quick_transcribe(
        self,
        duration: int = 10,
        translate_to_english: bool = True
    ) -> str:
        """
        Quick transcription with default settings.
        
        Args:
            duration (int): Recording duration in seconds (default: 10)
            translate_to_english (bool): Ignored; English transcription is always used
        
        Returns:
            str: Transcribed text
        """
        print(f"\n🎤 Quick Transcription Mode")
        print(f"Duration: {duration} seconds")
        print("Mode: Transcribe (English only)")

        return self.transcribe_from_mic(
            duration=duration,
            task='transcribe',
            language='en',
            verbose=True
        )


def record_and_transcribe(
    duration: Optional[int] = None,
    translate_to_english: bool = True,
    model: str = 'base',
    save_audio: bool = False
) -> str:
    """
    Simple function to record from microphone and transcribe.
    
    Args:
        duration (int, optional): Recording duration in seconds. None for manual stop.
        translate_to_english (bool): Translate to English if True, transcribe if False
        model (str): Whisper model to use ('tiny', 'base', 'small', 'medium', 'large')
        save_audio (bool): Save the recorded audio file
    
    Returns:
        str: Transcribed/translated text
    
    Example:
        >>> text = record_and_transcribe(duration=10, translate_to_english=True)
        🎤 Recording for 10 seconds...
        ✓ Recorded 10.0 seconds of audio
        🔄 Processing audio (translate)...
        >>> print(text)
        This is the transcribed text from your microphone.
    """
    mic_transcriber = MicrophoneTranscriber(model_name=model, device='cpu')
    
    return mic_transcriber.transcribe_from_mic(
        duration=duration,
        task='transcribe',
        language='en',
        save_audio=save_audio,
        verbose=True
    )


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎤 Microphone Transcription Module")
    print("="*70)
    print("\nThis module captures audio from your microphone and transcribes it.")
    print("\nExample usage:")
    print("  from mic_transcriber import record_and_transcribe")
    print("  text = record_and_transcribe(duration=10, translate_to_english=True)")
    print("  print(text)")
    print("\n" + "="*70)
