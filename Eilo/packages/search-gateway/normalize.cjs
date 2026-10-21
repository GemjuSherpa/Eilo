'use strict';
const { randomUUID } = require('node:crypto');
const { isIP } = require('node:net');
const { closed } = require('./validation.cjs');
function plain(value, limit) {
  return typeof value === 'string' && value.trim().length > 0 && Buffer.byteLength(value, 'utf8') <= limit &&
    !/[\p{Cc}\p{Cs}\u202a-\u202e\u2066-\u2069<>]/u.test(value);
}
/** Syntactic attribution URL only. No DNS, retrieval, redirect or publisher-rights approval. */
function sourceUrl(value) {
  if (!plain(value, 1024) || /\s|\\/u.test(value)) { return null; }
  const authority = /^https:\/\/([^/?#]+)/.exec(value)?.[1];
  if (!authority || /[@:]/.test(authority)) { return null; }
  let url;
  try { url = new URL(value); } catch { return null; }
  const host = url.hostname;
  if (url.protocol !== 'https:' || url.username || url.password || url.port || url.search || url.hash || isIP(host) ||
    host.length > 253 || !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(host) ||
    /(?:^|\.)(?:localhost|local|internal|lan|home|test|invalid|onion|example|arpa)$/.test(host)) { return null; }
  let decoded;
  try { decoded = decodeURIComponent(url.pathname); } catch { return null; }
  if (/[\p{Cc}\p{Cs}\u202a-\u202e\u2066-\u2069]/u.test(decoded) || Buffer.byteLength(url.href) > 1024) { return null; }
  return url.href;
}
function timestamp(value) {
  if (value === null) { return true; }
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value) &&
    Number.isFinite(Date.parse(value)) && new Date(value).toISOString() === value;
}
function reject() { throw new Error('Untrusted search result rejected'); }
function normalizeResults(body) {
  if (!(typeof body === 'string' || Buffer.isBuffer(body)) || Buffer.byteLength(body) > 32768) { return reject(); }
  let value;
  try { value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(Buffer.from(body))); } catch { return reject(); }
  if (!closed(value, ['version', 'items']) || value.version !== 1 || !Array.isArray(value.items) || value.items.length > 8) { return reject(); }
  const rows = value.items.map(item => {
    if (!closed(item, ['kind', 'title', 'summary', 'source', 'details', 'publishedAt', 'licenseRef']) ||
      !['place', 'article', 'weather', 'video'].includes(item.kind) || !plain(item.title, 160) || !plain(item.summary, 1024) ||
      !closed(item.source, ['name', 'url']) || !plain(item.source.name, 100) || !timestamp(item.publishedAt) ||
      !Array.isArray(item.details) || item.details.length > 6) { return reject(); }
    const url = sourceUrl(item.source.url), licenseRef = item.licenseRef === null ? null : sourceUrl(item.licenseRef);
    if (!url || (item.licenseRef !== null && !licenseRef)) { return reject(); }
    const details = item.details.map(detail => {
      if (!closed(detail, ['label', 'value']) || !plain(detail.label, 64) || !plain(detail.value, 256)) { return reject(); }
      return Object.freeze({ label: detail.label, value: detail.value });
    });
    return Object.freeze({ id: randomUUID(), kind: item.kind, title: item.title, summary: item.summary,
      source: Object.freeze({ name: item.source.name, url }), details: Object.freeze(details),
      publishedAt: item.publishedAt, licenseRef, sourceVerified: false,
      media: Object.freeze({ images: 'unavailable', video: 'unavailable' }) });
  });
  return Object.freeze(rows);
}
module.exports = { normalizeResults, sourceUrl };
