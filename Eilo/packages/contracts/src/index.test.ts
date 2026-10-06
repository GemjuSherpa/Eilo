import {describe, expect, it} from 'vitest';
import {controllerStates, modelStatuses, parseStateEvent} from './index';
const event = {version: 1, state: 'stopped', sessionId: '00000000-0000-4000-8000-000000000001', operationId: '00000000-0000-4000-8000-000000000002', generation: 0, privacyEpoch: 0};
describe('metadata-only native state boundary', () => {
  it.each(controllerStates)('accepts %s and returns an owned snapshot', state => {
    const input = {...event, state, ...(state === 'error' ? {errorCode: 'unexpected'} : {})};
    const result = parseStateEvent(input);
    expect(result).toEqual(input);
    expect(result).not.toBe(input);
  });
  it.each(['transcript', 'keys', 'audio', 'memory', 'email', 'message', 'stack', 'accountId'])('rejects personal/unknown field %s', key => {
    expect(parseStateEvent({...event, [key]: 'synthetic'})).toBeNull();
  });
  it.each([NaN, Infinity, -1, 0.5, Number.MAX_SAFE_INTEGER + 1, '1'])('rejects invalid counter %s', generation => {
    expect(parseStateEvent({...event, generation})).toBeNull();
    expect(parseStateEvent({...event, privacyEpoch: generation})).toBeNull();
  });
  it('rejects malformed state, ID, version and error combinations', () => {
    for (const change of [{state: 'secret'}, {sessionId: 'user@example.invalid'}, {operationId: ''}, {version: 2}, {state: 'error'}, {errorCode: 'unexpected'}, {state: 'error', errorCode: 'private exception text'}]) {
      expect(parseStateEvent({...event, ...change})).toBeNull();
    }
    expect(parseStateEvent(null)).toBeNull();
    expect(parseStateEvent([])).toBeNull();
    expect(parseStateEvent({...event, [Symbol('content')]: 'synthetic'})).toBeNull();
  });
  it('rejects accessors without executing them', () => {
    const input = {...event};
    Object.defineProperty(input, 'state', {get() {throw new Error('must not execute');}});
    expect(parseStateEvent(input)).toBeNull();
  });
});

describe('bounded model readiness presentation', () => {
  it.each(modelStatuses)('accepts native reason %s', modelStatus => {
    expect(parseStateEvent({...event, modelStatus})).toEqual({...event, modelStatus});
  });
  it('rejects arbitrary content and non-string readiness', () => {
    for (const modelStatus of ['synthetic private details', 1, null, {ready: true}]) {
      expect(parseStateEvent({...event, modelStatus})).toBeNull();
    }
  });
});
