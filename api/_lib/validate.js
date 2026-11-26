'use strict';
// Strict schema for a saved assessment. Only the 13 model inputs, the resulting risk and a short
// pseudonymous reference are accepted, so names and other identifiers have nowhere to go.
const score = require('../../portal/research-score');
const weights = require('../../portal/model_weights.json');
const model = 'cleveland-lr-' + require('./crypto').sha256(JSON.stringify(weights)).slice(0,12);
const FIELDS = score.limits;
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
  for (const k of Object.keys(FIELDS)) {
    if (!score.valid(k, src[k])) throw bad(`Invalid or missing measurement: ${k}.`);
    inputs[k] = src[k];
  }
  const risk = score.predict(weights, inputs);
  const label = String(body.label == null ? '' : body.label).trim();
  if (!LABEL.test(label)) throw bad('Reference can use letters, numbers, spaces and - _ # . only (40 characters).');
  return { inputs, risk: Math.round(risk * 10000) / 10000, label, model };
}

module.exports = { assessment, FIELDS };
