'use strict';
const { randomUUID, verify } = require('node:crypto');
const { performance } = require('node:perf_hooks');
const { closed, queryValid, textOnly, scopeValid, idValid, digest, approvedProfile } = require('./validation.cjs');
/** Canonical protocol bytes only; calling this does not establish user consent. */
function confirmationMessage(challenge, input) {
  if (!closed(challenge, ['id', 'provider', 'revision', 'expiresInMs']) || !idValid(challenge.id) ||
    typeof challenge.provider !== 'string' || !/^[a-z0-9-]{1,64}$/.test(challenge.provider) ||
    typeof challenge.revision !== 'string' || !/^[0-9a-f]{64}$/.test(challenge.revision) ||
    !Number.isInteger(challenge.expiresInMs) || challenge.expiresInMs < 1000 || challenge.expiresInMs > 60000 ||
    !closed(input, ['query', 'mediaTypes']) || !queryValid(input.query) || !textOnly(input.mediaTypes)) { return null; }
  return JSON.stringify(['eilo-search-confirm-v1', challenge.id, challenge.provider, challenge.revision, digest(input.query), ['text']]);
}
/** Server-only reference boundary. Query-free nonce setup; no HTTP or native signing adapter exists. */
function createConfirmationAuthority({ profile = null, publicKey = null, clock = () => performance.now(), ttlMs = 30000, maxPending = 4 } = {}) {
  const policy = approvedProfile(profile);
  const key = publicKey?.type === 'public' && publicKey.asymmetricKeyType === 'ec' &&
    publicKey.asymmetricKeyDetails?.namedCurve === 'prime256v1' ? publicKey : null;
  if (!Number.isInteger(ttlMs) || ttlMs < 1000 || ttlMs > 60000 || !Number.isInteger(maxPending) || maxPending < 1 || maxPending > 16) {
    throw new Error('Invalid search boundary limits');
  }
  const challenges = new Map();
  let lastClock = -Infinity, disabled = false, expiryTimer = null;
  function cancelExpiry() { if (expiryTimer !== null) { clearTimeout(expiryTimer); expiryTimer = null; } }
  function now() {
    let time;
    try { time = clock(); } catch { time = NaN; }
    if (!Number.isFinite(time) || time < lastClock) { challenges.clear(); cancelExpiry(); return null; }
    lastClock = time;
    for (const [id, item] of challenges) { if (time >= item.deadline) { challenges.delete(id); } }
    if (challenges.size === 0) { cancelExpiry(); }
    return time;
  }
  function arm(time) {
    cancelExpiry();
    if (time === null || challenges.size === 0) { return; }
    const deadline = Math.min(...[...challenges.values()].map(item => item.deadline));
    expiryTimer = setTimeout(() => { expiryTimer = null; arm(now()); }, Math.max(1, Math.ceil(deadline - time)));
    expiryTimer.unref?.();
  }
  function configured() { return !disabled && policy !== null && key !== null; }
  return Object.freeze({
    challenge(scope) {
      const time = now();
      if (!configured() || time === null || !scopeValid(scope) || challenges.size >= maxPending) { return null; }
      const id = randomUUID();
      challenges.set(id, { scope, deadline: time + ttlMs }); arm(time);
      // Never accept/store query text or a query digest in nonce setup.
      return Object.freeze({ id, provider: policy.id, revision: policy.revision, expiresInMs: ttlMs });
    },
    consume(id, input, scope, signature) {
      const time = now();
      if (!idValid(id)) { return false; }
      const item = challenges.get(id); challenges.delete(id); arm(time);
      if (!configured() || time === null || !item || item.scope !== scope || !scopeValid(scope) ||
        typeof signature !== 'string' || signature.length > 192 || !/^[A-Za-z0-9_-]+$/.test(signature)) { return false; }
      const message = confirmationMessage({ id, provider: policy.id, revision: policy.revision, expiresInMs: ttlMs }, input);
      if (!message) { return false; }
      const bytes = Buffer.from(signature, 'base64url');
      if (bytes.length < 8 || bytes.length > 144 || bytes.toString('base64url') !== signature) { return false; }
      try { return verify('sha256', Buffer.from(message, 'utf8'), key, bytes); } catch { return false; }
    },
    cancel(id) { if (idValid(id)) { challenges.delete(id); arm(now()); } },
    revokeScope(scope) { for (const [id, item] of challenges) { if (item.scope === scope) { challenges.delete(id); } } arm(now()); },
    clear() { challenges.clear(); cancelExpiry(); },
    disable() { disabled = true; challenges.clear(); cancelExpiry(); },
    binding() { return configured() ? Object.freeze({ provider: policy.id, revision: policy.revision }) : null; },
    diagnostics() { return Object.freeze({ pendingChallenges: challenges.size }); },
  });
}
module.exports = { createConfirmationAuthority, confirmationMessage };
