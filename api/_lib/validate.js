'use strict';
// Strict schema for a saved assessment. Only the 13 model inputs, the resulting risk and a short
// pseudonymous reference are accepted, so names and other identifiers have nowhere to go.
const FIELDS = {
  age: [18, 110, 1], sex: [0, 1, 1], cp: [1, 4, 1], trestbps: [70, 260, 1], chol: [80, 700, 1], fbs: [0, 1, 1],
  restecg: [0, 2, 1], thalach: [40, 230, 1], exang: [0, 1, 1], oldpeak: [0, 8, 0.1], slope: [1, 3, 1], ca: [0, 3, 1],
  thal: [3, 7, 1],
};
const LABEL = /^[A-Za-z0-9 _#.\-]{0,40}$/;

function bad(msg) { return Object.assign(new Error(msg), { status: 400 }); }

function assessment(body) {
  if (!body || typeof body !== 'object') throw bad('Send the assessment as JSON.');
  const allowed = new Set(['inputs', 'risk', 'label', 'model']);
  for (const k of Object.keys(body)) if (!allowed.has(k)) throw bad(`Unexpected field: ${k}.`);
  const inputs = {};
  const src = body.inputs;
  if (!src || typeof src !== 'object') throw bad('Missing inputs.');
  for (const k of Object.keys(src)) if (!(k in FIELDS)) throw bad(`Unexpected input: ${k}.`);
  for (const [k, [min, max, step]] of Object.entries(FIELDS)) {
    const v = Number(src[k]);
    if (!Number.isFinite(v) || v < min || v > max) throw bad(`${k} must be between ${min} and ${max}.`);
    inputs[k] = step < 1 ? Math.round(v * 10) / 10 : Math.round(v);
  }
  if (![3, 6, 7].includes(inputs.thal)) throw bad('thal must be 3, 6 or 7.');
  const risk = Number(body.risk);
  if (!Number.isFinite(risk) || risk < 0 || risk > 1) throw bad('risk must be between 0 and 1.');
  const label = String(body.label == null ? '' : body.label).trim();
  if (!LABEL.test(label)) throw bad('Reference can use letters, numbers, spaces and - _ # . only (40 characters).');
  const model = String(body.model || 'cleveland-lr').slice(0, 40);
  if (!/^[a-z0-9._-]+$/i.test(model)) throw bad('Invalid model name.');
  return { inputs, risk: Math.round(risk * 10000) / 10000, label, model };
}

module.exports = { assessment, FIELDS };
