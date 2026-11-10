// tests/test_appointments_and_reports.js
const fs = require('fs');
const assert = require('assert');

const aptHtml = fs.readFileSync('appointments.html', 'utf8');
assert(aptHtml.includes('appointments-list') || aptHtml.includes('appointment-card'), 'Missing appointments container');
assert(aptHtml.includes('Pending') || aptHtml.includes('status'), 'Missing status references');

const repHtml = fs.readFileSync('reports.html', 'utf8');
assert(repHtml.includes('reports-list') || repHtml.includes('report-card'), 'Missing reports container');
assert(repHtml.includes('download') || repHtml.includes('Download'), 'Missing download option');

console.log('Appointments and reports markup verified.');

