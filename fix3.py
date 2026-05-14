def get_run_part():
    return '''
    def run(self):
        """Run the complete meeting pipeline."""
        try:
            # Step 1: Face Recognition
            participants = self.capture_and_recognize_participants()
            if not participants: return
            
            image_path = participants[0]["image"]
            
            # Step 2: Display Info
            self.display_participants_info(participants)
            
            # Step 3-6: Record, Transcribe, Summarize, Store
            success = self.record_and_process_meeting(participants, image_path)
            
            if success:
                print("\\n" + "=" * 80)
                print("✓ MEETING PIPELINE COMPLETED SUCCESSFULLY")
                print("=" * 80)
            else:
                print("\\n" + "=" * 80)
                print("⚠️ MEETING PIPELINE COMPLETED WITH ERRORS")
                print("=" * 80)
                
        except KeyboardInterrupt:
            print("\\n\\n⚠️ Pipeline interrupted by user")
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            print(f"\\n❌ Error: {e}")
        finally:
            self.cleanup()
'''

with open('d:/miniproject/meeting_pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
# Remove everything from def run(self) to the end, excluding cleanup if possible, 
# actually cleanup is just cleanup, let's replace from def run(self): to before cleanup.
text = re.sub(r'    def run\(self\).*?(?=    def cleanup)', get_run_part(), text, flags=re.DOTALL)

with open('d:/miniproject/meeting_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(text)
