/**
 * Base HTTP client with CSRF protection and error handling.
 */
export function getCsrfToken() {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

export async function request(url, options = {}) {
  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {})
  };

  const csrf = getCsrfToken();
  if (csrf && !headers['X-CSRFToken']) {
    headers['X-CSRFToken'] = csrf;
  }

  const config = {
    ...options,
    headers
  };

  try {
    const response = await fetch(url, config);
    const contentType = response.headers.get('content-type') || '';
    
    if (response.status === 204) {
      return null;
    }

    if (contentType.includes('application/json')) {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || data.detail || 'Request failed with status ' + response.status);
      }
      return data;
    }

    if (!response.ok) {
      throw new Error('Request failed with status ' + response.status);
    }
    return response;
  } catch (err) {
    console.error('API Error:', err);
    throw err;
  }
}
