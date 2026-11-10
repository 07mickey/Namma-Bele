/**
 * Client-side validation & sanitization utilities for Farmer Frontend
 * Enforces clean, farmer-friendly data entry before hitting the network.
 */

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function validatePhone(phone) {
  if (!phone || typeof phone !== 'string') {
    return { isValid: false, error: 'Phone number is required.' };
  }
  const trimmed = phone.trim().replace(/[\s\-()]/g, '');
  // Validates standard 10-digit mobile number format or E.164 (+ followed by 8-15 digits)
  const tenDigitRegex = /^[0-9]{10}$/;
  const e164Regex = /^\+[1-9]\d{7,14}$/;
  if (tenDigitRegex.test(trimmed) || e164Regex.test(trimmed)) {
    const formatted = trimmed.startsWith('+') ? trimmed : '+91' + trimmed;
    return { isValid: true, error: '', formatted };
  }
  return { isValid: false, error: 'Please enter a valid 10-digit mobile number or E.164 format (+919876543210).' };
}

function validatePassword(password) {
  if (!password || typeof password !== 'string') {
    return { isValid: false, error: 'Password is required.' };
  }
  if (password.length < 6) {
    return { isValid: false, error: 'Password must be at least 6 characters long.' };
  }
  return { isValid: true, error: '' };
}

function validatePasswordMatch(password, confirmPassword) {
  if (!confirmPassword) {
    return { isValid: false, error: 'Please confirm your password.' };
  }
  if (password !== confirmPassword) {
    return { isValid: false, error: 'Passwords do not match. Please re-check.' };
  }
  return { isValid: true, error: '' };
}

function validateRequired(val, fieldName = 'This field') {
  if (!val || (typeof val === 'string' && val.trim() === '')) {
    return { isValid: false, error: `${fieldName} is required.` };
  }
  return { isValid: true, error: '' };
}

const Validation = {
  escapeHtml,
  validatePhone,
  validatePassword,
  validatePasswordMatch,
  validateRequired
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = Validation;
}
if (typeof window !== 'undefined') {
  window.Validation = Validation;
}
