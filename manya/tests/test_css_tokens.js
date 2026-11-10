// tests/test_css_tokens.js
const fs = require('fs');
const assert = require('assert');

const css = fs.readFileSync('css/styles.css', 'utf8');

// Check required color palette tokens: Green, White, Earth Brown
assert(css.includes('--color-primary-green'), 'Missing --color-primary-green');
assert(css.includes('--color-earth-brown'), 'Missing --color-earth-brown');
assert(css.includes('--glass-bg'), 'Missing --glass-bg');

// Check status badges
assert(css.includes('.status-pending'), 'Missing .status-pending');
assert(css.includes('.status-approved'), 'Missing .status-approved');
assert(css.includes('.status-rejected'), 'Missing .status-rejected');
assert(css.includes('.status-completed'), 'Missing .status-completed');

// Check backdrop-filter
assert(css.includes('backdrop-filter'), 'Missing backdrop-filter for glassmorphism');
console.log('CSS tokens and rules verified successfully.');

