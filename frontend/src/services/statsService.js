import api from './api';

export const statsService = {
  // Get dashboard statistics
  getDashboardStats: async () => {
    return await api.get('/stats/dashboard');
  },

  // Get people statistics
  getPeopleStats: async () => {
    return await api.get('/stats/people');
  },

  // Get meetings timeline
  getMeetingsTimeline: async () => {
    return await api.get('/stats/meetings/timeline');
  },
};

export default statsService;
