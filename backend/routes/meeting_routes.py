"""
Meeting Management API Routes
Handles complete meeting pipeline and meeting history.
"""

from flask import Blueprint, request, jsonify
import sys
import os
import logging
from datetime import datetime
from bson import ObjectId

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from opencv.database import FaceDatabase
from audio_to_text.mic_transcriber import MicrophoneTranscriber
from audio_to_text.audio_transcriber import AudioTranscriber
from audio_to_text.text_summarizer import TextSummarizer

logger = logging.getLogger(__name__)

# Create blueprint
meeting_bp = Blueprint('meeting', __name__, url_prefix='/api/meeting')

# Global instances
database = None
mic_transcriber = None
audio_transcriber = None
text_summarizer = None

def init_components():
    """Initialize meeting components."""
    global database, mic_transcriber, audio_transcriber, text_summarizer

    if database is None:
        logger.info("Initializing meeting components...")
        database = FaceDatabase()
        database.connect()
        mic_transcriber = MicrophoneTranscriber(model_name='base', device='cpu')
        audio_transcriber = AudioTranscriber(model_name='base', device='cpu')
        text_summarizer = TextSummarizer()
        logger.info("Meeting components initialized successfully")

@meeting_bp.route('/start', methods=['POST'])
def start_meeting():
    """Start a complete meeting (record, transcribe, summarize, store)."""
    try:
        init_components()

        data = request.json
        person_id = data.get('person_id')
        person_name = data.get('person_name')
        duration = data.get('duration', 30)
        image_path = data.get('image_path')

        if not person_id or not person_name:
            return jsonify({'error': 'Person ID and name required'}), 400

        logger.info(f"Starting meeting for {person_name} (duration: {duration}s)")

        # Prepare directories
        audio_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'meeting_data', 'audio')
        os.makedirs(audio_dir, exist_ok=True)

        # Record and transcribe
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f'meeting_{person_id}_{timestamp}.wav'
        audio_path = os.path.join(audio_dir, audio_filename)

        logger.info("Recording audio...")
        transcript = mic_transcriber.transcribe_from_mic(
            duration=duration,
            save_audio=True,
            output_audio_path=audio_path,
            verbose=True
        )

        logger.info("Generating summary...")
        summary = text_summarizer.summarize_to_bullets(
            text=transcript,
            max_bullets=10,
            verbose=True
        )

        # Store meeting in database
        logger.info("Storing meeting in database...")
        meeting_id = database.store_meeting(
            person_id=person_id,
            person_name=person_name,
            transcript=transcript,
            summary=summary,
            audio_path=audio_path,
            image_path=image_path
        )

        logger.info(f"Meeting completed successfully: {meeting_id}")

        return jsonify({
            'success': True,
            'meeting_id': meeting_id,
            'transcript': transcript,
            'summary': summary,
            'audio_path': audio_path,
            'duration': duration
        })

    except Exception as e:
        logger.error(f"Error starting meeting: {e}")
        return jsonify({'error': str(e)}), 500

@meeting_bp.route('/create', methods=['POST'])
def create_meeting():
    """Create meeting from existing audio/transcript."""
    try:
        init_components()

        data = request.json
        person_id = data.get('person_id')
        person_name = data.get('person_name')
        transcript = data.get('transcript')
        summary = data.get('summary')
        audio_path = data.get('audio_path')
        image_path = data.get('image_path')

        if not person_id or not person_name or not transcript:
            return jsonify({'error': 'Person ID, name, and transcript required'}), 400

        # Generate summary if not provided
        if not summary:
            logger.info("Generating summary...")
            summary = text_summarizer.summarize_to_bullets(
                text=transcript,
                max_bullets=10,
                verbose=True
            )

        # Store meeting
        
        # If image_path is a base64 string, save it correctly 
        if image_path and image_path.startswith('data:image'):
            # Save properly in meeting_data/images
            try:
                import base64
                from datetime import datetime
                import os
                
                parts = image_path.split(',')
                data_b64 = parts[1] if len(parts) > 1 else parts[0]
                
                images_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'meeting_data', 'images')
                os.makedirs(images_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_image_path = os.path.join(images_dir, f'meeting_{person_name}_{timestamp}.jpg')
                
                with open(new_image_path, 'wb') as f:
                    f.write(base64.b64decode(data_b64))
                
                image_path = new_image_path
            except Exception as e:
                logger.error(f"Failed to save base64 image: {e}")
                image_path = "" # Nullify or let it be

        meeting_id = database.store_meeting(
            person_id=person_id,
            person_name=person_name,
            transcript=transcript,
            summary=summary,
            audio_path=audio_path,
            image_path=image_path
        )

        return jsonify({
            'success': True,
            'meeting_id': meeting_id
        })

    except Exception as e:
        logger.error(f"Error creating meeting: {e}")
        return jsonify({'error': str(e)}), 500

@meeting_bp.route('/<meeting_id>', methods=['GET'])
def get_meeting(meeting_id):
    """Get meeting details by ID."""
    try:
        init_components()

        from bson import ObjectId

        meeting = database.meetings_collection.find_one({'_id': ObjectId(meeting_id)})

        if not meeting:
            return jsonify({'error': 'Meeting not found'}), 404

        # Convert ObjectId to string
        meeting['_id'] = str(meeting['_id'])
        meeting['person_id'] = str(meeting['person_id'])
        meeting['timestamp'] = meeting['timestamp'].isoformat()

        return jsonify({
            'success': True,
            'meeting': meeting
        })

    except Exception as e:
        logger.error(f"Error getting meeting: {e}")
        return jsonify({'error': str(e)}), 500

@meeting_bp.route('/list', methods=['GET'])
def list_meetings():
    """Get all meetings (paginated)."""
    try:
        init_components()

        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit

        # Get all meetings sorted by timestamp
        meetings = list(database.meetings_collection.find()
                       .sort('timestamp', -1)
                       .skip(skip)
                       .limit(limit))

        total = database.meetings_collection.count_documents({})

        # Convert ObjectIds to strings
        for meeting in meetings:
            meeting['_id'] = str(meeting['_id'])
            meeting['person_id'] = str(meeting['person_id'])
            meeting['timestamp'] = meeting['timestamp'].isoformat()

        return jsonify({
            'success': True,
            'meetings': meetings,
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })

    except Exception as e:
        logger.error(f"Error listing meetings: {e}")
        return jsonify({'error': str(e)}), 500

@meeting_bp.route('/person/<person_id>', methods=['GET'])
def get_person_meetings(person_id):
    """Get all meetings for a specific person."""
    try:
        init_components()

        meetings = database.get_all_meetings(person_id)

        # Convert ObjectIds and timestamps
        for meeting in meetings:
            meeting['_id'] = str(meeting['_id'])
            meeting['person_id'] = str(meeting['person_id'])
            meeting['timestamp'] = meeting['timestamp'].isoformat()

        return jsonify({
            'success': True,
            'meetings': meetings,
            'total': len(meetings)
        })

    except Exception as e:
        logger.error(f"Error getting person meetings: {e}")
        return jsonify({'error': str(e)}), 500

@meeting_bp.route('/<meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    """Delete a meeting."""
    try:
        init_components()

        from bson import ObjectId

        result = database.meetings_collection.delete_one({'_id': ObjectId(meeting_id)})

        if result.deleted_count == 0:
            return jsonify({'error': 'Meeting not found'}), 404

        return jsonify({
            'success': True,
            'message': 'Meeting deleted'
        })

    except Exception as e:
        logger.error(f"Error deleting meeting: {e}")
        return jsonify({'error': str(e)}), 500

@meeting_bp.route('/search', methods=['GET'])
def search_meetings():
    """Search meetings by keyword."""
    try:
        init_components()

        keyword = request.args.get('q', '')

        if not keyword:
            return jsonify({'error': 'Search keyword required'}), 400

        # Search in transcript and summary
        meetings = list(database.meetings_collection.find({
            '$or': [
                {'transcript': {'$regex': keyword, '$options': 'i'}},
                {'summary': {'$regex': keyword, '$options': 'i'}},
                {'person_name': {'$regex': keyword, '$options': 'i'}}
            ]
        }).sort('timestamp', -1))

        # Convert ObjectIds
        for meeting in meetings:
            meeting['_id'] = str(meeting['_id'])
            meeting['person_id'] = str(meeting['person_id'])
            meeting['timestamp'] = meeting['timestamp'].isoformat()

        return jsonify({
            'success': True,
            'meetings': meetings,
            'total': len(meetings)
        })

    except Exception as e:
        logger.error(f"Error searching meetings: {e}")
        return jsonify({'error': str(e)}), 500
