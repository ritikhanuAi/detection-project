/**
 * Reusable ProgressBar component.
 */
export class ProgressBar {
  constructor(containerEl, options = {}) {
    this.container = containerEl;
    this.options = {
      showPercentageText: true,
      label: 'Progress',
      ...options
    };
    this.init();
  }

  init() {
    this.container.innerHTML = `
      <div class="progress-container">
        <div class="progress-header">
          <span class="progress-label">${this.options.label}</span>
          <span class="progress-percent">0%</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" style="width: 0%;"></div>
        </div>
      </div>
    `;
    this.labelEl = this.container.querySelector('.progress-label');
    this.percentEl = this.container.querySelector('.progress-percent');
    this.fillEl = this.container.querySelector('.progress-fill');
  }

  update(percent, message = null) {
    const p = Math.max(0, Math.min(100, Math.round(percent)));
    this.fillEl.style.width = `${p}%`;
    this.percentEl.textContent = `${p}%`;
    if (message && this.labelEl) {
      this.labelEl.textContent = message;
    }
  }

  reset() {
    this.update(0, this.options.label);
  }
}
