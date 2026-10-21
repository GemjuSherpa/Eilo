'use strict';
const { createHash } = require('node:crypto');
function closed(value, fields) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) { return false; }
  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) { return false; }
  const properties = Object.getOwnPropertyDescriptors(value);
  return Reflect.ownKeys(properties).length === fields.length && fields.every(key =>
    Object.hasOwn(properties, key) && Object.hasOwn(properties[key], 'value'));
}
function queryValid(value) {
  return typeof value === 'string' && value === value.trim() && value.length > 0 &&
    Buffer.byteLength(value, 'utf8') <= 256 &&
    !/[\p{Cc}\p{Cs}\u202a-\u202e\u2066-\u2069]/u.test(value);
}
function textOnly(value) { return Array.isArray(value) && value.length === 1 && value[0] === 'text'; }
function scopeValid(value) { return typeof value === 'string' && /^[a-zA-Z0-9:_-]{1,128}$/.test(value); }
function idValid(value) { return typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value); }
function digest(value) { return createHash('sha256').update(value, 'utf8').digest('hex'); }
function approvedProfile(value) {
  if (!closed(value, ['id', 'revision', 'approved', 'licenseReviewed', 'retentionReviewed', 'regionReviewed', 'maxRequests']) ||
    typeof value.revision !== 'string' || !/^[0-9a-f]{64}$/.test(value.revision) ||
    typeof value.id !== 'string' || !/^[a-z0-9-]{1,64}$/.test(value.id) ||
    value.approved !== true || value.licenseReviewed !== true || value.retentionReviewed !== true ||
    value.regionReviewed !== true || !Number.isSafeInteger(value.maxRequests) || value.maxRequests < 1 || value.maxRequests > 10000) { return null; }
  return Object.freeze({ ...value });
}
module.exports = { closed, queryValid, textOnly, scopeValid, idValid, digest, approvedProfile };
