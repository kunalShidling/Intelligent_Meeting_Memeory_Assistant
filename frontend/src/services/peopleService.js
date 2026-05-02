import api from './api';

export const peopleService = {
  // Get all people
  getAllPeople: async () => {
    return await api.get('/people/');
  },

  // Get single person
  getPerson: async (personId) => {
    return await api.get(`/people/${personId}`);
  },

  // Get person's meetings
  getPersonMeetings: async (personId) => {
    return await api.get(`/people/${personId}/meetings`);
  },

  // Update person
  updatePerson: async (personId, name) => {
    return await api.put(`/people/${personId}`, { name });
  },

  // Delete person
  deletePerson: async (personId) => {
    return await api.delete(`/people/${personId}`);
  },

  // Search people
  searchPeople: async (query) => {
    return await api.get('/people/search', { params: { q: query } });
  },

  // Count people
  countPeople: async () => {
    return await api.get('/people/count');
  },
};

export default peopleService;
