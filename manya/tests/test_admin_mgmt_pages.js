// tests/test_admin_mgmt_pages.js
const fs = require('fs');
const assert = require('assert');

const aptsHtml = fs.readFileSync('admin-appointments.html', 'utf8');
assert(aptsHtml.includes('appointments-tbody') || aptsHtml.includes('admin-table'), 'Missing appointments table');
assert(aptsHtml.includes('Approve') || aptsHtml.includes('approve'), 'Missing approve action');
assert(aptsHtml.includes('Reject') || aptsHtml.includes('reject'), 'Missing reject action');

const repsHtml = fs.readFileSync('admin-reports.html', 'utf8');
assert(repsHtml.includes('type="file"'), 'Missing file input for PDF report upload');
assert(repsHtml.includes('reports-tbody') || repsHtml.includes('reports-list'), 'Missing reports table');

const farmersHtml = fs.readFileSync('admin-farmers.html', 'utf8');
assert(farmersHtml.includes('farmers-tbody') || farmersHtml.includes('farmers-list'), 'Missing farmers list');

console.log('Admin management pages structure verified.');

