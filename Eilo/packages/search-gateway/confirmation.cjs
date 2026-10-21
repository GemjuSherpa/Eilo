'use strict';
const { randomUUID, verify } = require('node:crypto');
const { performance } = require('node:perf_hooks');
const { closed, queryValid, textOnly, scopeValid, idValid, digest, approvedProfile } = require('./validation.cjs');

/** Server-only reference boundary. No HTTP route, native signing adapter or key enrollment exists. */
function createConfirmationAuthority({ profile = null, publicKey = null, clock = () => performance.now(), ttlMs = 30000, maxPending = 4 } = {}) {
  const policy = approvedProfile(profile);
  const key = publicKey?.type === 'public' && publicKey.asymmetricKeyType === 'ec' &&
    publicKey.asymmetricKeyDetails?.namedCurve === 'prime256v1' ? publicKey : null;
  if (!Number.isInteger(ttlMs) || ttlMs < 1000 || ttlMs > 60000 || !Number.isInteger(maxPending) || maxPending < 1 || maxPending > 16) {
    throw new Error('Invalid search boundary limits');
  }
  const previews = new Map(), tickets = new Map();
  let lastClock = -Infinity, disabled = false, expiryTimer = null;
  function cancelExpiry() { if (expiryTimer !== null) { clearTimeout(expiryTimer); expiryTimer = null; } }
  function now() {
    let time;
    try { time = clock(); } catch { time = NaN; }
    if (!Number.isFinite(time) || time < lastClock) { previews.clear(); tickets.clear(); cancelExpiry(); return null; }
    lastClock = time;
    for (const entries of [previews, tickets]) {
      for (const [id, item] of entries) { if (time >= item.deadline) { entries.delete(id); } }
    }
    if (previews.size + tickets.size === 0) { cancelExpiry(); }
    return time;
  }
  function arm(time) {
    cancelExpiry();
    if (time === null || previews.size + tickets.size === 0) { return; }
    const deadline = Math.min(...[...previews.values(), ...tickets.values()].map(item => item.deadline));
    expiryTimer = setTimeout(() => { expiryTimer = null; arm(now()); }, Math.max(1, Math.ceil(deadline - time)));
    expiryTimer.unref?.();
  }
  function configured() { return !disabled && policy !== null && key !== null; }
  return Object.freeze({
    preview(input, scope) {
      const time = now();
      if (!configured() || time === null || !scopeValid(scope)) { return null; }
      if (!closed(input, ['query', 'mediaTypes']) || !queryValid(input.query) || !textOnly(input.mediaTypes) || previews.size + tickets.size >= maxPending) { return null; }
      const id = randomUUID(), deadline = time + ttlMs;
      // The trusted native adapter must display these exact bytes and provider before signing.
      const challenge = JSON.stringify(['eilo-search-confirm-v1', id, policy.id, policy.revision, digest(input.query), ['text']]);
      previews.set(id, { query: input.query, scope, challenge, deadline }); arm(time);
      return Object.freeze({ id, query: input.query, provider: policy.id, mediaTypes: Object.freeze(['text']), challenge, expiresInMs: ttlMs });
    },
    confirm(id, signature, scope) {
      const time = now();
      if (!idValid(id)) { return null; }
      const item = previews.get(id);
      previews.delete(id); arm(time); // Invalid attempts consume the challenge too; never allow replay/retries.
      if (!configured() || time === null || !item || item.scope !== scope || !scopeValid(scope) ||
        typeof signature !== 'string' || signature.length > 192 || !/^[A-Za-z0-9_-]+$/.test(signature)) { return null; }
      const bytes = Buffer.from(signature, 'base64url');
      if (bytes.length < 8 || bytes.length > 144 || bytes.toString('base64url') !== signature) { return null; }
      let valid = false;
      try { valid = verify('sha256', Buffer.from(item.challenge, 'utf8'), key, bytes); } catch { /* Generic denial only. */ }
      if (!valid) { return null; }
      const ticket = randomUUID();
      tickets.set(ticket, { queryHash: digest(item.query), scope, deadline: item.deadline }); arm(time);
      return ticket;
    },
    consume(ticket, input, scope) {
      const time = now();
      if (!idValid(ticket)) { return false; }
      const item = tickets.get(ticket);
      tickets.delete(ticket); arm(time);
      return configured() && time !== null && !!item && item.scope === scope && scopeValid(scope) &&
        closed(input, ['query', 'mediaTypes']) && queryValid(input.query) && textOnly(input.mediaTypes) && digest(input.query) === item.queryHash;
    },
    cancel(id) { if (idValid(id)) { previews.delete(id); tickets.delete(id); arm(now()); } },
    revokeScope(scope) {
      for (const entries of [previews, tickets]) {
        for (const [id, item] of entries) { if (item.scope === scope) { entries.delete(id); } }
      }
      arm(now());
    },
    clear() { previews.clear(); tickets.clear(); cancelExpiry(); },
    disable() { disabled = true; previews.clear(); tickets.clear(); cancelExpiry(); },
    binding() { return configured() ? Object.freeze({ provider: policy.id, revision: policy.revision }) : null; },
    diagnostics() { return Object.freeze({ pendingPreviews: previews.size, pendingTickets: tickets.size }); },
  });
}
module.exports = { createConfirmationAuthority };
