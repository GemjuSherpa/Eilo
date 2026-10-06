import {parseStateEvent, type StateEvent} from '@eilo/contracts';
import NativeControl from './specs/NativeEiloControl';
export interface ControlSnapshot {
  version: 1; revision: number; controller: StateEvent; capturePending: boolean; speakerConfirmationRequired: boolean;
}
export type ControlCommand = 'start' | 'stop' | 'confirmSpeaker';
export interface ControlClient {
  snapshot(): Promise<ControlSnapshot>;
  command(name: ControlCommand, value?: string): Promise<ControlSnapshot>;
  subscribe(listener: (value: ControlSnapshot) => void, failed?: () => void): () => void;
}
export function decodeSnapshot(source: string): ControlSnapshot {
  if (source.length > 4096) {throw new Error('Native controls unavailable');}
  const value: unknown = JSON.parse(source);
  if (!value || typeof value !== 'object' || Array.isArray(value)) {throw new Error('Native controls unavailable');}
  const data = value as Record<string, unknown>;
  if (Object.keys(data).sort().join(',') !== 'capturePending,controller,revision,speakerConfirmationRequired,version' ||
      data.version !== 1 || typeof data.revision !== 'number' || !Number.isSafeInteger(data.revision) || data.revision < 0 || typeof data.capturePending !== 'boolean' || typeof data.speakerConfirmationRequired !== 'boolean') {
    throw new Error('Native controls unavailable');
  }
  const controller = parseStateEvent(data.controller);
  if (!controller) {throw new Error('Native controls unavailable');}
  return {version: 1, revision: data.revision, controller, capturePending: data.capturePending, speakerConfirmationRequired: data.speakerConfirmationRequired};
}
export const nativeControl: ControlClient = {
  async snapshot() {
    if (!NativeControl) {throw new Error('Native controls unavailable');}
    return decodeSnapshot(await NativeControl.getSnapshot());
  },
  async command(name, value = '') {
    if (!NativeControl) {throw new Error('Native controls unavailable');}
    return decodeSnapshot(await NativeControl.command(name, value));
  },
  subscribe(listener, failed) {
    if (!NativeControl) {return () => {};}
    const subscription = NativeControl.onSnapshot(source => {
      try {listener(decodeSnapshot(source));} catch {failed?.();}
    });
    return () => subscription.remove();
  },
};
