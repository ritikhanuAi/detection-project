import { request } from './client.js';

export const profilingApi = {
  getProfile: (jobId) => {
    return request(`/api/profiling/${jobId}/`);
  },

  triggerProfiling: (jobId) => {
    return request(`/api/profiling/${jobId}/trigger/`, { method: 'POST' });
  }
};
