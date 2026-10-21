'use strict';
const { generateKeyPairSync, sign } = require('node:crypto');
const { createConfirmationAuthority, confirmationMessage } = require('../confirmation.cjs');
const profile = Object.freeze({ id: 'fixture-provider', revision: 'a'.repeat(64), approved: true, licenseReviewed: true, retentionReviewed: true, regionReviewed: true, maxRequests: 3 });
const input = Object.freeze({ query: 'Synthetic museum hours', mediaTypes: ['text'] });
function fixture(options = {}) {
  const keys = generateKeyPairSync('ec', { namedCurve: 'prime256v1' });
  const authority = createConfirmationAuthority({ profile, publicKey: keys.publicKey, ...options });
  const request = (scope = 'scope-a') => {
    const nonce = authority.challenge(scope);
    const signature = sign('sha256', Buffer.from(confirmationMessage(nonce, input)), keys.privateKey).toString('base64url');
    return JSON.stringify({ version: 1, ticket: nonce.id, signature, ...input });
  };
  return { authority, request };
}
const item = Object.freeze({ kind: 'article', title: 'Synthetic source', summary: 'Fixture facts, not a live result.', source: { name: 'Fixture publisher', url: 'https://example.org/article' }, details: [], publishedAt: null, licenseRef: null });
const response = () => ({ status: 200, contentType: 'application/json', body: JSON.stringify({ version: 1, items: [item] }) });
module.exports = { fixture, profile, input, response, item };
