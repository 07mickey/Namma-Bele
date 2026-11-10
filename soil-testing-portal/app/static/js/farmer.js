/**
 * Soil Testing Portal — Farmer Dashboard Logic
 * Handles real-time appointment booking, timezone date restrictions (Asia/Kolkata),
 * 3-step wizard interaction, status tabs filtering, appointments listing,
 * detail inspection, and authenticated report downloads.
 */

document.addEventListener('DOMContentLoaded', async () => {
  let currentUser = null;
  let appointmentsList = [];
  let currentTab = 'All';
  let reportMap = {};

  // DOM Elements
  const welcomeName = document.getElementById('farmer-welcome-name');
  const appointmentForm = document.getElementById('appointment-form');
  const preferredDateInput = document.getElementById('preferred_date');
  const preferredTimeSelect = document.getElementById('preferred_time');
  const bookingSubmitBtn = document.getElementById('btn-submit-appointment');
  const bookingError = document.getElementById('booking-error');
  const bookingSuccess = document.getElementById('booking-success');
  const refreshBtn = document.getElementById('btn-refresh-appointments');

  const loadingIndicator = document.getElementById('appointments-loading');
  const emptyState = document.getElementById('appointments-empty');
  const emptyStateTitle = document.getElementById('empty-state-title');
  const emptyStateDesc = document.getElementById('empty-state-desc');
  const tableContainer = document.getElementById('appointments-table-container');
  const tbody = document.getElementById('appointments-tbody');

  // Multi-step Wizard elements
  const stepNode1 = document.getElementById('step-node-1');
  const stepNode2 = document.getElementById('step-node-2');
  const stepNode3 = document.getElementById('step-node-3');
  const stepCircle1 = document.getElementById('step-circle-1');
  const stepCircle2 = document.getElementById('step-circle-2');
  const stepCircle3 = document.getElementById('step-circle-3');
  const stepLine1 = document.getElementById('step-line-1');
  const stepLine2 = document.getElementById('step-line-2');

  const step1Container = document.getElementById('booking-step-1');
  const step2Container = document.getElementById('booking-step-2');
  const step3Container = document.getElementById('booking-step-3');

  const btnStep1Next = document.getElementById('btn-step-1-next');
  const btnStep2Prev = document.getElementById('btn-step-2-prev');
  const btnStep2Next = document.getElementById('btn-step-2-next');
  const btnStep3Prev = document.getElementById('btn-step-3-prev');

  const slotMorningCard = document.getElementById('slot-card-morning');
  const slotAfternoonCard = document.getElementById('slot-card-afternoon');

  const reviewLand = document.getElementById('review-land');
  const reviewAddress = document.getElementById('review-address');
  const reviewDate = document.getElementById('review-date');
  const reviewTime = document.getElementById('review-time');
  const reviewNotes = document.getElementById('review-notes');

  // Status Tab Elements & Counters
  const tabButtons = document.querySelectorAll('.farmer-tab-btn');
  const countAll = document.getElementById('count-all');
  const countPending = document.getElementById('count-pending');
  const countApproved = document.getElementById('count-approved');
  const countRejected = document.getElementById('count-rejected');
  const countCompleted = document.getElementById('count-completed');

  // Modal elements
  const modal = document.getElementById('appointment-modal');
  const modalTitle = document.getElementById('modal-title');
  const modalBody = document.getElementById('modal-body');
  const modalFooter = document.getElementById('modal-footer');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const modalCancelBtn = document.getElementById('modal-cancel-btn');

  // Stat elements
  const statTotal = document.getElementById('stat-total');
  const statPending = document.getElementById('stat-pending');
  const statApproved = document.getElementById('stat-approved');
  const statRejected = document.getElementById('stat-rejected');
  const statCompleted = document.getElementById('stat-completed');
  const statReports = document.getElementById('stat-reports');

  // 1. Authenticate and enforce farmer role
  try {
    const authData = await API.checkAuth();
    if (!authData || !authData.authenticated || !authData.user) {
      window.location.href = '/login';
      return;
    }
    const userRole = (authData.user.role || '').toLowerCase();
    if (!userRole.includes('farmer')) {
      if (userRole.includes('admin') || userRole.includes('coordinator')) {
        window.location.href = '/admin';
      } else if (userRole.includes('operator')) {
        window.location.href = '/operator';
      } else if (userRole.includes('field')) {
        window.location.href = '/field-worker';
      } else if (userRole.includes('lab')) {
        window.location.href = '/lab';
      } else if (userRole.includes('advisor')) {
        window.location.href = '/advisor';
      } else {
        window.location.href = '/login';
      }
      return;
    }
    currentUser = authData.user;
    if (welcomeName && currentUser.name) {
      welcomeName.textContent = currentUser.name;
    }
  } catch (err) {
    console.warn('Farmer auth verification fallback:', err);
  }

  // 2. Set min date on preferred_date input strictly according to Asia/Kolkata timezone
  function setKolkataMinDate() {
    try {
      const kolkataDateStr = new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Asia/Kolkata',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).format(new Date()); // Formats as YYYY-MM-DD
      preferredDateInput.min = kolkataDateStr;
      preferredDateInput.value = kolkataDateStr;
    } catch (_) {
      // Fallback to local ISO date
      const localIso = new Date().toISOString().split('T')[0];
      preferredDateInput.min = localIso;
      preferredDateInput.value = localIso;
    }
  }
  setKolkataMinDate();

  // Helper: Format date strings
  function formatDate(dStr) {
    if (!dStr) return 'N/A';
    return dStr;
  }

  // 3. Multi-Step Stepper Navigation State Manager
  function goToStep(stepNum) {
    hideBookingAlerts();

    // Hide all step views
    step1Container.classList.remove('active');
    step2Container.classList.remove('active');
    step3Container.classList.remove('active');

    // Reset stepper indicators
    stepNode1.classList.remove('active', 'completed');
    stepNode2.classList.remove('active', 'completed');
    stepNode3.classList.remove('active', 'completed');
    stepLine1.classList.remove('active');
    stepLine2.classList.remove('active');

    stepCircle1.textContent = '1';
    stepCircle2.textContent = '2';
    stepCircle3.textContent = '3';

    if (stepNum === 1) {
      step1Container.classList.add('active');
      stepNode1.classList.add('active');
    } else if (stepNum === 2) {
      step2Container.classList.add('active');
      stepNode1.classList.add('completed');
      stepCircle1.textContent = '✓';
      stepLine1.classList.add('active');
      stepNode2.classList.add('active');
    } else if (stepNum === 3) {
      step3Container.classList.add('active');
      stepNode1.classList.add('completed');
      stepCircle1.textContent = '✓';
      stepLine1.classList.add('active');
      stepNode2.classList.add('completed');
      stepCircle2.textContent = '✓';
      stepLine2.classList.add('active');
      stepNode3.classList.add('active');
    }
  }

  // Step 1 -> Step 2 validation & transition
  if (btnStep1Next) {
    btnStep1Next.addEventListener('click', () => {
      const landVal = document.getElementById('land_details').value.trim();
      const addrVal = document.getElementById('address').value.trim();
      const dateVal = document.getElementById('preferred_date').value;

      if (!landVal) {
        showBookingError('Land / Field details are required.');
        return;
      }
      if (!addrVal) {
        showBookingError('Field location address is required.');
        return;
      }
      if (!dateVal) {
        showBookingError('Please choose a collection date.');
        return;
      }
      if (dateVal < preferredDateInput.min) {
        showBookingError(`Appointment date cannot be in the past (${preferredDateInput.min} or later).`);
        return;
      }

      goToStep(2);
    });
  }

  // Step 2 Slot Cards Interaction
  function selectSlot(slotValue) {
    preferredTimeSelect.value = slotValue;
    if (slotValue === '09:00-12:00') {
      slotMorningCard.classList.add('selected');
      slotAfternoonCard.classList.remove('selected');
      const radioM = slotMorningCard.querySelector('input[type="radio"]');
      if (radioM) radioM.checked = true;
    } else {
      slotAfternoonCard.classList.add('selected');
      slotMorningCard.classList.remove('selected');
      const radioA = slotAfternoonCard.querySelector('input[type="radio"]');
      if (radioA) radioA.checked = true;
    }
  }

  if (slotMorningCard && slotAfternoonCard) {
    slotMorningCard.addEventListener('click', () => selectSlot('09:00-12:00'));
    slotAfternoonCard.addEventListener('click', () => selectSlot('14:00-17:00'));
  }

  // Step 2 Buttons
  if (btnStep2Prev) {
    btnStep2Prev.addEventListener('click', () => goToStep(1));
  }

  if (btnStep2Next) {
    btnStep2Next.addEventListener('click', () => {
      const chosenSlot = preferredTimeSelect.value;
      if (!chosenSlot) {
        showBookingError('Please select a collection time window.');
        return;
      }

      // Populate Step 3 Review Card
      reviewLand.textContent = document.getElementById('land_details').value.trim();
      reviewAddress.textContent = document.getElementById('address').value.trim();
      reviewDate.textContent = formatDate(document.getElementById('preferred_date').value);
      reviewTime.textContent = chosenSlot === '09:00-12:00' ? 'Morning Window (09:00 AM – 12:00 PM)' : 'Afternoon Window (02:00 PM – 05:00 PM)';
      const notesVal = document.getElementById('notes').value.trim();
      reviewNotes.textContent = notesVal || 'None provided';

      goToStep(3);
    });
  }

  // Step 3 Prev Button
  if (btnStep3Prev) {
    btnStep3Prev.addEventListener('click', () => goToStep(2));
  }

  // 4. Load Farmer's Appointments
  async function loadAppointments() {
    loadingIndicator.style.display = 'block';
    emptyState.style.display = 'none';
    tableContainer.style.display = 'none';
    tbody.innerHTML = '';

    try {
      const data = await API.get('/api/appointments');
      appointmentsList = (data && data.appointments) || [];

      // Update statistics & tab counts
      let pendingCount = 0;
      let approvedCount = 0;
      let rejectedCount = 0;
      let completedCount = 0;

      appointmentsList.forEach((appt) => {
        if (appt.status === 'Pending') pendingCount++;
        else if (appt.status === 'Approved') approvedCount++;
        else if (appt.status === 'Rejected') rejectedCount++;
        else if (appt.status === 'Completed') completedCount++;
      });

      statTotal.textContent = appointmentsList.length;
      statPending.textContent = pendingCount;
      statApproved.textContent = approvedCount;
      statRejected.textContent = rejectedCount;
      statCompleted.textContent = completedCount;

      // Update Tab Counter Badges
      if (countAll) countAll.textContent = appointmentsList.length;
      if (countPending) countPending.textContent = pendingCount;
      if (countApproved) countApproved.textContent = approvedCount;
      if (countRejected) countRejected.textContent = rejectedCount;
      if (countCompleted) countCompleted.textContent = completedCount;

      loadingIndicator.style.display = 'none';

      // Concurrently check report availability for Completed appointments
      let reportsCount = 0;
      const reportPromises = appointmentsList.map(async (appt) => {
        if (appt.status === 'Completed') {
          try {
            const reportData = await API.get(`/api/appointments/${appt.id}/report`);
            if (reportData && reportData.report) {
              reportsCount++;
              return { apptId: appt.id, report: reportData.report };
            }
          } catch (_) {
            return { apptId: appt.id, report: null };
          }
        }
        return { apptId: appt.id, report: null };
      });

      const reportResults = await Promise.all(reportPromises);
      reportMap = {};
      reportResults.forEach((r) => {
        if (r && r.report) {
          reportMap[r.apptId] = r.report;
        }
      });
      statReports.textContent = reportsCount;

      // Update Latest Appointment Status Card (M2 Integration)
      const latestStatusBadge = document.getElementById('status-badge-container');
      const latestStatusContent = document.getElementById('status-card-content');
      if (latestStatusBadge && latestStatusContent) {
        if (appointmentsList.length === 0) {
          latestStatusBadge.innerHTML = '<span class="badge" style="background: rgba(110, 140, 120, 0.15); color: var(--color-text-muted);">No Active Request</span>';
          latestStatusContent.innerHTML = `
            <p style="color: var(--color-text-muted); margin-bottom: 0.75rem; font-size: 0.92rem;">
              You have not requested any soil-testing appointments yet.
            </p>
            <a href="#booking-section" class="btn btn-primary btn-sm">
              Request Your First Soil Test &rarr;
            </a>
          `;
        } else {
          const sorted = [...appointmentsList].sort((a, b) => (b.id || 0) - (a.id || 0));
          const latest = sorted[0];
          const status = (latest.status || 'Pending').trim();
          let badgeClass = 'badge-pending';
          let explanation = 'Your appointment request has been submitted and is currently being reviewed by the agricultural coordinator.';

          if (status.toLowerCase() === 'approved') {
            badgeClass = 'badge-approved';
            explanation = 'Your appointment has been approved! The field coordinator will visit your land on the scheduled date for sample collection.';
          } else if (status.toLowerCase() === 'completed') {
            badgeClass = 'badge-completed';
            explanation = 'Soil laboratory analysis is complete! Your official PDF report has been generated and is available for download.';
          } else if (status.toLowerCase() === 'rejected') {
            badgeClass = 'badge-rejected';
            explanation = 'Your request could not be accepted for the selected date. Please review the notes or book an alternate date.';
          }

          latestStatusBadge.innerHTML = `<span class="badge ${badgeClass}">${escapeHtml(status)}</span>`;

          latestStatusContent.innerHTML = `
            <div class="status-details-grid">
              <div class="detail-item">
                <span class="detail-label">Land / Field Details</span>
                <span class="detail-value">${escapeHtml(latest.land_details || 'Field Details Provided')}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Field Address</span>
                <span class="detail-value">${escapeHtml(latest.address || 'Village Address Provided')}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Scheduled Date &amp; Slot</span>
                <span class="detail-value">${escapeHtml(formatDate(latest.preferred_date) || 'N/A')} (${escapeHtml(latest.preferred_time || 'General')})</span>
              </div>
            </div>

            <div class="status-explanation">
              <strong>Status Note:</strong> ${explanation}
              ${status.toLowerCase() === 'completed' ? `<div style="margin-top: 0.75rem;"><button type="button" class="btn btn-primary btn-sm" onclick="const btn = document.querySelector('.btn-view-details[data-id=\\'${latest.id}\\']'); if(btn){btn.click();} else {window.location.hash = '#appointments-table-container';}">📄 View / Download Verified PDF Report</button></div>` : ''}
            </div>
          `;
        }
      }

      // Render appointments according to active filter tab
      renderAppointmentsTable();
    } catch (err) {
      loadingIndicator.style.display = 'none';
      showAlert(err.message || 'Failed to load appointments.', 'error');
    }
  }

  // 5. Render Appointments Table with Status Filtering & Empty States
  function renderAppointmentsTable() {
    tbody.innerHTML = '';

    const filtered = appointmentsList.filter((appt) => {
      if (currentTab === 'All') return true;
      return appt.status.toLowerCase() === currentTab.toLowerCase();
    });

    if (filtered.length === 0) {
      tableContainer.style.display = 'none';
      emptyState.style.display = 'block';

      if (appointmentsList.length === 0) {
        if (emptyStateTitle) emptyStateTitle.textContent = 'No appointments found';
        if (emptyStateDesc) emptyStateDesc.textContent = 'You have not booked any soil testing appointments yet. Use the form above to book your first test.';
      } else {
        if (emptyStateTitle) emptyStateTitle.textContent = `No ${currentTab} appointments`;
        if (emptyStateDesc) emptyStateDesc.textContent = `There are currently no bookings with status "${currentTab}". Switch tabs above to view other appointments.`;
      }
      return;
    }

    emptyState.style.display = 'none';
    tableContainer.style.display = 'block';

    // Render table rows safely
    filtered.forEach((appt) => {
      const tr = document.createElement('tr');
      const report = reportMap[appt.id];

      let reportCellHtml = '<span style="color: var(--slate-400); font-size: 0.85rem;">Not available</span>';
      if (appt.status === 'Completed') {
        if (report) {
          reportCellHtml = `
            <button class="btn btn-outline btn-sm btn-download-row" data-id="${escapeHtml(appt.id)}" data-filename="${escapeHtml(report.original_filename)}" type="button">
              ⬇️ Download PDF
            </button>
          `;
        } else {
          reportCellHtml = '<span class="badge" style="background: var(--slate-100); color: var(--slate-600);">Lab Report Pending</span>';
        }
      }

      tr.innerHTML = `
        <td><strong>#${escapeHtml(appt.id)}</strong></td>
        <td>
          <div>${escapeHtml(formatDate(appt.preferred_date))}</div>
          <div style="font-size: 0.85rem; color: var(--slate-600);">${escapeHtml(appt.preferred_time)}</div>
        </td>
        <td style="max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(appt.land_details)}">
          ${escapeHtml(appt.land_details)}
        </td>
        <td style="max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(appt.address)}">
          ${escapeHtml(appt.address)}
        </td>
        <td>
          <span class="badge badge-${escapeHtml(appt.status.toLowerCase())}">${escapeHtml(appt.status)}</span>
        </td>
        <td>${reportCellHtml}</td>
        <td>
          <button class="btn btn-secondary btn-sm btn-view-details" data-id="${escapeHtml(appt.id)}" type="button">
            View Details
          </button>
          <a href="/farmer/tracking?id=${escapeHtml(appt.id)}" class="btn btn-secondary btn-sm" style="color: var(--color-forest-green); font-weight: 600; text-decoration: none;">
            🛰️ Track
          </a>
        </td>
      `;
      tbody.appendChild(tr);
    });

    // Attach download button handlers
    tbody.querySelectorAll('.btn-download-row').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        const filename = e.currentTarget.getAttribute('data-filename') || `Soil_Report_${id}.pdf`;
        await downloadReport(id, filename);
      });
    });

    // Attach view details button handlers
    tbody.querySelectorAll('.btn-view-details').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        await openAppointmentModal(id);
      });
    });
  }

  // 6. Setup Tab Button Click Handlers
  tabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      tabButtons.forEach((b) => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      currentTab = btn.getAttribute('data-status') || 'All';
      renderAppointmentsTable();
    });
  });

  // 7. Create Appointment Form Handler (Executed on Step 3)
  appointmentForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideBookingAlerts();

    const land_details = document.getElementById('land_details').value.trim();
    const address = document.getElementById('address').value.trim();
    const preferred_date = document.getElementById('preferred_date').value;
    const preferred_time = document.getElementById('preferred_time').value;
    const notes = document.getElementById('notes').value.trim();

    // Client-side validations
    if (!land_details) {
      showBookingError('Land / Field details are required.');
      goToStep(1);
      return;
    }
    if (!address) {
      showBookingError('Field location address is required.');
      goToStep(1);
      return;
    }
    if (!preferred_date) {
      showBookingError('Please choose a collection date.');
      goToStep(1);
      return;
    }
    if (preferred_date < preferredDateInput.min) {
      showBookingError(`Appointment date cannot be in the past (${preferredDateInput.min} or later).`);
      goToStep(1);
      return;
    }
    if (!preferred_time) {
      showBookingError('Please select a preferred time slot.');
      goToStep(2);
      return;
    }

    const payload = {
      land_details,
      address,
      preferred_date,
      preferred_time,
      notes: notes || undefined,
    };

    bookingSubmitBtn.disabled = true;
    bookingSubmitBtn.innerHTML = '<span class="spinner"></span> Submitting Request...';

    try {
      const res = await API.post('/api/appointments', payload);
      bookingSubmitBtn.disabled = false;
      bookingSubmitBtn.textContent = 'Confirm & Book Appointment';

      showBookingSuccess(`Appointment #${res.appointment.id} successfully booked! Status is Pending.`);
      showAlert(`Appointment #${res.appointment.id} created successfully! Initial status is Pending.`, 'success');

      // Reset form and wizard to Step 1
      appointmentForm.reset();
      setKolkataMinDate();
      selectSlot('09:00-12:00');
      goToStep(1);

      // Reload appointments table
      await loadAppointments();
    } catch (err) {
      bookingSubmitBtn.disabled = false;
      bookingSubmitBtn.textContent = 'Confirm & Book Appointment';
      showBookingError(err.message || 'Failed to book appointment. Please check all fields.');
    }
  });

  function showBookingError(msg) {
    bookingError.textContent = msg;
    bookingError.style.display = 'block';
  }

  function showBookingSuccess(msg) {
    bookingSuccess.textContent = msg;
    bookingSuccess.style.display = 'block';
  }

  function hideBookingAlerts() {
    bookingError.style.display = 'none';
    bookingSuccess.style.display = 'none';
  }

  // 8. Open Appointment Details Modal with Friendly Status Explanation
  async function openAppointmentModal(apptId) {
    modalTitle.textContent = `Appointment #${apptId} Details`;
    modalBody.innerHTML = '<div style="text-align: center; padding: 1.5rem;"><span class="spinner" style="border-top-color: var(--primary);"></span> Loading details...</div>';
    modalFooter.innerHTML = '<button type="button" class="btn btn-secondary" id="modal-close-inner">Close</button>';
    modal.style.display = 'flex';

    document.getElementById('modal-close-inner').onclick = closeModal;

    try {
      const data = await API.get(`/api/appointments/${apptId}`);
      const appt = data.appointment;

      // Status Explanation Banner (Adapted from M2's farmer-centric messaging)
      let statusExplanation = '';
      if (appt.status === 'Pending') {
        statusExplanation = '<div style="background: rgba(245, 158, 11, 0.12); border-left: 4px solid #b45309; padding: 0.75rem 1rem; border-radius: 4px; font-size: 0.88rem; color: #92400e; margin-bottom: 1rem;"><strong>Pending Review:</strong> Your appointment request has been recorded and is awaiting laboratory extension coordinator assignment.</div>';
      } else if (appt.status === 'Approved') {
        statusExplanation = '<div style="background: rgba(2, 132, 199, 0.12); border-left: 4px solid #0369a1; padding: 0.75rem 1rem; border-radius: 4px; font-size: 0.88rem; color: #075985; margin-bottom: 1rem;"><strong>Approved:</strong> A field coordinator will visit your plot on the scheduled date for core soil sampling.</div>';
      } else if (appt.status === 'Rejected') {
        statusExplanation = '<div style="background: rgba(225, 29, 72, 0.12); border-left: 4px solid #be123c; padding: 0.75rem 1rem; border-radius: 4px; font-size: 0.88rem; color: #9f1239; margin-bottom: 1rem;"><strong>Declined:</strong> This request could not be accommodated. You may submit a new request with revised dates or notes.</div>';
      } else if (appt.status === 'Completed') {
        statusExplanation = '<div style="background: rgba(22, 163, 74, 0.12); border-left: 4px solid #15803d; padding: 0.75rem 1rem; border-radius: 4px; font-size: 0.88rem; color: #166534; margin-bottom: 1rem;"><strong>Completed:</strong> Laboratory soil analysis is complete and your certified test report is ready for download.</div>';
      }

      let reportHtml = '';
      let downloadBtnHtml = '';

      if (appt.status === 'Completed') {
        try {
          const repData = await API.get(`/api/appointments/${apptId}/report`);
          const rep = repData.report;
          const sizeKb = (rep.file_size_bytes / 1024).toFixed(1);
          reportHtml = `
            <div style="background: var(--status-completed-bg); border: 1px solid #bbf7d0; padding: 1rem; border-radius: var(--radius-sm); margin-top: 1rem;">
              <h4 style="color: var(--status-completed-text); margin-bottom: 0.5rem;">Official Soil Test Report Available</h4>
              <p style="font-size: 0.9rem; margin-bottom: 0.25rem;"><strong>File:</strong> ${escapeHtml(rep.original_filename)} (${sizeKb} KB)</p>
              <p style="font-size: 0.9rem; margin-bottom: 0.25rem;"><strong>Uploaded At:</strong> ${escapeHtml(rep.uploaded_at)}</p>
              <p style="font-size: 0.8rem; color: var(--slate-600); word-break: break-all;"><strong>SHA-256 Checksum:</strong> ${escapeHtml(rep.checksum_sha256)}</p>
            </div>
          `;
          downloadBtnHtml = `
            <button type="button" class="btn btn-primary" id="btn-modal-download">
              ⬇️ Download Report (PDF)
            </button>
          `;
        } catch (_) {
          reportHtml = `
            <div class="alert alert-info" style="margin-top: 1rem;">
              <span>Soil sample collected. The official laboratory report has not been uploaded yet. Please check back soon.</span>
            </div>
          `;
        }
      } else {
        reportHtml = `
          <div class="alert alert-warning" style="margin-top: 1rem;">
            <span>Report will be uploaded by lab technicians once appointment status is Completed.</span>
          </div>
        `;
      }

      modalBody.innerHTML = `
        ${statusExplanation}
        <div style="margin-bottom: 1rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <span style="font-size: 1.1rem; font-weight: 700;">Status</span>
            <span class="badge badge-${escapeHtml(appt.status.toLowerCase())}">${escapeHtml(appt.status)}</span>
          </div>
          <p style="margin-bottom: 0.5rem;"><strong>Preferred Date:</strong> ${escapeHtml(appt.preferred_date)}</p>
          <p style="margin-bottom: 0.5rem;"><strong>Preferred Time Slot:</strong> ${escapeHtml(appt.preferred_time)}</p>
          <p style="margin-bottom: 0.5rem;"><strong>Field Details:</strong> ${escapeHtml(appt.land_details)}</p>
          <p style="margin-bottom: 0.5rem;"><strong>Address:</strong> ${escapeHtml(appt.address)}</p>
          <p style="margin-bottom: 0.5rem;"><strong>Notes:</strong> ${appt.notes ? escapeHtml(appt.notes) : '<em style="color: var(--slate-400);">None provided</em>'}</p>
          <p style="font-size: 0.85rem; color: var(--slate-600);"><strong>Created:</strong> ${escapeHtml(appt.created_at)}</p>
        </div>
        ${reportHtml}
      `;

      modalFooter.innerHTML = `
        ${downloadBtnHtml}
        <button type="button" class="btn btn-secondary" id="modal-close-inner-2">Close</button>
      `;

      document.getElementById('modal-close-inner-2').onclick = closeModal;

      const modalDl = document.getElementById('btn-modal-download');
      if (modalDl) {
        modalDl.onclick = async () => {
          modalDl.disabled = true;
          modalDl.innerHTML = '<span class="spinner"></span> Downloading...';
          await downloadReport(apptId, `Soil_Report_${apptId}.pdf`);
          modalDl.disabled = false;
          modalDl.innerHTML = '⬇️ Download Report (PDF)';
        };
      }
    } catch (err) {
      modalBody.innerHTML = '';
      const errBox = document.createElement('div');
      errBox.className = 'alert alert-error';
      errBox.textContent = err.message || 'Failed to load details.';
      modalBody.appendChild(errBox);
      if (err.status === 401) {
        showAlert('Your session has expired. Redirecting to login...', 'warning');
        setTimeout(() => { window.location.href = '/login'; }, 1500);
      }
    }
  }

  // 9. Download Report Binary
  async function downloadReport(apptId, filename) {
    showAlert('Initiating secure report download...', 'info', 2000);
    try {
      await API.download(`/api/appointments/${apptId}/report/download`, filename);
      showAlert('Report downloaded successfully!', 'success');
    } catch (err) {
      showAlert(err.message || 'Failed to download report PDF.', 'error');
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

  if (refreshBtn) {
    refreshBtn.onclick = () => loadAppointments();
  }

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

  // Initial load
  await loadAppointments();
});
