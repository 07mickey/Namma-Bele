// tests/test_admin_module.js
const assert = require('assert');

// Test that admin JS module file exists and has required API signatures
const fs = require('fs');
const content = fs.readFileSync('js/admin.js', 'utf8');

assert(content.includes('adminLogin'), 'Missing adminLogin in js/admin.js');
assert(content.includes('updateAppointmentStatus'), 'Missing updateAppointmentStatus in js/admin.js');
assert(content.includes('uploadReport'), 'Missing uploadReport in js/admin.js');
assert(content.includes('getFarmers'), 'Missing getFarmers in js/admin.js');
assert(content.includes('requireAdminAuth'), 'Missing requireAdminAuth in js/admin.js');

console.log('Admin JS module structure verified.');

