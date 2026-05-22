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
    <div className="space-y-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Dashboard</p>
          <h1 className="text-4xl font-semibold text-slate-900">Home</h1>
          <p className="text-slate-600">Welcome to Meeting Assistant</p>
        </div>
        <Link
          to="/start-meeting"
          className="group inline-flex items-center gap-2 rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-900/20 transition hover:-translate-y-0.5 hover:bg-slate-800"
        >
          <Video className="w-4 h-4" />
          <span>Start New Meeting</span>
        </Link>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
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
      <div className="bg-white/90 rounded-2xl border border-amber-100 shadow-sm">
        <div className="px-6 py-5 border-b border-amber-100">
          <h2 className="text-xl font-semibold text-slate-900">Recent Meetings</h2>
        </div>
        <div className="divide-y divide-amber-100/70">
          {recentMeetings.length === 0 ? (
            <div className="px-6 py-10 text-center text-slate-500">
              <Video className="w-12 h-12 mx-auto mb-3 text-amber-300" />
              <p>No meetings yet. Start your first meeting!</p>
              <Link
                to="/start-meeting"
                className="mt-4 inline-block text-teal-600 hover:text-teal-700 font-semibold"
              >
                Start Meeting →
              </Link>
            </div>
          ) : (
            recentMeetings.map((meeting) => (
              <Link
                key={meeting._id}
                to={`/meeting/${meeting._id}`}
                className="block px-6 py-4 transition hover:bg-amber-50/40"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-lg font-semibold text-slate-900">
                        {meeting.person_name}
                      </h3>
                      <span className="text-sm text-slate-500">
                        • {formatDistanceToNow(new Date(meeting.timestamp), { addSuffix: true })}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-600 line-clamp-2">
                      {meeting.summary?.split('\n')[0] || 'No summary'}
                    </p>
                  </div>
                  <div className="ml-4">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-teal-100 text-teal-800">
                      View Details
                    </span>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
        {recentMeetings.length > 0 && (
          <div className="px-6 py-4 bg-amber-50/50">
            <Link
              to="/people"
              className="text-sm text-teal-600 hover:text-teal-700 font-semibold"
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
          className="rounded-2xl p-6 text-white shadow-lg shadow-teal-500/20 transition-all bg-gradient-to-br from-teal-600 to-emerald-500 hover:from-teal-500 hover:to-emerald-400"
        >
          <Video className="w-10 h-10 mb-3" />
          <h3 className="text-xl font-semibold">Start New Meeting</h3>
          <p className="mt-2 text-teal-100">
            Quickly recognize a person and start recording a meeting
          </p>
        </Link>

        <Link
          to="/people"
          className="rounded-2xl p-6 text-white shadow-lg shadow-amber-500/20 transition-all bg-gradient-to-br from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400"
        >
          <Users className="w-10 h-10 mb-3" />
          <h3 className="text-xl font-semibold">View People</h3>
          <p className="mt-2 text-amber-100">
            Browse registered people and their meeting history
          </p>
        </Link>
      </div>
    </div>
  );
}
