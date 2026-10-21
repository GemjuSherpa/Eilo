'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { createGateway } = require('../gateway.cjs');
const { normalizeResults } = require('../normalize.cjs');
const { fixture, profile, response, item } = require('./fixture.cjs');
test('images/video, asset URLs, tap/autoplay flags and client license claims never authorize egress', async () => {
  for (const patch of [{ mediaTypes: ['image'] }, { mediaTypes: ['video'] }, { mediaTypes: ['text', 'video'] }, { assetUrl: 'https://example.org/video.mp4' }, { licenseAccepted: true }, { tappedPlay: true }, { autoplay: true }, { displayImages: true }]) {
    const h = fixture(); let transportCalls = 0, budgetCalls = 0;
    const g = createGateway({ profile, authority: h.authority, reserveBudget: () => { budgetCalls++; return true; }, transport: async () => { transportCalls++; return response(); } });
    const request = JSON.stringify({ ...JSON.parse(h.request()), ...patch });
    assert.equal((await g.execute(request, { scope: 'scope-a', online: true })).status, 'denied');
    assert.equal(transportCalls, 0); assert.equal(budgetCalls, 0);
  }
});
test('a license reference never becomes a media grant and hidden tracking fields reject the response', () => {
  const licensed = { ...item, kind: 'video', licenseRef: 'https://creativecommons.org/licenses/by/4.0/' };
  const [result] = normalizeResults(JSON.stringify({ version: 1, items: [licensed] }));
  assert.equal(result.sourceVerified, false); assert.deepEqual(result.media, { images: 'unavailable', video: 'unavailable' });
  for (const extra of [{ thumbnail: 'https://example.org/pixel.gif' }, { embed: '<iframe>private</iframe>' }, { media: { video: 'available' } }]) {
    assert.throws(() => normalizeResults(JSON.stringify({ version: 1, items: [{ ...licensed, ...extra }] })));
  }
});
test('binary media/MIME mismatches never publish or invoke a player/URL action', async () => {
  for (const contentType of ['image/png', 'video/mp4', 'text/html']) {
    const h = fixture(), g = createGateway({ profile, authority: h.authority, reserveBudget: () => true, transport: async () => ({ status: 200, contentType, body: Buffer.from([0, 0, 0, 16, 102, 116, 121, 112]) }) });
    const result = await g.execute(h.request(), { scope: 'scope-a', online: true });
    assert.equal(result.status, 'result_rejected'); assert.deepEqual(result.results, []);
  }
});
