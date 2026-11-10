// tests/test_home_page.js
const fs = require('fs');
const assert = require('assert');

const html = fs.readFileSync('index.html', 'utf8');

// Core Title & Route Links
assert(html.includes('Soil Testing Appointment & Report Access Portal'), 'Missing portal title');
assert(html.includes('How It Works') || html.includes('Process'), 'Missing How it works');
assert(html.includes('login.html'), 'Missing login link');
assert(html.includes('register.html'), 'Missing register link');
assert(html.includes('book-appointment.html'), 'Missing book appointment link');

// Award-Winning Layout Components (Referencing high-end natural UI)
assert(html.includes('bento-grid'), 'Missing editorial bento grid layout');
assert(html.includes('faq-section') || html.includes('faq-item'), 'Missing interactive FAQ accordion section');
assert(html.includes('spotlight') || html.includes('card-spotlight'), 'Missing featured soil health card spotlight');
assert(html.includes('crop-pill') || html.includes('crop-tab'), 'Missing interactive crop selector tabs');
assert(html.includes('sprout') || html.includes('soil-mound'), 'Missing organic soil sprout hero visual element');

console.log('Home page structure and award-winning UI/UX components verified.');
