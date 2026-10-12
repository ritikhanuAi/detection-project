import { getCsrfToken } from './client.js';

/**
 * Uploads a file with real-time percentage feedback via XHR upload.onprogress.
 * @param {string} url - Target upload URL.
 * @param {FormData} formData - Payload with files and metadata.
 * @param {Function} onProgress - Callback: (percent: number, loadedBytes: number, totalBytes: number) => void
 * @returns {Promise<any>}
 */
export function uploadWithProgress(url, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url, true);
    xhr.setRequestHeader('Accept', 'application/json');

    const csrf = getCsrfToken();
    if (csrf) {
      xhr.setRequestHeader('X-CSRFToken', csrf);
    }

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
          onProgress(percent, event.loaded, event.total);
        }
      };
    }

    xhr.onload = () => {
      try {
        const responseData = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(responseData);
        } else {
          reject(new Error(responseData.error || responseData.detail || `Upload failed (${xhr.status})`));
        }
      } catch (err) {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(xhr.responseText);
        } else {
          reject(new Error(`Upload failed (${xhr.status})`));
        }
      }
    };

    xhr.onerror = () => {
      reject(new Error('Network error during file upload.'));
    };

    xhr.send(formData);
  });
}
