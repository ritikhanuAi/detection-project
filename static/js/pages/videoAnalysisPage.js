import { FileUploadZone } from '../components/FileUploadZone.js';
import { ProgressBar } from '../components/ProgressBar.js';
import { Toast } from '../components/Toast.js';
import { renderStatusBadge } from '../components/StatusBadge.js';
import { jobsApi } from '../api/jobsApi.js';
import { profilingApi } from '../api/profilingApi.js';

document.addEventListener('DOMContentLoaded', () => {
  const dropzoneEl = document.getElementById('videoDropzone');
  const startBtn = document.getElementById('startProfilingBtn');
  const progressSec = document.getElementById('progressSection');
  const progressBarEl = document.getElementById('profilingProgressBar');
  const resultsWorkbench = document.getElementById('resultsWorkbench');
  const stepper = document.getElementById('videoStepper');
  const jobsContainer = document.getElementById('videoJobsTableContainer');
  const refreshJobsBtn = document.getElementById('refreshVideoJobsBtn');

  const pBar = new ProgressBar(progressBarEl, { label: 'Upload Progress' });

  function setStep(stepNum) {
    if (!stepper) return;
    const items = stepper.querySelectorAll('.step-item');
    items.forEach((item, idx) => {
      item.classList.remove('active', 'completed');
      if (idx + 1 < stepNum) {
        item.classList.add('completed');
      } else if (idx + 1 === stepNum) {
        item.classList.add('active');
      }
    });
  }

  const uploader = new FileUploadZone(dropzoneEl, {
    stage: 'stage1',
    endpoint: '/api/jobs/',
    allowedExtensions: ['.mp4', '.mov', '.avi', '.mkv'],
    onFileSelect: (file) => {
      startBtn.disabled = false;
      startBtn.innerHTML = `<span>Upload "${file.name}" & Start Video Analysis</span> <svg class="icon icon-sm" viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`;
    }
  });

  startBtn.addEventListener('click', async () => {
    startBtn.disabled = true;
    progressSec.style.display = 'block';
    setStep(2);

    try {
      // 1. Upload Video with real-time percentage feedback
      pBar.update(0, 'Uploading video to server...');
      const jobResponse = await uploader.upload();
      const jobId = jobResponse.id;

      Toast.success('Video upload complete. Triggering AI pipeline...');
      setStep(3);

      // 2. Trigger Profiling pipeline
      await profilingApi.triggerProfiling(jobId);

      // 3. Poll until done
      pBar.update(15, 'Extracting sharp keyframes and analyzing with VLM...');
      await jobsApi.pollJobUntilDone(jobId, (job) => {
        pBar.update(job.progress_percent, job.progress_message || 'Processing...');
      });

      // 4. Render results
      setStep(4);
      pBar.update(100, 'Consensus profiling complete!');
      Toast.success('Video analysis completed successfully!');
      await loadProfileResults(jobId);
      loadVideoJobs();

    } catch (err) {
      Toast.error(err.message || 'Video analysis failed');
      pBar.update(100, `Error: ${err.message}`);
    }
  });

  async function loadProfileResults(jobId) {
    try {
      const profile = await profilingApi.getProfile(jobId);

      // Populate 5 attributes
      document.getElementById('valRoadType').textContent = profile.road_type;
      document.getElementById('valPavement').textContent = profile.pavement_type;
      document.getElementById('valCarriageway').textContent = profile.carriageway_type;
      document.getElementById('valLanes').textContent = profile.lanes;
      document.getElementById('valWidth').textContent = `${profile.estimated_width_m} m`;

      // Populate confidence scores
      const conf = profile.confidence_scores || {};
      setConf('RoadType', conf.road_type || 0.8);
      setConf('Pavement', conf.pavement_type || 0.8);
      setConf('Carriageway', conf.carriageway_type || 0.8);
      setConf('Lanes', conf.lanes || 0.8);
      setConf('Width', conf.estimated_width_m || 0.8);

      // Model Config banner
      document.getElementById('configNameText').textContent = profile.model_config_selected;

      // Keyframes Gallery
      const grid = document.getElementById('keyframesGrid');
      const frames = profile.extracted_frames || [];
      grid.innerHTML = frames.map((relPath, idx) => `
        <div class="keyframe-card">
          <img src="/media/${relPath}" class="keyframe-img" alt="Keyframe ${idx + 1}" />
          <div class="keyframe-info">
            <span>Frame #${idx + 1}</span>
            <span>Sharp</span>
          </div>
        </div>
      `).join('');

      resultsWorkbench.style.display = 'block';
      resultsWorkbench.scrollIntoView({ behavior: 'smooth' });

    } catch (err) {
      Toast.error('Failed to load profile results: ' + err.message);
    }
  }

  function setConf(key, val) {
    const p = Math.round(val * 100);
    const bar = document.getElementById(`confBar${key}`);
    const txt = document.getElementById(`confText${key}`);
    if (bar) bar.style.width = `${p}%`;
    if (txt) txt.textContent = `${p}%`;
  }

  // Load Per Video Analysis Jobs Table
  async function loadVideoJobs() {
    if (!jobsContainer) return;
    jobsContainer.innerHTML = '<p style="padding: 24px; text-align: center; color: var(--theme-text-muted);">Loading recent video analysis jobs...</p>';
    try {
      const data = await jobsApi.listJobs({ stage: 'stage1', page_size: 10 });
      const jobs = data.results || [];

      if (jobs.length === 0) {
        jobsContainer.innerHTML = '<p style="padding: 24px; text-align: center; color: var(--theme-text-muted);">No video analysis jobs found. Upload a video above to begin.</p>';
        return;
      }

      jobsContainer.innerHTML = `
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
      jobsContainer.innerHTML = `<p style="padding: 24px; text-align: center; color: var(--theme-incorrect);">Failed to load video jobs: ${err.message}</p>`;
    }
  }

  if (refreshJobsBtn) {
    refreshJobsBtn.addEventListener('click', () => {
      loadVideoJobs();
      Toast.success('Video analysis jobs refreshed');
    });
  }

  // Check URL query parameters for existing job_id
  const urlParams = new URLSearchParams(window.location.search);
  const existingJobId = urlParams.get('job_id');
  if (existingJobId) {
    setStep(4);
    loadProfileResults(existingJobId);
  }

  // Initial load of jobs table
  loadVideoJobs();
});
