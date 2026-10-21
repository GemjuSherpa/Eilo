'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { setImmediate: tick } = require('node:timers/promises');
const { createGateway, readRequest } = require('../gateway.cjs');
const { fixture, profile, input, response } = require('./fixture.cjs');
function gateway(h, options = {}) { return createGateway({ profile, authority: h.authority, reserveBudget: () => true, transport: async () => response(), ...options }); }
const context = { scope: 'scope-a', online: true };
test('closed request parser rejects private fields, malformed UTF-8, oversized bodies and media', () => {
  const h = fixture(), good = JSON.parse(h.request()); assert.ok(readRequest(JSON.stringify(good)));
  for (const patch of [{ transcript: 'private' }, { accountId: 'person' }, { location: [0,0] }, { endpoint: 'https://localhost' }, { confirmed: true }, { mediaTypes: ['video'] }, { version: true }]) {
    assert.equal(readRequest(JSON.stringify({ ...good, ...patch })), null);
  }
  for (const body of [null, {}, ' '.repeat(2049), Buffer.from([0xff]), '[]', '{']) { assert.equal(readRequest(body), null); }
});
test('default, wrong provider/revision, missing authoritative budget or offline cannot reach transport', async () => {
  for (const config of [{ profile: null }, { authority: null }, { profile: { ...profile, id: 'other' } }, { profile: { ...profile, revision: 'b'.repeat(64) } }, { reserveBudget: null }, { reserveBudget: () => false }, { reserveBudget: () => Promise.resolve(true) }, { reserveBudget: () => Promise.reject(new Error('private funding error')) }]) {
    const h = fixture(); let calls = 0; const g = gateway(h, { transport: async () => { calls++; return response(); }, ...config });
    assert.notEqual((await g.execute(h.request(), context)).status, 'ok'); assert.equal(calls, 0);
  }
  const h = fixture(); let calls = 0; const g = gateway(h, { transport: async () => { calls++; return response(); } });
  const body = h.request(); assert.equal((await g.execute(body, { scope: 'scope-a' })).status, 'offline');
  assert.equal((await g.execute(body, context)).status, 'denied'); assert.equal(calls, 0);
});
test('only exact confirmed query/text goes to fixture transport; attempts and tickets are bounded', async () => {
  const h = fixture(); let calls = 0;
  const g = gateway(h, { transport: async (outbound, options) => { calls++; assert.deepEqual(outbound, input); assert.deepEqual(Object.keys(options), ['signal']); return response(); } });
  const body = h.request(); assert.equal((await g.execute(body, context)).status, 'ok');
  assert.equal((await g.execute(body, context)).status, 'denied');
  await g.execute(h.request(), context); await g.execute(h.request(), context);
  assert.equal((await g.execute(h.request(), context)).status, 'budget_exhausted'); assert.equal(calls, 3);
  assert.deepEqual(g.diagnostics(), { inFlight: 0, reservedAttempts: 3 });
  assert.equal(JSON.stringify(g).includes(input.query), false);
});
test('timeout returns promptly but a transport ignoring abort retains capacity; late data never publishes', async () => {
  const h = fixture(); let finish;
  const g = gateway(h, { timeoutMs: 100, maxConcurrent: 1, transport: () => new Promise(resolve => { finish = resolve; }) });
  assert.equal((await g.execute(h.request(), context)).status, 'timeout');
  assert.equal(g.diagnostics().inFlight, 1);
  assert.equal((await g.execute(h.request(), context)).status, 'busy');
  finish(response()); await tick(); assert.equal(g.diagnostics().inFlight, 0);
});
test('scope revocation, caller abort and permanent disable reject pending/late replies', async () => {
  for (const reason of ['scope', 'signal', 'disable']) {
    const h = fixture(); let finish; const controller = new AbortController();
    const g = gateway(h, { transport: (_input, options) => { options.signal.addEventListener('abort', () => {}); return new Promise(resolve => { finish = resolve; }); } });
    const pending = g.execute(h.request(), { ...context, signal: controller.signal }); await tick();
    if (reason === 'scope') { g.revokeScope('scope-a'); } else if (reason === 'signal') { controller.abort(); } else { g.disable(); }
    assert.equal((await pending).status, 'revoked'); assert.equal(g.diagnostics().inFlight, 1);
    finish(response()); await tick(); assert.equal(g.diagnostics().inFlight, 0);
  }
});
test('transport/normalizer failures, wrong content types and overlarge bodies give generic fallback', async () => {
  for (const bad of [{ status: 429, contentType: 'application/json', body: '' }, { status: 503, contentType: 'application/json', body: 'private error' }, { ...response(), contentType: 'text/html' }, { ...response(), body: 'x'.repeat(32769) }, { ...response(), cookie: 'private' }]) {
    const h = fixture(), g = gateway(h, { transport: async () => bad });
    const result = await g.execute(h.request(), context); assert.notEqual(result.status, 'ok'); assert.deepEqual(result.results, []); assert.equal(result.localResponseRequired, true); assert.equal(JSON.stringify(result).includes('private'), false);
  }
  const h = fixture(), g = gateway(h, { transport: async () => { throw new Error('private exception'); } });
  assert.equal((await g.execute(h.request(), context)).status, 'provider_error');
});

test('invalid fields consume an extractable ticket; late configuration cannot replay a failed attempt', async () => {
  const h = fixture(), good = h.request(), g = gateway(h);
  assert.equal((await g.execute(JSON.stringify({ ...JSON.parse(good), confirmed: true }), context)).status, 'denied');
  assert.equal((await g.execute(good, context)).status, 'denied');
  const pending = h.request(), missingTransport = gateway(h, { transport: null });
  assert.equal((await missingTransport.execute(pending, context)).status, 'unavailable');
  assert.equal((await g.execute(pending, context)).status, 'denied');
});
test('re-entrant budget callbacks cannot bypass cancellation, concurrency or per-instance attempt limits', async () => {
  const h = fixture(); let calls = 0, g;
  g = gateway(h, { reserveBudget: () => { g.revokeScope('scope-a'); return true; }, transport: async () => { calls++; return response(); } });
  assert.equal((await g.execute(h.request(), context)).status, 'revoked'); assert.equal(calls, 0); assert.equal(g.diagnostics().inFlight, 0);
  let nested;
  g = gateway(h, { profile: { ...profile, maxRequests: 1 }, reserveBudget: () => { nested = g.execute(h.request(), context); return true; }, transport: async () => { calls++; return response(); } });
  assert.equal((await g.execute(h.request(), context)).status, 'ok');
  assert.equal((await nested).status, 'budget_exhausted'); assert.equal(calls, 1);
});

test('revocation during the final configuration check still owns the response until processing finishes', async () => {
  const h = fixture(); let received = false, revoked = false, g;
  const authority = { ...h.authority, binding() {
    if (received && !revoked) { revoked = true; g.revokeScope('scope-a'); }
    return h.authority.binding();
  } };
  g = gateway(h, { authority, transport: async () => { received = true; return response(); } });
  const result = await g.execute(h.request(), context);
  assert.equal(result.status, 'revoked'); assert.deepEqual(result.results, []); assert.equal(g.diagnostics().inFlight, 0);
});
