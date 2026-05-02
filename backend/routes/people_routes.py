"""
People Management API Routes
Handles person records and profiles.
"""

from flask import Blueprint, request, jsonify
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from opencv.database import FaceDatabase

logger = logging.getLogger(__name__)

# Create blueprint
people_bp = Blueprint('people', __name__, url_prefix='/api/people')

# Global instance
database = None

def init_database():
    """Initialize database connection."""
    global database

    if database is None:
        logger.info("Initializing database...")
        database = FaceDatabase()
        database.connect()
        logger.info("Database initialized successfully")

@people_bp.route('/', methods=['GET'])
def get_all_people():
    """Get all registered people."""
    try:
        init_database()

        people = database.get_all_embeddings()

        # Add meeting count for each person
        valid_people = []
        for person in people:
            # Skip people without valid _id
            if '_id' not in person or not person['_id']:
                logger.warning(f"Skipping person without valid _id: {person.get('name', 'Unknown')}")
                continue

            person_id = str(person['_id'])
            meetings = database.get_all_meetings(person_id)
            person['meeting_count'] = len(meetings)
            person['_id'] = person_id
            if 'date' in person:
                person['date'] = person['date'].isoformat()

            import base64
            if person.get('image_path') and os.path.exists(person['image_path']):
                try:
                    with open(person['image_path'], 'rb') as img_file:
                       person['person_image'] = 'data:image/jpeg;base64,' + base64.b64encode(img_file.read()).decode('utf-8')
                except Exception as img_err:
                    logger.warning(f"Failed to read image for {person_id}: {img_err}")

            # Don't send embedding (too large)
            if 'embedding' in person:
                del person['embedding']
            valid_people.append(person)

        return jsonify({
            'success': True,
            'people': valid_people,
            'total': len(valid_people)
        })

    except Exception as e:
        logger.error(f"Error getting people: {e}")
        return jsonify({'error': str(e)}), 500

@people_bp.route('/<person_id>', methods=['GET'])
def get_person(person_id):
    """Get person details by ID."""
    try:
        init_database()

        from bson import ObjectId

        person = database.collection.find_one({'_id': ObjectId(person_id)})

        if not person:
            return jsonify({'error': 'Person not found'}), 404

        # Add meeting history
        meetings = database.get_all_meetings(person_id)

        # Convert ObjectId and dates
        person['_id'] = str(person['_id'])
        if 'date' in person:
            person['date'] = person['date'].isoformat()

        import base64
        if person.get('image_path') and os.path.exists(person['image_path']):
            try:
                with open(person['image_path'], 'rb') as img_file:
                    person['person_image'] = 'data:image/jpeg;base64,' + base64.b64encode(img_file.read()).decode('utf-8')
            except Exception as img_err:
                logger.warning(f"Failed to read image for {person_id}: {img_err}")

        # Remove embedding (too large)
        if 'embedding' in person:
            del person['embedding']

        # Convert meeting timestamps
        for meeting in meetings:
            meeting['_id'] = str(meeting['_id'])
            meeting['person_id'] = str(meeting['person_id'])
            meeting['timestamp'] = meeting['timestamp'].isoformat()

        person['meetings'] = meetings
        person['meeting_count'] = len(meetings)

        return jsonify({
            'success': True,
            'person': person
        })

    except Exception as e:
        logger.error(f"Error getting person: {e}")
        return jsonify({'error': str(e)}), 500

@people_bp.route('/<person_id>/meetings', methods=['GET'])
def get_person_meetings_route(person_id):
    """Get all meetings for a person."""
    try:
        init_database()

        meetings = database.get_all_meetings(person_id)

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
        logger.error(f"Error getting person meetings: {e}")
        return jsonify({'error': str(e)}), 500

@people_bp.route('/<person_id>', methods=['PUT'])
def update_person(person_id):
    """Update person information."""
    try:
        init_database()

        from bson import ObjectId
        from datetime import datetime

        data = request.json
        name = data.get('name')

        if not name:
            return jsonify({'error': 'Name required'}), 400

        result = database.collection.update_one(
            {'_id': ObjectId(person_id)},
            {'$set': {
                'name': name,
                'updated_at': datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
            }}
        )

        if result.matched_count == 0:
            return jsonify({'error': 'Person not found'}), 404

        return jsonify({
            'success': True,
            'message': 'Person updated'
        })

    except Exception as e:
        logger.error(f"Error updating person: {e}")
        return jsonify({'error': str(e)}), 500

@people_bp.route('/<person_id>', methods=['DELETE'])
def delete_person(person_id):
    """Delete a person and all their meetings."""
    try:
        init_database()

        from bson import ObjectId

        # Delete all meetings
        database.meetings_collection.delete_many({'person_id': person_id})

        # Delete person
        result = database.collection.delete_one({'_id': ObjectId(person_id)})

        if result.deleted_count == 0:
            return jsonify({'error': 'Person not found'}), 404

        return jsonify({
            'success': True,
            'message': 'Person and meetings deleted'
        })

    except Exception as e:
        logger.error(f"Error deleting person: {e}")
        return jsonify({'error': str(e)}), 500

@people_bp.route('/search', methods=['GET'])
def search_people():
    """Search people by name."""
    try:
        init_database()

        query = request.args.get('q', '')

        if not query:
            return jsonify({'error': 'Search query required'}), 400

        # Search by name (case-insensitive)
        people = list(database.collection.find({
            'name': {'$regex': query, '$options': 'i'}
        }))

        # Add meeting count
        valid_people = []
        for person in people:
            # Skip people without valid _id
            if '_id' not in person or not person['_id']:
                continue

            person_id = str(person['_id'])
            meetings = database.get_all_meetings(person_id)
            person['meeting_count'] = len(meetings)
            person['_id'] = person_id
            if 'date' in person:
                person['date'] = person['date'].isoformat()

            import base64
            if person.get('image_path') and os.path.exists(person['image_path']):
                try:
                    with open(person['image_path'], 'rb') as img_file:
                       person['person_image'] = 'data:image/jpeg;base64,' + base64.b64encode(img_file.read()).decode('utf-8')
                except Exception as img_err:
                    logger.warning(f"Failed to read image for {person_id}: {img_err}")

            if 'embedding' in person:
                del person['embedding']
            valid_people.append(person)

        return jsonify({
            'success': True,
            'people': valid_people,
            'total': len(valid_people)
        })

    except Exception as e:
        logger.error(f"Error searching people: {e}")
        return jsonify({'error': str(e)}), 500

@people_bp.route('/count', methods=['GET'])
def count_people():
    """Get total number of registered people."""
    try:
        init_database()

        count = database.count_embeddings()

        return jsonify({
            'success': True,
            'count': count
        })

    except Exception as e:
        logger.error(f"Error counting people: {e}")
        return jsonify({'error': str(e)}), 500
