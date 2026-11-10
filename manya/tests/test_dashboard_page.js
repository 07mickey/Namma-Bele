// tests/test_dashboard_page.js
const fs = require('fs');
const assert = require('assert');

const html = fs.readFileSync('dashboard.html', 'utf8');
assert(html.includes('farmer-name') || html.includes('Welcome'), 'Missing farmer greeting');
assert(html.includes('latest-status') || html.includes('appointment-status'), 'Missing status card');
assert(html.includes('book-appointment.html'), 'Missing book test link');
assert(html.includes('appointments.html'), 'Missing appointments link');
assert(html.includes('reports.html'), 'Missing reports link');
assert(html.includes('logout'), 'Missing logout option');
console.log('Dashboard structure verified.');

