import sys
import os

# Setup backend env
sys.path.insert(0, os.path.abspath('opencv'))
sys.path.insert(0, os.path.abspath('audio_to_text'))
sys.path.insert(0, os.path.abspath('.'))

from backend.routes.face_routes import init_components

try:
    print("Initialize components...")
    init_components()
    print("Done init.")
except Exception as e:
    import traceback
    traceback.print_exc()
