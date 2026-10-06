export const controllerStates = [
  'setup', 'permission_required', 'stopped', 'standby', 'listening',
  'thinking', 'speaking', 'paused', 'error',
] as const;
export const errorCodes = [
  'permission_denied', 'unavailable', 'timeout', 'quota', 'unexpected',
] as const;
export const modelStatuses = ['ready', 'missing', 'incompatible', 'corrupt', 'incomplete', 'unsupported', 'offline_voice_missing'] as const;
export type ModelStatus = (typeof modelStatuses)[number];
export type ControllerState = (typeof controllerStates)[number];
export type ErrorCode = (typeof errorCodes)[number];
export interface StateEvent {
  version: 1;
  state: ControllerState;
  sessionId: string;
  operationId: string;
  generation: number;
  privacyEpoch: number;
  errorCode?: ErrorCode;
  modelStatus?: ModelStatus;
}
const keys = ['version', 'state', 'sessionId', 'operationId', 'generation', 'privacyEpoch'];
const opaqueId = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
function boundedCounter(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}
/** Native presentation events are metadata only. Never accept extra content fields. */
export function parseStateEvent(input: unknown): StateEvent | null {
  if (input === null || typeof input !== 'object' || Object.getPrototypeOf(input) !== Object.prototype) {
    return null;
  }
  const descriptors = Object.getOwnPropertyDescriptors(input);
  const names = Reflect.ownKeys(input);
  if (names.some(key => typeof key !== 'string' || (!keys.includes(key) && key !== 'errorCode' && key !== 'modelStatus')) ||
      keys.some(key => !Object.hasOwn(descriptors, key)) ||
      Object.values(descriptors).some(descriptor => !Object.hasOwn(descriptor, 'value'))) {
    return null;
  }
  const value = input as Record<string, unknown>;
  if (value.version !== 1 || !controllerStates.some(state => state === value.state) ||
      typeof value.sessionId !== 'string' || !opaqueId.test(value.sessionId) ||
      typeof value.operationId !== 'string' || !opaqueId.test(value.operationId) ||
      !boundedCounter(value.generation) || !boundedCounter(value.privacyEpoch)) {
    return null;
  }
  if (Object.hasOwn(value, 'modelStatus') && !modelStatuses.some(status => status === value.modelStatus)) {
    return null;
  }
  if (value.state === 'error' ? !errorCodes.some(code => code === value.errorCode) : Object.hasOwn(value, 'errorCode')) {
    return null;
  }
  return {
    version: 1, state: value.state as ControllerState,
    sessionId: value.sessionId, operationId: value.operationId,
    generation: value.generation, privacyEpoch: value.privacyEpoch,
    ...(Object.hasOwn(value, 'modelStatus') ? {modelStatus: value.modelStatus as ModelStatus} : {}),
    ...(value.state === 'error' ? {errorCode: value.errorCode as ErrorCode} : {}),
  };
}
