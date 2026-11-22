'use strict';
const A = require('./_lib/auth');
const R = require('./_lib/releases');

module.exports = A.handle(async (req, res) => {
  if (!(await A.requireSession(req, res))) return;
  try {
    const { version, builds, checksums } = await R.latest();
    A.json(res, 200, { version, builds, checksums });
  } catch {
    A.json(res, 502, { error: 'Could not reach the release server. Try again shortly.' });
  }
});
