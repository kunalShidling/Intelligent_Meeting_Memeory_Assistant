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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">People Directory</h1>
          <p className="mt-2 text-gray-600">
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
        <div className="text-center py-16 bg-white rounded-xl shadow-sm border border-gray-100">
          <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">
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
              className="bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md hover:border-blue-100 transition-all duration-200 p-6 group relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 p-16 bg-blue-50/50 rounded-full blur-2xl -mr-8 -mt-8 group-hover:bg-blue-100/50 transition-all duration-500"></div>
              
              <div className="relative flex items-start space-x-4">
                <div className="bg-gray-50 p-2 rounded-xl border border-gray-100 shrink-0">
                  {person.person_image ? (
                    <img src={person.person_image} alt={person.name} className="w-12 h-12 rounded-lg object-cover" />
                  ) : (
                    <Users className="w-12 h-12 p-2 text-blue-600" />
                  )}
                </div>
                <div className="flex-1 mt-1">
                  <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">{person.name}</h3>
                  <p className="text-gray-500 text-sm mt-1">
                    {person.meeting_count} {person.meeting_count === 1 ? 'interaction' : 'interactions'}
                  </p>
                  {person.date && (
                    <p className="text-xs text-gray-400 mt-2 font-medium uppercase tracking-wider">
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
