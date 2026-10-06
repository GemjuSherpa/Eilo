import { parseStateEvent, type StateEvent } from '@eilo/contracts';
import NativeControl from './specs/NativeEiloControl';
export interface ControlPreferences {
  version: 1;
  historyChoice: 'none' | 'private' | 'history';
  onboardingComplete: boolean;
  historyAvailable: boolean;
  historyEnabled: boolean;
  backgroundConsent: boolean;
  privateSession: boolean;
  volume: number;
}
export interface ControlSnapshot {
  version: 1;
  revision: number;
  controller: StateEvent;
  capturePending: boolean;
  speakerConfirmationRequired: boolean;
  preferences: ControlPreferences;
}
export type ControlCommand =
  | 'start'
  | 'stop'
  | 'confirmSpeaker'
  | 'history'
  | 'completeOnboarding'
  | 'background'
  | 'volume';
export interface ControlClient {
  snapshot(): Promise<ControlSnapshot>;
  command(name: ControlCommand, value?: string): Promise<ControlSnapshot>;
  subscribe(
    listener: (value: ControlSnapshot) => void,
    failed?: () => void,
  ): () => void;
}
export function decodeSnapshot(source: string): ControlSnapshot {
  if (source.length > 4096) {
    throw new Error('Native controls unavailable');
  }
  const value: unknown = JSON.parse(source);
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Native controls unavailable');
  }
  const data = value as Record<string, unknown>;
  if (
    Object.keys(data).sort().join(',') !==
      'capturePending,controller,preferences,revision,speakerConfirmationRequired,version' ||
    data.version !== 1 ||
    typeof data.revision !== 'number' ||
    !Number.isSafeInteger(data.revision) ||
    data.revision < 0 ||
    typeof data.capturePending !== 'boolean' ||
    typeof data.speakerConfirmationRequired !== 'boolean'
  ) {
    throw new Error('Native controls unavailable');
  }
  const controller = parseStateEvent(data.controller);
  if (!controller) {
    throw new Error('Native controls unavailable');
  }
  const raw = data.preferences;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    throw new Error('Native settings unavailable');
  }
  const preferences = raw as Record<string, unknown>;
  if (
    Object.keys(preferences).sort().join(',') !==
      'backgroundConsent,historyAvailable,historyChoice,historyEnabled,onboardingComplete,privateSession,version,volume' ||
    preferences.version !== 1 ||
    !['none', 'private', 'history'].includes(
      String(preferences.historyChoice),
    ) ||
    [
      'onboardingComplete',
      'historyAvailable',
      'historyEnabled',
      'backgroundConsent',
      'privateSession',
    ].some(key => typeof preferences[key] !== 'boolean') ||
    typeof preferences.volume !== 'number' ||
    !Number.isInteger(preferences.volume) ||
    preferences.volume < 0 ||
    preferences.volume > 100 ||
    (preferences.historyEnabled &&
      (!preferences.historyAvailable ||
        preferences.historyChoice !== 'history' ||
        preferences.privateSession)) ||
    (preferences.onboardingComplete && preferences.historyChoice === 'none')
  ) {
    throw new Error('Native settings unavailable');
  }
  const validated: ControlPreferences = {
    version: 1,
    historyChoice:
      preferences.historyChoice as ControlPreferences['historyChoice'],
    onboardingComplete: preferences.onboardingComplete as boolean,
    historyAvailable: preferences.historyAvailable as boolean,
    historyEnabled: preferences.historyEnabled as boolean,
    backgroundConsent: preferences.backgroundConsent as boolean,
    privateSession: preferences.privateSession as boolean,
    volume: preferences.volume,
  };
  return {
    version: 1,
    revision: data.revision,
    controller,
    capturePending: data.capturePending,
    speakerConfirmationRequired: data.speakerConfirmationRequired,
    preferences: validated,
  };
}
export const nativeControl: ControlClient = {
  async snapshot() {
    if (!NativeControl) {
      throw new Error('Native controls unavailable');
    }
    return decodeSnapshot(await NativeControl.getSnapshot());
  },
  async command(name, value = '') {
    if (!NativeControl) {
      throw new Error('Native controls unavailable');
    }
    return decodeSnapshot(await NativeControl.command(name, value));
  },
  subscribe(listener, failed) {
    if (!NativeControl) {
      return () => {};
    }
    const subscription = NativeControl.onSnapshot(source => {
      try {
        listener(decodeSnapshot(source));
      } catch {
        failed?.();
      }
    });
    return () => subscription.remove();
  },
};
