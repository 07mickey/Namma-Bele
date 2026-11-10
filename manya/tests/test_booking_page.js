// tests/test_booking_page.js
const fs = require('fs');
const assert = require('assert');

const html = fs.readFileSync('book-appointment.html', 'utf8');
assert(html.includes('name="land_details"'), 'Missing land_details field');
assert(html.includes('name="address"'), 'Missing address field');
assert(html.includes('name="preferred_date"'), 'Missing preferred_date field');
assert(html.includes('name="preferred_time"'), 'Missing preferred_time field');
assert(html.includes('name="notes"'), 'Missing notes field');
console.log('Booking page elements verified.');

