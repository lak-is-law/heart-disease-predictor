'use strict';
// Atomic snapshots and optimistic transactions across serverless instances.
const READ = `
if redis.call('EXISTS', KEYS[3]) == 1 or redis.call('EXISTS', KEYS[4]) == 0 then return {'closed'} end
return {'ok', redis.call('GET', KEYS[2]) or '', redis.call('HGETALL', KEYS[1])}
`;
const COMMIT = `
if redis.call('EXISTS', KEYS[3]) == 1 or redis.call('EXISTS', KEYS[4]) == 0 then return 'closed' end
if (redis.call('GET', KEYS[2]) or '') ~= ARGV[1] then return 'conflict' end
local writes = cjson.decode(ARGV[3])
for id, token in pairs(writes) do
  if token == cjson.null then redis.call('HDEL', KEYS[1], id)
  else redis.call('HSET', KEYS[1], id, token) end
end
redis.call('SET', KEYS[2], ARGV[2])
return 'ok'
`;
const CLOSE = `
redis.call('SET', KEYS[3], '1')
redis.call('DEL', KEYS[1], KEYS[2])
return 'ok'
`;
function memory(engine, script, keys, args) {
  const get = (k) => engine._get(k)?.v;
  if (script === CLOSE) {
    engine.data.set(keys[2], { v: '1', exp: 0 });
    engine.data.delete(keys[0]); engine.data.delete(keys[1]); engine._save();
    return 'ok';
  }
  if (get(keys[2]) !== undefined || get(keys[3]) === undefined) return script === READ ? ['closed'] : 'closed';
  const raw = get(keys[1]) || '';
  if (script === READ) return ['ok', raw, Object.entries(get(keys[0]) || {}).flat()];
  if (script !== COMMIT) throw new Error('Unknown sync script');
  if (raw !== args[0]) return 'conflict';
  const rows = { ...(get(keys[0]) || {}) };
  for (const [id, value] of Object.entries(JSON.parse(args[2]))) {
    if (value === null) delete rows[id]; else rows[id] = value;
  }
  engine.data.set(keys[0], { v: rows, exp: 0 });
  engine.data.set(keys[1], { v: args[1], exp: 0 });
  engine._save();
  return 'ok';
}
module.exports = { READ, COMMIT, CLOSE, memory };
