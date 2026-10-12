/**
 * ImageZoomModal for inspecting crops and defect bounding boxes.
 */
export class ImageZoomModal {
  constructor() {
    this.createDom();
    this.bindEvents();
  }

  createDom() {
    this.backdrop = document.createElement('div');
    this.backdrop.className = 'modal-backdrop';
    this.backdrop.id = 'zoomModal';

    this.backdrop.innerHTML = `
      <div class="modal-content">
        <button class="modal-close" id="zoomModalClose">&times;</button>
        <div class="card-header">
          <div>
            <h3 class="card-title" id="zoomModalTitle">Defect Inspection</h3>
            <p class="card-subtitle" id="zoomModalSubtitle"></p>
          </div>
          <div id="zoomModalBadge"></div>
        </div>
        <div class="zoom-container">
          <img class="zoom-image-main" id="zoomModalImg" src="" alt="Defect Visual Inspection" />
          <div style="width: 100%; background: #090d16; border: 1px solid var(--theme-border); padding: 12px; border-radius: 6px;">
            <span style="font-weight: 600; font-size: 0.8rem; text-transform: uppercase; color: var(--theme-text-muted);">AI Verification Reason:</span>
            <p style="font-size: 0.9rem; margin-top: 4px; color: var(--theme-text-primary);" id="zoomModalReason"></p>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(this.backdrop);

    this.titleEl = this.backdrop.querySelector('#zoomModalTitle');
    this.subtitleEl = this.backdrop.querySelector('#zoomModalSubtitle');
    this.imgEl = this.backdrop.querySelector('#zoomModalImg');
    this.reasonEl = this.backdrop.querySelector('#zoomModalReason');
    this.badgeEl = this.backdrop.querySelector('#zoomModalBadge');
    this.closeBtn = this.backdrop.querySelector('#zoomModalClose');
  }

  bindEvents() {
    this.closeBtn.addEventListener('click', () => this.close());
    this.backdrop.addEventListener('click', (e) => {
      if (e.target === this.backdrop) {
        this.close();
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.backdrop.classList.contains('open')) {
        this.close();
      }
    });
  }

  open({ title, subtitle, imageUrl, reason, badgeHtml }) {
    this.titleEl.textContent = title || 'Defect Inspector';
    this.subtitleEl.textContent = subtitle || '';
    this.imgEl.src = imageUrl || '';
    this.reasonEl.textContent = reason || 'No details provided.';
    this.badgeEl.innerHTML = badgeHtml || '';

    this.backdrop.classList.add('open');
  }

  close() {
    this.backdrop.classList.remove('open');
  }
}

export const ZoomModal = new ImageZoomModal();
