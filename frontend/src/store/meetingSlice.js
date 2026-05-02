import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  currentMeeting: null,
  meetings: [],
  loading: false,
  error: null,
};

const meetingSlice = createSlice({
  name: 'meeting',
  initialState,
  reducers: {
    setCurrentMeeting: (state, action) => {
      state.currentMeeting = action.payload;
    },
    setMeetings: (state, action) => {
      state.meetings = action.payload;
    },
    addMeeting: (state, action) => {
      state.meetings.unshift(action.payload);
    },
    removeMeeting: (state, action) => {
      state.meetings = state.meetings.filter(m => m._id !== action.payload);
    },
    setLoading: (state, action) => {
      state.loading = action.payload;
    },
    setError: (state, action) => {
      state.error = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
});

export const {
  setCurrentMeeting,
  setMeetings,
  addMeeting,
  removeMeeting,
  setLoading,
  setError,
  clearError,
} = meetingSlice.actions;

export default meetingSlice.reducer;
