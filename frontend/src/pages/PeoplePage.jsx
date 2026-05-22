import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Users, Search, Loader2 } from 'lucide-react';
import LoadingSpinner from '../components/Common/LoadingSpinner';
import SearchBar from '../components/Common/SearchBar';
import peopleService from '../services/peopleService';

export default function PeoplePage() {
  const [people, setPeople] = useState([]);
  const [filteredPeople, setFilteredPeople] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadPeople();
  }, []);

  useEffect(() => {
    if (searchQuery.trim()) {
      const filtered = people.filter((person) =>
        person.name.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredPeople(filtered);
    } else {
      setFilteredPeople(people);
    }
  }, [searchQuery, people]);

  const loadPeople = async () => {
    try {
      setLoading(true);
      const response = await peopleService.getAllPeople();
      setPeople(response.people || []);
      setFilteredPeople(response.people || []);
    } catch (err) {
      setError(err.error || 'Failed to load people');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="xl" text="Loading people..." />
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
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Directory</p>
          <h1 className="text-3xl font-semibold text-slate-900">People Directory</h1>
          <p className="mt-2 text-slate-600">
            {people.length} registered {people.length === 1 ? 'person' : 'people'}
          </p>
        </div>
      </div>

      {/* Search */}
      <SearchBar
        value={searchQuery}
        onChange={setSearchQuery}
        placeholder="Search people by name..."
      />

      {/* People Grid */}
      {filteredPeople.length === 0 ? (
        <div className="text-center py-16 bg-white/90 rounded-2xl shadow-sm border border-amber-100">
          <Users className="w-16 h-16 text-amber-300 mx-auto mb-4" />
          <p className="text-slate-500 text-lg">
            {searchQuery ? 'No people matching the search query.' : 'No people registered yet.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredPeople
            .filter((person) => person._id && person._id !== '')
            .map((person) => (
            <Link
              key={person._id}
              to={`/person/${person._id}`}
              className="bg-white/90 rounded-2xl shadow-sm border border-amber-100 hover:shadow-lg hover:border-teal-200 transition-all duration-200 p-6 group relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 p-16 bg-teal-50/60 rounded-full blur-2xl -mr-8 -mt-8 group-hover:bg-teal-100/60 transition-all duration-500"></div>
              
              <div className="relative flex items-start space-x-4">
                <div className="bg-amber-50/40 p-2 rounded-xl border border-amber-100 shrink-0">
                  {person.person_image ? (
                    <img src={person.person_image} alt={person.name} className="w-12 h-12 rounded-lg object-cover" />
                  ) : (
                    <Users className="w-12 h-12 p-2 text-teal-600" />
                  )}
                </div>
                <div className="flex-1 mt-1">
                  <h3 className="text-lg font-semibold text-slate-900 group-hover:text-teal-700 transition-colors">{person.name}</h3>
                  <p className="text-slate-500 text-sm mt-1">
                    {person.meeting_count} {person.meeting_count === 1 ? 'interaction' : 'interactions'}
                  </p>
                  {person.date && (
                    <p className="text-xs text-slate-400 mt-2 font-medium uppercase tracking-wider">
                      Initiated: {new Date(person.date).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
