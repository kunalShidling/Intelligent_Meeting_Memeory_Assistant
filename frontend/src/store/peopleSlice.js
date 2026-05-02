import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  people: [],
  currentPerson: null,
  loading: false,
  error: null,
};

const peopleSlice = createSlice({
  name: 'people',
  initialState,
  reducers: {
    setPeople: (state, action) => {
      state.people = action.payload;
    },
    setCurrentPerson: (state, action) => {
      state.currentPerson = action.payload;
    },
    addPerson: (state, action) => {
      state.people.push(action.payload);
    },
    removePerson: (state, action) => {
      state.people = state.people.filter(p => p._id !== action.payload);
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
  setPeople,
  setCurrentPerson,
  addPerson,
  removePerson,
  setLoading,
  setError,
  clearError,
} = peopleSlice.actions;

export default peopleSlice.reducer;
