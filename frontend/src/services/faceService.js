import api from './api';

export const faceService = {
  // Capture face from camera
  captureface: async () => {
    return await api.post('/face/capture');
  },

  // Detect face in image
  detectFace: async (imagePath) => {
    return await api.post('/face/detect', { image_path: imagePath });
  },

  // Recognize person from image
  recognizeFace: async (imagePath) => {
    return await api.post('/face/recognize', { image_path: imagePath });
  },

  // Register new person
  registerPerson: async (name, imagePath) => {
    return await api.post('/face/register', { name, image_path: imagePath });
  },

  // Check camera status
  getCameraStatus: async () => {
    return await api.get('/face/camera/status');
  },
};

export default faceService;
