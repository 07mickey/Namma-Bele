// tests/test_auth_pages.js
const fs = require('fs');
const assert = require('assert');

const regHtml = fs.readFileSync('register.html', 'utf8');
assert(regHtml.includes('name="name"'), 'Registration missing name field');
assert(regHtml.includes('name="phone"'), 'Registration missing phone field');
assert(regHtml.includes('name="password"'), 'Registration missing password field');
assert(regHtml.includes('name="confirm_password"'), 'Registration missing confirm password field');

const loginHtml = fs.readFileSync('login.html', 'utf8');
assert(loginHtml.includes('name="phone"'), 'Login missing phone field');
assert(loginHtml.includes('name="password"'), 'Login missing password field');
assert(loginHtml.includes('error-banner') || loginHtml.includes('alert'), 'Login missing error message area');

console.log('Auth pages markup verified.');

