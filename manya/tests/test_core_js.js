// tests/test_core_js.js
const assert = require('assert');
const { validatePhone, validatePassword, validatePasswordMatch } = require('../js/validation.js');

// Phone tests: must be 10 numeric digits
assert.strictEqual(validatePhone('9876543210').isValid, true);
assert.strictEqual(validatePhone('12345').isValid, false);
assert.strictEqual(validatePhone('98765abcde').isValid, false);
assert.strictEqual(validatePhone('').isValid, false);

// Password tests: min 6 chars
assert.strictEqual(validatePassword('123456').isValid, true);
assert.strictEqual(validatePassword('123').isValid, false);
assert.strictEqual(validatePassword('').isValid, false);

// Password match tests
assert.strictEqual(validatePasswordMatch('secret1', 'secret1').isValid, true);
assert.strictEqual(validatePasswordMatch('secret1', 'secret2').isValid, false);
assert.strictEqual(validatePasswordMatch('secret1', '').isValid, false);

console.log('Core JS validation tests passed.');

