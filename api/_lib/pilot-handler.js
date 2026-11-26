'use strict';
const A = require('./auth');
const C = require('./crypto');
const db = require('./db');
const P = require('./pilot');
const templates = ['Understanding a blood pressure reading', 'Preparing questions about cholesterol', 'Bringing a medicine list'];
module.exports = A.handle(async (req, res) => {
  const write = req.method === 'POST';
  if (!write && req.method !== 'GET') return A.json(res, 405, { error: 'Method not allowed.' });
  const s = await A.requireSession(req, res, { mutating: write });
  if (!s) return;
  const id = P.code(s.uid), workspaceKey = 'workspace:' + s.uid, draft = P.draftKey(s.uid);
  if (!write) {
    const state = await P.load();
    const member = state.members[id];
    const saved = await db.get(draft);
    const workspace = await db.get(workspaceKey);
    const visits = Object.values(state.visits).filter(v => workspace === 'facility' ? member && v.shared : v.patient === id);
    const result = { id, workspace, admin: s.role === 'admin', clinic: state.clinic, member, visits,
      draft: saved ? C.decrypt(saved, draft) : null, library: member ? state.library : [], templates: member ? templates : [] };
    if (member === 'manager') result.members = Object.keys(state.members);
    if (workspace === 'facility' && visits.length) await A.audit(s.uid, s.email, 'rehearsal_inbox_opened', req);
    return A.json(res, 200, result);
  }
  if (await A.hit('pilot', s.uid, 120, 60)) P.fail(429, 'Please try again in a moment.');
  const b = await A.readJson(req);
  if (b.action === 'workspace') {
    if (!['patient','facility'].includes(b.workspace)) P.fail(400, 'Choose a workspace.');
    await db.set('rehearsal:account:' + id, '1');
    await db.set(workspaceKey, b.workspace);
  } else if (b.action === 'draft') {
    await db.set(draft, C.encrypt(P.summary(b), draft));
  } else {
    await P.change(async state => {
      const member = state.members[id];
      const target = String(b.target || '');
      if (['setup','inviteStaff','inviteVisit','removeStaff'].includes(b.action) && !/^[a-f0-9]{40}$/.test(target)) P.fail(400,'Enter the account code shown in the recipient’s workspace.');
      if (b.action === 'setup') {
        if (s.role !== 'admin' || (state.clinic && Object.values(state.members).includes('manager'))) P.fail(403, 'Only an administrator can register the pilot clinic once.');
        if (!(await db.get('rehearsal:account:' + target)) && b.action !== 'removeStaff') P.fail(400,'No rehearsal account matches that code. Check with its owner.');
        state.clinic = { name: P.field(b.name, 80, true), instructions: P.field(b.instructions, 300, true) };
        state.members[target] = 'manager';
      } else if (b.action === 'inviteStaff' || b.action === 'removeStaff') {
        if (member !== 'manager' || state.members[target] === 'manager') P.fail(403, 'Clinic manager access required.');
        if (!(await db.get('rehearsal:account:' + target)) && b.action !== 'removeStaff') P.fail(400,'No rehearsal account matches that code. Check with its owner.');
        if (b.action === 'inviteStaff') state.members[target] = 'staff';
        else delete state.members[target];
      } else if (b.action === 'library') {
        if (!member || !templates.includes(b.template)) P.fail(403,'Choose a fictional teaching case.');
        if (!state.library.includes(b.template)) state.library.push(b.template);
      } else if (b.action === 'inviteVisit') {
        if (!member) P.fail(403,'Clinic membership required.');
        if (!(await db.get('rehearsal:account:' + target)) && b.action !== 'removeStaff') P.fail(400,'No rehearsal account matches that code. Check with its owner.');
        const visit = P.field(b.visit, 80, true);
        if (!/^[a-f0-9-]{36}$/.test(visit)) P.fail(400,'Invalid visit reference.');
        if (Object.hasOwn(state.visits,visit)) {
          if (state.visits[visit].patient !== target) P.fail(409,'Visit reference already used.');
          return;
        }
        state.visits[visit] = { visit, patient: target, version: 0, shared: false };
      } else {
        const v = Object.hasOwn(state.visits, b.visit) && state.visits[b.visit];
        if (!v) P.fail(404,'Visit unavailable.');
        if (b.action === 'review') {
          if (!member || !v.shared) P.fail(403,'Visit unavailable.');
          if (b.version !== v.version) P.fail(409,'A corrected summary is available. Read it before confirming.');
          if (!v.reviewed) v.reviewed = { by: s.name || s.email, time: Date.now() };
        } else {
          if (v.patient !== id) P.fail(403,'Visit unavailable.');
          if (b.action === 'share') {
            const content = P.summary(b);
            if (v.shared && JSON.stringify(content) === JSON.stringify(v.content) && (b.version === v.version || b.version === v.version - 1)) return;
            if (b.version !== v.version) P.fail(409,'Visit changed. Refresh before sharing.');
            Object.assign(v, { content, shared: true, reviewed: null, time: Date.now(), version: v.version + 1 });
          } else if (b.action === 'withdraw') {
            if (v.shared && b.version !== v.version) P.fail(409,'Visit changed. Refresh before withdrawing.');
            if (v.shared) { delete v.content; v.shared = false; v.reviewed = null; v.version++; }
          } else P.fail(400,'Unknown action.');
        }
      }
    });
    await A.audit(s.uid,s.email,'rehearsal_' + b.action,req);
  }
  A.json(res,200,{ok:true});
});
