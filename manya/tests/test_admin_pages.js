// tests/test_admin_pages.js
const fs = require('fs');
const assert = require('assert');

const loginHtml = fs.readFileSync('admin-login.html', 'utf8');
assert(loginHtml.includes('name="username"'), 'Admin login missing username field');
assert(loginHtml.includes('name="password"'), 'Admin login missing password field');
assert(loginHtml.includes('Admin Portal') || loginHtml.includes('Administrator'), 'Admin login missing role badge');

const dashHtml = fs.readFileSync('admin-dashboard.html', 'utf8');
assert(dashHtml.includes('admin-appointments.html'), 'Admin dashboard missing appointments link');
assert(dashHtml.includes('admin-reports.html'), 'Admin dashboard missing reports link');
assert(dashHtml.includes('admin-farmers.html'), 'Admin dashboard missing farmers link');

console.log('Admin pages structure verified.');

