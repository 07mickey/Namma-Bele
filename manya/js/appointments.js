/**
 * Appointments handler for Farmer Frontend
 * Manages appointment booking, validation, and listing.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Enforce authentication on appointment views
  if (typeof Auth !== 'undefined') {
    Auth.requireAuth();
  }

  const bookingForm = document.getElementById('booking-form');
  const dateInput = document.getElementById('preferred_date');

  // 1. Initialize Date Constraints (min = tomorrow)
  if (dateInput) {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const yyyy = tomorrow.getFullYear();
    const mm = String(tomorrow.getMonth() + 1).padStart(2, '0');
    const dd = String(tomorrow.getDate()).padStart(2, '0');
    const minDateStr = `${yyyy}-${mm}-${dd}`;

    dateInput.min = minDateStr;
    dateInput.value = minDateStr; // sensible default
  }

  // 2. Handle Booking Form Submission
  if (bookingForm) {
    const landDetailsInput = document.getElementById('land_details');
    const addressInput = document.getElementById('address');
    const timeSelect = document.getElementById('preferred_time');
    const notesInput = document.getElementById('notes');
    const submitBtn = document.getElementById('submit-booking-btn');
    const alertBanner = document.getElementById('booking-alert');

    function showError(elementId, errorMsg) {
      const errEl = document.getElementById(elementId);
      const inputEl = document.getElementById(elementId.replace('-error', ''));
      if (errEl) {
        errEl.textContent = errorMsg;
        errEl.classList.add('visible');
      }
      if (inputEl) {
        inputEl.classList.add('is-invalid');
      }
    }

    function clearError(elementId) {
      const errEl = document.getElementById(elementId);
      const inputEl = document.getElementById(elementId.replace('-error', ''));
      if (errEl) {
        errEl.textContent = '';
        errEl.classList.remove('visible');
      }
      if (inputEl) {
        inputEl.classList.remove('is-invalid');
      }
    }

    // Input blur clears
    landDetailsInput?.addEventListener('input', () => clearError('land_details-error'));
    addressInput?.addEventListener('input', () => clearError('address-error'));
    dateInput?.addEventListener('input', () => clearError('preferred_date-error'));

    bookingForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (alertBanner) alertBanner.style.display = 'none';

      let hasError = false;

      // Validate Land Details
      if (!landDetailsInput.value.trim()) {
        showError('land_details-error', 'Please provide your land/plot details.');
        hasError = true;
      } else {
        clearError('land_details-error');
      }

      // Validate Address
      if (!addressInput.value.trim()) {
        showError('address-error', 'Please provide farm location or village address.');
        hasError = true;
      } else {
        clearError('address-error');
      }

      // Validate Date (must be in the future)
      if (!dateInput.value) {
        showError('preferred_date-error', 'Please select a preferred testing date.');
        hasError = true;
      } else {
        const selectedDate = new Date(dateInput.value + 'T00:00:00');
        const now = new Date();
        now.setHours(0, 0, 0, 0);

        if (selectedDate <= now) {
          showError('preferred_date-error', 'Selected date must be tomorrow or in the future.');
          hasError = true;
        } else {
          clearError('preferred_date-error');
        }
      }

      if (hasError) return;

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span>⏳</span> Submitting Request...';

      const payload = {
        land_details: landDetailsInput.value.trim(),
        address: addressInput.value.trim(),
        preferred_date: dateInput.value,
        preferred_time: timeSelect ? timeSelect.value : 'Morning',
        notes: notesInput ? notesInput.value.trim() : ''
      };

      const result = await API.createAppointment(payload);

      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span>📨</span> Submit Soil Test Request';

      if (result.ok) {
        // Redirect to appointments list with success notice
        window.location.href = 'appointments.html?booked=1';
      } else if (result.offline) {
        // Backend offline indicator
        if (alertBanner) {
          alertBanner.className = 'glass-alert glass-alert-offline';
          alertBanner.innerHTML = `<strong>Backend Offline:</strong> ${result.error}`;
          alertBanner.style.display = 'flex';
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      } else {
        // API error
        if (alertBanner) {
          alertBanner.className = 'glass-alert glass-alert-error';
          alertBanner.innerHTML = `<strong>Request Failed:</strong> ${result.error || 'Unable to submit appointment request.'}`;
          alertBanner.style.display = 'flex';
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      }
    });
  }
});

