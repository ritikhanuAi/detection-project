import { FileUploadZone } from '../components/FileUploadZone.js';
import { ProgressBar } from '../components/ProgressBar.js';
import { DataTable } from '../components/DataTable.js';
import { renderStatusBadge } from '../components/StatusBadge.js';
import { ZoomModal } from '../components/ImageZoomModal.js';
import { Toast } from '../components/Toast.js';
import { jobsApi } from '../api/jobsApi.js';
import { validationApi } from '../api/validationApi.js';
import { uploadWithProgress } from '../api/uploadApi.js';

document.addEventListener('DOMContentLoaded', () => {
  const jsonDropEl = document.getElementById('jsonDropzone');
  const imagesDropEl = document.getElementById('imagesDropzone');
  const startBtn = document.getElementById('startValidationBtn');
  const progressSec = document.getElementById('progressSection');
  const progressBarEl = document.getElementById('validationProgressBar');
  const resultsWorkbench = document.getElementById('resultsWorkbench');
  const tableContainer = document.getElementById('detectionsTableContainer');
  const downloadBtn = document.getElementById('downloadExportBtn');
  const stepper = document.getElementById('jsonStepper');

  let selectedJsonFile = null;
  let selectedZipFile = null;
  let currentJobId = null;

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

  // JSON dropzone
  new FileUploadZone(jsonDropEl, {
    allowedExtensions: ['.json'],
    onFileSelect: (file) => {
      selectedJsonFile = file;
      startBtn.disabled = false;
      startBtn.innerHTML = `<span>Validate "${file.name}"</span> <svg class="icon icon-sm" viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`;
    }
  });

  // Images ZIP dropzone
  new FileUploadZone(imagesDropEl, {
    allowedExtensions: ['.zip'],
    onFileSelect: (file) => {
      selectedZipFile = file;
      Toast.success(`Attached image archive: ${file.name}`);
    }
  });

  startBtn.addEventListener('click', async () => {
    if (!selectedJsonFile) {
      Toast.error('Please select a detection JSON file first.');
      return;
    }

    startBtn.disabled = true;
    progressSec.style.display = 'block';
    setStep(2);

    try {
      pBar.update(0, 'Uploading detection files...');
      
      const formData = new FormData();
      formData.append('json_file', selectedJsonFile);
      if (selectedZipFile) {
        formData.append('images_zip', selectedZipFile);
      }

      const uploadResp = await uploadWithProgress('/api/validation/run/', formData, (percent) => {
        pBar.update(percent, 'Uploading detection files...');
      });

      currentJobId = uploadResp.job_id;
      Toast.success('Upload complete. Auditing detections with AI...');
      setStep(3);

      // Poll until finished
      pBar.update(15, 'Extracting crops and verifying visual evidence...');
      await jobsApi.pollJobUntilDone(currentJobId, (job) => {
        pBar.update(job.progress_percent, job.progress_message || 'Auditing detections...');
      });

      // Complete
      setStep(4);
      pBar.update(100, 'Detection audit complete!');
      Toast.success('JSON defect validation completed successfully!');
      await loadValidationResults(currentJobId);

    } catch (err) {
      Toast.error(err.message || 'Validation failed');
      pBar.update(100, `Error: ${err.message}`);
    }
  });

  async function loadValidationResults(jobId) {
    currentJobId = jobId;
    try {
      // 1. Load summary
      const summary = await validationApi.getSummary(jobId);
      document.getElementById('valTotal').textContent = summary.total;
      document.getElementById('valCorrect').textContent = summary.correct;
      document.getElementById('valIncorrect').textContent = summary.incorrect;
      document.getElementById('valReview').textContent = summary.needs_review;
      document.getElementById('valPrecision').textContent = `${summary.precision_rate}%`;

      // 2. Set export download link
      downloadBtn.href = validationApi.getExportUrl(jobId);

      // 3. Initialize DataTable
      new DataTable(tableContainer, {
        columns: [
          {
            key: 'crop_url',
            label: 'Crop Preview',
            render: (val, row) => {
              if (!val) return '<span style="color:var(--theme-text-muted);">No image</span>';
              return `<img src="${val}" class="table-thumb" alt="Crop" data-annotated="${row.annotated_url || val}" data-reason="${row.reason}" data-class="${row.class_name}" data-status="${row.ai_status}" />`;
            }
          },
          {
            key: 'class_name',
            label: 'Defect Class',
            render: (val, row) => `<strong>${val}</strong> <span style="font-size:0.75rem; color:var(--theme-text-muted); font-family:var(--font-mono);">(${(row.original_confidence * 100).toFixed(0)}%)</span>`
          },
          {
            key: 'ai_status',
            label: 'AI Verdict',
            render: (val) => renderStatusBadge(val)
          },
          {
            key: 'ai_confidence',
            label: 'AI Conf.',
            render: (val) => `<span style="font-family:var(--font-mono); font-size:0.8rem; font-weight:600; color:var(--theme-accent-primary);">${(val * 100).toFixed(0)}%</span>`
          },
          {
            key: 'reason',
            label: 'AI Verification Rationale',
            render: (val) => `<div style="max-width: 380px; font-size: 0.82rem; color: var(--theme-text-secondary); line-height: 1.4;">${val || 'No explanation provided.'}</div>`
          }
        ],
        fetchData: (params) => validationApi.listDetections(jobId, params)
      });

      // Bind thumbnail click to ZoomModal
      tableContainer.addEventListener('click', (e) => {
        const thumb = e.target.closest('.table-thumb');
        if (thumb) {
          ZoomModal.open({
            title: `Inspection: ${thumb.dataset.class}`,
            subtitle: `AI Verdict: ${thumb.dataset.status}`,
            imageUrl: thumb.dataset.annotated || thumb.src,
            reason: thumb.dataset.reason,
            badgeHtml: renderStatusBadge(thumb.dataset.status)
          });
        }
      });

      resultsWorkbench.style.display = 'block';
      resultsWorkbench.scrollIntoView({ behavior: 'smooth' });

    } catch (err) {
      Toast.error('Failed to load validation results: ' + err.message);
    }
  }

  // Check URL query parameters for existing job_id
  const urlParams = new URLSearchParams(window.location.search);
  const existingJobId = urlParams.get('job_id');
  if (existingJobId) {
    setStep(4);
    loadValidationResults(existingJobId);
  }
});
