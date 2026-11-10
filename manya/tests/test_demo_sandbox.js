// tests/test_demo_sandbox.js
const assert = require('assert');
const fs = require('fs');

// 1. Verify Farmer Login has automatic pre-filling in HTML and script
const loginHtml = fs.readFileSync('login.html', 'utf8');
assert(loginHtml.includes('value="9876543210"'), 'login.html missing pre-filled value for phone input');
assert(loginHtml.includes('value="password123"'), 'login.html missing pre-filled value for password input');
assert(loginHtml.includes('fillFarmerCredentials()'), 'login.html missing fillFarmerCredentials invocation');
assert(loginHtml.includes('loginDemoMode'), 'login.html missing demo login option');

// 2. Verify Admin Login has automatic pre-filling in HTML and script
const adminLoginHtml = fs.readFileSync('admin-login.html', 'utf8');
assert(adminLoginHtml.includes('value="admin"'), 'admin-login.html missing pre-filled value for username input');
assert(adminLoginHtml.includes('value="admin123"'), 'admin-login.html missing pre-filled value for password input');
assert(adminLoginHtml.includes('fillAdminCredentials()'), 'admin-login.html missing fillAdminCredentials invocation');
assert(adminLoginHtml.includes('loginAdminDemoMode'), 'admin-login.html missing admin demo login option');
assert(adminLoginHtml.includes('js/api.js'), 'admin-login.html missing js/api.js inclusion');

// 3. Verify Farmer Registration has pre-filled demo data and autofill handler
const registerHtml = fs.readFileSync('register.html', 'utf8');
assert(registerHtml.includes('value="Ramesh Patil"'), 'register.html missing pre-filled value for name input');
assert(registerHtml.includes('value="9876543210"'), 'register.html missing pre-filled value for phone input');
assert(registerHtml.includes('fillSampleRegistration()'), 'register.html missing fillSampleRegistration invocation');

// 4. Verify DemoStore operations in js/api.js
const { DemoStore, API } = require('../js/api.js');
assert(typeof DemoStore !== 'undefined', 'DemoStore must be exported from js/api.js');
const initialApts = DemoStore.getAppointments();
assert(Array.isArray(initialApts) && initialApts.length >= 3, 'DemoStore must provide initial sample appointments');

// Test status updating
const updated = DemoStore.updateStatus(101, 'Approved');
assert.strictEqual(updated, true, 'DemoStore.updateStatus must return true for valid appointment');

// Test adding an appointment
const newApt = DemoStore.addAppointment({
  land_details: 'Survey 99, South Acre',
  address: 'Demo Village',
  preferred_date: '2026-11-20',
  preferred_time: 'Morning (8:00 AM - 12:00 PM)',
  notes: 'Testing DemoStore'
});
assert(newApt && newApt.id, 'DemoStore.addAppointment must generate an ID');
assert.strictEqual(newApt.status, 'Pending', 'New appointment must have initial status Pending');

// Test adding a report
const newRep = DemoStore.addReport({
  appointment_id: newApt.id,
  remarks: 'Test soil report'
});
assert(newRep && newRep.id, 'DemoStore.addReport must generate a report');

// Test PDF blob generator
const sampleBlob = DemoStore.generateSamplePdfBlob('101');
assert(sampleBlob instanceof Blob || typeof sampleBlob === 'object', 'DemoStore must generate sample blob');

console.log('Demo sandbox and automatic credential pre-filling verified successfully.');
