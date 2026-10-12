import { request } from './client.js';

export const validationApi = {
  listDetections: (jobId, params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/api/validation/${jobId}/detections/${query ? '?' + query : ''}`);
  },

  getSummary: (jobId) => {
    return request(`/api/validation/${jobId}/summary/`);
  },

  getExportUrl: (jobId) => {
    return `/api/validation/${jobId}/export/`;
  }
};
