import api from './api';

export const meetingService = {
  // Start complete meeting (record, transcribe, summarize)
  startMeeting: async (personId, personName, duration, imagePath) => {
    return await api.post('/meeting/start', {
      person_id: personId,
      person_name: personName,
      duration,
      image_path: imagePath
    });
  },

  // Create meeting from existing data
  createMeeting: async (data) => {
    return await api.post('/meeting/create', data);
  },

  // Get single meeting
  getMeeting: async (meetingId) => {
    return await api.get(`/meeting/${meetingId}`);
  },

  // List all meetings (paginated)
  listMeetings: async (page = 1, limit = 10) => {
    return await api.get('/meeting/list', { params: { page, limit } });
  },

  // Get meetings for person
  getPersonMeetings: async (personId) => {
    return await api.get(`/meeting/person/${personId}`);
  },

  // Delete meeting
  deleteMeeting: async (meetingId) => {
    return await api.delete(`/meeting/${meetingId}`);
  },

  // Search meetings
  searchMeetings: async (keyword) => {
    return await api.get('/meeting/search', { params: { q: keyword } });
  },

  // Get relevant meetings for a participant set
  getRelatedMeetings: async (payload) => {
    return await api.post('/meeting/related', payload);
  },
};

export default meetingService;
