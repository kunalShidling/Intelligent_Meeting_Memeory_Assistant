"""
Face Recognition API Routes
Handles face detection, recognition, and registration.
"""

from flask import Blueprint, request, jsonify
import sys
import os
import base64
import tempfile
import logging
import threading
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from opencv.camera import Camera
from opencv.detector import FaceDetector
from opencv.embedder import FaceEmbedder
from opencv.database import FaceDatabase
from opencv.recognizer import FaceRecognizer
from opencv.face_tracker import FaceTracker
from opencv import config as opencv_config

logger = logging.getLogger(__name__)

# Create blueprint
face_bp = Blueprint('face', __name__, url_prefix='/api/face')

# Initialize components (shared across requests)
camera = None
detector = None
embedder = None
database = None
recognizer = None
tracker = None
components_lock = threading.Lock()

def init_components():
    """Initialize face recognition components."""
    global camera, detector, embedder, database, recognizer, tracker

    if all(component is not None for component in (detector, embedder, database, recognizer, camera, tracker)):
        return

    with components_lock:
        if all(component is not None for component in (detector, embedder, database, recognizer, camera, tracker)):
            return

        logger.info("Initializing face recognition components...")
        try:
            detector = FaceDetector()
            embedder = FaceEmbedder()
            database = FaceDatabase()
            database.connect()
            recognizer = FaceRecognizer(database)
            camera = Camera()
            tracker = FaceTracker()
            logger.info("Components initialized successfully")
        except Exception:
            # Reset globals to avoid partially initialized shared state.
            detector = None
            embedder = None
            database = None
            recognizer = None
            camera = None
            raise

def _encode_face_image(face_image):
    if face_image is None:
        return None
    try:
        import cv2
        success, buffer = cv2.imencode('.jpg', face_image)
        if not success:
            return None
        return 'data:image/jpeg;base64,' + base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        logger.debug(f"Failed to encode face image: {e}")
        return None

@face_bp.route('/capture', methods=['POST'])
def capture_face():
    """Capture face from camera."""
    try:
        init_components()

        if camera.cap is None or not camera.cap.isOpened():
            camera.open()

        # Capture frame from camera
        ret, frame = camera.read_frame()

        if not ret:
            return jsonify({'error': 'Failed to capture from camera'}), 500

        # Save to temp file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = os.path.join(tempfile.gettempdir(), f'capture_{timestamp}.jpg')

        import cv2
        cv2.imwrite(temp_path, frame)

        # Encode image to base64
        with open(temp_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')

        return jsonify({
            'success': True,
            'image': f'data:image/jpeg;base64,{img_data}',
            'path': temp_path
        })

    except Exception as e:
        logger.error(f"Error capturing face: {e}")
        return jsonify({'error': str(e)}), 500

@face_bp.route('/detect', methods=['POST'])
def detect_face():
    """Detect face in uploaded image."""
    try:
        init_components()

        data = request.json
        image_path = data.get('image_path')

        if not image_path:
            return jsonify({'error': 'No image path provided'}), 400

        # Detect face
        success, face, detection_info = detector.detect_and_extract_largest_face(image_path)

        if not success:
            return jsonify({
                'success': False,
                'error': 'No face detected'
            }), 200

        return jsonify({
            'success': True,
            'confidence': float(detection_info['confidence']),
            'box': detection_info.get('box')
        })

    except Exception as e:
        logger.error(f"Error detecting face: {e}")
        return jsonify({'error': str(e)}), 500

@face_bp.route('/recognize', methods=['POST'])
def recognize_face():
    """Recognize person from image."""
    temp_path = None
    try:
        init_components()

        data = request.get_json(silent=True) or {}
        image_path = data.get('image_path')
        image_data = data.get('image_data')

        if not image_path and not image_data:
            return jsonify({
                'success': False,
                'error': 'No image provided',
                'camera_detected': False
            }), 400

        if image_data:
            # It's a base64 image (data:image/jpeg;base64,...)
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            temp_path = os.path.join(tempfile.gettempdir(), f'recognize_{timestamp}.jpg')
            try:
                with open(temp_path, 'wb') as f:
                    f.write(base64.b64decode(image_data))
            except Exception as decode_error:
                logger.warning(f"Invalid image data supplied for recognition: {decode_error}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid camera image data',
                    'camera_detected': False
                }), 400
            image_path = temp_path

        # Detect all faces in frame
        faces = detector.detect_and_extract_all_faces(image_path)

        if not faces:
            return jsonify({
                'success': False,
                'error': 'No face detected in the camera frame. Make sure the camera is on and your face is visible.',
                'camera_detected': True,
                'person_detected': False,
                'requires_registration': False
            }), 200

        detections = []
        for face_img, detection_info in faces:
            detections.append({
                'face_image': face_img,
                'box': detection_info.get('box'),
                'confidence': detection_info.get('confidence')
            })

        tracked_faces = tracker.update(detections)
        results = []
        now = datetime.now().timestamp()

        for track in tracked_faces:
            if track.face_image is None:
                continue

            needs_embedding = tracker.should_refresh_embedding(track)
            if needs_embedding:
                success, embedding = embedder.embed_face(track.face_image)
                if success:
                    track.embedding = embedding
                    track.last_embedding_at = time.time()

            if track.embedding is None:
                track.name = 'Unknown'
                track.person_id = None
                track.confidence = None
                track.requires_registration = tracker.should_prompt_registration(track)
                if track.requires_registration:
                    tracker.mark_prompted(track)
            else:
                if needs_embedding or track.name is None:
                    recognized, name, confidence = recognizer.recognize(track.embedding)
                    if recognized and name:
                        track.name = name
                        track.confidence = float(confidence)
                        track.requires_registration = False
                        track.unknown_since = None
                        track.prompt_at = None
                    else:
                        track.name = 'Unregistered'
                        track.confidence = float(confidence) if confidence else None
                        if track.unknown_since is None:
                            track.unknown_since = now
                        track.requires_registration = tracker.should_prompt_registration(track)
                        if track.requires_registration:
                            tracker.mark_prompted(track)

            person = None
            person_id = None
            if track.name and track.name not in ('Unknown', 'Unregistered'):
                person = database.get_person_by_name(track.name)
                person_id = str(person['_id']) if person else None
                track.person_id = person_id

                if person_id and needs_embedding:
                    # Only save the profile photo once (first registration).
                    if not person or not person.get('image_path'):
                        logger.info("Person recognized with no profile image. Saving first-time image.")

                        import shutil
                        images_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'meeting_data', 'images')
                        os.makedirs(images_dir, exist_ok=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        persistent_image_path = os.path.join(images_dir, f'person_{person_id}_{timestamp}.jpg')
                        shutil.copy(image_path, persistent_image_path)

                        database.update_person_image(person_id, persistent_image_path)
                        person = database.get_person_by_name(track.name)

            person_image_base64 = None
            if person and person.get('image_path') and os.path.exists(person['image_path']):
                with open(person['image_path'], 'rb') as img_file:
                    person_image_base64 = 'data:image/jpeg;base64,' + base64.b64encode(img_file.read()).decode('utf-8')

            last_meeting = None
            if person_id:
                if track.last_meeting_at is None or (now - track.last_meeting_at) > 30:
                    meeting = database.get_last_meeting(person_id)
                    if meeting:
                        track.last_meeting = {
                            'timestamp': meeting['timestamp'].isoformat(),
                            'summary': meeting['summary'],
                            'transcript': meeting['transcript'][:200] + '...' if len(meeting['transcript']) > 200 else meeting['transcript']
                        }
                    else:
                        track.last_meeting = None
                    track.last_meeting_at = now

                last_meeting = track.last_meeting

            results.append({
                'track_id': track.track_id,
                'name': track.name,
                'confidence': track.confidence,
                'person_id': person_id,
                'requires_registration': track.requires_registration,
                'box': track.box,
                'face_image': _encode_face_image(track.face_image),
                'person_image': person_image_base64,
                'last_meeting': last_meeting,
                'camera_detected': True,
                'person_detected': True
            })

        return jsonify({
            'success': True,
            'faces': results,
            'camera_detected': True,
            'person_detected': True
        })

    except Exception as e:
        logger.error(f"Error recognizing face: {e}")
        return jsonify({
            'success': False,
            'error': f'Face recognition failed: {str(e)}',
            'camera_detected': False
        }), 500
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_path}: {e}")

@face_bp.route('/register', methods=['POST'])
def register_person():
    """Register new person."""
    try:
        init_components()

        data = request.json
        name = data.get('name')
        image_path = data.get('image_path')
        image_data = data.get('image_data')

        if not name or (not image_path and not image_data):
            return jsonify({'error': 'Name and image required'}), 400

        # If it's passed as image_path but happens to be base64
        if image_path and image_path.startswith('data:image'):
            image_data = image_path
            image_path = None

        if image_data:
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            temp_path = os.path.join(tempfile.gettempdir(), f'register_{timestamp}.jpg')
            with open(temp_path, 'wb') as f:
                f.write(base64.b64decode(image_data))
            image_path = temp_path

        # Detect face
        success, face, detection_info = detector.detect_and_extract_largest_face(image_path)

        if not success:
            return jsonify({'error': 'No face detected'}), 400

        # Generate embedding
        success, embedding = embedder.embed_face(face)

        if not success:
            return jsonify({'error': 'Failed to generate embedding'}), 500

        # Store in database
        success = database.store_embedding(name, embedding, check_duplicates=True)

        if not success:
            return jsonify({'error': 'Failed to store embedding (duplicate or database error)'}), 500

        # Get person ID
        person = database.get_person_by_name(name)
        person_id = str(person['_id']) if person else None

        # Copy image to meeting_data/images
        import shutil
        images_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'meeting_data', 'images')
        os.makedirs(images_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_image_path = os.path.join(images_dir, f'person_{person_id}_{timestamp}.jpg')
        shutil.copy(image_path, new_image_path)

        # Update person image path
        database.update_person_image(person_id, new_image_path)

        if recognizer:
            recognizer.invalidate_cache()
        if tracker:
            tracker.reset()

        return jsonify({
            'success': True,
            'name': name,
            'person_id': person_id,
            'image_path': new_image_path
        })

    except Exception as e:
        logger.error(f"Error registering person: {e}")
        return jsonify({'error': str(e)}), 500

@face_bp.route('/camera/status', methods=['GET'])
def camera_status():
    """Check camera status."""
    try:
        init_components()

        if camera.cap is None or not camera.cap.isOpened():
            camera.open()

        ret, _ = camera.read_frame()

        return jsonify({
            'available': ret,
            'status': 'active' if ret else 'unavailable'
        })

    except Exception as e:
        return jsonify({
            'available': False,
            'status': 'error',
            'error': str(e)
        }), 500

@face_bp.route('/refresh', methods=['POST'])
def refresh_detection():
    """Refresh face detection pipeline without restarting the app."""
    try:
        init_components()

        if tracker:
            tracker.reset()
        if recognizer:
            recognizer.invalidate_cache()
        if camera:
            camera.last_frame_hash = None
            if camera.cap is None or not camera.cap.isOpened():
                camera.open()

        return jsonify({
            'success': True,
            'message': 'Face detection refreshed'
        })

    except Exception as e:
        logger.error(f"Error refreshing face detection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
