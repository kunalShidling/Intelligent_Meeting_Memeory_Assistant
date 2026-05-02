import axios from 'axios';

// Retry configuration
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60 seconds
});

// Retry helper function with exponential backoff
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const shouldRetry = (error) => {
  // Retry on network errors or 5xx server errors
  return (
    !error.response ||
    error.code === 'ECONNREFUSED' ||
    error.code === 'ENOTFOUND' ||
    error.code === 'ETIMEDOUT' ||
    (error.response && error.response.status >= 500)
  );
};

// Request interceptor with retry logic
api.interceptors.request.use(
  (config) => {
    config.retryCount = config.retryCount || 0;
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor with retry
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  async (error) => {
    const config = error.config;

    // Check if we should retry
    if (config && shouldRetry(error) && config.retryCount < MAX_RETRIES) {
      config.retryCount += 1;

      // Calculate delay with exponential backoff
      const delay = RETRY_DELAY * Math.pow(2, config.retryCount - 1);

      console.log(`Retrying request (${config.retryCount}/${MAX_RETRIES}) after ${delay}ms...`);

      await sleep(delay);

      return api(config);
    }

    // Log error after all retries exhausted
    if (config && config.retryCount >= MAX_RETRIES) {
      console.error('API Error: Max retries reached', error);
    } else {
      console.error('API Error:', error);
    }

    if (error.response) {
      // Server responded with error
      return Promise.reject(error.response.data);
    } else if (error.request) {
      // Request made but no response
      return Promise.reject({ error: 'Unable to connect to server. Please ensure the backend is running.' });
    } else {
      // Request setup error
      return Promise.reject({ error: error.message });
    }
  }
);

export default api;
