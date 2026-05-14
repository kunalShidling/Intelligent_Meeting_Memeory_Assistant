with open('d:/miniproject/meeting_pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

lines = text.split('\n')
new_lines = []
skip = False
for i, line in enumerate(lines):
    if "for p in participants:" in line:
        skip = True
        new_lines.append("            for p in participants:")
        new_lines.append("                self.database.store_meeting(")
        new_lines.append("                    person_id=p['id'],")
        new_lines.append("                    person_name=p['name'],")
        new_lines.append("                    image_path=image_path,")
        new_lines.append("                    audio_path=audio_path,")
        new_lines.append("                    transcript_path=transcript_path,")
        new_lines.append("                    transcript=transcript,")
        new_lines.append("                    summary_path=summary_path,")
        new_lines.append("                    summary=summary")
        new_lines.append("                )")
        new_lines.append("            meeting_id = 'group_meeting'")
    elif skip and "meeting_id = " in line and "group_meeting" in line:
        skip = False
    elif not skip:
        # Also clean up the messed up person_name occurrences we broke
        if "audio_filename = f\"meeting_{group_names.replace" in line:
            line = "            group_names = '_'.join([p['name'].replace(' ', '_') for p in participants[:3]])"
            new_lines.append(line)
            new_lines.append(f"            audio_filename = f'meeting_{{group_names}}_{{timestamp}}.wav'")
        elif "transcript_filename =" in line and "group_names" in line:
            new_lines.append(f"            transcript_filename = f'transcript_{{group_names}}_{{timestamp}}.txt'")
        elif "summary_filename =" in line and "group_names" in line:
            new_lines.append(f"            summary_filename = f'summary_{{group_names}}_{{timestamp}}.txt'")
        else:
            new_lines.append(line)

with open('d:/miniproject/meeting_pipeline.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))
