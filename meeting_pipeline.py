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
    
    def capture_and_recognize_face(self) -> Tuple[Optional[str], Optional[str], Optional[str], bool]:
        """
        Capture face from camera and recognize person.
        
        Returns:
            Tuple: (person_id, person_name, image_path, is_new_person)
        """
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: FACE RECOGNITION")
        logger.info("=" * 80)
        
        print("\n📷 Starting camera for face detection...")
        print("Position yourself in front of the camera")
        print("Press 'c' to capture your face")
        print("Press 'q' to quit\n")
        
        # Open camera
        if not self.camera.open():
            logger.error("Failed to open camera")
            print("❌ Failed to open camera. Please check your camera connection.")
            return None, None, None, False
        
        captured_image_path = None
        
        while True:
            # Read frame from camera
            success, frame = self.camera.read_frame()
            if not success or frame is None:
                logger.error("Failed to read frame from camera")
                return None, None, None, False
            
            # Detect faces in frame
            detections = self.detector.detect_faces(frame)
            
            # Draw rectangles around detected faces
            display_frame = frame.copy()
            for detection in detections:
                box = detection['box']
                x, y, w, h = box
                confidence = detection['confidence']
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(display_frame, f"Face {confidence:.2f}", (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Display instructions
            cv2.putText(display_frame, "Press 'c' to capture | 'q' to quit",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow("Face Recognition - Capture", display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('c'):
                # Capture current frame
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                captured_image_path = str(self.images_dir / f"capture_{timestamp}.jpg")
                cv2.imwrite(captured_image_path, frame)
                logger.info(f"Frame captured: {captured_image_path}")
                break
            elif key == ord('q'):
                logger.info("Face capture cancelled by user")
                cv2.destroyAllWindows()
                return None, None, None, False
        
        cv2.destroyAllWindows()
        
        # Process captured face
        if captured_image_path is None:
            return None, None, None, False
        
        # Detect and extract face
        logger.info("Detecting face in captured image...")
        success, face_img, detection_info = self.detector.detect_and_extract_largest_face(captured_image_path)
        
        if not success:
            logger.error("No face detected in captured image")
            print("❌ No face detected. Please try again.")
            return None, None, None, False
        
        print(f"✓ Face detected with confidence: {detection_info['confidence']:.2f}")
        
        # Generate embedding
        logger.info("Generating face embedding...")
        embedding = self.embedder.generate_embedding(face_img)
        
        if embedding is None:
            logger.error("Failed to generate embedding")
            print("❌ Failed to generate face embedding. Please try again.")
            return None, None, None, False
        
        print("✓ Face embedding generated")
        
        # Try to recognize person
        logger.info("Searching for matching face in database...")
        best_match_name, similarity, all_matches = self.recognizer.find_best_match(embedding)
        
        if best_match_name and similarity >= opencv_config.RECOGNITION_THRESHOLD:
            # Person recognized
            logger.info(f"Person recognized: {best_match_name} (similarity: {similarity:.4f})")
            print(f"\n✓ Person Recognized: {best_match_name}")
            print(f"  Similarity: {similarity:.2%}")
            
            # Get person record
            person_record = self.database.get_person_by_name(best_match_name)
            person_id = str(person_record['_id'])
            
            # Update embedding and image if confidence is high enough
            if opencv_config.UPDATE_THRESHOLD <= similarity < opencv_config.DUPLICATE_THRESHOLD:
                logger.info(f"High confidence ({similarity:.4f}). Updating embedding and image for {best_match_name}.")
                self.database.update_person_embedding_and_image(person_id, embedding, captured_image_path)
                
                # Clear recognizer cache to ensure subsequent match updates use the new embedding
                self.recognizer._cached_records = None
            else:
                # Otherwise, just update the image to the most recent one
                self.database.update_person_image(person_id, captured_image_path)
            
            return person_id, best_match_name, captured_image_path, False
        else:
            # New person
            logger.info("No match found - new person")
            print("\n👤 New person detected!")
            
            # Get name
            name = input("Please enter your name: ").strip()
            if not name:
                logger.error("No name provided")
                return None, None, None, False
            
            # Store in database
            logger.info(f"Registering new person: {name}")
            if self.database.store_embedding(name, embedding, check_duplicates=False):
                person_record = self.database.get_person_by_name(name)
                person_id = str(person_record['_id'])
                
                # Update with image path
                self.database.update_person_image(person_id, captured_image_path)
                
                print(f"✓ Registered: {name}")
                return person_id, name, captured_image_path, True
            else:
                logger.error("Failed to register new person")
                return None, None, None, False
    
    def display_person_info(self, person_id: str, person_name: str, image_path: str, is_new: bool):
        """
        Display person information and last meeting summary.
        
        Args:
            person_id: Person's database ID
            person_name: Person's name
            image_path: Path to person's image
            is_new: Whether this is a new person
        """
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: PERSON INFORMATION")
        logger.info("=" * 80)
        
        print(f"\n{'=' * 80}")
        print(f"PERSON INFORMATION")
        print(f"{'=' * 80}")
        print(f"Name: {person_name}")
        print(f"ID: {person_id}")
        print(f"Status: {'New Registration' if is_new else 'Returning'}")
        print(f"{'=' * 80}")
        
        if not is_new:
            # Get last meeting
            last_meeting = self.database.get_last_meeting(person_id)
            
            if last_meeting:
                print(f"\n📝 LAST MEETING SUMMARY")
                print(f"{'=' * 80}")
                print(f"Date: {last_meeting['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"\nSummary:")
                print(last_meeting['summary'])
                print(f"{'=' * 80}")
            else:
                print("\n(No previous meetings recorded)")
        
        # Display image
        if os.path.exists(image_path):
            img = cv2.imread(image_path)
            if img is not None:
                cv2.imshow(f"Recognized: {person_name}", img)
                print("\n[Image displayed in window - Press any key to continue]")
                cv2.waitKey(0)
                cv2.destroyAllWindows()
    
    def record_and_process_meeting(self, person_id: str, person_name: str, image_path: str) -> bool:
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
        audio_filename = f"meeting_{person_name.replace(' ', '_')}_{timestamp}.wav"
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
            meeting_id = self.database.store_meeting(
                person_id=person_id,
                person_name=person_name,
                transcript=transcript,
                summary=summary,
                audio_path=audio_path,
                image_path=image_path
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
            self.display_person_info(person_id, person_name, image_path, is_new)
            
            # Step 3-6: Record and Process Meeting
            success = self.record_and_process_meeting(person_id, person_name, image_path)
            
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
