"""
Statistics API Routes
Provides dashboard statistics and analytics.
"""

from flask import Blueprint, jsonify
import sys
import os
import logging
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from opencv.database import FaceDatabase

logger = logging.getLogger(__name__)

# Create blueprint
stats_bp = Blueprint('stats', __name__, url_prefix='/api/stats')

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

@stats_bp.route('/dashboard', methods=['GET'])
def get_dashboard_stats():
    """Get statistics for dashboard."""
    try:
        init_database()

        # Total people
        total_people = database.count_embeddings()

        # Total meetings
        total_meetings = database.meetings_collection.count_documents({})

        # Total minutes (approximate from meetings)
        meetings = list(database.meetings_collection.find({}, {'transcript': 1}))

        # Estimate: ~150 words per minute, ~5 characters per word
        total_chars = sum(len(m.get('transcript', '')) for m in meetings)
        total_minutes = int(total_chars / (150 * 5)) if total_chars > 0 else 0

        # Recent meetings (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_meetings = database.meetings_collection.count_documents({
            'timestamp': {'$gte': week_ago}
        })

        # Get recent meeting list
        recent_meeting_list = list(database.meetings_collection.find()
                                   .sort('timestamp', -1)
                                   .limit(5))

        # Convert ObjectIds
        for meeting in recent_meeting_list:
            meeting['_id'] = str(meeting['_id'])
            meeting['person_id'] = str(meeting['person_id'])
            meeting['timestamp'] = meeting['timestamp'].isoformat()
            # Truncate transcript for dashboard
            if 'transcript' in meeting and len(meeting['transcript']) > 150:
                meeting['transcript'] = meeting['transcript'][:150] + '...'

        return jsonify({
            'success': True,
            'stats': {
                'total_people': total_people,
                'total_meetings': total_meetings,
                'total_minutes': total_minutes,
                'recent_meetings_count': recent_meetings
            },
            'recent_meetings': recent_meeting_list
        })

    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({'error': str(e)}), 500

@stats_bp.route('/people', methods=['GET'])
def get_people_stats():
    """Get people-related statistics."""
    try:
        init_database()

        people = database.get_all_embeddings()

        # Calculate stats per person
        people_stats = []
        for person in people:
            person_id = str(person.get('_id', ''))
            meetings = database.get_all_meetings(person_id)

            # Calculate total duration
            total_chars = sum(len(m.get('transcript', '')) for m in meetings)
            total_duration = int(total_chars / (150 * 5)) if total_chars > 0 else 0

            people_stats.append({
                'person_id': person_id,
                'name': person.get('name'),
                'meeting_count': len(meetings),
                'total_duration_minutes': total_duration,
                'last_meeting': meetings[0]['timestamp'].isoformat() if meetings else None
            })

        # Sort by meeting count
        people_stats.sort(key=lambda x: x['meeting_count'], reverse=True)

        return jsonify({
            'success': True,
            'stats': people_stats,
            'total': len(people_stats)
        })

    except Exception as e:
        logger.error(f"Error getting people stats: {e}")
        return jsonify({'error': str(e)}), 500

@stats_bp.route('/meetings/timeline', methods=['GET'])
def get_meetings_timeline():
    """Get meeting timeline for charts."""
    try:
        init_database()

        # Get meetings from last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)

        meetings = list(database.meetings_collection.find({
            'timestamp': {'$gte': thirty_days_ago}
        }, {'timestamp': 1}))

        # Group by date
        timeline = {}
        for meeting in meetings:
            date = meeting['timestamp'].date().isoformat()
            timeline[date] = timeline.get(date, 0) + 1

        # Sort by date
        sorted_timeline = [{'date': k, 'count': v} for k, v in sorted(timeline.items())]

        return jsonify({
            'success': True,
            'timeline': sorted_timeline
        })

    except Exception as e:
        logger.error(f"Error getting meetings timeline: {e}")
        return jsonify({'error': str(e)}), 500
