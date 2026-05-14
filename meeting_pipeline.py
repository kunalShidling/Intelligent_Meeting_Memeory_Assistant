"""
Integrated Meeting Pipeline
Combines face recognition with audio transcription and summarization.

Workflow:
1. Detect and recognize person using camera
2. Display person info and last meeting summary
3. Record conversation audio
4. Transcribe audio to text
5. Summarize conversation
6. Store meeting record in database
"""

import os
import sys
import cv2
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict

# Add module paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'opencv'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'audio_to_text'))

# Import opencv modules
from opencv.camera import Camera
from opencv.detector import FaceDetector
from opencv.embedder import FaceEmbedder
from opencv.database import FaceDatabase
from opencv.recognizer import FaceRecognizer
import opencv.config as opencv_config

# Import audio modules
from audio_to_text.mic_transcriber import MicrophoneTranscriber
from audio_to_text.text_summarizer import TextSummarizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class MeetingPipeline:
    """
    Integrated pipeline for face recognition and meeting recording.
    """
    
    def __init__(self):
        """Initialize all components."""
        logger.info("=" * 80)
        logger.info("INITIALIZING MEETING PIPELINE")
        logger.info("=" * 80)
        
        # Storage directories
        self.storage_dir = Path(__file__).parent / "meeting_data"
        self.images_dir = self.storage_dir / "images"
        self.audio_dir = self.storage_dir / "audio"
        self.transcripts_dir = self.storage_dir / "transcripts"
        
        # Create directories
        for directory in [self.images_dir, self.audio_dir, self.transcripts_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.camera = None
        self.detector = None
        self.embedder = None
        self.database = None
        self.recognizer = None
        self.mic_transcriber = None
        self.summarizer = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all system components."""
        try:
            # Face recognition components
            logger.info("Initializing camera...")
            self.camera = Camera()
            
            logger.info("Initializing face detector...")
            self.detector = FaceDetector()
            
            logger.info("Initializing face embedder...")
            self.embedder = FaceEmbedder()
            
            logger.info("Initializing database...")
            self.database = FaceDatabase()
            if not self.database.connect():
                raise Exception("Failed to connect to database")
            
            logger.info("Initializing face recognizer...")
            self.recognizer = FaceRecognizer(self.database)
            
            # Audio components
            logger.info("Initializing microphone transcriber...")
            self.mic_transcriber = MicrophoneTranscriber(
                model_name='base',
                device='cpu'
            )
            
            logger.info("Initializing text summarizer...")
            self.summarizer = TextSummarizer()
            
            logger.info("✓ All components initialized successfully")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def capture_and_recognize_participants(self) -> list:
        logger.info("
" + "=" * 80)
        logger.info("FACE RECOGNITION (PARTICIPANTS)")
        logger.info("=" * 80)
        
        if not self.camera.open(): return []
        captured_image_path = None
        while True:
            success, frame = self.camera.read_frame()
            if not success: break
            detections = self.detector.detect_faces(frame)
            display_frame = frame.copy()
            for i, d in enumerate(detections):
                x, y, w, h = d['box']
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0,255,0), 2)
            cv2.imshow("Face Capture", display_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('c'):
                captured_image_path = str(self.images_dir / f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                cv2.imwrite(captured_image_path, frame)
                break
            elif key == ord('q'): break
        cv2.destroyAllWindows()
        
        if not captured_image_path: return []
        
        faces_data = self.detector.detect_and_extract_all_faces(captured_image_path)
        participants = []
        for i, (face_img, detection_info) in enumerate(faces_data):
            embedding = self.embedder.generate_embedding(face_img)
            if embedding is None: continue
            best_match_name, similarity, _ = self.recognizer.find_best_match(embedding)
            
            if best_match_name and similarity >= opencv_config.RECOGNITION_THRESHOLD:
                p_rec = self.database.get_person_by_name(best_match_name)
                participants.append({"id": str(p_rec['_id']), "name": best_match_name, "image": captured_image_path, "is_new": False})
            else:
                cv2.imshow("New", face_img)
                cv2.waitKey(100)
                name = input("Enter name: ").strip()
                cv2.destroyAllWindows()
                if name and self.database.store_embedding(name, embedding, False):
                    p_rec = self.database.get_person_by_name(name)
                    participants.append({"id": str(p_rec['_id']), "name": name, "image": captured_image_path, "is_new": True})
        return participants
    def display_participants_info(self, participants: list):
        for p in participants:
            print(f"
--- {p['name']} ---")
            if not p['is_new']:
                lm = self.database.get_last_meeting(p['id'])
                if lm: print(f"Last Meeting:
{lm['summary']}")
    def record_and_process_meeting(self, participants: list, image_path: str) -> bool:
        """
        Record conversation, transcribe, summarize, and store.
        
        Args:
            person_id: Person's database ID
            person_name: Person's name
            image_path: Path to person's image
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: MEETING RECORDING")
        logger.info("=" * 80)
        
        print(f"\n{'=' * 80}")
        print("MEETING RECORDING")
        print(f"{'=' * 80}")
        print("Options:")
        print("  1. Record conversation for fixed duration")
        print("  2. Record until manually stopped (Ctrl+C)")
        print("  3. Skip recording")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '3':
            logger.info("Recording skipped by user")
            print("Recording skipped.")
            return True
        
        # Prepare audio file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        group_names = '_'.join([p['name'].replace(' ', '_') for p in participants[:3]])
        audio_filename = f\"meeting_{group_names}_{timestamp}.wav\"
        audio_path = str(self.audio_dir / audio_filename)
        
        # Record audio
        try:
            if choice == '1':
                duration = int(input("Enter recording duration in seconds: "))
                logger.info(f"Recording for {duration} seconds...")
                audio_data = self.mic_transcriber.record_audio(duration=duration)
            else:
                logger.info("Recording until Ctrl+C...")
                audio_data = self.mic_transcriber.record_audio(duration=None)
            
            # Save audio
            self.mic_transcriber.save_audio_to_file(audio_data, audio_path)
            print(f"✓ Audio saved: {audio_filename}")
            
        except KeyboardInterrupt:
            print("\n\n⚠ Recording interrupted by user")
            # Still try to save what was recorded
            try:
                if len(self.mic_transcriber.recording) > 0:
                    import numpy as np
                    audio_data = np.concatenate(self.mic_transcriber.recording)
                    self.mic_transcriber.save_audio_to_file(audio_data, audio_path)
                    print(f"✓ Partial audio saved: {audio_filename}")
                else:
                    logger.warning("No audio data to save")
                    return False
            except Exception as e:
                logger.error(f"Failed to save interrupted recording: {e}")
                return False
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            print(f"❌ Recording failed: {e}")
            return False
        
        # Transcribe audio
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: TRANSCRIPTION")
        logger.info("=" * 80)
        
        print(f"\n{'=' * 80}")
        print("TRANSCRIPTION")
        print(f"{'=' * 80}")
        print("Transcribing audio to text...")
        
        try:
            transcript = self.mic_transcriber.transcriber.transcribe_audio(
                audio_path,
                task='transcribe'
            )
            
            print(f"✓ Transcription complete ({len(transcript)} characters)")
            print(f"\nTranscript Preview:")
            print("-" * 80)
            print(transcript[:500] + ("..." if len(transcript) > 500 else ""))
            print("-" * 80)
            
            # Save transcript
            transcript_filename = f"transcript_{person_name.replace(' ', '_')}_{timestamp}.txt"
            transcript_path = str(self.transcripts_dir / transcript_filename)
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(transcript)
            logger.info(f"Transcript saved: {transcript_path}")
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            print(f"❌ Transcription failed: {e}")
            return False
        
        # Summarize conversation
        logger.info("\n" + "=" * 80)
        logger.info("STEP 5: SUMMARIZATION")
        logger.info("=" * 80)
        
        print(f"\n{'=' * 80}")
        print("SUMMARIZATION")
        print(f"{'=' * 80}")
        print("Generating summary...")
        
        try:
            summary = self.summarizer.summarize_to_bullets(
                transcript,
                max_bullets=10,
                verbose=False
            )
            
            print(f"✓ Summary generated")
            print(f"\nMeeting Summary:")
            print("=" * 80)
            print(summary)
            print("=" * 80)
            
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            print(f"❌ Summarization failed: {e}")
            summary = "Summary generation failed"
        
        # Store meeting in database
        logger.info("\n" + "=" * 80)
        logger.info("STEP 6: STORING MEETING")
        logger.info("=" * 80)
        
        print(f"\n{'=' * 80}")
        print("STORING MEETING")
        print(f"{'=' * 80}")
        
        try:
            meeting_id = "group_meeting"
            for p in participants:
                self.database.store_meeting(
                    person_id=p['id'],
                    person_name=p['name'],
                    image_path=image_path,
                    audio_path=audio_path,
                    transcript_path=transcript_path,
                    transcript=transcript,
                    summary_path=summary_path,
                    summary=summary
                )
            
            if meeting_id:
                print(f"✓ Meeting stored successfully")
                print(f"  Meeting ID: {meeting_id}")
                logger.info(f"Meeting stored with ID: {meeting_id}")
                return True
            else:
                print("❌ Failed to store meeting")
                logger.error("Failed to store meeting")
                return False
                
        except Exception as e:
            logger.error(f"Error storing meeting: {e}")
            print(f"❌ Error storing meeting: {e}")
            return False
    
    def run(self):
        """
        Run the complete meeting pipeline.
        """
        try:
            # Step 1: Face Recognition
            person_id, person_name, image_path, is_new = self.capture_and_recognize_face()
            
            if person_id is None:
                print("\n❌ Pipeline terminated - No person identified")
                return
            
            # Step 2: Display Person Info
            self.display_participants_info(participants)
            
            # Step 3-6: Record and Process Meeting
            success = self.record_and_process_meeting(participants, image_path)
            
            if success:
                print("\n" + "=" * 80)
                print("✓ MEETING PIPELINE COMPLETED SUCCESSFULLY")
                print("=" * 80)
                logger.info("Pipeline completed successfully")
            else:
                print("\n" + "=" * 80)
                print("⚠ MEETING PIPELINE COMPLETED WITH ERRORS")
                print("=" * 80)
                logger.warning("Pipeline completed with errors")
            
        except KeyboardInterrupt:
            print("\n\n⚠ Pipeline interrupted by user")
            logger.info("Pipeline interrupted by user")
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            print(f"\n❌ Pipeline error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources."""
        logger.info("\nCleaning up resources...")
        
        if self.camera:
            self.camera.close()
        
        if self.database:
            self.database.disconnect()
        
        cv2.destroyAllWindows()
        
        logger.info("✓ Cleanup complete")


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("INTEGRATED MEETING PIPELINE")
    print("Face Recognition + Audio Transcription + Summarization")
    print("=" * 80)
    print("\nThis pipeline will:")
    print("  1. Recognize your face using the camera")
    print("  2. Show previous meeting summary (if returning)")
    print("  3. Record your conversation")
    print("  4. Transcribe the audio to text")
    print("  5. Generate a meeting summary")
    print("  6. Store everything in the database")
    print("\nMake sure you have:")
    print("  ✓ Camera connected")
    print("  ✓ Microphone connected")
    print("  ✓ MongoDB running")
    print("  ✓ Groq API key configured")
    print("=" * 80)
    
    input("\nPress Enter to start...")
    
    pipeline = MeetingPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
