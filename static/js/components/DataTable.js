/**
 * Modular DataTable supporting sorting, searching, filter chips, and pagination.
 */
export class DataTable {
  constructor(containerEl, options = {}) {
    this.container = containerEl;
    this.options = {
      columns: [],
      fetchData: async (params) => ({ count: 0, results: [] }),
      onRowClick: null,
      ...options
    };

    this.state = {
      page: 1,
      pageSize: 10,
      search: '',
      status: '',
      ordering: 'id'
    };

    this.init();
  }

  init() {
    this.container.innerHTML = `
      <div class="filter-bar">
        <div class="filter-chips" id="filterChips">
          <button class="filter-chip active" data-status="">All</button>
          <button class="filter-chip" data-status="Correct">Correct</button>
          <button class="filter-chip" data-status="Incorrect/False">Incorrect</button>
          <button class="filter-chip" data-status="Needs Review">Needs Review</button>
        </div>
        <div>
          <input type="text" class="search-input" id="tableSearch" placeholder="Search class, image, reason..." />
        </div>
      </div>
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr id="tableHeaderRow"></tr>
          </thead>
          <tbody id="tableBody">
            <tr><td colspan="${this.options.columns.length}" style="text-align: center; padding: 24px; color: var(--theme-text-muted);">Loading data...</td></tr>
          </tbody>
        </table>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px;">
        <span style="font-size: 0.85rem; color: var(--theme-text-secondary);" id="tableCountInfo">Showing 0 results</span>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-secondary" id="prevPageBtn" disabled>Previous</button>
          <button class="btn btn-secondary" id="nextPageBtn" disabled>Next</button>
        </div>
      </div>
    `;

    this.headerRow = this.container.querySelector('#tableHeaderRow');
    this.bodyEl = this.container.querySelector('#tableBody');
    this.searchInput = this.container.querySelector('#tableSearch');
    this.filterChips = this.container.querySelector('#filterChips');
    this.countInfo = this.container.querySelector('#tableCountInfo');
    this.prevBtn = this.container.querySelector('#prevPageBtn');
    this.nextBtn = this.container.querySelector('#nextPageBtn');

    this.renderHeaders();
    this.bindEvents();
    this.load();
  }

  renderHeaders() {
    this.headerRow.innerHTML = this.options.columns
      .map(col => `<th data-key="${col.key}">${col.label}</th>`)
      .join('');
  }

  bindEvents() {
    // Search input with debounce
    let debounceTimer;
    this.searchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        this.state.search = e.target.value.trim();
        this.state.page = 1;
        this.load();
      }, 300);
    });

    // Filter chips
    this.filterChips.addEventListener('click', (e) => {
      const chip = e.target.closest('.filter-chip');
      if (!chip) return;
      this.filterChips.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      this.state.status = chip.dataset.status;
      this.state.page = 1;
      this.load();
    });

    // Pagination buttons
    this.prevBtn.addEventListener('click', () => {
      if (this.state.page > 1) {
        this.state.page--;
        this.load();
      }
    });

    this.nextBtn.addEventListener('click', () => {
      this.state.page++;
      this.load();
    });
  }

  async load() {
    this.bodyEl.innerHTML = `<tr><td colspan="${this.options.columns.length}" style="text-align:center; padding: 20px; color: var(--theme-text-muted);">Fetching records...</td></tr>`;

    try {
      const data = await this.options.fetchData({
        page: this.state.page,
        page_size: this.state.pageSize,
        status: this.state.status,
        search: this.state.search,
        ordering: this.state.ordering
      });

      const results = data.results || [];
      const total = data.count || 0;
      const totalPages = data.total_pages || 1;

      if (results.length === 0) {
        this.bodyEl.innerHTML = `<tr><td colspan="${this.options.columns.length}" style="text-align:center; padding: 24px; color: var(--theme-text-muted);">No matching records found.</td></tr>`;
      } else {
        this.bodyEl.innerHTML = results.map(row => {
          const cells = this.options.columns.map(col => {
            if (col.render) {
              return `<td>${col.render(row[col.key], row)}</td>`;
            }
            return `<td>${row[col.key] !== undefined ? row[col.key] : ''}</td>`;
          }).join('');
          return `<tr data-id="${row.id}">${cells}</tr>`;
        }).join('');
      }

      this.countInfo.textContent = `Page ${this.state.page} of ${totalPages} (${total} total records)`;
      this.prevBtn.disabled = this.state.page <= 1;
      this.nextBtn.disabled = this.state.page >= totalPages;

    } catch (err) {
      this.bodyEl.innerHTML = `<tr><td colspan="${this.options.columns.length}" style="text-align:center; padding: 20px; color: var(--theme-incorrect);">Error loading table data: ${err.message}</td></tr>`;
    }
  }
}
