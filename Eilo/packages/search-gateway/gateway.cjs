'use strict';
const { closed, queryValid, textOnly, scopeValid, idValid, approvedProfile } = require('./validation.cjs');
const unavailable = status => Object.freeze({ status, results: Object.freeze([]), localResponseRequired: true });
function readWire(body) {
  if (!(typeof body === 'string' || Buffer.isBuffer(body)) || Buffer.byteLength(body) > 2048) { return null; }
  let value;
  try { value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(Buffer.from(body))); } catch { return null; }
  return value;
}
function validRequest(value) {
  if (!closed(value, ['version', 'ticket', 'query', 'mediaTypes']) || value.version !== 1 ||
    !idValid(value.ticket) || !queryValid(value.query) || !textOnly(value.mediaTypes)) { return null; }
  return value;
}
function readRequest(body) { return validRequest(readWire(body)); }
/** No listener or network implementation. All capabilities are server-owned, closed by default. */
function createGateway({ profile = null, authority = null, transport = null, reserveBudget = null, normalize = null, maxConcurrent = 2, timeoutMs = 3000 } = {}) {
  const policy = approvedProfile(profile), active = new Map();
  if (!Number.isInteger(maxConcurrent) || maxConcurrent < 1 || maxConcurrent > 4 ||
    !Number.isInteger(timeoutMs) || timeoutMs < 100 || timeoutMs > 10000) { throw new Error('Invalid gateway limits'); }
  let disabled = false, attempts = 0;
  function configured() {
    if (disabled || !policy || typeof transport !== 'function' || typeof reserveBudget !== 'function' ||
      typeof normalize !== 'function' || !['binding', 'consume', 'cancel', 'revokeScope', 'disable'].every(name => typeof authority?.[name] === 'function')) { return false; }
    try { const binding = authority.binding(); return binding?.provider === policy.id && binding?.revision === policy.revision; } catch { return false; }
  }
  function cancelEntry(entry, status) {
    if (entry.cancelled) { return; }
    entry.cancelled = true; entry.reason = status; entry.controller.abort(); entry.notify?.({ kind: status });
  }
  return Object.freeze({
    async execute(body, { scope = null, online = false, signal = null } = {}) {
      const wire = readWire(body), request = validRequest(wire);
      if (!request || !scopeValid(scope)) {
        try { if (wire && typeof wire === 'object' && idValid(wire.ticket)) { authority?.cancel(wire.ticket); } } catch { /* Generic denial. */ }
        return unavailable('denied');
      }
      const input = Object.freeze({ query: request.query, mediaTypes: Object.freeze(['text']) });
      // A failed attempt cannot replay a valid ticket with a new request or refreshed budget.
      let confirmed = false;
      try { confirmed = authority?.consume(request.ticket, input, scope) === true; } catch { /* Missing authority denies. */ }
      if (!confirmed) { return unavailable('denied'); }
      if (!configured()) { return unavailable('unavailable'); }
      if (online !== true) { return unavailable('offline'); }
      if (signal && (!(signal instanceof AbortSignal) || signal.aborted)) { return unavailable('revoked'); }
      if (active.size >= maxConcurrent) { return unavailable('busy'); }
      if (attempts >= policy.maxRequests) { return unavailable('budget_exhausted'); }
      // Reserve local capacity before invoking any injected callback: it may revoke/re-enter.
      attempts++;
      const key = Symbol(), entry = { scope, controller: new AbortController(), cancelled: false, reason: null, notify: null };
      active.set(key, entry);
      const onAbort = () => cancelEntry(entry, 'revoked');
      signal?.addEventListener('abort', onAbort, { once: true });
      const beforeTransport = status => { active.delete(key); signal?.removeEventListener('abort', onAbort); return unavailable(status); };
      let funded = false;
      try {
        const reservation = reserveBudget(Object.freeze({ provider: policy.id, revision: policy.revision }));
        if (reservation && typeof reservation.then === 'function') { Promise.resolve(reservation).catch(() => {}); }
        funded = reservation === true;
      } catch { /* Unknown funding denies. */ }
      // Synchronous true must mean an exclusive external funded reservation. No refund is inferred.
      if (!funded) { return beforeTransport('budget_exhausted'); }
      if (entry.cancelled || !configured() || signal?.aborted) { return beforeTransport('revoked'); }
      const interrupted = new Promise(resolve => { entry.notify = resolve; });
      const timer = setTimeout(() => cancelEntry(entry, 'timeout'), timeoutMs);
      // Even a transport ignoring AbortSignal retains its slot until it actually settles.
      const remote = Promise.resolve().then(() => {
        if (entry.cancelled) { return null; }
        return transport(input, Object.freeze({ signal: entry.controller.signal }));
      }).then(response => ({ kind: 'response', response }), () => ({ kind: 'provider_error' })).finally(() => { active.delete(key); });
      try {
        const outcome = await Promise.race([remote, interrupted]);
        if (entry.cancelled || !configured()) { return unavailable(entry.reason ?? 'revoked'); }
        if (outcome.kind !== 'response') { return unavailable(outcome.kind); }
        const response = outcome.response;
        if (!closed(response, ['status', 'contentType', 'body']) || !Number.isInteger(response.status)) { return unavailable('provider_error'); }
        if (response.status === 429) { return unavailable('provider_limited'); }
        if (response.status !== 200) { return unavailable('provider_error'); }
        if (response.contentType !== 'application/json' || !(typeof response.body === 'string' || Buffer.isBuffer(response.body)) || Buffer.byteLength(response.body) > 32768) { return unavailable('result_rejected'); }
        let results;
        try { results = normalize(response.body); } catch { return unavailable('result_rejected'); }
        if (!Array.isArray(results) || results.length > 8 || entry.cancelled || !configured()) { return unavailable('result_rejected'); }
        return Object.freeze({ status: 'ok', results, localResponseRequired: false });
      } finally {
        clearTimeout(timer); signal?.removeEventListener('abort', onAbort); entry.notify = null;
      }
    },
    revokeScope(scope) {
      try { authority?.revokeScope?.(scope); } catch { /* Still abort all matching transport work. */ }
      for (const entry of active.values()) { if (entry.scope === scope) { cancelEntry(entry, 'revoked'); } }
    },
    disable() {
      disabled = true; try { authority?.disable?.(); } catch { /* Local disable remains authoritative. */ }
      for (const entry of active.values()) { cancelEntry(entry, 'revoked'); }
    },
    diagnostics() { return Object.freeze({ inFlight: active.size, reservedAttempts: attempts }); },
  });
}
module.exports = { createGateway, readRequest };
