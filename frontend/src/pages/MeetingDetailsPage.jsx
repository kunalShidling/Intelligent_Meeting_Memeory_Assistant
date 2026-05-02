import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Calendar, User, FileText, Mic, Trash2, AlertCircle } from 'lucide-react';
import LoadingSpinner from '../components/Common/LoadingSpinner';
import meetingService from '../services/meetingService';

export default function MeetingDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [meeting, setMeeting] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadMeeting();
  }, [id]);

  const loadMeeting = async () => {
    try {
      setLoading(true);
      const response = await meetingService.getMeeting(id);
      setMeeting(response.meeting);
    } catch (err) {
      setError(err.error || 'Failed to load meeting');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Delete this meeting?')) {
      return;
    }

    try {
      setDeleting(true);
      await meetingService.deleteMeeting(id);
      navigate('/');
    } catch (err) {
      alert(err.error || 'Failed to delete meeting');
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="xl" text="Loading meeting..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <AlertCircle className="w-5 h-5 text-red-600 inline mr-2" />
        <span className="text-red-800">{error}</span>
      </div>
    );
  }

  if (!meeting) {
    return <div>Meeting not found</div>;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Back Button */}
      <Link
        to="/"
        className="inline-flex items-center text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="w-4 h-4 mr-1" />
        Back to Dashboard
      </Link>

      {/* Meeting Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center space-x-2 text-gray-600 mb-2">
              <Calendar className="w-4 h-4" />
              <span className="text-sm">
                {new Date(meeting.timestamp).toLocaleString()}
              </span>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Meeting with {meeting.person_name}
            </h1>
            <Link
              to={`/person/${meeting.person_id}`}
              className="inline-flex items-center text-blue-600 hover:text-blue-700"
            >
              <User className="w-4 h-4 mr-1" />
              View Profile
            </Link>
          </div>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="flex items-center space-x-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
            <span>{deleting ? 'Deleting...' : 'Delete'}</span>
          </button>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center space-x-2 mb-4">
          <FileText className="w-5 h-5 text-gray-600" />
          <h2 className="text-xl font-semibold text-gray-900">Summary</h2>
        </div>
        <div className="prose prose-sm max-w-none">
          <div className="whitespace-pre-line text-gray-700">
            {meeting.summary}
          </div>
        </div>
      </div>

      {/* Full Transcript */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Mic className="w-5 h-5 text-gray-600" />
          <h2 className="text-xl font-semibold text-gray-900">Full Transcript</h2>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
          <p className="text-gray-700 whitespace-pre-wrap">
            {meeting.transcript}
          </p>
        </div>
      </div>

      {/* Metadata */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Meeting Information</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600">Meeting ID</p>
            <p className="text-sm font-mono text-gray-900">{meeting._id}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Person ID</p>
            <p className="text-sm font-mono text-gray-900">{meeting.person_id}</p>
          </div>
          {meeting.audio_path && (
            <div>
              <p className="text-sm text-gray-600">Audio File</p>
              <p className="text-sm text-gray-900">{meeting.audio_path.split('/').pop()}</p>
            </div>
          )}
          {meeting.image_path && (
            <div>
              <p className="text-sm text-gray-600">Image File</p>
              <p className="text-sm text-gray-900">{meeting.image_path.split('/').pop()}</p>
            </div>
          )}
          <div>
            <p className="text-sm text-gray-600">Transcript Length</p>
            <p className="text-sm text-gray-900">{meeting.transcript.length} characters</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Estimated Duration</p>
            <p className="text-sm text-gray-900">
              ~{Math.round(meeting.transcript.length / (150 * 5))} minutes
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
