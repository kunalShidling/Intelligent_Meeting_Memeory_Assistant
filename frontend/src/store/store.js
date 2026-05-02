import { configureStore } from '@reduxjs/toolkit';
import meetingReducer from './meetingSlice';
import peopleReducer from './peopleSlice';
import uiReducer from './uiSlice';

export const store = configureStore({
  reducer: {
    meeting: meetingReducer,
    people: peopleReducer,
    ui: uiReducer,
  },
});

export default store;
