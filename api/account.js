'use strict';
const crypto = require('crypto');
const A = require('./_lib/auth');
const C = require('./_lib/crypto');
const db = require('./_lib/db');

function deletionCode() {
  const chars = '23456789ABCDEFGHJKMNPQRSTUVWXYZ';
  const bytes = crypto.randomBytes(6);
  let out = '';
  for (let i = 0; i < 6; i++) out += chars[bytes[i] % chars.length];
  return out;
}

function siteOrigin(req) {
  if (process.env.SITE_URL) return process.env.SITE_URL.replace(/\/+$/, '');
  const host = req.headers.host || 'localhost';
  return (/^(localhost|127\.)/.test(host) ? 'http://' : 'https://') + host;
}

async function sendDeletionEmail(toEmail, name, code, confirmUrl) {
  const key = process.env.RESEND_API_KEY || '';
  const from = process.env.MAIL_FROM || '';
  if (!key || !from || toEmail.endsWith('@oauth.invalid')) return false;
  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + key, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from,
        to: [toEmail],
        subject: 'Confirm CardioSense account deletion',
        text: `Hi ${name || 'there'},\n\nYou asked to permanently delete your CardioSense account.\n\nConfirmation code: ${code}\n\nOr open this link and type CONFIRM and YES to delete your account:\n${confirmUrl}\n\nThis code expires in 15 minutes. If you did not request this, ignore this email.`,
        html: `<p>Hi ${String(name || 'there').replace(/[<>&]/g, '')},</p><p>You asked to permanently delete your CardioSense account.</p><p><strong>Confirmation code:</strong> <code>${code}</code></p><p><a href="${confirmUrl}">Yes, confirm account deletion</a></p><p>This code expires in 15 minutes. If you did not request this, ignore this email.</p>`,
      }),
    });
    return res.ok;
  } catch { return false; }
}

module.exports = A.handle(async (req, res) => {
  const route = new URL(req.url, 'http://localhost');
  if (route.pathname === '/api/pilot' || route.searchParams.get('route') === 'pilot') {
    return require('./_lib/pilot-handler')(req, res);
  }
  const s = await A.requireSession(req, res, { mutating: req.method !== 'GET' });
  if (!s) return;

  if (req.method === 'GET') {
    const rows = (await db.range('audit:' + s.uid, 30)).map((r) => { try { return JSON.parse(r); } catch { return null; } }).filter(Boolean);
    const prof = (await A.getProfile(s.uid)) || A.sanitizeProfile({}, s.name);
    const user = {
      email: s.email, name: prof.name !== undefined ? prof.name : s.name, role: s.role,
      onboarded: Boolean(prof.onboardedAt), onboardingSkipped: Boolean(prof.onboardingSkippedAt), tourSeen: Boolean(prof.tourSeenAt),
    };
    return A.json(res, 200, { user, profile: prof, activity: rows, mustChange: s.mustChange });
  }
  if (req.method !== 'POST') return A.json(res, 405, { error: 'Method not allowed.' });
  const body = await A.readJson(req);

  if (body.action === 'tour') {
    const existing = (await A.getProfile(s.uid)) || A.sanitizeProfile({}, s.name);
    const saved = await A.saveProfile(s.uid, { ...existing, tourSeenAt: Date.now() });
    await A.syncSessions(s.uid, { tourSeen: true });
    return A.json(res, 200, {
      ok: true,
      user: { email: s.email, name: saved.name || s.name, role: s.role, onboarded: Boolean(saved.onboardedAt), onboardingSkipped: Boolean(saved.onboardingSkippedAt), tourSeen: true },
    });
  }

  if (body.action === 'profile' || body.action === 'onboarding') {
    if (await A.hit('profile', s.uid, 30, 600)) return A.json(res, 429, { error: 'Too many updates. Try again in a few minutes.' });
    const existing = (await A.getProfile(s.uid)) || A.sanitizeProfile({}, s.name);

    if (body.action === 'onboarding' && body.skip) {
      const nextProf = await A.saveProfile(s.uid, { ...existing, onboardingSkippedAt: Date.now() });
      await A.syncSessions(s.uid, { onboardingSkipped: true });
      await A.audit(s.uid, s.email, 'onboarding_skipped', req);
      return A.json(res, 200, {
        ok: true,
        user: { email: s.email, name: nextProf.name || s.name, role: s.role, onboarded: Boolean(nextProf.onboardedAt), onboardingSkipped: true },
        profile: nextProf,
      });
    }

    const name = A.cleanStr(body.name !== undefined ? body.name : existing.name, 80);
    if (!name || name.length < 2) return A.json(res, 400, { error: 'Enter a display name (at least 2 characters).' });

    const candidate = A.sanitizeProfile({
      ...existing,
      ...(body.headline !== undefined ? { headline: body.headline } : {}),
      ...(body.roleType !== undefined ? { roleType: body.roleType } : {}),
      ...(body.organization !== undefined ? { organization: body.organization } : {}),
      ...(body.country !== undefined ? { country: body.country } : {}),
      ...(body.experience !== undefined ? { experience: body.experience } : {}),
      ...(body.useCase !== undefined ? { useCase: body.useCase } : {}),
      ...(body.referralSource !== undefined ? { referralSource: body.referralSource } : {}),
      ...(body.referralDetail !== undefined ? { referralDetail: body.referralDetail } : {}),
      ...(body.acceptedGuidelines !== undefined ? { acceptedGuidelines: body.acceptedGuidelines } : {}),
      name,
    });

    if (body.action === 'onboarding') {
      if (!candidate.roleType) return A.json(res, 400, { error: 'Select the option that best describes your role.' });
      if (!candidate.referralSource) return A.json(res, 400, { error: 'Tell us how you heard about CardioSense.' });
      if (!candidate.acceptedGuidelines) return A.json(res, 400, { error: 'Confirm the research-prototype guidelines to continue.' });
      candidate.onboardedAt = existing.onboardedAt || Date.now();
      candidate.onboardingSkippedAt = null;
    }

    const saved = await A.saveProfile(s.uid, candidate);
    const dbUser = await A.findUser(s.email);
    if (dbUser && dbUser.source !== 'env') {
      dbUser.name = saved.name;
      await A.saveUser(dbUser);
    }
    await A.syncSessions(s.uid, {
      name: saved.name,
      onboarded: Boolean(saved.onboardedAt),
      onboardingSkipped: Boolean(saved.onboardingSkippedAt),
    });
    await A.audit(
      s.uid, s.email,
      body.action === 'onboarding' ? 'onboarding_completed' : 'profile_updated',
      req,
      body.action === 'onboarding' ? saved.referralSource : saved.name,
    );
    return A.json(res, 200, {
      ok: true,
      user: {
        email: s.email, name: saved.name, role: s.role,
        onboarded: Boolean(saved.onboardedAt), onboardingSkipped: Boolean(saved.onboardingSkippedAt), tourSeen: Boolean(saved.tourSeenAt),
      },
      profile: saved,
    });
  }

  if (body.action === 'delete-request') {
    if (await A.hit('delreq', s.uid, 5, 900)) return A.json(res, 429, { error: 'Too many deletion requests. Try again in 15 minutes.' });
    const user = await A.findUser(s.email);
    if (!user || user.source === 'env') return A.json(res, 400, { error: 'This bootstrap account is defined in environment variables and cannot be deleted here.' });
    if (A.normEmail(body.email) !== s.email) return A.json(res, 400, { error: 'Enter your exact account email address.' });
    if (String(body.phrase || '').trim().toUpperCase() !== 'CONFIRM') return A.json(res, 400, { error: 'Type CONFIRM to send the confirmation email.' });

    const code = deletionCode();
    const token = C.randomId(24);
    await db.set('del:' + s.uid, JSON.stringify({ codeHash: C.sha256(code), tokenHash: C.sha256(token), attempts: 0 }), 900);
    const confirmUrl = `${siteOrigin(req)}/dashboard?delete_token=${encodeURIComponent(token)}#dash-delete-panel`;
    const emailed = await sendDeletionEmail(s.email, s.name, code, confirmUrl);
    await A.audit(s.uid, s.email, 'account_delete_requested', req);
    return A.json(res, 200, { ok: true, emailed, ...(emailed ? {} : { confirmationCode: code }) });
  }

  if (body.action === 'delete-account') {
    const user = await A.findUser(s.email);
    if (!user || user.source === 'env') return A.json(res, 400, { error: 'This bootstrap account is defined in environment variables and cannot be deleted here.' });
    if (A.normEmail(body.email) !== s.email) return A.json(res, 400, { error: 'Enter your exact account email address.' });
    if (String(body.phrase || '').trim().toUpperCase() !== 'CONFIRM') return A.json(res, 400, { error: 'Type CONFIRM to permanently delete your account.' });
    if (String(body.yes || '').trim().toUpperCase() !== 'YES') return A.json(res, 400, { error: 'Type YES to confirm account deletion.' });

    const raw = await db.get('del:' + s.uid);
    if (!raw) return A.json(res, 400, { error: 'Your confirmation code expired or was not requested. Send a new one.' });
    let rec;
    try { rec = JSON.parse(raw); } catch { rec = null; }
    if (!rec) return A.json(res, 400, { error: 'Request a new confirmation code first.' });

    const codeStr = String(body.code || '').trim().toUpperCase();
    const tokenStr = String(body.token || '').trim();
    const okCode = codeStr && C.safeEqual(C.sha256(codeStr), rec.codeHash);
    const okToken = tokenStr && C.safeEqual(C.sha256(tokenStr), rec.tokenHash);
    if (!okCode && !okToken) {
      rec.attempts = (rec.attempts || 0) + 1;
      if (rec.attempts >= 5) {
        await db.del('del:' + s.uid);
        return A.json(res, 429, { error: 'Too many incorrect codes. Request a new confirmation email.' });
      }
      await db.set('del:' + s.uid, JSON.stringify(rec), 900);
      return A.json(res, 400, { error: 'The email confirmation code does not match.' });
    }

    await A.deleteUserAccount(user);
    await A.endSession(req, res);
    try { await db.push('audit:all', JSON.stringify({ t: Date.now(), ev: 'account_deleted', u: '[deleted]' }), 1000); } catch { /* ignore */ }
    return A.json(res, 200, { ok: true });
  }

  if (body.action === 'password') {
    if (await A.hit('pwchange', s.uid, 8, 900)) return A.json(res, 429, { error: 'Too many attempts. Try again later.' });
    const user = await A.findUser(s.email);
    if (!user || user.source === 'env') return A.json(res, 400, { error: 'This account is managed outside the app. Change its password where it was created.' });
    if (!C.checkPassword(String(body.current || ''), user.pw)) return A.json(res, 401, { error: 'Current password is incorrect.' });
    const problem = C.passwordProblem(String(body.next || ''), user.email);
    if (problem) return A.json(res, 400, { error: problem });
    user.pw = C.hashPassword(body.next);
    user.mustChange = false;
    await A.saveUser(user);
    await A.endAllSessions(user.id);              // every other device signs out
    const fresh = await A.createSession(res, user);
    await A.audit(user.id, user.email, 'password_changed', req);
    return A.json(res, 200, { ok: true, csrf: fresh.csrf });
  }

  if (body.action === 'signout-all') {
    await A.endAllSessions(s.uid);
    await A.audit(s.uid, s.email, 'signout_all', req);
    await A.endSession(req, res);
    return A.json(res, 200, { ok: true });
  }

  A.json(res, 400, { error: 'Unknown action.' });
});
