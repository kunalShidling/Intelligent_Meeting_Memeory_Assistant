import api from './api';

export const audioService = {
  // Record audio from microphone
  recordAudio: async (duration, personId) => {
    return await api.post('/audio/record', { duration, person_id: personId });
  },

  // Transcribe audio file
  transcribeAudio: async (audioPath) => {
    return await api.post('/audio/transcribe', { audio_path: audioPath });
  },

  // Summarize text
  summarizeText: async (text, maxBullets = 10) => {
    return await api.post('/audio/summarize', { text, max_bullets: maxBullets });
  },

  // Record and transcribe in one step
  recordAndTranscribe: async (duration) => {
    return await api.post('/audio/record-and-transcribe', { duration });
  },

  // Process uploaded audio file (transcribe + summarize)
  processAudioFile: async (audioBlob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    return await api.post('/audio/process-file', formData, {
    });
  },

  // Check async audio job status
  getJobStatus: async (jobId) => {
    return await api.get(`/audio/job/${jobId}`);
  },

  // List audio devices
  getAudioDevices: async () => {
    return await api.get('/audio/devices');
  },
};

export default audioService;
