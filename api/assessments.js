'use strict';
const A = require('./_lib/auth');
const V = require('./_lib/validate');
const sync = require('./_lib/assessment-sync');
module.exports = A.handle(async (req, res) => {
  if (!['GET', 'POST', 'PUT', 'DELETE'].includes(req.method)) return A.json(res, 405, { error: 'Method not allowed.' });
  const s = await A.requireSession(req, res, { mutating: req.method !== 'GET' });
  if (!s) return;
  const url = new URL(req.url, 'http://x');
  if (req.method === 'GET') {
    if (await A.hit('sync-read', s.uid, 120, 60)) {
      res.setHeader('Retry-After', '60');
      return A.json(res, 429, { error: 'Too many refreshes. Try again in a minute.' });
    }
    const token = url.searchParams.get('cursor');
    if (token && token.length > 1024) return A.json(res, 400, { error: 'Invalid sync cursor.' });
    return A.json(res, 200, await sync.list(s, token));
  }
  if (await A.hit('write', s.uid, 120, 60)) {
    res.setHeader('Retry-After', '60');
    return A.json(res, 429, { error: 'Slow down for a moment.' });
  }
  const operation = req.headers['idempotency-key'];
  if (operation !== undefined && (typeof operation !== 'string' || !/^[A-Za-z0-9_-]{16,100}$/.test(operation))) return A.json(res, 400, { error: 'Invalid save identifier.' });
  const id = url.searchParams.get('id') || undefined;
  const action = req.method === 'POST' ? 'create' : req.method === 'PUT' ? 'update' : url.searchParams.get('all') === '1' ? 'erase' : 'delete';
  if (['update', 'delete'].includes(action) && (!id || !/^[a-z0-9]+-[A-Za-z0-9_-]+$/.test(id))) return A.json(res, 400, { error: 'Invalid id.' });
  const revisionHeader = req.headers['if-match'];
  let expectedRevision;
  if (revisionHeader !== undefined) {
    if (!/^[1-9][0-9]*$/.test(revisionHeader) || !Number.isSafeInteger(Number(revisionHeader))) return A.json(res, 400, { error: 'Invalid assessment revision.' });
    expectedRevision = Number(revisionHeader);
  }
  if (action === 'update' && expectedRevision === undefined) return A.json(res, 428, { error: 'An assessment revision is required to prevent overwriting another device.' });
  const body = ['create', 'update'].includes(action) ? V.assessment(await A.readJson(req)) : undefined;
  const result = await sync.mutate(s, { action, id, body, expectedRevision, operation });
  if (!result.replayed) await A.audit(s.uid, s.email, { create: 'assessment_saved', update: 'assessment_updated', delete: 'assessment_deleted', erase: 'assessments_erased' }[action], req);
  A.json(res, action === 'create' && !result.replayed ? 201 : 200, result);
});
