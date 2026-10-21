import { useEffect, useRef, useState } from 'react';
import { AppState, Text, View } from 'react-native';
import type { StateEvent } from '@eilo/contracts';
import type { ControlSnapshot } from './ControlClient';
import NativeControl from './specs/NativeEiloControl';
import { styles, type Colors } from './Onboarding';

type Identity = Pick<
  StateEvent,
  'sessionId' | 'operationId' | 'generation' | 'privacyEpoch'
>;
export interface SpokenPresentation extends Identity {
  version: 1;
  revision: number;
  cardId: string;
  clauses: string[];
  interrupted: boolean;
  earlierClausesOmitted: boolean;
}
export type PresentationReader = () => Promise<string>;
export const nativePresentationReader: PresentationReader = async () => {
  if (!NativeControl) {
    throw new Error('Presentation unavailable');
  }
  return NativeControl.command('presentation', '');
};
export function acknowledgeClearedPresentation(identity: Identity) {
  const tuple = [
    identity.sessionId,
    identity.operationId,
    identity.generation,
    identity.privacyEpoch,
  ];
  NativeControl?.command('presentationReady', JSON.stringify(tuple)).catch(
    () => {},
  );
}
export function samePresentationIdentity(a: Identity, b: Identity) {
  return (
    a.sessionId === b.sessionId &&
    a.operationId === b.operationId &&
    a.generation === b.generation &&
    a.privacyEpoch === b.privacyEpoch
  );
}
/** Separate volatile content envelope; the state-event schema remains content-free. */
export function decodePresentation(
  source: string,
  expected: Identity,
): SpokenPresentation {
  if (source.length > 32768) {
    throw new Error('Presentation unavailable');
  }
  const value: unknown = JSON.parse(source);
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Presentation unavailable');
  }
  const data = value as Record<string, unknown>;
  if (
    Object.keys(data).sort().join(',') !==
      'cardId,clauses,earlierClausesOmitted,generation,interrupted,operationId,privacyEpoch,revision,sessionId,version' ||
    data.version !== 1 ||
    !Number.isSafeInteger(data.revision) ||
    (data.revision as number) < 0 ||
    typeof data.interrupted !== 'boolean' ||
    typeof data.earlierClausesOmitted !== 'boolean' ||
    !Array.isArray(data.clauses) ||
    data.clauses.length > 32 ||
    data.clauses.some(
      text =>
        typeof text !== 'string' ||
        !text.trim() ||
        text.length > 1024 ||
        text.includes('\0'),
    ) ||
    data.clauses.reduce((sum, text) => sum + (text as string).length, 0) >
      4096 ||
    typeof data.cardId !== 'string' ||
    ((data.clauses.length > 0 || data.interrupted) &&
      !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(
        data.cardId,
      )) ||
    (data.cardId !== '' &&
      !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(
        data.cardId,
      )) ||
    !samePresentationIdentity(data as unknown as Identity, expected)
  ) {
    throw new Error('Presentation unavailable');
  }
  return data as unknown as SpokenPresentation;
}

export function useSpokenPresentation(
  snapshot: ControlSnapshot | null,
  blocked: boolean,
  reader: PresentationReader = nativePresentationReader,
) {
  const [foreground, setForeground] = useState(
    AppState.currentState === 'active',
  );
  const [value, setValue] = useState<SpokenPresentation | null>(null);
  const enabled =
    !!snapshot &&
    !blocked &&
    foreground &&
    snapshot.preferences.display.text &&
    !snapshot.preferences.display.voiceOnly &&
    ['standby', 'listening', 'thinking', 'speaking', 'error'].includes(
      snapshot.controller.state,
    );
  const latest = useRef({ snapshot, enabled });
  latest.current = { snapshot, enabled };
  useEffect(() => {
    const listener = AppState.addEventListener('change', state => {
      if (state !== 'active') {
        latest.current.enabled = false;
        setValue(null);
      }
      setForeground(state === 'active');
    });
    return () => listener.remove();
  }, []);
  const identity = snapshot?.controller;
  useEffect(() => {
    let attached = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    setValue(null);
    if (!enabled || !identity) {
      return;
    }
    const poll = async () => {
      try {
        const source = await reader();
        const current = latest.current;
        if (
          !attached ||
          !current.enabled ||
          !current.snapshot ||
          !samePresentationIdentity(identity, current.snapshot.controller)
        ) {
          return;
        }
        const incoming = decodePresentation(source, identity);
        setValue(previous =>
          !previous || incoming.revision >= previous.revision
            ? incoming
            : previous,
        );
      } catch {
        if (attached) {
          setValue(null);
        }
      } finally {
        if (attached && latest.current.enabled) {
          timer = setTimeout(poll, 250);
        }
      }
    };
    poll();
    return () => {
      attached = false;
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [enabled, identity, reader]);
  return enabled &&
    identity &&
    value &&
    samePresentationIdentity(value, identity)
    ? value
    : null;
}

export function SpokenReply({
  value,
  colors,
}: {
  value: SpokenPresentation | null;
  colors: Colors;
}) {
  if (!value || (!value.clauses.length && !value.interrupted)) {
    return null;
  }
  return (
    <View testID="spoken-reply" accessibilityLiveRegion="polite">
      <Text
        accessibilityRole="header"
        style={[styles.body, { color: colors.text }]}
      >
        Spoken reply
      </Text>
      {value.earlierClausesOmitted && (
        <Text style={[styles.body, { color: colors.secondary_text }]}>
          Showing the most recent completed clauses.
        </Text>
      )}
      {value.clauses.length > 0 && (
        <Text selectable style={[styles.body, { color: colors.text }]}>
          {value.clauses.join(' ')}
        </Text>
      )}
      {value.interrupted && (
        <Text style={[styles.body, { color: colors.secondary_text }]}>
          Reply interrupted. Unfinished words are omitted.
        </Text>
      )}
    </View>
  );
}
