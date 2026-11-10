// admin_login.js
// Front‑end logic for the Admin Login page.
// -------------------------------------------------
// 1. Validate that email and password fields are not empty.
// 2. Show a simple error message if validation fails.
// 3. Toggle password visibility when the eye button is pressed.
// 4. Display a loading spinner on the Login button while a request would be sent.
// 5. Stub for future integration with the Flask backend API.
// -------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('loginForm');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const toggleBtn = document.getElementById('togglePassword');
    const errorDiv = document.getElementById('errorMessage');
    const loginBtn = document.getElementById('loginButton');
    const spinner = loginBtn.querySelector('.spinner');
    const btnText = loginBtn.querySelector('.btn-text');

    // Helper to show error message
    const showError = (msg) => {
        errorDiv.textContent = msg;
    };

    // Helper to clear error message
    const clearError = () => {
        errorDiv.textContent = '';
    };

    // Toggle password visibility
    toggleBtn.addEventListener('click', () => {
        const type = passwordInput.type === 'password' ? 'text' : 'password';
        passwordInput.type = type;
        // Change aria‑label for accessibility
        toggleBtn.setAttribute('aria-label', type === 'password' ? 'Show password' : 'Hide password');
    });

    // Form submission handler – performs client‑side validation only.
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        clearError();
        const email = emailInput.value.trim();
        const password = passwordInput.value;

        // Empty‑field validation
        if (!email) {
            showError('Please enter your email address.');
            emailInput.focus();
            return;
        }
        if (!password) {
            showError('Please enter your password.');
            passwordInput.focus();
            return;
        }

        // Show loading state
        loginBtn.disabled = true;
        spinner.classList.remove('hidden');
        btnText.textContent = 'Logging in…';

        // --- Backend integration point ---
        // Replace the following setTimeout with a real fetch call, e.g.:
        // const response = await fetch('/api/admin/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });
        // const data = await response.json();
        // handle success / error based on response status.
        // ---------------------------------
        // Temporary placeholder to demonstrate the loading UI.
        await new Promise((resolve) => setTimeout(resolve, 1500));

        // Since we do not have a backend yet, always show an error.
        showError('Login service not available – backend integration pending.');

        // Reset button state
        loginBtn.disabled = false;
        spinner.classList.add('hidden');
        btnText.textContent = 'Login';
    });
});
