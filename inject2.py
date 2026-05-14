with open('d:/miniproject/meeting_pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Update record_and_process_meeting signature and logic
text = re.sub(
    r'def record_and_process_meeting\(self, person_id: str, person_name: str, image_path: str\) -> bool:', 
    r'def record_and_process_meeting(self, participants: list, image_path: str) -> bool:', 
    text
)
# Update log
text = re.sub(
    r'logger\.info\(f"Starting meeting for \{person_name\}"\)',
    r'logger.info(f"Starting meeting for { [p[\'name\'] for p in participants] }")',
    text
)
# Inside record_and_process_meeting, save for each participant or update database
text = re.sub(
    r'meeting_id = self\.database\.store_meeting\([^)]+\)',
    r'''for p in participants:
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
            meeting_id = "group_meeting"''',
    text,
    count=1
)

# Update run
text = re.sub(
    r'person_id, person_name, image_path, is_new = self\.capture_and_recognize_face\(\)\s+if person_id is None:\s+return',
    r'''participants = self.capture_and_recognize_participants()
        if not participants:
            return
        image_path = participants[0]["image"]''',
    text
)

text = re.sub(
    r'self\.display_person_info\(person_id, person_name, image_path, is_new\)',
    r'self.display_participants_info(participants)',
    text
)
text = re.sub(
    r'success = self\.record_and_process_meeting\(person_id, person_name, image_path\)',
    r'success = self.record_and_process_meeting(participants, image_path)',
    text
)

with open('d:/miniproject/meeting_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(text)
