#!/usr/bin/env node
// Usage: node scripts/add-user.js <email> "<password, 12+ characters>" [admin] ["Display name"]
// Prints a JSON fragment to merge into the CARDIOSENSE_USERS environment variable.
const { hashPassword, passwordProblem } = require('../api/_lib/crypto');
const [email, password, role, name] = process.argv.slice(2);
const problem = email && password ? passwordProblem(password, email) : 'Missing email or password.';
if (problem) {
  console.error('Usage: node scripts/add-user.js <email> "<password>" [admin] ["Name"]\n' + problem);
  process.exit(1);
}
console.log(JSON.stringify({
  [email.trim().toLowerCase()]: { hash: hashPassword(password), role: role === 'admin' ? 'admin' : 'clinician', name: name || '' },
}));
