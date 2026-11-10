// tests/test_fix_pass.js
const assert = require('assert');
const { escapeHtml } = require('../js/validation.js');

// 1. Test HTML entity escaping
assert(typeof escapeHtml === 'function', 'escapeHtml must be a defined function');
assert.strictEqual(
  escapeHtml('<script>alert("xss")</script> & \'test\''),
  '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt; &amp; &#39;test&#39;'
);
assert.strictEqual(escapeHtml('Plot 42 & 43'), 'Plot 42 &amp; 43');
assert.strictEqual(escapeHtml(null), '');
assert.strictEqual(escapeHtml(undefined), '');

console.log('Fix pass validation tests passed.');
