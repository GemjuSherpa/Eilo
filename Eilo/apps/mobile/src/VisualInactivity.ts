import { useCallback, useEffect, useRef, useState } from 'react';
import { AccessibilityInfo } from 'react-native';

export interface VisualActivity {
  speech: boolean;
  processing: boolean;
  loading: boolean;
  video: boolean;
  pinned: boolean;
}
const idleMs = 20000;
function visualTime(): number | null {
  const clock = (globalThis as unknown as { performance?: { now(): number } })
    .performance;
  if (!clock || typeof clock.now !== 'function') {
    return null;
  }
  const value = clock.now();
  return Number.isFinite(value) ? value : null;
}
/** Volatile display policy only; this module has no microphone/controller authority. */
export function useVisualInactivity(
  cardKey: string | null,
  revision: number,
  activity: VisualActivity,
  onHidden?: (key: string) => void,
) {
  const [screenReader, setScreenReader] = useState(true);
  const [focused, setFocused] = useState(false);
  const [interaction, setInteraction] = useState(0);
  const [hiddenKey, setHiddenKey] = useState<string | null>(null);
  const blocked =
    screenReader ||
    focused ||
    activity.speech ||
    activity.processing ||
    activity.loading ||
    activity.video ||
    activity.pinned;
  const latest = useRef({ cardKey, blocked, onHidden });
  latest.current = { cardKey, blocked, onHidden };
  const last = useRef({
    cardKey: null as string | null,
    revision: -1,
    interaction: -1,
    blocked: true,
    at: 0,
  });
  useEffect(() => {
    let attached = true;
    let changed = false;
    try {
      Promise.resolve(AccessibilityInfo.isScreenReaderEnabled())
        .then(enabled => {
          if (attached && !changed && typeof enabled === 'boolean') {
            setScreenReader(enabled);
          }
        })
        .catch(() => {});
    } catch {
      /* Unknown accessibility state conservatively keeps cards visible. */
    }
    const listener = AccessibilityInfo.addEventListener(
      'screenReaderChanged',
      enabled => {
        changed = true;
        if (enabled) {
          latest.current.blocked = true;
        }
        setScreenReader(enabled);
      },
    );
    return () => {
      attached = false;
      listener.remove();
    };
  }, []);
  useEffect(() => {
    const now = visualTime();
    if (now === null) {
      return;
    }
    if (
      last.current.cardKey !== cardKey ||
      last.current.revision !== revision ||
      last.current.interaction !== interaction ||
      last.current.blocked !== blocked
    ) {
      last.current = { cardKey, revision, interaction, blocked, at: now };
    }
    if (!cardKey || blocked || hiddenKey === cardKey) {
      return;
    }
    let timer: ReturnType<typeof setTimeout>;
    const check = () => {
      if (latest.current.cardKey !== cardKey || latest.current.blocked) {
        return;
      }
      const current = visualTime();
      if (current === null) {
        return;
      }
      const elapsed = current - last.current.at;
      if (elapsed < idleMs) {
        timer = setTimeout(check, Math.min(idleMs, idleMs - elapsed));
        return;
      }
      setHiddenKey(cardKey);
      latest.current.onHidden?.(cardKey);
    };
    timer = setTimeout(check, Math.max(0, idleMs - (now - last.current.at)));
    return () => clearTimeout(timer);
  }, [cardKey, revision, interaction, blocked, hiddenKey]);
  const interact = useCallback(() => {
    const current = visualTime();
    if (current !== null) {
      last.current.at = current;
    }
    setInteraction(value => value + 1);
  }, []);
  const focus = useCallback(() => {
    latest.current.blocked = true;
    setFocused(true);
    interact();
  }, [interact]);
  const blur = useCallback(() => {
    setFocused(false);
    interact();
  }, [interact]);
  const hide = useCallback(() => {
    if (cardKey && latest.current.cardKey === cardKey) {
      setHiddenKey(cardKey);
      latest.current.onHidden?.(cardKey);
    }
  }, [cardKey]);
  return {
    visible: !!cardKey && hiddenKey !== cardKey,
    interact,
    focus,
    blur,
    hide,
  };
}
