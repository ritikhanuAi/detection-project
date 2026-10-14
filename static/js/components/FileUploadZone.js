import { uploadWithProgress } from '../api/uploadApi.js';
import { Toast } from './Toast.js';

export class FileUploadZone {
  constructor(element, options = {}) {
    this.el = element;
    this.options = {
      endpoint: '/api/jobs/',
      fileInputName: 'input_file',
      stage: 'stage1',
      allowedExtensions: [],
      onUploadStart: null,
      onProgress: null,
      onSuccess: null,
      onError: null,
      ...options
    };

    this.selectedFile = null;
    this.init();
  }

  init() {
    this.el.innerHTML = `
      <div class="upload-zone" id="dropTarget">
        <input type="file" id="hiddenFileInput" style="display: none;" />
        <div class="upload-icon">
          <svg class="icon icon-xl" viewBox="0 0 24 24">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
          </svg>
        </div>
        <div style="font-weight: 600; font-size: 1rem;">Click or drag file to upload</div>
        <div class="upload-hint">Supported: ${this.options.allowedExtensions.join(', ')}</div>
        <div id="fileSelectedBadge" style="display: none; margin-top: 10px;">
          <span class="badge badge-neutral" id="selectedFileName"></span>
        </div>
      </div>
    `;

    this.dropTarget = this.el.querySelector('#dropTarget');
    this.fileInput = this.el.querySelector('#hiddenFileInput');
    this.fileBadge = this.el.querySelector('#fileSelectedBadge');
    this.fileNameSpan = this.el.querySelector('#selectedFileName');

    this.bindEvents();
  }

  bindEvents() {
    this.dropTarget.addEventListener('click', () => this.fileInput.click());

    this.fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        this.handleFile(e.target.files[0]);
      }
    });

    ['dragenter', 'dragover'].forEach(eventName => {
      this.dropTarget.addEventListener(eventName, (e) => {
        e.preventDefault();
        this.dropTarget.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      this.dropTarget.addEventListener(eventName, (e) => {
        e.preventDefault();
        this.dropTarget.classList.remove('dragover');
      });
    });

    this.dropTarget.addEventListener('drop', (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        this.handleFile(e.dataTransfer.files[0]);
      }
    });
  }

  handleFile(file) {
    if (this.options.allowedExtensions.length > 0) {
      const ext = '.' + file.name.split('.').pop().toLowerCase();
      if (!this.options.allowedExtensions.includes(ext)) {
        Toast.error(`Invalid file format. Allowed: ${this.options.allowedExtensions.join(', ')}`);
        return;
      }
    }

    this.selectedFile = file;
    this.fileNameSpan.textContent = `${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
    this.fileBadge.style.display = 'block';

    if (this.options.onFileSelect) {
      this.options.onFileSelect(file);
    }
  }

  async upload(additionalFormData = {}) {
    if (!this.selectedFile) {
      Toast.error('Please select a file first.');
      return;
    }

    const formData = new FormData();
    formData.append(this.options.fileInputName, this.selectedFile);
    formData.append('stage', this.options.stage);

    for (const [key, val] of Object.entries(additionalFormData)) {
      formData.append(key, val);
    }

    if (this.options.onUploadStart) {
      this.options.onUploadStart(this.selectedFile);
    }

    try {
      const response = await uploadWithProgress(
        this.options.endpoint,
        formData,
        (percent, loaded, total) => {
          if (this.options.onProgress) {
            this.options.onProgress(percent, loaded, total);
          }
        }
      );

      if (this.options.onSuccess) {
        this.options.onSuccess(response);
      }
      return response;
    } catch (err) {
      if (this.options.onError) {
        this.options.onError(err);
      } else {
        Toast.error(err.message || 'Upload failed');
      }
      throw err;
    }
  }
}
