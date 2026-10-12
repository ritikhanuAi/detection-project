import { request } from './client.js';

export const jobsApi = {
  listJobs: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/api/jobs/${query ? '?' + query : ''}`);
  },

  getJob: (jobId) => {
    return request(`/api/jobs/${jobId}/`);
  },

  pollJobUntilDone: (jobId, onProgress, intervalMs = 2000, maxAttempts = 180) => {
    return new Promise((resolve, reject) => {
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        try {
          const job = await jobsApi.getJob(jobId);
          if (onProgress) {
            onProgress(job);
          }

          if (job.status === 'done') {
            clearInterval(interval);
            resolve(job);
          } else if (job.status === 'failed') {
            clearInterval(interval);
            reject(new Error(job.error_message || 'Job processing failed.'));
          } else if (attempts >= maxAttempts) {
            clearInterval(interval);
            reject(new Error('Job polling timed out.'));
          }
        } catch (err) {
          clearInterval(interval);
          reject(err);
        }
      }, intervalMs);
    });
  }
};
