import { jobsApi } from '../api/jobsApi.js';
import { renderStatusBadge } from '../components/StatusBadge.js';
import { Toast } from '../components/Toast.js';

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('jobsTableContainer');
  const refreshBtn = document.getElementById('refreshJobsBtn');

  async function loadJobs() {
    container.innerHTML = '<p style="padding: 24px; text-align: center; color: var(--theme-text-muted);">Loading recent jobs...</p>';
    try {
      const data = await jobsApi.listJobs({ page_size: 10 });
      const jobs = data.results || [];

      if (jobs.length === 0) {
        container.innerHTML = '<p style="padding: 24px; text-align: center; color: var(--theme-text-muted);">No inspection jobs found. Launch Stage 1 or Stage 2 above.</p>';
        return;
      }

      container.innerHTML = `
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Stage</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Created At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${jobs.map(job => `
                <tr>
                  <td><code style="font-family: var(--font-mono); font-size: 0.75rem;">${job.id.substring(0, 8)}...</code></td>
                  <td><strong>${job.stage === 'stage1' ? 'Stage 1: Profiler' : 'Stage 2: Validator'}</strong></td>
                  <td>${renderStatusBadge(job.status)}</td>
                  <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                      <div class="confidence-bar" style="width: 80px;">
                        <div class="confidence-bar-fill" style="width: ${job.progress_percent}%;"></div>
                      </div>
                      <span style="font-size: 0.75rem;">${job.progress_percent}%</span>
                    </div>
                  </td>
                  <td style="color: var(--theme-text-muted); font-size: 0.8rem;">${new Date(job.created_at).toLocaleString()}</td>
                  <td>
                    ${job.stage === 'stage1' 
                      ? `<a href="/stage1/?job_id=${job.id}" class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.75rem;">Inspect &rarr;</a>`
                      : `<a href="/stage2/?job_id=${job.id}" class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.75rem;">Inspect &rarr;</a>`
                    }
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

  refreshBtn.addEventListener('click', () => {
    loadJobs();
    Toast.success('Jobs refreshed');
  });

  loadJobs();
});
