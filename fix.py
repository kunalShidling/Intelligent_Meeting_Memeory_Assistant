with open('d:/miniproject/meeting_pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
text = re.sub(
    r"audio_filename = f\"meeting_\{person_name\.replace[^}]*\}_\w+\.wav\"",
    r"group_names = '_'.join([p['name'].replace(' ', '_') for p in participants[:3]])\n        audio_filename = f\"meeting_{group_names}_{timestamp}.wav\"",
    text
)
# For summary and transcript paths
text = re.sub(r'person_name', 'group_names', text)
text = re.sub(r'person_id', '",".join([p["id"] for p in participants])', text)
with open('d:/miniproject/meeting_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(text)
