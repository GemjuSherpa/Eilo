'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { fallback, fallbackStatuses } = require('../fallback.cjs');
const { createGateway } = require('../gateway.cjs');
const { fixture, profile, response } = require('./fixture.cjs');
test('every failure has an explicit bounded notice, no source facts and no automatic resume authority', () => {
  for (const status of fallbackStatuses) {
    const result = fallback(status);
    assert.equal(result.status, status); assert.ok(result.notice.length > 0 && result.notice.length < 200);
    assert.deepEqual(result.results, []); assert.equal(result.sourceStatus, 'none'); assert.equal(result.resumeAutomatically, false);
    assert.equal(result.requiresNativeEligibility, true); assert.equal(result.retryNeedsConfirmation, true);
    assert.equal(result.offerOfflineAnswer, status !== 'revoked'); assert.ok(Object.isFrozen(result));
  }
  const hostile = { toString() { throw new Error('must not coerce'); } };
  for (const value of [undefined, null, hostile, '__proto__', 'private provider exception']) { assert.equal(fallback(value).status, 'unavailable'); }
});
test('offline, budget, timeout,429, failure and no results do not claim model knowledge is live search', async () => {
  for (const mode of ['offline', 'budget_exhausted', 'timeout', 'provider_limited', 'provider_error', 'no_results']) {
    const h = fixture();
    const g = createGateway({ profile, authority: h.authority, timeoutMs: 100, reserveBudget: () => mode !== 'budget_exhausted', transport: async () => {
      if (mode === 'timeout') { return new Promise(() => {}); }
      if (mode === 'provider_limited') { return { ...response(), status: 429 }; }
      if (mode === 'provider_error') { throw new Error('Private provider text must not escape'); }
      if (mode === 'no_results') { return { ...response(), body: '{"version":1,"items":[]}' }; }
      return response();
    } });
    const result = await g.execute(h.request(), { scope: 'scope-a', online: mode !== 'offline' });
    assert.equal(result.status, mode); assert.equal(result.offerOfflineAnswer, true); assert.equal(result.sourceStatus, 'none');
    assert.equal(result.resumeAutomatically, false); assert.equal(JSON.stringify(result).includes('Private provider'), false);
    g.disable();
  }
});
test('revocation after an explicit request cannot turn Stop/lock into a local model or audio command', async () => {
  const h = fixture(), controller = new AbortController(); controller.abort();
  const g = createGateway({ profile, authority: h.authority, reserveBudget: () => true, transport: async () => response() });
  const body = h.request(), result = await g.execute(body, { scope: 'scope-a', online: true, signal: controller.signal });
  assert.equal(result.status, 'revoked'); assert.equal(result.offerOfflineAnswer, false); assert.equal(result.resumeAutomatically, false);
  assert.equal((await g.execute(body, { scope: 'scope-a', online: true })).status, 'denied');
});
