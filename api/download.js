'use strict';
const A = require('./_lib/auth');
const R = require('./_lib/releases');

module.exports = A.handle(async (req, res) => {
  const s = await A.getSession(req);
  if (!s) {
    res.statusCode = 302;
    res.setHeader('Location', '/signin?next=/download');
    return res.end();
  }
  const id = Number(new URL(req.url, 'http://x').searchParams.get('id'));
  try {
    const { builds, checksums } = await R.latest();
    const allowed = [...builds, ...(checksums ? [checksums] : [])].some((a) => a.id === id);
    if (!allowed) return A.json(res, 404, { error: 'That file is not part of the current release.' });
    const url = await R.signedUrl(id);
    if (!url) return A.json(res, 502, { error: 'The download could not be started. Try again shortly.' });
    await A.audit(s.uid, s.email, 'download', req, id);
    res.statusCode = 302;
    res.setHeader('Location', url);
    res.setHeader('Cache-Control', 'no-store');
    res.end();
  } catch {
    A.json(res, 502, { error: 'The download could not be started. Try again shortly.' });
  }
});
