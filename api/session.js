'use strict';
const { getUser, json } = require('./_lib/auth');

module.exports = (req, res) => {
  json(res, 200, { user: getUser(req) });
};
