'use strict';
const messages = Object.freeze({
  denied: 'Search was not authorized. You can continue with an offline answer.',
  unavailable: 'Live search is unavailable. You can continue with an offline answer.',
  offline: 'You are offline. An offline answer uses local model knowledge.',
  busy: 'Search is busy. Offline conversation remains available.',
  budget_exhausted: 'The search limit has been reached. Offline conversation remains available.',
  provider_limited: 'The search provider limited this request. Offline conversation remains available.',
  timeout: 'Search timed out. You can continue with an offline answer.',
  provider_error: 'Search failed. You can continue with an offline answer.',
  result_rejected: 'Search results could not be safely used. You can continue with an offline answer.',
  revoked: 'Search was cancelled.',
  no_results: 'No usable search results were returned. You can continue with an offline answer.',
});
function fallback(status) {
  const known = typeof status === 'string' && Object.hasOwn(messages, status) ? status : 'unavailable';
  return Object.freeze({ status: known, notice: messages[known], results: Object.freeze([]),
    offerOfflineAnswer: known !== 'revoked', requiresNativeEligibility: true,
    resumeAutomatically: false, retryNeedsConfirmation: true, sourceStatus: 'none' });
}
function success(results) {
  return Object.freeze({ status: 'ok', results, notice: null, offerOfflineAnswer: false,
    requiresNativeEligibility: true, resumeAutomatically: false, retryNeedsConfirmation: true,
    sourceStatus: 'untrusted_provider_data' });
}
module.exports = { fallback, success, fallbackStatuses: Object.freeze(Object.keys(messages)) };
