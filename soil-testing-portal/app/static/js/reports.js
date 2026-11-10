/**
 * Reports handler for Farmer Frontend
 * Securely lists and downloads verified PDF soil test reports.
 */

const Reports = {
  async init() {
    if (typeof Auth !== 'undefined') {
      Auth.requireAuth();
    }

    const container = document.getElementById('reports-list');
    const alertBanner = document.getElementById('reports-alert');
    const filterNotice = document.getElementById('filter-notice');
    if (!container) return;

    // Optional query parameter filtering by appointment_id
    const urlParams = new URLSearchParams(window.location.search);
    const filterAppointmentId = urlParams.get('appointment_id');

    if (filterAppointmentId && filterNotice) {
      filterNotice.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.65rem 1rem; background: rgba(255, 255, 255, 0.7); border: 1px solid rgba(27, 67, 50, 0.15); border-radius: var(--radius-md); font-size: 0.88rem;">
          <span>Showing report linked to Appointment <strong>#${Validation.escapeHtml(filterAppointmentId)}</strong></span>
          <a href="reports.html" style="color: var(--color-primary-green); font-weight: 700; text-decoration: none;">View All Reports &rarr;</a>
        </div>
      `;
      filterNotice.style.display = 'block';
    }

    const result = await API.getFarmerReports();

    if (result.offline) {
      if (alertBanner) {
        alertBanner.className = 'glass-alert glass-alert-offline';
        alertBanner.innerHTML = `<strong>Backend Offline:</strong> ${Validation.escapeHtml(result.error)}<br><span style="font-size:0.85rem;">[Notice: Waiting for Person 1's Flask API to serve verified PDF reports.]</span>`;
        alertBanner.style.display = 'flex';
      }
      container.innerHTML = `
        <div class="glass-card" style="text-align: center; padding: 2.75rem 1.5rem;">
          <h3 style="font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--color-text-main);">
            Report Service Awaiting Backend
          </h3>
          <p style="color: var(--color-text-muted); max-width: 480px; margin: 0 auto 1.5rem;">
            When Person 1's backend is running on http://127.0.0.1:5000 and the admin uploads your soil report, your PDF document will be securely accessible here.
          </p>
          <a href="appointments.html" class="btn btn-secondary">Check Appointment Status</a>
        </div>
      `;
      return;
    }

    if (!result.ok) {
      if (alertBanner) {
        alertBanner.className = 'glass-alert glass-alert-error';
        alertBanner.innerHTML = `<strong>Error:</strong> ${Validation.escapeHtml(result.error || 'Failed to fetch reports.')}`;
        alertBanner.style.display = 'flex';
      }
      container.innerHTML = '';
      return;
    }

    let reports = result.data?.reports || [];

    if (filterAppointmentId) {
      reports = reports.filter(r => String(r.appointment_id) === String(filterAppointmentId));
    }

    if (reports.length === 0) {
      container.innerHTML = `
        <div class="glass-card" style="text-align: center; padding: 3rem 1.5rem;">
          <h3 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--color-text-main);">
            No Soil Test Reports Available Yet
          </h3>
          <p style="color: var(--color-text-muted); margin-bottom: 1.5rem; max-width: 480px; margin-left: auto; margin-right: auto;">
            Soil test reports appear here after your field sample has been analyzed in the laboratory and the administrator uploads your official PDF report.
          </p>
          <a href="appointments.html" class="btn btn-primary">View Appointment Status</a>
        </div>
      `;
      return;
    }

    container.innerHTML = reports.map(report => {
      const fileName = report.file_name || `soil_test_report_${report.id || 'doc'}.pdf`;
      const dateFormatted = report.report_date ? new Date(report.report_date).toLocaleDateString() : 'Recent';
      const safeReportId = Validation.escapeHtml(report.id || '');
      const safeFileName = Validation.escapeHtml(fileName);

      return `
        <div class="glass-card report-card glass-card-hover">
          <div class="report-card-top">
            <div class="report-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--color-primary-green);">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
              ${Validation.escapeHtml(report.land_details || 'Farm Land Soil Report')}
            </div>
            <span class="status-badge status-completed">Verified PDF Report</span>
          </div>

          <div class="report-meta-grid">
            <div>
              <span class="detail-label" style="display:block; font-size:0.75rem; color:var(--color-text-subtle); text-transform:uppercase; font-weight:700;">Report Date</span>
              <span style="font-size:0.95rem; font-weight:600; color:var(--color-text-main);">${Validation.escapeHtml(dateFormatted)}</span>
            </div>
            <div>
              <span class="detail-label" style="display:block; font-size:0.75rem; color:var(--color-text-subtle); text-transform:uppercase; font-weight:700;">Appointment Reference</span>
              <span style="font-size:0.95rem; font-weight:600; color:var(--color-text-main);">#${Validation.escapeHtml(report.appointment_id || 'N/A')}</span>
            </div>
            <div>
              <span class="detail-label" style="display:block; font-size:0.75rem; color:var(--color-text-subtle); text-transform:uppercase; font-weight:700;">Official Document</span>
              <span style="font-size:0.95rem; font-weight:600; color:var(--color-text-main);">${safeFileName}</span>
            </div>
          </div>

          <div class="report-card-bottom">
            <span style="font-size: 0.88rem; color: var(--color-text-muted);">
              Official laboratory soil fertility, N-P-K &amp; organic carbon certificate.
            </span>
            <button 
              type="button"
              onclick="Reports.download(event, '${safeReportId}', '${safeFileName}')" 
              class="btn btn-primary"
              style="padding: 0.5rem 1.35rem; font-size: 0.92rem;"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              Download PDF Report
            </button>
          </div>
        </div>
      `;
    }).join('');
  },

  async download(e, reportId, fileName = 'soil_report.pdf') {
    const btn = e?.currentTarget || (typeof event !== 'undefined' ? event?.currentTarget : null);
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = 'Preparing Download...';
    }

    try {
      const res = await API.downloadReport(reportId);

      if (res.ok && res.data) {
        // Create an Object URL from the blob and trigger browser download
        const blobUrl = window.URL.createObjectURL(res.data);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = blobUrl;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(blobUrl);
        a.remove();
      } else if (res.offline) {
        alert(`Backend Offline: ${res.error}\n\n[Notice: Person 1's Flask backend is not running at http://127.0.0.1:5000]`);
      } else {
        alert(`Download Error: ${res.error || 'Could not access report. Please try again later.'}`);
      }
    } catch (err) {
      alert('Could not download file: ' + err.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Download PDF Report
        `;
      }
    }
  }
};

document.addEventListener('DOMContentLoaded', () => Reports.init());

if (typeof window !== 'undefined') {
  window.Reports = Reports;
}
