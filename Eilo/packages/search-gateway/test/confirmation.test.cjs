'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { generateKeyPairSync, sign } = require('node:crypto');
const { createConfirmationAuthority } = require('../index.cjs');
const profile = { id: 'fixture-provider', revision: 'a'.repeat(64), approved: true, licenseReviewed: true, retentionReviewed: true, regionReviewed: true, maxRequests: 3 };
const input = { query: 'Synthetic public museum hours', mediaTypes: ['text'] };
function harness(options = {}) {
  const keys = generateKeyPairSync('ec', { namedCurve: 'prime256v1' });
  let time = 0;
  const authority = createConfirmationAuthority({ profile, publicKey: keys.publicKey, clock: () => time, ...options });
  const signature = preview => sign('sha256', Buffer.from(preview.challenge), keys.privateKey).toString('base64url');
  const ticket = (scope = 'scope-a') => { const preview = authority.preview(input, scope); return authority.confirm(preview.id, signature(preview), scope); };
  return { authority, signature, ticket, setTime: value => { time = value; } };
}
test('default and unregistered/unreviewed profiles cannot create previews', () => {
  assert.equal(createConfirmationAuthority().preview(input, 'scope-a'), null);
  assert.equal(createConfirmationAuthority({ profile }).preview(input, 'scope-a'), null);
  for (const patch of [{ approved: false }, { maxRequests: 0 }, { retentionReviewed: false }, { licenseReviewed: 'true' }, { endpoint: 'https://example.org' }]) {
    const h = harness({ profile: { ...profile, ...patch } }); assert.equal(h.authority.preview(input, 'scope-a'), null);
  }
});
test('exact query/provider challenge needs registered-key signature; confirmation and ticket are one-use', () => {
  const h = harness(), p = h.authority.preview(input, 'scope-a');
  assert.equal(p.query, input.query); assert.equal(p.provider, profile.id);
  const ticket = h.authority.confirm(p.id, h.signature(p), 'scope-a'); assert.ok(ticket);
  assert.equal(h.authority.confirm(p.id, h.signature(p), 'scope-a'), null);
  assert.equal(h.authority.consume(ticket, input, 'scope-a'), true);
  assert.equal(h.authority.consume(ticket, input, 'scope-a'), false);
  assert.deepEqual(h.authority.diagnostics(), { pendingPreviews: 0, pendingTickets: 0 });
});
test('forged flags, altered challenge, changed query/scope/media and replay cannot authorize', () => {
  for (const change of [{ query: input.query + '?' }, { mediaTypes: ['video'] }, { confirmed: true }]) {
    const h = harness(); assert.equal(h.authority.consume(h.ticket(), { ...input, ...change }, 'scope-a'), false);
  }
  const h = harness(), p = h.authority.preview(input, 'scope-a');
  assert.equal(h.authority.confirm(p.id, h.signature({ ...p, challenge: p.challenge + 'x' }), 'scope-a'), null);
  assert.equal(h.authority.confirm(p.id, h.signature(p), 'scope-a'), null);
  assert.equal(h.authority.consume(h.ticket(), input, 'scope-b'), false);
  const other = harness(), preview = h.authority.preview(input, 'scope-a');
  assert.equal(h.authority.confirm(preview.id, other.signature(preview), 'scope-a'), null);
});
test('expiry boundary, rollback, scope revocation and clear discard outstanding work', () => {
  const h = harness(); let ticket = h.ticket(); h.setTime(29999); assert.equal(h.authority.consume(ticket, input, 'scope-a'), true);
  ticket = h.ticket(); h.setTime(59999); assert.equal(h.authority.consume(ticket, input, 'scope-a'), false);
  ticket = h.ticket(); h.setTime(1); assert.equal(h.authority.consume(ticket, input, 'scope-a'), false);
  h.setTime(60000); ticket = h.ticket(); h.authority.revokeScope('scope-a'); assert.equal(h.authority.consume(ticket, input, 'scope-a'), false);
  ticket = h.ticket(); h.authority.clear(); assert.equal(h.authority.consume(ticket, input, 'scope-a'), false);
});
test('bounded previews reject controls, huge/malformed payloads, getters and non-text media without retaining them', () => {
  const h = harness(); const getter = Object.defineProperty({ mediaTypes: ['text'] }, 'query', { get() { throw new Error('must not execute'); }, enumerable: true });
  for (const bad of [getter, null, [], { ...input, query: 'x'.repeat(257) }, { ...input, query: ' trailing ' }, { ...input, query: 'x\n' }, { ...input, query: 'x\u202e' }, { ...input, query: '\ud800' }, { ...input, location: [0, 0] }, { ...input, mediaTypes: ['image'] }]) {
    assert.equal(h.authority.preview(bad, 'scope-a'), null);
  }
  for (let i = 0; i < 4; i++) { assert.ok(h.authority.preview(input, 'scope-a')); }
  assert.equal(h.authority.preview(input, 'scope-a'), null);
  assert.equal(JSON.stringify(h.authority).includes(input.query), false);
  h.setTime(NaN); assert.deepEqual(h.authority.diagnostics(), { pendingPreviews: 0, pendingTickets: 0 });
});

test('Unicode query bytes remain exact and multi-byte bounds are enforced', () => {
  const h = harness();
  for (const query of ['公開博物館の開館時間', 'museum 🏛️ hours']) {
    const request = { query, mediaTypes: ['text'] }, p = h.authority.preview(request, 'scope-a');
    assert.equal(p.query, query);
    const ticket = h.authority.confirm(p.id, h.signature(p), 'scope-a');
    assert.equal(h.authority.consume(ticket, request, 'scope-a'), true);
  }
  assert.equal(h.authority.preview({ query: 'é'.repeat(129), mediaTypes: ['text'] }, 'scope-a'), null);
});

test('revocation is permanent for this authority and scope cancellation leaves unrelated work alone', () => {
  const h = harness(), a = h.ticket('scope-a'), b = h.ticket('scope-b');
  assert.deepEqual(h.authority.binding(), { provider: profile.id, revision: profile.revision });
  h.authority.revokeScope('scope-a'); assert.equal(h.authority.consume(a, input, 'scope-a'), false);
  assert.equal(h.authority.consume(b, input, 'scope-b'), true);
  const pending = h.ticket(); h.authority.disable();
  assert.equal(h.authority.binding(), null); assert.equal(h.authority.consume(pending, input, 'scope-a'), false);
  assert.equal(h.authority.preview(input, 'scope-a'), null);
});
