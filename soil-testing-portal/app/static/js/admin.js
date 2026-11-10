/**
 * Soil Testing Portal — Administrator Management Logic
 * Handles real-time appointment queue, status filtering, bounded pagination,
 * state machine transitions, PDF report upload with progress, and report verification downloads.
 */

document.addEventListener('DOMContentLoaded', async () => {
  let currentUser = null;
  let currentStatusFilter = '';
  let currentPage = 1;
  const perPage = 10;
  let totalPages = 1;
  let loadedAppointments = [];
  let currentReportMap = {};
  let currentSearchQuery = '';

  // DOM Elements
  const adminUserInfo = document.getElementById('admin-user-info');
  const refreshBtn = document.getElementById('btn-admin-refresh');
  const filterButtons = document.querySelectorAll('.filter-btn');
  const loadingIndicator = document.getElementById('admin-loading');
  const emptyState = document.getElementById('admin-empty');
  const emptyMsg = document.getElementById('admin-empty-msg');
  const tableContainer = document.getElementById('admin-table-container');
  const tbody = document.getElementById('admin-tbody');
  const paginationBar = document.getElementById('admin-pagination');
  const paginationInfo = document.getElementById('pagination-info');
  const prevPageBtn = document.getElementById('btn-prev-page');
  const nextPageBtn = document.getElementById('btn-next-page');

  // Search DOM Elements
  const searchInput = document.getElementById('admin-search-input');
  const clearSearchBtn = document.getElementById('btn-clear-search');
  const searchNotice = document.getElementById('admin-search-scope-text');

  // Stat Elements
  const statTotal = document.getElementById('admin-stat-total');
  const statPending = document.getElementById('admin-stat-pending');
  const statApproved = document.getElementById('admin-stat-approved');
  const statRejected = document.getElementById('admin-stat-rejected');
  const statCompleted = document.getElementById('admin-stat-completed');
  const statReports = document.getElementById('admin-stat-reports');

  // Modal Elements
  const modal = document.getElementById('admin-modal');
  const modalTitle = document.getElementById('admin-modal-title');
  const modalBody = document.getElementById('admin-modal-body');
  const modalFooter = document.getElementById('admin-modal-footer');
  const modalCloseBtn = document.getElementById('admin-modal-close');
  const modalCancelBtn = document.getElementById('admin-modal-cancel');

  // 1. Authenticate and enforce admin role
  try {
    const authData = await API.checkAuth();
    if (!authData || !authData.authenticated || !authData.user) {
      window.location.href = '/login';
      return;
    }
    if (authData.user.role !== 'admin') {
      window.location.href = '/farmer';
      return;
    }
    currentUser = authData.user;
    if (adminUserInfo) {
      adminUserInfo.textContent = `${currentUser.name} (${currentUser.phone})`;
    }
  } catch (err) {
    window.location.href = '/login';
    return;
  }

  // 2. Fetch Dashboard Statistics
  async function loadStatistics() {
    try {
      // Fetch counts using status filters
      const [allRes, pendRes, appRes, rejRes, compRes] = await Promise.all([
        API.get('/api/admin/appointments?per_page=1'),
        API.get('/api/admin/appointments?status=Pending&per_page=1'),
        API.get('/api/admin/appointments?status=Approved&per_page=1'),
        API.get('/api/admin/appointments?status=Rejected&per_page=1'),
        API.get('/api/admin/appointments?status=Completed&per_page=100'),
      ]);

      statTotal.textContent = (allRes.pagination && allRes.pagination.total_count) || 0;
      statPending.textContent = (pendRes.pagination && pendRes.pagination.total_count) || 0;
      statApproved.textContent = (appRes.pagination && appRes.pagination.total_count) || 0;
      statRejected.textContent = (rejRes.pagination && rejRes.pagination.total_count) || 0;
      statCompleted.textContent = (compRes.pagination && compRes.pagination.total_count) || 0;

      // Count reports uploaded among completed appointments
      const completedList = (compRes && compRes.appointments) || [];
      const reportChecks = completedList.map(async (appt) => {
        try {
          const rep = await API.get(`/api/admin/appointments/${appt.id}/report`);
          return rep && rep.report ? 1 : 0;
        } catch (_) {
          return 0;
        }
      });
      const checkResults = await Promise.all(reportChecks);
      const totalReports = checkResults.reduce((sum, val) => sum + val, 0);
      statReports.textContent = totalReports;
    } catch (err) {
      console.warn('Failed to load summary statistics:', err);
    }
  }

  // 3. Load Appointments Queue with Filtering & Pagination
  async function loadQueue(page = 1) {
    currentPage = page;
    loadingIndicator.style.display = 'block';
    emptyState.style.display = 'none';
    tableContainer.style.display = 'none';
    paginationBar.style.display = 'none';
    tbody.innerHTML = '';

    let url = `/api/admin/appointments?page=${currentPage}&per_page=${perPage}`;
    if (currentStatusFilter) {
      url += `&status=${encodeURIComponent(currentStatusFilter)}`;
    }

    try {
      const data = await API.get(url);
      const appointments = (data && data.appointments) || [];
      const pagination = data && data.pagination;

      loadingIndicator.style.display = 'none';

      if (appointments.length === 0) {
        emptyState.style.display = 'block';
        emptyMsg.textContent = currentStatusFilter
          ? `No ${currentStatusFilter} appointments found in the queue.`
          : 'No soil testing appointments have been booked yet.';
        return;
      }

      tableContainer.style.display = 'block';

      // Check report presence for completed appointments in this page
      const reportPromises = appointments.map(async (appt) => {
        if (appt.status === 'Completed') {
          try {
            const repData = await API.get(`/api/admin/appointments/${appt.id}/report`);
            return { apptId: appt.id, report: repData.report };
          } catch (_) {
            return { apptId: appt.id, report: null };
          }
        }
        return { apptId: appt.id, report: null };
      });
      const reportResults = await Promise.all(reportPromises);
      const reportMap = {};
      reportResults.forEach((r) => {
        if (r && r.report) reportMap[r.apptId] = r.report;
      });

      loadedAppointments = appointments;
      currentReportMap = reportMap;

      applySearchAndRender();

      // Update Pagination Controls
      if (pagination) {
        totalPages = pagination.total_pages || 1;
        paginationInfo.textContent = `Page ${pagination.page} of ${totalPages} (${pagination.total_count} total)`;
        prevPageBtn.disabled = pagination.page <= 1;
        nextPageBtn.disabled = pagination.page >= totalPages;
        paginationBar.style.display = 'flex';
      }
    } catch (err) {
      loadingIndicator.style.display = 'none';
      showAlert(err.message || 'Failed to load appointment queue.', 'error');
    }
  }

  function applySearchAndRender() {
    tbody.innerHTML = '';
    const query = (searchInput ? searchInput.value : '').trim().toLowerCase();
    currentSearchQuery = query;

    let filtered = loadedAppointments;
    if (query) {
      if (clearSearchBtn) clearSearchBtn.style.display = 'inline-block';
      filtered = loadedAppointments.filter((appt) => {
        const idStr = String(appt.id || '').toLowerCase();
        const nameStr = String(appt.farmer_name || '').toLowerCase();
        const phoneStr = String(appt.farmer_phone || '').toLowerCase();
        const landStr = String(appt.land_details || '').toLowerCase();
        const addrStr = String(appt.address || '').toLowerCase();
        return (
          idStr.includes(query) ||
          nameStr.includes(query) ||
          phoneStr.includes(query) ||
          landStr.includes(query) ||
          addrStr.includes(query)
        );
      });
      if (searchNotice) {
        searchNotice.textContent = `Showing ${filtered.length} of ${loadedAppointments.length} appointments on this page matching "${searchInput.value.trim()}".`;
      }
    } else {
      if (clearSearchBtn) clearSearchBtn.style.display = 'none';
      if (searchNotice) {
        searchNotice.textContent = 'Search filters the appointments loaded on the current page.';
      }
    }

    if (loadedAppointments.length === 0) {
      tableContainer.style.display = 'none';
      emptyState.style.display = 'block';
      emptyMsg.textContent = currentStatusFilter
        ? `No ${currentStatusFilter} appointments found in the queue.`
        : 'No soil testing appointments have been booked yet.';
      return;
    }

    if (filtered.length === 0) {
      tableContainer.style.display = 'none';
      emptyState.style.display = 'block';
      emptyMsg.textContent = `No appointments matching "${searchInput.value.trim()}" found on this page.`;
      return;
    }

    emptyState.style.display = 'none';
    tableContainer.style.display = 'block';

    filtered.forEach((appt) => {
      const tr = document.createElement('tr');
      const report = currentReportMap[appt.id];

      let reportStatusHtml = '<span style="color: var(--slate-400); font-size: 0.85rem;">Pending Visit</span>';
      if (appt.status === 'Completed') {
        if (report) {
          reportStatusHtml = '<span class="badge badge-completed">Report Uploaded</span>';
        } else {
          reportStatusHtml = '<span class="badge badge-pending">Needs Report</span>';
        }
      } else if (appt.status === 'Rejected') {
        reportStatusHtml = '<span style="color: var(--slate-400); font-size: 0.85rem;">Rejected</span>';
      }

      tr.innerHTML = `
        <td><strong>#${escapeHtml(appt.id)}</strong></td>
        <td>
          <div style="font-weight: 600;">${escapeHtml(appt.farmer_name || 'Farmer')}</div>
          <div style="font-size: 0.85rem; color: var(--slate-600);">${escapeHtml(appt.farmer_phone || 'N/A')}</div>
        </td>
        <td>
          <div>${escapeHtml(appt.preferred_date)}</div>
          <div style="font-size: 0.85rem; color: var(--slate-600);">${escapeHtml(appt.preferred_time)}</div>
        </td>
        <td style="max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(appt.land_details)} - ${escapeHtml(appt.address)}">
          <div>${escapeHtml(appt.land_details)}</div>
          <div style="font-size: 0.85rem; color: var(--slate-600);">${escapeHtml(appt.address)}</div>
        </td>
        <td>
          <span class="badge badge-${escapeHtml(appt.status.toLowerCase())}">${escapeHtml(appt.status)}</span>
        </td>
        <td>${reportStatusHtml}</td>
        <td>
          <button class="btn btn-primary btn-sm btn-manage-appt" data-id="${escapeHtml(appt.id)}" type="button">
            Manage
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    // Attach manage button handlers
    document.querySelectorAll('.btn-manage-appt').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        await openManageModal(id);
      });
    });
  }

  // Search input listeners
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      applySearchAndRender();
    });
  }

  if (clearSearchBtn) {
    clearSearchBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      applySearchAndRender();
      if (searchInput) searchInput.focus();
    });
  }

  // Filter Buttons Click Handlers
  filterButtons.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      filterButtons.forEach((b) => b.classList.remove('active'));
      e.currentTarget.classList.add('active');
      currentStatusFilter = e.currentTarget.getAttribute('data-status');
      if (searchInput) searchInput.value = '';
      loadQueue(1);
    });
  });

  // Pagination Button Handlers
  prevPageBtn.addEventListener('click', () => {
    if (currentPage > 1) {
      if (searchInput) searchInput.value = '';
      loadQueue(currentPage - 1);
    }
  });

  nextPageBtn.addEventListener('click', () => {
    if (currentPage < totalPages) {
      if (searchInput) searchInput.value = '';
      loadQueue(currentPage + 1);
    }
  });

  if (refreshBtn) {
    refreshBtn.onclick = () => {
      loadStatistics();
      if (searchInput) searchInput.value = '';
      loadQueue(currentPage);
    };
  }

  // 4. Manage Appointment Modal (Status transitions and Report Upload)
  async function openManageModal(apptId) {
    modalTitle.textContent = `Manage Appointment #${apptId}`;
    modalBody.innerHTML = '<div style="text-align: center; padding: 2rem;"><span class="spinner" style="border-top-color: var(--primary);"></span> Loading appointment details...</div>';
    modalFooter.innerHTML = '<button type="button" class="btn btn-secondary" id="modal-admin-close-1">Close</button>';
    modal.style.display = 'flex';

    document.getElementById('modal-admin-close-1').onclick = closeModal;

    try {
      const data = await API.get(`/api/admin/appointments/${apptId}`);
      const appt = data.appointment;

      // Check if report exists
      let report = null;
      try {
        const repData = await API.get(`/api/admin/appointments/${apptId}/report`);
        report = repData.report;
      } catch (_) {}

      renderModalContent(appt, report);
    } catch (err) {
      modalBody.innerHTML = '';
      const errBox = document.createElement('div');
      errBox.className = 'alert alert-error';
      errBox.textContent = err.message || 'Failed to load appointment details.';
      modalBody.appendChild(errBox);
      if (err.status === 401) {
        showAlert('Your session has expired. Redirecting to login...', 'warning');
        setTimeout(() => { window.location.href = '/login'; }, 1500);
      }
    }
  }

  function renderModalContent(appt, report) {
    // 1. Status transition buttons according to state machine
    let statusActionsHtml = '';
    if (appt.status === 'Pending') {
      statusActionsHtml = `
        <div style="background: var(--slate-100); padding: 1rem; border-radius: var(--radius-sm); margin-top: 1rem;">
          <h4 style="font-size: 0.95rem; margin-bottom: 0.5rem;">Status Actions (Pending State)</h4>
          <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
            <button type="button" class="btn btn-success btn-sm" id="btn-action-approve">
              ✓ Approve Appointment
            </button>
            <button type="button" class="btn btn-danger btn-sm" id="btn-action-reject">
              ✕ Reject Appointment
            </button>
          </div>
        </div>
      `;
    } else if (appt.status === 'Approved') {
      statusActionsHtml = `
        <div style="background: var(--slate-100); padding: 1rem; border-radius: var(--radius-sm); margin-top: 1rem;">
          <h4 style="font-size: 0.95rem; margin-bottom: 0.5rem;">Status Actions (Approved State)</h4>
          <p style="font-size: 0.85rem; color: var(--slate-600); margin-bottom: 0.5rem;">Mark appointment Completed once field visit and soil analysis are finished.</p>
          <button type="button" class="btn btn-primary btn-sm" id="btn-action-complete">
            ✓ Mark as Completed
          </button>
        </div>
      `;
    } else if (appt.status === 'Completed' || appt.status === 'Rejected') {
      statusActionsHtml = `
        <div style="margin-top: 1rem; font-size: 0.85rem; color: var(--slate-600); background: var(--slate-100); padding: 0.75rem; border-radius: var(--radius-sm);">
          Status is <strong>${escapeHtml(appt.status)}</strong> (Terminal State). No further status transitions allowed.
        </div>
      `;
    }

    // 2. Report Upload / Audit Section
    let reportSectionHtml = '';
    if (appt.status === 'Completed') {
      if (report) {
        const sizeKb = (report.file_size_bytes / 1024).toFixed(1);
        reportSectionHtml = `
          <div style="background: var(--status-completed-bg); border: 1px solid #bbf7d0; padding: 1rem; border-radius: var(--radius-sm); margin-top: 1.25rem;">
            <h4 style="color: var(--status-completed-text); margin-bottom: 0.5rem;">Official PDF Report Uploaded</h4>
            <p style="font-size: 0.9rem; margin-bottom: 0.25rem;"><strong>Original Filename:</strong> ${escapeHtml(report.original_filename)} (${sizeKb} KB)</p>
            <p style="font-size: 0.9rem; margin-bottom: 0.25rem;"><strong>Upload Date:</strong> ${escapeHtml(report.uploaded_at)}</p>
            <p style="font-size: 0.8rem; color: var(--slate-600); word-break: break-all; margin-bottom: 0.75rem;"><strong>SHA-256 Checksum:</strong> ${escapeHtml(report.checksum_sha256)}</p>
            <button type="button" class="btn btn-primary btn-sm" id="btn-admin-download-report">
              ⬇️ Download Report for Verification
            </button>
          </div>
        `;
      } else {
        reportSectionHtml = `
          <div style="background: var(--slate-50); border: 1px dashed var(--slate-400); padding: 1.25rem; border-radius: var(--radius-sm); margin-top: 1.25rem;">
            <h4 style="margin-bottom: 0.5rem; color: var(--dark);">Upload Official Soil Test PDF Report</h4>
            <p style="font-size: 0.85rem; color: var(--slate-600); margin-bottom: 0.75rem;">
              Appointment is Completed. Upload the verified lab test report (PDF only, maximum 10 MB).
            </p>
            <form id="upload-report-form">
              <div class="form-group" style="margin-bottom: 0.75rem;">
                <input type="file" id="report-file-input" name="file" accept=".pdf,application/pdf" class="form-control" required>
              </div>
              <div id="upload-feedback" style="display: none; margin-bottom: 0.75rem;"></div>
              <button type="submit" id="btn-submit-upload" class="btn btn-success btn-sm">
                ⬆️ Upload PDF Report
              </button>
            </form>
          </div>
        `;
      }
    }

    modalBody.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
          <span style="font-size: 1.1rem; font-weight: 700;">Status</span>
          <span class="badge badge-${escapeHtml(appt.status.toLowerCase())}">${escapeHtml(appt.status)}</span>
        </div>
        <p style="margin-bottom: 0.35rem;"><strong>Farmer Name:</strong> ${escapeHtml(appt.farmer_name || 'N/A')}</p>
        <p style="margin-bottom: 0.35rem;"><strong>Farmer Phone:</strong> ${escapeHtml(appt.farmer_phone || 'N/A')}</p>
        <p style="margin-bottom: 0.35rem;"><strong>Preferred Date:</strong> ${escapeHtml(appt.preferred_date)}</p>
        <p style="margin-bottom: 0.35rem;"><strong>Time Slot:</strong> ${escapeHtml(appt.preferred_time)}</p>
        <p style="margin-bottom: 0.35rem;"><strong>Land Details:</strong> ${escapeHtml(appt.land_details)}</p>
        <p style="margin-bottom: 0.35rem;"><strong>Address / Location:</strong> ${escapeHtml(appt.address)}</p>
        <p style="margin-bottom: 0.35rem;"><strong>Special Notes:</strong> ${appt.notes ? escapeHtml(appt.notes) : '<em style="color: var(--slate-400);">None</em>'}</p>
        <p style="font-size: 0.85rem; color: var(--slate-600);"><strong>Created:</strong> ${escapeHtml(appt.created_at)} | <strong>Updated:</strong> ${escapeHtml(appt.updated_at || appt.created_at)}</p>
      </div>

      <div id="modal-status-feedback" style="display: none; margin-bottom: 0.75rem;"></div>
      ${statusActionsHtml}
      ${reportSectionHtml}
    `;

    modalFooter.innerHTML = '<button type="button" class="btn btn-secondary" id="modal-admin-close-2">Close</button>';
    document.getElementById('modal-admin-close-2').onclick = closeModal;

    // Attach Status Action Handlers
    const btnApprove = document.getElementById('btn-action-approve');
    if (btnApprove) {
      btnApprove.onclick = () => updateStatus(appt.id, 'Approved');
    }

    const btnReject = document.getElementById('btn-action-reject');
    if (btnReject) {
      btnReject.onclick = () => updateStatus(appt.id, 'Rejected');
    }

    const btnComplete = document.getElementById('btn-action-complete');
    if (btnComplete) {
      btnComplete.onclick = () => updateStatus(appt.id, 'Completed');
    }

    // Attach Report Download Handler
    const btnDl = document.getElementById('btn-admin-download-report');
    if (btnDl && report) {
      btnDl.onclick = async () => {
        btnDl.disabled = true;
        btnDl.innerHTML = '<span class="spinner"></span> Downloading...';
        await API.download(`/api/admin/appointments/${appt.id}/report/download`, report.original_filename);
        btnDl.disabled = false;
        btnDl.innerHTML = '⬇️ Download Report for Verification';
      };
    }

    // Attach Upload Form Handler
    const uploadForm = document.getElementById('upload-report-form');
    if (uploadForm) {
      uploadForm.onsubmit = async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById('report-file-input');
        const uploadBtn = document.getElementById('btn-submit-upload');
        const feedback = document.getElementById('upload-feedback');

        if (!fileInput.files || fileInput.files.length === 0) {
          showUploadFeedback('Please select a PDF file to upload.', 'error');
          return;
        }

        const file = fileInput.files[0];
        if (!file.name.toLowerCase().endsWith('.pdf')) {
          showUploadFeedback('Only PDF files (.pdf extension) are accepted.', 'error');
          return;
        }

        // Client-side 10 MB check
        if (file.size > 10 * 1024 * 1024) {
          showUploadFeedback('File exceeds maximum allowed size of 10 MB.', 'error');
          return;
        }

        const formData = new FormData();
        formData.append('file', file);

        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<span class="spinner"></span> Uploading & verifying PDF...';
        showUploadFeedback('Streaming file and validating PDF structure...', 'info');

        try {
          const res = await API.upload(`/api/admin/appointments/${appt.id}/report`, formData);
          showAlert(`Report for appointment #${appt.id} uploaded successfully!`, 'success');
          // Refresh modal to show uploaded report metadata
          await openManageModal(appt.id);
          // Refresh statistics and queue
          loadStatistics();
          loadQueue(currentPage);
        } catch (err) {
          uploadBtn.disabled = false;
          uploadBtn.innerHTML = '⬆️ Upload PDF Report';
          showUploadFeedback(err.message || 'Report upload failed.', 'error');
        }

        function showUploadFeedback(msg, type) {
          feedback.className = `alert alert-${type}`;
          const span = document.createElement('span');
          span.textContent = msg;
          feedback.replaceChildren(span);
          feedback.style.display = 'block';
        }
      };
    }
  }

  // 5. Update Status API Call
  async function updateStatus(apptId, newStatus) {
    const feedback = document.getElementById('modal-status-feedback');
    if (feedback) {
      feedback.className = 'alert alert-info';
      const span = document.createElement('span');
      span.textContent = `Updating status to ${newStatus}...`;
      feedback.replaceChildren(span);
      feedback.style.display = 'block';
    }

    try {
      const res = await API.patch(`/api/admin/appointments/${apptId}/status`, { status: newStatus });
      showAlert(`Appointment #${apptId} status successfully updated to '${newStatus}'!`, 'success');
      // Reload modal content and refresh queue
      await openManageModal(apptId);
      loadStatistics();
      loadQueue(currentPage);
    } catch (err) {
      if (feedback) {
        feedback.className = 'alert alert-error';
        const span = document.createElement('span');
        span.textContent = err.message || 'Status transition failed.';
        feedback.replaceChildren(span);
        feedback.style.display = 'block';
      }
      showAlert(err.message || 'Status transition failed.', 'error');
      if (err.status === 401) {
        setTimeout(() => { window.location.href = '/login'; }, 1500);
      }
    }
  }

  function closeModal() {
    modal.style.display = 'none';
  }

  modalCloseBtn.onclick = closeModal;
  modalCancelBtn.onclick = closeModal;
  window.onclick = (e) => {
    if (e.target === modal) closeModal();
  };

  // Safe HTML Escaping Helper (coerces all inputs to string and escapes HTML entities)
  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // 6. Registered Farmers Directory (MANYA Design Integration)
  const farmersTbody = document.getElementById('farmers-directory-tbody');
  const farmersSearchInput = document.getElementById('farmer-directory-search');
  let loadedFarmers = [];

  function renderFarmersDirectory(list) {
    if (!farmersTbody) return;
    if (!list || list.length === 0) {
      farmersTbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--color-text-muted); padding: 2rem;">No registered farmers found.</td></tr>`;
      return;
    }

    farmersTbody.innerHTML = list.map(f => `
      <tr>
        <td style="font-weight: 700;">#${escapeHtml(f.id || '')}</td>
        <td style="font-weight: 700; color: var(--color-text-main);">${escapeHtml(f.name || 'Farmer')}</td>
        <td>📱 ${escapeHtml(f.phone || 'N/A')}</td>
        <td><span class="badge" style="background: rgba(107, 138, 40, 0.12); color: var(--namma-green, #6B8A28);">${escapeHtml(f.appointment_count || 0)} Bookings</span></td>
        <td><span class="status-badge status-completed">${escapeHtml(f.account_status || 'ACTIVE')}</span></td>
        <td>
          <a href="tel:${escapeHtml(f.phone || '')}" class="btn btn-secondary btn-sm" style="padding: 0.25rem 0.65rem; font-size: 0.82rem; text-decoration: none;">
            📞 Call
          </a>
        </td>
      </tr>
    `).join('');
  }

  async function loadFarmersDirectory() {
    if (!farmersTbody) return;
    try {
      const res = await API.get('/api/admin/farmers');
      if (res && res.farmers) {
        loadedFarmers = res.farmers;
        renderFarmersDirectory(loadedFarmers);
      }
    } catch (err) {
      console.warn('Failed to load farmers directory:', err);
      if (farmersTbody) {
        farmersTbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--slate-500); padding: 1.5rem;">Could not load farmers list.</td></tr>`;
      }
    }
  }

  if (farmersSearchInput) {
    farmersSearchInput.addEventListener('input', () => {
      const q = (farmersSearchInput.value || '').toLowerCase().trim();
      const filtered = loadedFarmers.filter(f => 
        (f.name || '').toLowerCase().includes(q) ||
        (f.phone || '').includes(q)
      );
      renderFarmersDirectory(filtered);
    });
  }

  // Initial loads
  await loadStatistics();
  await loadQueue(1);
  await loadFarmersDirectory();
});

