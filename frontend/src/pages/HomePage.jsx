import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Users, Video, Clock, TrendingUp } from 'lucide-react';
import StatsCard from '../components/Dashboard/StatsCard';
import LoadingSpinner from '../components/Common/LoadingSpinner';
import statsService from '../services/statsService';
import { formatDistanceToNow } from 'date-fns';

export default function HomePage() {
  const [stats, setStats] = useState(null);
  const [recentMeetings, setRecentMeetings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const response = await statsService.getDashboardStats();
      setStats(response.stats);
      setRecentMeetings(response.recent_meetings || []);
    } catch (err) {
      setError(err.error || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="xl" text="Loading dashboard..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Home</h1>
          <p className="mt-1 text-gray-600">Welcome to Meeting Assistant</p>
        </div>
        <Link
          to="/start-meeting"
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors flex items-center space-x-2"
        >
          <Video className="w-5 h-5" />
          <span>Start New Meeting</span>
        </Link>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total People"
          value={stats?.total_people || 0}
          icon={Users}
          to="/people"
        />
        <StatsCard
          title="Total Meetings"
          value={stats?.total_meetings || 0}
          icon={Video}
          to="/people"
        />
        <StatsCard
          title="Total Minutes"
          value={stats?.total_minutes || 0}
          icon={Clock}
          to="/people"
        />
        <StatsCard
          title="This Week"
          value={stats?.recent_meetings_count || 0}
          icon={TrendingUp}
          to="/people"
        />
      </div>

      {/* Recent Meetings */}
      <div className="bg-white rounded-lg shadow-md">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Recent Meetings</h2>
        </div>
        <div className="divide-y divide-gray-200">
          {recentMeetings.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-500">
              <Video className="w-12 h-12 mx-auto mb-3 text-gray-400" />
              <p>No meetings yet. Start your first meeting!</p>
              <Link
                to="/start-meeting"
                className="mt-4 inline-block text-blue-600 hover:text-blue-700 font-medium"
              >
                Start Meeting →
              </Link>
            </div>
          ) : (
            recentMeetings.map((meeting) => (
              <Link
                key={meeting._id}
                to={`/meeting/${meeting._id}`}
                className="block px-6 py-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-lg font-medium text-gray-900">
                        {meeting.person_name}
                      </h3>
                      <span className="text-sm text-gray-500">
                        • {formatDistanceToNow(new Date(meeting.timestamp), { addSuffix: true })}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-600 line-clamp-2">
                      {meeting.summary?.split('\n')[0] || 'No summary'}
                    </p>
                  </div>
                  <div className="ml-4">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                      View Details
                    </span>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
        {recentMeetings.length > 0 && (
          <div className="px-6 py-4 bg-gray-50">
            <Link
              to="/people"
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              View all meetings →
            </Link>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link
          to="/start-meeting"
          className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg p-6 text-white hover:from-blue-600 hover:to-blue-700 transition-all"
        >
          <Video className="w-10 h-10 mb-3" />
          <h3 className="text-xl font-semibold">Start New Meeting</h3>
          <p className="mt-2 text-blue-100">
            Quickly recognize a person and start recording a meeting
          </p>
        </Link>

        <Link
          to="/people"
          className="bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg p-6 text-white hover:from-purple-600 hover:to-purple-700 transition-all"
        >
          <Users className="w-10 h-10 mb-3" />
          <h3 className="text-xl font-semibold">View People</h3>
          <p className="mt-2 text-purple-100">
            Browse registered people and their meeting history
          </p>
        </Link>
      </div>
    </div>
  );
}
