/**
 * Semantic StatusBadge renderer for verdicts and job states.
 */
export function renderStatusBadge(status) {
  let badgeClass = 'badge-neutral';
  let label = status || 'Unknown';

  switch (status) {
    case 'Correct':
      badgeClass = 'badge-correct';
      break;
    case 'Incorrect/False':
    case 'failed':
      badgeClass = 'badge-incorrect';
      break;
    case 'Needs Review':
    case 'queued':
      badgeClass = 'badge-review';
      break;
    case 'running':
    case 'uploading':
      badgeClass = 'badge-running';
      break;
    case 'done':
      badgeClass = 'badge-correct';
      break;
  }

  return `<span class="badge ${badgeClass}">${label}</span>`;
}
