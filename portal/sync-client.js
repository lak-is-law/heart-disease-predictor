/* In-memory, account/session-scoped sync. No health data is persisted on this device. */
(function (root) {
  'use strict';
  function create(options) {
    var owner = '', generation = 0, records = [], cursor = '', pending = null, tail = Promise.resolve(), saving = null, sending = false, lastStatus = '', unreadable = new Set();
    function identity() { return options.identity() || ''; }
    function status(text) { if (options.onStatus && text !== lastStatus) options.onStatus(text, Boolean(pending)); lastStatus = text; }
    function publish() { if (options.onChange) options.onChange(records.slice()); }
    function reset() {
      generation++; owner = identity(); records = []; cursor = ''; pending = null; unreadable = new Set();
      publish(); status(owner ? 'Cloud sync ready. Only assessments you choose to save are uploaded.' : 'Sign in to access your cloud assessments.');
    }
    function checkOwner() { if (identity() !== owner) reset(); }
    function run(work) {
      checkOwner();
      var ticket = generation, expectedOwner = owner;
      function valid() {
        if (identity() !== expectedOwner || ticket !== generation) throw new Error('Your session changed. Review the current account before saving.');
        if (!owner) throw new Error('Sign in to continue.');
      }
      var task = tail.catch(function () {}).then(async function () { valid(); return work(valid); });
      tail = task;
      return task;
    }
    async function pull(valid) {
      var data;
      try { data = await options.request('GET', '/api/assessments' + (cursor ? '?cursor=' + encodeURIComponent(cursor) : '')); }
      catch (e) {
        valid();
        if (e.status !== 409 || !cursor) throw e;
        data = await options.request('GET', '/api/assessments');
      }
      valid();
      if (data.full) unreadable.clear();
      (data.deleted || []).concat(data.items.map(function (item) { return item.id; })).forEach(function (id) { unreadable.delete(id); });
      (data.unreadable || []).forEach(function (id) { unreadable.add(id); });
      var map = new Map((data.full ? [] : records).map(function (item) { return [item.id, item]; }));
      (data.deleted || []).concat(data.unreadable || []).forEach(function (id) { map.delete(id); });
      data.items.forEach(function (item) { map.set(item.id, item); });
      var next = Array.from(map.values()).sort(function (a, b) { return b.createdAt - a.createdAt || a.id.localeCompare(b.id); });
      cursor = data.cursor;
      if (JSON.stringify(next) !== JSON.stringify(records)) { records = next; publish(); }
      status(unreadable.size ? 'Some cloud records could not be read. Your export may be incomplete. Contact support.' : pending ? 'Save pending in this tab. Keep it open and choose Retry.' : 'Cloud records are up to date.');
      return data;
    }
    function refresh() {
      return run(async function (valid) {
        try { return await pull(valid); } catch (e) { valid(); status(e.message || 'Offline. Cloud data could not be refreshed.'); throw e; }
      });
    }
    async function send(valid) {
      if (!pending) return;
      if (Date.now() - pending.at >= 23 * 60 * 60 * 1000) {
        status('This pending save is too old to retry safely. Check your cloud records, then discard the pending save.');
        throw new Error('Retry window expired. Check cloud records before saving again.');
      }
      sending = true;
      status('Syncing your selected assessment…');
      try {
        var result = await options.request('POST', '/api/assessments', pending.body, { 'Idempotency-Key': pending.key });
        valid();
        pending = null;
        // The write is confirmed even if the subsequent refresh fails.
        if (result.item) {
          records = records.filter(function (item) { return item.id !== result.item.id; });
          records.unshift(result.item); publish();
        }
        status(result.deleted ? 'This assessment was already deleted on another device.' : 'Saved to your encrypted cloud account.');
        return result;
      } catch (e) {
        valid();
        pending.attempts++;
        pending.retryAt = Date.now() + Math.max(e.retryAfter || 0, Math.min(60000, 1000 * Math.pow(2, Math.min(pending.attempts, 6))) * (0.8 + Math.random() * 0.4));
        pending.autoRetry = !e.status || e.status === 429 || e.status >= 500;
        status((e.message || 'Connection interrupted.') + ' Save remains in this tab only. Keep it open and choose Retry.');
        throw e;
      } finally { sending = false; }
    }
    function save(body) {
      if (saving) return saving;
      saving = run(async function (valid) {
        var copy = JSON.parse(JSON.stringify(body));
        if (pending && JSON.stringify(pending.body) !== JSON.stringify(copy)) throw new Error('A different save is pending. Retry or discard it before saving this assessment.');
        if (!pending) pending = { body: copy, key: root.crypto.randomUUID(), at: Date.now(), attempts: 0, retryAt: 0, autoRetry: true };
        return send(valid);
      }).finally(function () { saving = null; });
      return saving;
    }
    function retry(automatic) {
      return run(async function (valid) {
        if (automatic && pending && (!pending.autoRetry || Date.now() < pending.retryAt)) return;
        return send(valid);
      });
    }
    function remove(item) {
      return run(async function (valid) {
        await options.request('DELETE', '/api/assessments?id=' + encodeURIComponent(item.id), null, { 'If-Match': String(item.revision) });
        valid(); return pull(valid);
      });
    }
    function erase() {
      return run(async function (valid) {
        await options.request('DELETE', '/api/assessments?all=1');
        valid(); pending = null; return pull(valid);
      });
    }
    return { refresh: refresh, save: save, retry: retry, remove: remove, erase: erase, reset: reset, announce: status,
      discard: function () { checkOwner(); if (sending) { status('A save request is in progress. Wait for it to finish before discarding.'); return; } pending = null; status('Pending save discarded from this tab. A previously received cloud save may still exist; refresh to check.'); },
      hasPending: function () { checkOwner(); return Boolean(pending); },
      snapshot: function () { checkOwner(); return records.slice(); }
    };
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { create: create };
  else root.CSSync = { create: create };
})(typeof window !== 'undefined' ? window : globalThis);
