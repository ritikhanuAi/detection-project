import { jobsApi } from '../api/jobsApi.js';
import { renderStatusBadge } from '../components/StatusBadge.js';
import { Toast } from '../components/Toast.js';

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('jobsTableContainer');
  const refreshBtn = document.getElementById('refreshJobsBtn');

  async function loadJobs() {
    if (!container) return;
    container.innerHTML = '<p style="padding: 24px; text-align: center; color: var(--theme-text-muted);">Loading recent video analysis jobs...</p>';
    try {
      const data = await jobsApi.listJobs({ stage: 'stage1', page_size: 10 });
      const jobs = data.results || [];

      if (jobs.length === 0) {
        container.innerHTML = '<p style="padding: 24px; text-align: center; color: var(--theme-text-muted);">No video analysis jobs found. Upload a video above to begin.</p>';
        return;
      }

      container.innerHTML = `
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Analysis Type</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Created At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${jobs.map(job => `
                <tr>
                  <td><code style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--theme-accent-primary); font-weight: 600;">${job.id.substring(0, 8)}...</code></td>
                  <td><strong>Video Analysis</strong></td>
                  <td>${renderStatusBadge(job.status)}</td>
                  <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                      <div class="confidence-bar" style="width: 80px;">
                        <div class="confidence-bar-fill" style="width: ${job.progress_percent}%;"></div>
                      </div>
                      <span style="font-size: 0.75rem; font-family: var(--font-mono);">${job.progress_percent}%</span>
                    </div>
                  </td>
                  <td style="color: var(--theme-text-muted); font-size: 0.8rem;">${new Date(job.created_at).toLocaleString()}</td>
                  <td>
                    <a href="/video-analysis/?job_id=${job.id}" class="btn btn-secondary" style="padding: 3px 10px; font-size: 0.75rem; gap: 4px;">
                      <span>Inspect</span>
                      <svg class="icon icon-sm" viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                    </a>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    } catch (err) {
      container.innerHTML = `<p style="padding: 24px; text-align: center; color: var(--theme-incorrect);">Failed to load jobs: ${err.message}</p>`;
    }
  }

  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      loadJobs();
      Toast.success('Video analysis jobs refreshed');
    });
  }

  loadJobs();
});
