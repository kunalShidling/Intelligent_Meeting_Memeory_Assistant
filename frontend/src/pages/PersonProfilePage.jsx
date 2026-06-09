import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Users, Calendar, Trash2, AlertCircle } from 'lucide-react';
import LoadingSpinner from '../components/Common/LoadingSpinner';
import peopleService from '../services/peopleService';
import { formatDistanceToNow } from 'date-fns';

export default function PersonProfilePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [person, setPerson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const splitSummaryIntoPoints = (summary) => {
    if (!summary) return [];

    const points = String(summary)
      .split(/\r?\n/)
      .map(line => line.trim())
      .filter(Boolean)
      .map(line => line.replace(/^[•\-*\d.\s]+/, '').trim())
      .filter(Boolean);

    return points.length ? points : [String(summary).trim()];
  };

  useEffect(() => {
    loadPerson();
  }, [id]);

  const loadPerson = async () => {
    try {
      setLoading(true);
      const response = await peopleService.getPerson(id);
      setPerson(response.person);
    } catch (err) {
      setError(err.error || 'Failed to load person');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete ${person.name} and all their meetings?`)) {
      return;
    }

    try {
      setDeleting(true);
      await peopleService.deletePerson(id);
      navigate('/people');
    } catch (err) {
      alert(err.error || 'Failed to delete person');
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="xl" text="Loading profile..." />
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

  if (!person) {
    return <div>Person not found</div>;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Back Button */}
      <Link
        to="/people"
        className="inline-flex items-center text-slate-500 hover:text-slate-900 transition-colors"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        <span className="font-medium tracking-wide">Back to Directory</span>
      </Link>

      <div className="bg-white/90 rounded-3xl border border-amber-100 p-8 relative overflow-hidden shadow-sm">
        <div className="flex items-start justify-between relative z-10">
          <div className="flex items-center space-x-6">
            <div className="bg-teal-50 rounded-2xl p-2 border border-teal-100 shrink-0">
              {person.person_image ? (
                 <img src={person.person_image} alt={person.name} className="w-24 h-24 rounded-bl-xl rounded-tr-xl object-cover drop-shadow-md" />
              ) : (
                <Users className="w-16 h-16 text-teal-600 m-2" />
              )}
            </div>
            <div>
              <h1 className="text-4xl font-semibold text-slate-900 tracking-wide mb-2">{person.name}</h1>
              <p className="text-slate-500 tracking-wider uppercase text-sm mb-2">ID: {person._id}</p>
              {person.date && (
                <p className="text-sm font-medium text-teal-600 mt-1 uppercase tracking-widest">
                  Initialized: {new Date(person.date).toLocaleDateString()}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="flex items-center space-x-2 px-5 py-2.5 text-rose-600 hover:bg-rose-50 rounded-full transition-colors disabled:opacity-50 border border-transparent"
          >
            <Trash2 className="w-4 h-4" />
            <span className="font-medium tracking-wide">{deleting ? 'Erasing...' : 'Erase Profile'}</span>
          </button>
        </div>

        <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
          <div className="bg-amber-50/50 border border-amber-100 rounded-[20px] p-6 text-center">
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Total Telemetries</p>
            <p className="text-4xl font-bold text-slate-900 tracking-tight">{person.meeting_count || 0}</p>
          </div>
          <div className="bg-amber-50/50 border border-amber-100 rounded-[20px] p-6 text-center">
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Last Contact</p>
            <p className="text-xl font-medium text-slate-900 tracking-wide mt-2">
              {person.meetings && person.meetings.length > 0
                ? formatDistanceToNow(new Date(person.meetings[0].timestamp), { addSuffix: true })
                : 'No Streams Recorded'}
            </p>
          </div>
          <div className="bg-amber-50/50 border border-amber-100 rounded-[20px] p-6 text-center">
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Node Status</p>
            <p className="text-xl font-medium text-teal-600 tracking-wide mt-2">A C T I V E</p>
          </div>
        </div>
      </div>

      <div className="bg-white/90 rounded-3xl border border-amber-100 overflow-hidden shadow-sm relative">
        <div className="px-8 py-6 border-b border-amber-100 relative z-10">
          <h2 className="text-2xl font-semibold text-slate-900 tracking-wide">Historical Logs</h2>
        </div>
        <div className="divide-y divide-amber-100/70 relative z-10">
          {!person.meetings || person.meetings.length === 0 ? (
            <div className="px-8 py-16 text-center text-slate-500">
              <Calendar className="w-14 h-14 mx-auto mb-4 opacity-50" />
              <p className="text-lg">No streams detected for this entity.</p>
            </div>
          ) : (
            person.meetings
              .filter((meeting) => meeting._id && meeting._id !== '')
              .map((meeting) => (
              <Link
                key={meeting._id}
                to={`/meeting/${meeting._id}`}
                className="block px-8 py-6 hover:bg-amber-50/40 transition-colors group"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 pr-10">
                    <div className="flex items-center space-x-3 mb-2">
                      <Calendar className="w-4 h-4 text-teal-600" />
                      <span className="text-sm text-slate-500 font-medium tracking-wide">
                        {new Date(meeting.timestamp).toLocaleString()}
                      </span>
                      <span className="text-xs font-semibold uppercase tracking-widest text-teal-600 bg-teal-50 px-2 py-0.5 rounded-md border border-teal-100">
                        {formatDistanceToNow(new Date(meeting.timestamp), { addSuffix: true })}
                      </span>
                    </div>
                    <div className="mt-3 text-[15px] text-slate-600 line-clamp-3 whitespace-pre-line leading-relaxed group-hover:text-slate-900 transition-colors">
                      {meeting.summary || 'No summary available'}
                    </div>
                  </div>
                  <div className="ml-4 flex-shrink-0 pt-2">
                    <span className="inline-flex items-center px-4 py-2 bg-teal-50 text-teal-600 hover:bg-teal-600 hover:text-white rounded-xl transition-all duration-300 text-sm font-medium border border-teal-100 focus:outline-none">
                      Extract Log →
                    </span>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
