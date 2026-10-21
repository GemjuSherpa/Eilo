'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { generateKeyPairSync, sign } = require('node:crypto');
const { createConfirmationAuthority, confirmationMessage } = require('../index.cjs');
const profile = { id: 'fixture-provider', revision: 'a'.repeat(64), approved: true, licenseReviewed: true, retentionReviewed: true, regionReviewed: true, maxRequests: 3 };
const input = { query: 'Synthetic public museum hours', mediaTypes: ['text'] };
function harness(options = {}) {
  const keys = generateKeyPairSync('ec', { namedCurve: 'prime256v1' }); let time = 0;
  const authority = createConfirmationAuthority({ profile, publicKey: keys.publicKey, clock: () => time, ...options });
  const signature = (nonce, request = input) => sign('sha256', Buffer.from(confirmationMessage(nonce, request)), keys.privateKey).toString('base64url');
  const ticket = (scope = 'scope-a') => { const nonce = authority.challenge(scope); return { id: nonce.id, signature: signature(nonce) }; };
  const consume = (ticket, request = input, scope = 'scope-a') => authority.consume(ticket.id, request, scope, ticket.signature);
  return { authority, signature, ticket, consume, setTime: value => { time = value; } };
}
test('default, unregistered and unreviewed profiles cannot issue a challenge', () => {
  assert.equal(createConfirmationAuthority().challenge('scope-a'), null);
  assert.equal(createConfirmationAuthority({ profile }).challenge('scope-a'), null);
  const hidden = Object.create(null, Object.fromEntries(Object.entries(profile).map(([key, value]) => [key, { value, enumerable: false }])));
  assert.equal(harness({ profile: hidden }).authority.challenge('scope-a'), null);
  for (const patch of [{ approved: false }, { maxRequests: 0 }, { retentionReviewed: false }, { licenseReviewed: 'true' }, { endpoint: 'https://example.org' }]) {
    assert.equal(harness({ profile: { ...profile, ...patch } }).authority.challenge('scope-a'), null);
  }
});
test('nonce setup is query-free; exact query/provider/revision signature is consumed once', () => {
  const h = harness(), nonce = h.authority.challenge('scope-a');
  assert.deepEqual(Object.keys(nonce).sort(), ['expiresInMs', 'id', 'provider', 'revision']);
  assert.equal(JSON.stringify(nonce).includes(input.query), false);
  assert.equal(h.authority.challenge({ query: input.query }), null);
  assert.equal(h.authority.preview, undefined);
  const proof = { id: nonce.id, signature: h.signature(nonce) };
  assert.equal(h.consume(proof), true); assert.equal(h.consume(proof), false);
  assert.deepEqual(h.authority.diagnostics(), { pendingChallenges: 0 });
});
test('forged fields, altered provider/revision/query/media, cross-scope and other-key signatures cannot authorize', () => {
  for (const patch of [{ query: input.query + '?' }, { mediaTypes: ['video'] }, { confirmed: true }]) {
    const h = harness(); assert.equal(h.consume(h.ticket(), { ...input, ...patch }), false);
  }
  for (const patch of [{ provider: 'other' }, { revision: 'b'.repeat(64) }]) {
    const h = harness(), nonce = h.authority.challenge('scope-a');
    assert.equal(h.authority.consume(nonce.id, input, 'scope-a', h.signature({ ...nonce, ...patch })), false);
  }
  const h = harness(); assert.equal(h.consume(h.ticket(), input, 'scope-b'), false);
  const other = harness(), nonce = h.authority.challenge('scope-a');
  assert.equal(h.authority.consume(nonce.id, input, 'scope-a', other.signature(nonce)), false);
  assert.equal(h.authority.consume(nonce.id, input, 'scope-a', h.signature(nonce)), false);
});
test('expiry boundary, rollback, scope revocation and clear discard outstanding nonces', () => {
  const h = harness(); let ticket = h.ticket(); h.setTime(29999); assert.equal(h.consume(ticket), true);
  ticket = h.ticket(); h.setTime(59999); assert.equal(h.consume(ticket), false);
  ticket = h.ticket(); h.setTime(1); assert.equal(h.consume(ticket), false);
  h.setTime(60000); ticket = h.ticket(); h.authority.revokeScope('scope-a'); assert.equal(h.consume(ticket), false);
  ticket = h.ticket(); h.authority.clear(); assert.equal(h.consume(ticket), false);
});
test('bounded challenges and canonical-message validation reject getters, controls and non-text media', () => {
  const h = harness(), nonce = h.authority.challenge('scope-a');
  const getter = Object.defineProperty({ mediaTypes: ['text'] }, 'query', { get() { throw new Error('must not execute'); }, enumerable: true });
  const mediaGetter = Object.defineProperty([], '0', { get() { throw new Error('must not execute'); }, enumerable: true });
  for (const bad of [getter, { ...input, mediaTypes: mediaGetter }, null, [], { ...input, query: 'x'.repeat(257) }, { ...input, query: ' trailing ' }, { ...input, query: 'x\n' }, { ...input, query: 'x\u202e' }, { ...input, query: '\ud800' }, { ...input, location: [0, 0] }, { ...input, mediaTypes: ['image'] }]) { assert.equal(confirmationMessage(nonce, bad), null); }
  for (let i = 0; i < 3; i++) { assert.ok(h.authority.challenge('scope-a')); }
  assert.equal(h.authority.challenge('scope-a'), null);
  h.setTime(NaN); assert.equal(h.authority.challenge('scope-a'), null); assert.deepEqual(h.authority.diagnostics(), { pendingChallenges: 0 });
});
test('Unicode query bytes remain exact and multi-byte bounds are enforced', () => {
  const h = harness();
  for (const query of ['公開博物館の開館時間', 'museum 🏛️ hours']) {
    const request = { query, mediaTypes: ['text'] }, nonce = h.authority.challenge('scope-a');
    assert.equal(h.authority.consume(nonce.id, request, 'scope-a', h.signature(nonce, request)), true);
  }
  assert.equal(confirmationMessage(h.authority.challenge('scope-a'), { query: 'é'.repeat(129), mediaTypes: ['text'] }), null);
});
test('revocation is permanent for an authority; cancellation leaves unrelated scope nonces alone', () => {
  const h = harness(), a = h.ticket('scope-a'), b = h.ticket('scope-b');
  assert.deepEqual(h.authority.binding(), { provider: profile.id, revision: profile.revision });
  h.authority.revokeScope('scope-a'); assert.equal(h.consume(a), false); assert.equal(h.consume(b, input, 'scope-b'), true);
  const pending = h.ticket(); h.authority.disable(); assert.equal(h.authority.binding(), null); assert.equal(h.consume(pending), false); assert.equal(h.authority.challenge('scope-a'), null);
});
test('idle expiry purges nonce references without requiring another request', t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const h = harness(), ticket = h.ticket(); assert.deepEqual(h.authority.diagnostics(), { pendingChallenges: 1 });
  h.setTime(30000); t.mock.timers.tick(29999); assert.deepEqual(h.authority.diagnostics(), { pendingChallenges: 1 });
  t.mock.timers.tick(1); assert.deepEqual(h.authority.diagnostics(), { pendingChallenges: 0 }); assert.equal(h.consume(ticket), false);
});
