#!/usr/bin/env node
// Usage: node scripts/add-user.js someone@example.com "a strong password"
// Prints a JSON fragment to merge into the CARDIOSENSE_USERS environment variable.
const { hashPassword } = require('../api/_lib/auth');
const [email, password] = process.argv.slice(2);
if (!email || !password || password.length < 10) {
  console.error('Usage: node scripts/add-user.js <email> <password of 10+ characters>');
  process.exit(1);
}
console.log(JSON.stringify({ [email.trim().toLowerCase()]: hashPassword(password) }));
