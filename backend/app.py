"""
Main Flask Application for Meeting Assistant
Provides REST API for face recognition, audio processing, and meeting management.
"""

import os
import sys

# Suppress TensorFlow/oneDNN warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress INFO and WARNING logs
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN optimizations messages

# Handle NumPy compatibility
try:
    import numpy
    numpy_version = tuple(int(x) for x in numpy.__version__.split('.')[:2])
    if numpy_version >= (2, 0):
        os.environ['NUMPY_EXPERIMENTAL_ARRAY_FUNCTION'] = '0'
except:
    pass

# Add parent directory, opencv, and audio_to_text to sys.path so modules can find each other
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'opencv'))
sys.path.insert(0, os.path.join(parent_dir, 'audio_to_text'))

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
import os
import logging

# Import route blueprints
from routes.face_routes import face_bp
from routes.audio_routes import audio_bp
from routes.meeting_routes import meeting_bp
from routes.people_routes import people_bp
from routes.stats_routes import stats_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Enable CORS for React frontend
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:5173"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Initialize SocketIO for real-time features
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000", "http://localhost:5173"])

# Register blueprints
app.register_blueprint(face_bp)
app.register_blueprint(audio_bp)
app.register_blueprint(meeting_bp)
app.register_blueprint(people_bp)
app.register_blueprint(stats_bp)

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'Meeting Assistant API is running'
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File too large'}), 413

# Serve uploaded files
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files."""
    upload_folder = os.path.join(os.path.dirname(__file__), '..', 'meeting_data')
    return send_from_directory(upload_folder, filename)

if __name__ == '__main__':
    logger.info("Starting Meeting Assistant API Server...")
    logger.info("API Documentation: http://localhost:5000/api/health")

    # Run with SocketIO support
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True
    )
