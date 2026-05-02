import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  isLoading: false,
  notification: null,
  theme: 'light',
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    showNotification: (state, action) => {
      state.notification = action.payload; // { type: 'success'|'error'|'info', message: string }
    },
    hideNotification: (state) => {
      state.notification = null;
    },
    setTheme: (state, action) => {
      state.theme = action.payload;
    },
  },
});

export const {
  setLoading,
  showNotification,
  hideNotification,
  setTheme,
} = uiSlice.actions;

export default uiSlice.reducer;
